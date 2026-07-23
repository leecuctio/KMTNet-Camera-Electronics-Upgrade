"""Master calibration frame builders (track B).

master bias: per amp, overscan-corrected trimmed planes sigma-clip stacked (ADU).
master flat: per filter; overscan+bias+gain corrected planes normalized per
frame by the chip-level illumination, stacked, then renormalized so each
chip's median response is 1.0. Amp-to-amp sensitivity differences are
preserved in the response so flat division also corrects gain residuals.
master fringe: per filter; small-scale sky-normalized residual pattern of
flat-fielded science frames, clip-stacked across different pointings
(fraction-of-sky planes; v1.6).
master illumination: per filter; block-median-smoothed large-scale
sky response of flat-fielded science frames of different pointings,
chip median response renormalized to 1.0 (v1.6)."""
from __future__ import annotations

import numpy as np
from astropy.io import fits

from .. import PIPENAME, VERSION
from ..background import block_smooth
from ..geometry import AmpGeom, section_slices
from ..io_l0 import L0Exposure
from ..io_l1 import IncrementalMEFWriter, utcnow_iso
from ..steps.gain import to_electrons
from ..steps.overscan import correct_overscan
from .caldb import CalDB, MasterFile


def clipped_mean_stack(stack: np.ndarray, clip: float = 3.0) -> np.ndarray:
    """Sigma-clipped mean along axis 0 (MAD-based sigma)."""
    med = np.median(stack, axis=0)
    sig = 1.4826 * np.median(np.abs(stack - med), axis=0)
    good = np.abs(stack - med) <= np.maximum(clip * sig, 1e-6)
    cnt = good.sum(axis=0)
    mean = np.where(good, stack, 0.0).sum(axis=0) / np.maximum(cnt, 1)
    return np.where(cnt > 0, mean, med).astype(np.float32)


def _corrected_plane(exp: L0Exposure, geom: AmpGeom, config,
                     reference_level: float | None = None) -> tuple[np.ndarray, dict]:
    """Overscan-corrected, DATASEC-trimmed amp plane in ADU (float32)."""
    raw = exp.read_amp(geom.extname)
    use_cols = config.overscan_cols
    if use_cols is None and exp.is_mock:
        use_cols = 32  # trailing 16 of 48 mock overscan cols are mirrored
    stats, _ = correct_overscan(raw, geom, use_cols=use_cols,
                                clip=config.overscan_clip, smooth=config.overscan_smooth,
                                reference_level=reference_level,
                                max_dev=config.overscan_max_dev_adu)
    return np.ascontiguousarray(raw[section_slices(geom.datasec)]), stats


def _master_primary(caltype: str, exps: list[L0Exposure], calver: str,
                    extra=None) -> fits.Header:
    h = fits.Header()
    h["IMAGETYP"] = (f"M{caltype}", f"master {caltype.lower()} frame")
    h["CALTYPE"] = (caltype, "calibration product type")
    h["CALVER"] = (calver, "calibration product version")
    h["CREATOR"] = (f"{PIPENAME}_{VERSION}", "creation program")
    h["DATE"] = (utcnow_iso(), "creation date")
    h["NCOMBINE"] = (len(exps), "number of input exposures")
    first = exps[0].primary
    for k in ("OBSERVAT", "SITEID", "TELESCOP", "DATE-OBS", "MJD-OBS", "MOCKDATA"):
        if k in first:
            h[k] = first[k]
    for i, e in enumerate(exps, 1):
        h[f"INPUT{i:02d}"] = (e.path.name, "input L0 exposure")
    if extra:
        for key, value, comment in extra:
            h[key] = (value, comment)
    return h


def _check_imagetyp(exps: list[L0Exposure], expected: str) -> list[str]:
    warnings = []
    for e in exps:
        it = str(e.primary.get("IMAGETYP", "")).strip().upper()
        if it != expected:
            warnings.append(f"{e.path.name}: IMAGETYP={it!r} (expected {expected})")
    return warnings


