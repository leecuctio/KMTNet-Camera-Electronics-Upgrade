"""Master calibration frame builders (track B).

master bias: per amp, overscan-corrected trimmed planes sigma-clip stacked (ADU).
master flat: per filter; overscan+bias+gain corrected planes normalized per
frame by the chip-level illumination, stacked, then renormalized so each
chip's median response is 1.0. Amp-to-amp sensitivity differences are
preserved in the response so flat division also corrects gain residuals."""
from __future__ import annotations

import numpy as np
from astropy.io import fits

from .. import PIPENAME, VERSION
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
