"""Row-wise local overscan correction from each amp's BIASSEC."""
from __future__ import annotations

import numpy as np

from ..geometry import AmpGeom, section_slices
from . import CalHistRow


def sliding_median(a: np.ndarray, window: int) -> np.ndarray:
    """Odd-window running median with edge padding (no scipy dependency)."""
    if window <= 1 or a.size <= 2:
        return a
    window = min(window if window % 2 == 1 else window + 1, a.size | 1)
    pad = window // 2
    padded = np.pad(a, pad, mode="edge")
    view = np.lib.stride_tricks.sliding_window_view(padded, window)
    return np.median(view, axis=-1)


def row_levels(ovsc: np.ndarray, clip: float = 3.0) -> np.ndarray:
    """Sigma-clipped mean overscan level per row (MAD-based clipping)."""
    med = np.median(ovsc, axis=1)
    resid = ovsc - med[:, None]
    sigma = 1.4826 * np.median(np.abs(resid), axis=1)
    good = np.abs(resid) <= np.maximum(clip * sigma, 1e-6)[:, None]
    cnt = good.sum(axis=1)
    total = np.sum(np.where(good, ovsc, 0.0), axis=1)
    mean = np.where(cnt > 0, total / np.maximum(cnt, 1), med)
    return mean.astype(np.float64)


def correct_overscan(raw: np.ndarray, geom: AmpGeom, use_cols: int | None = None,
                     clip: float = 3.0, smooth: int = 51,
                     reference_level: float | None = None,
                     max_dev: float = 100.0) -> tuple[dict, CalHistRow]:
    """Subtract the smoothed row-wise overscan level from the full amp image.

    use_cols limits the fit to the first N BIASSEC columns (mock64 products
    mirror the trailing 16 of 48 overscan columns from real pixels, so those
    duplicated columns are excluded from the fit with use_cols=32).

    Contamination guard: some frames carry sky-level signal in the overscan
    region (seen in legacy data: an amp's overscan follows the sky instead of
    the bias). A row-wise fit would then subtract the sky along with the
    bias. When reference_level (the bias-epoch overscan level, OVSCLVL from
    the master bias) is given and the frame's overscan level deviates from it
    by more than max_dev ADU, the reference constant is subtracted instead
    and ovsc_fallback is set so the caller can flag the amp (MASK_NOOVSC).
    """
    ovsc = raw[section_slices(geom.biassec)]
    ncols = ovsc.shape[1]
    if use_cols and 0 < use_cols < ncols:
        ovsc = ovsc[:, :use_cols]
        ncols = use_cols
    level = row_levels(ovsc, clip=clip)
    level_s = sliding_median(level, smooth)
    frame_level = float(np.median(level_s))
    fallback = bool(reference_level is not None
                    and abs(frame_level - reference_level) > max_dev)
    # residuals must be taken before the in-place subtraction: ovsc is a view of raw
    resid = ovsc - level_s[:, None].astype(np.float32)
    if fallback:
        raw -= np.float32(reference_level)
    else:
        raw -= level_s[:, None].astype(np.float32)
    stats = {
        "ovsc_mean_adu": frame_level,
        "ovsc_rms_adu": float(np.std(resid)),
        "ovsc_cols_used": int(ncols),
        "ovsc_fallback": fallback,
        "ovsc_ref_adu": reference_level,
    }
    row = CalHistRow("OVERSCAN", True,
                     params=f"row-wise clipped mean, cols={ncols}, smooth={smooth}")
    return stats, row