def build_master_bias(inputs, out_path, caldb: CalDB, config,
                      calver: str = "") -> dict:
    exps = [L0Exposure(p) for p in inputs]
    try:
        warnings = _check_imagetyp(exps, "BIAS")
        date_tag = str(exps[0].primary.get("DATE-OBS", ""))[:10].replace("-", "")
        calver = calver or f"MB-{date_tag}-n{len(exps)}"
        phdr = _master_primary("BIAS", exps, calver)
        geoms_by_exp = [{g.extname: g for g in e.amps} for e in exps]
        stats = {}
        with IncrementalMEFWriter(out_path, phdr) as writer:
            for g in exps[0].amps:
                planes_stats = [_corrected_plane(e, gb[g.extname], config)
                                for e, gb in zip(exps, geoms_by_exp)]
                stack = np.stack([p for p, _ in planes_stats])
                ovsc_level = float(np.median([s["ovsc_mean_adu"] for _, s in planes_stats]))
                plane = clipped_mean_stack(stack, clip=3.0)
                del stack, planes_stats
                hdr = fits.Header()
                hdr["EXTNAME"] = g.extname
                hdr["BUNIT"] = ("ADU", "overscan-corrected bias level")
                hdr["BIASMED"] = (float(np.median(plane)), "median residual bias [ADU]")
                hdr["BIASRMS"] = (float(1.4826 * np.median(np.abs(plane - np.median(plane)))),
                                  "robust RMS of master bias [ADU]")
                hdr["OVSCLVL"] = (ovsc_level,
                                  "bias-epoch raw overscan level [ADU]")
                writer.append_image(plane, hdr)
                stats[g.extname] = {"med": hdr["BIASMED"], "rms": hdr["BIASRMS"],
                                    "ovsc_level": ovsc_level}
            writer.finalize()
        site = str(exps[0].primary.get("OBSERVAT", ""))
        caldb.register(out_path, "MBIAS", site=site,
                       dateobs=str(exps[0].primary.get("DATE-OBS", "")), calver=calver)
        return {"calver": calver, "warnings": warnings, "amps": stats}
    finally:
        for e in exps:
            e.close()


