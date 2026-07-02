"""Science-frame preprocessing chain (track A): L0 amp MEF -> L1 CCD MEF.

Order (keyword spec section 12): saturation/linearity flagging on raw ADU ->
overscan -> bias -> (dark) -> crosstalk -> gain -> flat -> BPM -> CCD assembly.
Amps are processed per controller group (the crosstalk coupling domain), so
peak memory stays at ~one group's planes plus one CCD's assembled planes."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import MASK_BAD, MASK_NOOVSC, MASK_SAT
from .geometry import ccd_detsec, fmtsec, section_slices
from .io_l0 import L0Exposure
from .io_l1 import (IncrementalMEFWriter, build_plane_header,
                    build_primary_header, calhist_hdu)
from .steps import CalHistRow
from .steps.ampmatch import match_amps
from .steps.assemble import assemble_ccd, ccd_wcs_cards, flag_seams, seam_metrics
from .steps.bias import bias_calhist, subtract_bias
from .steps.bpm import apply_bpm, bpm_calhist
from .steps.dark import dark_calhist
from .steps.flat import divide_flat, flat_calhist
from .steps.gain import to_electrons
from .steps.linearity import flag_nonlinear, linearity_calhist
from .steps.overscan import correct_overscan
from .steps.saturation import flag_saturation
from .steps.xtalk import apply_crosstalk
from .variance import init_variance, read_noise_e

L1_NAME_RE = re.compile(r"^(?P<prefix>[A-Za-z]+)\.(?P<date>\d{8})\.(?P<num>\d{6})\.")


@dataclass
class PipelineConfig:
    overscan_cols: int | None = None    # None: auto (32 for mock, all columns otherwise)
    overscan_smooth: int = 51
    overscan_clip: float = 3.0
    overscan_max_dev_adu: float = 100.0  # contamination guard vs master-bias OVSCLVL
    do_bias: bool = True
    do_dark: bool = False               # design doc open question #2: default off
    do_flat: bool = True
    do_bpm: bool = True
    with_var: bool = False              # VAR is reconstructible; omitted by default (D-007 amendment)
    ampmatch: str = "auto"              # amp-boundary harmonization: auto|multiplicative|additive|off
    ampmatch_width: int = 32            # boundary zone width [pixels]
    ampmatch_sky_min_e: float = 100.0   # auto: below this sky level use additive matching
    default_gain: float = 1.0           # used when GAIN is a placeholder (<= 0)
    min_flat_response: float = 0.1
    expected_amps: int | None = 64
    strict: bool = True
    compute_sha256: bool = True


def l1_name_for(l0_path) -> str:
    m = L1_NAME_RE.match(Path(l0_path).name)
    if m:
        return f"{m.group('prefix')}.{m.group('date')}.{m.group('num')}.ceu.l1ccd.mef.fits"
    stem = Path(l0_path).name.replace(".fits", "")
    return f"{stem}.l1ccd.fits"


def _ampmatch_calhist(config: "PipelineConfig", chip_planes: dict) -> CalHistRow:
    if config.ampmatch == "off":
        return CalHistRow("AMPMATCH", False, params="disabled")
    applied = [p["ampmatch"] for p in chip_planes.values()
               if p.get("ampmatch") and p["ampmatch"].applied]
    if not applied:
        return CalHistRow("AMPMATCH", False, params="no usable boundaries")
    modes = ",".join(sorted({a.mode for a in applied}))
    max_dev = max(a.max_deviation() for a in applied)
    return CalHistRow("AMPMATCH", True,
                      params=f"mode={modes}, width={config.ampmatch_width}, "
                             f"max_corr={max_dev:.4g}")


def _masked_stats(arr: np.ndarray, mask: np.ndarray) -> dict:
    sub = arr[::8, ::8]
    good = mask[::8, ::8] == 0
    vals = sub[good] if good.any() else sub.ravel()
    med = float(np.median(vals))
    mad = float(1.4826 * np.median(np.abs(vals - med)))
    return {"median_e": med, "mad_std_e": mad}


def process_exposure(l0_path, caldb, outdir, config: PipelineConfig | None = None,
                     force: bool = False) -> dict:
    """Process one L0 exposure to L1. Returns the QA record."""
    config = config or PipelineConfig()
    t0 = time.monotonic()
    outdir = Path(outdir)
    out_path = outdir / l1_name_for(l0_path)
    if out_path.exists() and not force:
        raise FileExistsError(f"Output exists: {out_path}; use force to overwrite")

    with L0Exposure(l0_path) as exp:
        issues = exp.validate(config.expected_amps)
        if issues and config.strict:
            raise ValueError(f"{exp.path.name}: L0 validation failed: {issues}")

        primary = exp.primary
        site = str(primary.get("OBSERVAT", "")).strip()
        filt = str(primary.get("FILTER", "")).strip()
        dateobs = str(primary.get("DATE-OBS", ""))
        ovsc_cols = config.overscan_cols
        if ovsc_cols is None and exp.is_mock:
            ovsc_cols = 32  # mock BIASSEC mirrors its trailing 16 columns

        bias = caldb.open("MBIAS", site=site, date=dateobs) if config.do_bias else None
        flat = caldb.open("MFLAT", site=site, filt=filt, date=dateobs) if config.do_flat else None
        bpm = caldb.open("BPM", site=site, date=dateobs) if config.do_bpm else None
        xmat, xen = exp.xtalk_matrix()

        qa: dict = {
            "l0_file": exp.path.name,
            "l1_file": out_path.name,
            "imagetyp": str(primary.get("IMAGETYP", "")),
            "object": str(primary.get("OBJECT", "")),
            "filter": filt,
            "exptime": float(primary.get("EXPTIME", 0.0) or 0.0),
            "date_obs": dateobs,
            "mock": exp.is_mock,
            "validation_issues": issues,
            "masters": {
                "bias": bias.name if bias else None,
                "flat": flat.name if flat else None,
                "bpm": bpm.name if bpm else None,
            },
            "amps": {},
            "ccds": {},
        }

        try:
            gain_all_measured = True
            xtalk_row = None
            n_ovsc_fallback = 0
            fallback_amps: set[str] = set()
            chip_planes: dict[str, dict] = {}

            for group in exp.ctrl_groups():
                sci_by: dict[str, np.ndarray] = {}
                mask_by: dict[str, np.ndarray] = {}
                ovsc_by: dict[str, dict] = {}
                for g in group:
                    raw = exp.read_amp(g.extname)
                    mask = np.zeros(g.data_shape, dtype=np.uint8)
                    n_sat, _ = flag_saturation(raw, g, mask)
                    n_nl = flag_nonlinear(raw, g, mask)
                    stats, _ = correct_overscan(
                        raw, g, use_cols=ovsc_cols,
                        clip=config.overscan_clip, smooth=config.overscan_smooth,
                        reference_level=(bias.ovsc_level(g.extname) if bias else None),
                        max_dev=config.overscan_max_dev_adu)
                    if stats["ovsc_fallback"]:
                        mask |= MASK_NOOVSC
                        n_ovsc_fallback += 1
                        fallback_amps.add(g.extname)
                    sci = np.ascontiguousarray(raw[section_slices(g.datasec)])
                    del raw
                    if bias is not None:
                        subtract_bias(sci, g.extname, bias)
                    sci_by[g.extname] = sci
                    mask_by[g.extname] = mask
                    ovsc_by[g.extname] = stats
                    qa["amps"][g.extname] = {**stats, "n_sat": n_sat, "n_nonlin": n_nl}

                row = apply_crosstalk(group, sci_by, xmat, xen, mask_by_ext=mask_by)
                if xtalk_row is None or row.applied:
                    xtalk_row = row

                var_by: dict[str, np.ndarray] = {}
                for g in group:
                    gval, measured = to_electrons(sci_by[g.extname], g, config.default_gain)
                    gain_all_measured &= measured
                    rn_e = read_noise_e(g.rdnoise, ovsc_by[g.extname]["ovsc_rms_adu"], gval)
                    var = init_variance(sci_by[g.extname], rn_e) if config.with_var else None
                    n_flatbad = 0
                    if flat is not None:
                        n_flatbad = divide_flat(sci_by[g.extname], var, mask_by[g.extname],
                                                g.extname, flat, config.min_flat_response)
                    n_bpm = 0
                    if bpm is not None:
                        n_bpm = apply_bpm(mask_by[g.extname], g.extname, bpm)
                    if var is not None:
                        var_by[g.extname] = var
                    qa["amps"][g.extname].update({
                        "gain_e_adu": gval, "gain_measured": measured,
                        "rn_e": rn_e, "n_flat_bad": n_flatbad, "n_bpm": n_bpm,
                    })

                for chip in [c for c in exp.chips if any(g.chip == c for g in group)]:
                    geoms = [g for g in group if g.chip == chip]
                    am = None
                    if config.ampmatch != "off":
                        # amps recovered via the OVSCLVL fallback carry additive
                        # baseline errors that can exceed the multiplicative cap:
                        # force additive matching anchored on the healthy amps
                        chip_fb = {g.extname for g in geoms} & fallback_amps
                        am = match_amps(
                            geoms, sci_by, mask_by,
                            mode="additive" if chip_fb else config.ampmatch,
                            width=config.ampmatch_width,
                            sky_min_e=config.ampmatch_sky_min_e,
                            max_add=2000.0 if chip_fb else 200.0,
                            anchor=({g.extname for g in geoms} - chip_fb) or None)
                        if am.applied and config.with_var and am.mode == "multiplicative":
                            for ext, factor in am.corrections.items():
                                if factor != 1.0:
                                    var_by[ext] *= np.float32(factor * factor)
                    sci_ccd = assemble_ccd(geoms, sci_by, np.float32)
                    var_ccd = assemble_ccd(geoms, var_by, np.float32) if config.with_var else None
                    mask_ccd = assemble_ccd(geoms, mask_by, np.uint8)
                    for g in geoms:
                        sci_by.pop(g.extname)
                        var_by.pop(g.extname, None)
                        mask_by.pop(g.extname)
                    seams = seam_metrics(sci_ccd, geoms, mask_ccd)
                    flag_seams(mask_ccd, geoms)
                    ref = geoms[0]
                    chip_planes[chip] = {
                        "sci": sci_ccd, "var": var_ccd, "mask": mask_ccd,
                        "seams": seams,
                        "ampmatch": am,
                        "wcs": ccd_wcs_cards(ref, exp.hdul[ref.extname].header),
                        "detsec": ccd_detsec(geoms),
                        "namps": len(geoms),
                    }
                    stats = _masked_stats(sci_ccd, mask_ccd)
                    qa["ccds"][chip] = {
                        **stats,
                        "seams_e": seams,
                        "seam_max_abs_e": max((abs(v) for v in seams.values()), default=0.0),
                        "n_sat": int(np.count_nonzero(mask_ccd & MASK_SAT)),
                        "n_bad": int(np.count_nonzero(mask_ccd & MASK_BAD)),
                        "ampmatch": ({"mode": am.mode, "sky_e": am.sky_e,
                                      "max_corr": am.max_deviation(),
                                      "corr": am.corrections}
                                     if am and am.applied else None),
                    }

            n_measured = sum(1 for a in qa["amps"].values() if a["gain_measured"])
            calhist = [
                CalHistRow("SATURATION", True, params="flagged on raw ADU (SATURAT)"),
                CalHistRow("OVERSCAN", True,
                           params=f"row-wise clipped mean, cols={ovsc_cols or 'all'}, "
                                  f"smooth={config.overscan_smooth}"
                                  + (f"; contaminated->OVSCLVL fallback: {n_ovsc_fallback} amps"
                                     if n_ovsc_fallback else "")),
                bias_calhist(bias),
                dark_calhist(None, config.do_dark),
                linearity_calhist(None),
                xtalk_row or CalHistRow("XTALK", False, params="no XTALKINFO"),
                CalHistRow("GAIN", True,
                           params=f"to electrons; measured {n_measured}/{len(qa['amps'])} amps"),
                flat_calhist(flat, config.min_flat_response),
                bpm_calhist(bpm),
                _ampmatch_calhist(config, chip_planes),
                CalHistRow("ASSEMBLE", True,
                           params="CCDSEC placement, CHIPFLP=None, approx WCS"),
            ]

            prov = {
                "l0file": exp.path.name,
                "l0sha256": exp.sha256() if config.compute_sha256 else "",
                "bias": (bias.name, bias.calver) if bias else ("", ""),
                "dark": ("", ""),
                "flat": (flat.name, flat.calver) if flat else ("", ""),
                "bpm": (bpm.name, bpm.calver) if bpm else ("", ""),
                "gainappl": gain_all_measured,
                "xtalkapl": bool(xtalk_row and xtalk_row.applied),
                "varincl": config.with_var,
                "bunit": "electron",
            }
            with IncrementalMEFWriter(out_path, build_primary_header(primary, prov)) as writer:
                for chip in exp.chips:
                    planes = chip_planes.pop(chip)
                    extras = [
                        ("DETSEC", fmtsec(*planes["detsec"]), "CCD placement in mosaic"),
                        ("NAMPS", planes["namps"], "amplifiers assembled"),
                        ("SEAMMAX", max((abs(v) for v in planes["seams"].values()), default=0.0),
                         "max |median seam step| [e-]"),
                    ]
                    am = planes["ampmatch"]
                    if am and am.applied:
                        extras.append(("AMMODE", am.mode, "amp-boundary match mode"))
                        for ext, val in am.corrections.items():
                            extras.append((f"AMC{ext}"[:8], val,
                                           "amp match factor" if am.mode == "multiplicative"
                                           else "amp match offset [e-]"))
                    extras += planes["wcs"]
                    writer.append_image(planes["sci"],
                                        build_plane_header("SCI", chip, extras))
                    if planes["var"] is not None:
                        writer.append_image(planes["var"], build_plane_header("VAR", chip))
                    writer.append_image(planes["mask"], build_plane_header("MASK", chip))
                    del planes
                writer.append_hdu(calhist_hdu(calhist))
                writer.finalize()
        finally:
            for m in (bias, flat, bpm):
                if m is not None:
                    m.close()

    qa["runtime_s"] = round(time.monotonic() - t0, 2)
    return qa