def build_master_flat(inputs, out_path, caldb: CalDB, config,
                      bias_path=None, calver: str = "") -> dict:
    exps = [L0Exposure(p) for p in inputs]
    bias = MasterFile(bias_path) if bias_path else None
    try:
        warnings = _check_imagetyp(exps, "FLAT")
        filters = {str(e.primary.get("FILTER", "")).strip() for e in exps}
        if len(filters) != 1:
            raise ValueError(f"Input flats span multiple filters: {sorted(filters)}")
        filt = filters.pop()
        geoms_by_exp = [{g.extname: g for g in e.amps} for e in exps]

        fallbacks: list[str] = []

        def corrected(e, geom):
            ref = bias.ovsc_level(geom.extname) if bias is not None else None
            plane, stats = _corrected_plane(e, geom, config, reference_level=ref)
            if stats["ovsc_fallback"]:
                fallbacks.append(f"{e.path.name}[{geom.extname}]")
            if bias is not None:
                plane -= bias.plane(geom.extname)
            to_electrons(plane, geom, config.default_gain)
            return plane

        # pass 1: per-exposure, per-chip illumination normalization
        norms = []
        for e, gb in zip(exps, geoms_by_exp):
            chip_meds: dict[str, list[float]] = {}
            for g in e.amps:
                med = float(np.median(corrected(e, gb[g.extname])[::8, ::8]))
                chip_meds.setdefault(g.chip, []).append(med)
            norms.append({c: float(np.median(m)) for c, m in chip_meds.items()})
        # pass 2: normalized stack per amp
        planes = {}
        for g in exps[0].amps:
            stack = np.stack([
                corrected(e, gb[g.extname]) / np.float32(norm[g.chip])
                for e, gb, norm in zip(exps, geoms_by_exp, norms)])
            planes[g.extname] = clipped_mean_stack(stack, clip=3.0)
            del stack
        # renormalize: chip median response -> 1.0
        chips = {}
        for g in exps[0].amps:
            chips.setdefault(g.chip, []).append(float(np.median(planes[g.extname][::8, ::8])))
        chip_norm = {c: float(np.median(m)) for c, m in chips.items()}
        date_tag = str(exps[0].primary.get("DATE-OBS", ""))[:10].replace("-", "")
        calver = calver or f"MF{filt}-{date_tag}-n{len(exps)}"
        phdr = _master_primary("FLAT", exps, calver, extra=[
            ("FILTER", filt, "filter of input flats"),
            ("CALBIAS", bias.name if bias else "", "master bias used"),
        ])
        stats = {}
        with IncrementalMEFWriter(out_path, phdr) as writer:
            for g in exps[0].amps:
                plane = planes.pop(g.extname) / np.float32(chip_norm[g.chip])
                hdr = fits.Header()
                hdr["EXTNAME"] = g.extname
                hdr["BUNIT"] = ("response", "normalized flat response")
                hdr["FLATMED"] = (float(np.median(plane)), "median response")
                writer.append_image(plane, hdr)
                stats[g.extname] = {"med": hdr["FLATMED"]}
            writer.finalize()
        site = str(exps[0].primary.get("OBSERVAT", ""))
        caldb.register(out_path, "MFLAT", site=site, filt=filt,
                       dateobs=str(exps[0].primary.get("DATE-OBS", "")), calver=calver)
        if fallbacks:
            warnings.append(f"overscan contamination fallback used: {sorted(set(fallbacks))}")
        return {"calver": calver, "filter": filt, "warnings": warnings,
                "chip_norm_e": chip_norm, "amps": stats}
    finally:
        if bias is not None:
            bias.close()
        for e in exps:
            e.close()


# --------------------------------------------------------------------------- #
# Sky-based masters (v1.6): fringe and illumination from science frames
# --------------------------------------------------------------------------- #

SKY_MASTER_MIN_FRAMES = 3
SKY_MASTER_SMOOTH_BOX = 128     # large-scale smoothing box [px]
SKY_MASTER_CLIP = 2.5           # star rejection in the frame stack


def _flatfielded_plane(exp: L0Exposure, geom: AmpGeom, config,
                       bias, flat) -> np.ndarray:
    """Overscan+bias corrected, gain-applied, flat-fielded amp plane [e-]."""
    ref = bias.ovsc_level(geom.extname) if bias is not None else None
    plane, _stats = _corrected_plane(exp, geom, config, reference_level=ref)
    if bias is not None:
        plane -= bias.plane(geom.extname)
    to_electrons(plane, geom, config.default_gain)
    if flat is not None:
        f = flat.plane(geom.extname)
        plane /= np.where(f > config.min_flat_response, f, np.float32(1.0))
    return plane


def _sky_master_prep(inputs, config, bias_path, flat_path):
    """Common setup for the fringe/illumination builders.

    Returns (exps, bias, flat, filt, chip_sky, warnings) where chip_sky is a
    per-exposure list of {chip: sky_e} normalizations (pass 1)."""
    if len(inputs) < SKY_MASTER_MIN_FRAMES:
        raise ValueError(f"need >= {SKY_MASTER_MIN_FRAMES} science frames, "
                         f"got {len(inputs)}")
    exps = [L0Exposure(p) for p in inputs]
    warnings = _check_imagetyp(exps, "OBJECT")
    filters = {str(e.primary.get("FILTER", "")).strip() for e in exps}
    if len(filters) != 1:
        for e in exps:
            e.close()
        raise ValueError(f"Inputs span multiple filters: {sorted(filters)}")
    filt = filters.pop()
    field_list = [str(e.primary.get("OBJECT", "")).strip() for e in exps]
    fields = set(field_list)
    if len(fields) < SKY_MASTER_MIN_FRAMES:
        warnings.append(
            f"only {len(fields)} distinct fields in {len(exps)} frames; "
            "per-field structure (stellar density gradients) may imprint")
    dupes = sorted({f for f in fields if field_list.count(f) > 1})
    if dupes:
        warnings.append(
            f"repeated pointings {dupes}: stars fall on the same pixels in "
            "every visit and survive the clipped stack - prefer one frame "
            "per field")
    bias = MasterFile(bias_path) if bias_path else None
    flat = MasterFile(flat_path) if flat_path else None
    if flat is None:
        warnings.append("built without a master flat (raw response mixed in)")
    # pass 1: per-exposure chip sky level [e-]
    chip_sky = []
    for e in exps:
        geoms = {g.extname: g for g in e.amps}
        meds: dict[str, list[float]] = {}
        for g in e.amps:
            plane = _flatfielded_plane(e, geoms[g.extname], config, bias, flat)
            meds.setdefault(g.chip, []).append(float(np.median(plane[::8, ::8])))
        chip_sky.append({c: max(float(np.median(m)), 1e-3) for c, m in meds.items()})
    return exps, bias, flat, filt, chip_sky, warnings


def build_master_fringe(inputs, out_path, caldb: CalDB, config,
                        bias_path=None, flat_path=None, calver: str = "",
                        box: int = SKY_MASTER_SMOOTH_BOX) -> dict:
    """Fraction-of-sky fringe pattern per amp, clip-stacked over frames."""
    exps, bias, flat, filt, chip_sky, warnings = _sky_master_prep(
        inputs, config, bias_path, flat_path)
    try:
        geoms_by_exp = [{g.extname: g for g in e.amps} for e in exps]
        date_tag = str(exps[0].primary.get("DATE-OBS", ""))[:10].replace("-", "")
        calver = calver or f"FR{filt}-{date_tag}-n{len(exps)}"
        phdr = _master_primary("FRINGE", exps, calver, extra=[
            ("FILTER", filt, "filter of input frames"),
            ("CALBIAS", bias.name if bias else "", "master bias used"),
            ("CALFLAT", flat.name if flat else "", "master flat used"),
            ("SMOOTHBX", box, "large-scale removal box [px]"),
        ])
        phdr["BUNIT"] = ("sky_fraction", "fringe amplitude per unit sky")
        amps_qa = {}
        with IncrementalMEFWriter(out_path, phdr) as writer:
            for g in exps[0].amps:
                def fringe_frame(e, gb, sky, _g=g):
                    p = _flatfielded_plane(e, gb[_g.extname], config, bias, flat)
                    return (p - block_smooth(p, box)) / np.float32(sky[_g.chip])
                stack = np.stack([fringe_frame(e, gb, sky)
                                  for e, gb, sky in zip(exps, geoms_by_exp, chip_sky)])
                plane = clipped_mean_stack(stack, clip=SKY_MASTER_CLIP)
                del stack
                amp_mad = float(1.4826 * np.median(np.abs(plane - np.median(plane))))
                hdr = fits.Header()
                hdr["EXTNAME"] = g.extname
                hdr["BUNIT"] = ("sky_fraction", "fringe amplitude per unit sky")
                hdr["FRNGAMP"] = (amp_mad, "robust amplitude [fraction of sky]")
                writer.append_image(plane, hdr)
                amps_qa[g.extname] = {"amp_mad": amp_mad}
            writer.finalize()
        site = str(exps[0].primary.get("OBSERVAT", ""))
        caldb.register(out_path, "MFRINGE", site=site, filt=filt,
                       dateobs=str(exps[0].primary.get("DATE-OBS", "")), calver=calver)
        med_amp = float(np.median([a["amp_mad"] for a in amps_qa.values()]))
        if med_amp < 1e-4:
            warnings.append(
                f"median template amplitude {med_amp:.2e} of sky: no measurable "
                "fringing; the run step will skip these amps")
        return {"calver": calver, "filter": filt, "warnings": warnings,
                "median_amp": med_amp, "amps": amps_qa}
    finally:
        if bias is not None:
            bias.close()
        if flat is not None:
            flat.close()
        for e in exps:
            e.close()


def build_master_illum(inputs, out_path, caldb: CalDB, config,
                       bias_path=None, flat_path=None, calver: str = "",
                       box: int = SKY_MASTER_SMOOTH_BOX) -> dict:
    """Smooth dark-sky illumination response per amp (chip median = 1)."""
    exps, bias, flat, filt, chip_sky, warnings = _sky_master_prep(
        inputs, config, bias_path, flat_path)
    try:
        geoms_by_exp = [{g.extname: g for g in e.amps} for e in exps]
        # pass 2: sky-normalized clip-stack, then large-scale smoothing
        planes = {}
        for g in exps[0].amps:
            stack = np.stack([
                _flatfielded_plane(e, gb[g.extname], config, bias, flat)
                / np.float32(sky[g.chip])
                for e, gb, sky in zip(exps, geoms_by_exp, chip_sky)])
            raw = clipped_mean_stack(stack, clip=SKY_MASTER_CLIP)
            del stack
            planes[g.extname] = block_smooth(raw, box)
        # renormalize: chip median response -> 1.0 (dense subsample: a sparse
        # one biases the median of a smooth gradient plane)
        chips: dict[str, list[float]] = {}
        for g in exps[0].amps:
            chips.setdefault(g.chip, []).append(
                float(np.median(planes[g.extname][::2, ::2])))
        chip_norm = {c: max(float(np.median(m)), 1e-6) for c, m in chips.items()}
        date_tag = str(exps[0].primary.get("DATE-OBS", ""))[:10].replace("-", "")
        calver = calver or f"IL{filt}-{date_tag}-n{len(exps)}"
        phdr = _master_primary("ILLUM", exps, calver, extra=[
            ("FILTER", filt, "filter of input frames"),
            ("CALBIAS", bias.name if bias else "", "master bias used"),
            ("CALFLAT", flat.name if flat else "", "master flat used"),
            ("SMOOTHBX", box, "block-median smoothing box [px]"),
        ])
        phdr["BUNIT"] = ("response", "normalized sky illumination response")
        amps_qa = {}
        with IncrementalMEFWriter(out_path, phdr) as writer:
            for g in exps[0].amps:
                plane = planes.pop(g.extname) / np.float32(chip_norm[g.chip])
                dev = float(np.max(np.abs(plane - 1.0)))
                hdr = fits.Header()
                hdr["EXTNAME"] = g.extname
                hdr["BUNIT"] = ("response", "normalized sky illumination response")
                hdr["ILLUMDEV"] = (dev, "max |response - 1|")
                writer.append_image(plane, hdr)
                amps_qa[g.extname] = {"max_dev": dev}
            writer.finalize()
        site = str(exps[0].primary.get("OBSERVAT", ""))
        caldb.register(out_path, "MILLUM", site=site, filt=filt,
                       dateobs=str(exps[0].primary.get("DATE-OBS", "")), calver=calver)
        max_dev = max(a["max_dev"] for a in amps_qa.values())
        if max_dev > 0.2:
            warnings.append(
                f"max |response-1| = {max_dev:.3f} (> 0.2): check field "
                "diversity/masking before using this master")
        return {"calver": calver, "filter": filt, "warnings": warnings,
                "max_dev": max_dev, "amps": amps_qa}
    finally:
        if bias is not None:
            bias.close()
        if flat is not None:
            flat.close()
        for e in exps:
            e.close()
