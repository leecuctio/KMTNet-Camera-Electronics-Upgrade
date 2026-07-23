"""Mesh-based background estimation (SExtractor-style, pure numpy).

A coarse grid of sigma-clipped box medians is interpolated bilinearly to full
resolution. Used by the per-CCD sky model (steps/sky.py) and, with a larger
box, as the large-scale smoother for the illumination and fringe master
builders (calib/masters.py). Masked pixels are excluded from the box
statistics; boxes with too few usable pixels inherit the global median."""
from __future__ import annotations

import numpy as np

MIN_BOX_FRACTION = 0.05     # usable-pixel fraction below which a box is invalid
BOX_SUBSAMPLE = 2           # in-box subsampling for the median (speed)


def mesh_medians(arr: np.ndarray, mask: np.ndarray | None, box: int,
                 exclude_bits: int = 0xFF, clip: float = 3.0) -> np.ndarray:
    """Grid of clipped medians over box x box cells; NaN where unusable."""
    ny, nx = arr.shape
    gy = (ny + box - 1) // box
    gx = (nx + box - 1) // box
    mesh = np.full((gy, gx), np.nan, dtype=np.float64)
    s = BOX_SUBSAMPLE
    for i in range(gy):
        ys = slice(i * box, min((i + 1) * box, ny))
        for j in range(gx):
            xs = slice(j * box, min((j + 1) * box, nx))
            sub = arr[ys, xs][::s, ::s]
            if mask is not None:
                good = (mask[ys, xs][::s, ::s] & exclude_bits) == 0
                vals = sub[good]
            else:
                vals = sub.ravel()
            if vals.size < max(16, int(MIN_BOX_FRACTION * sub.size)):
                continue
            med = float(np.median(vals))
            sig = 1.4826 * float(np.median(np.abs(vals - med)))
            if sig > 0:
                vals = vals[np.abs(vals - med) <= clip * sig]
                if vals.size:
                    med = float(np.median(vals))
            mesh[i, j] = med
    if np.isnan(mesh).any():
        fill = np.nanmedian(mesh) if np.isfinite(mesh).any() else 0.0
        mesh = np.where(np.isnan(mesh), fill, mesh)
    return mesh


def bilinear_expand(mesh: np.ndarray, ny: int, nx: int, box: int,
                    rows: np.ndarray | None = None) -> np.ndarray:
    """Interpolate box-center mesh values to pixel resolution (float32).

    rows: optional 1-D array of row indices to evaluate (returns len(rows), nx);
    None evaluates the full image."""
    gy, gx = mesh.shape
    y_idx = np.arange(ny, dtype=np.float64) if rows is None \
        else np.asarray(rows, dtype=np.float64)
    x_idx = np.arange(nx, dtype=np.float64)
    fy = np.clip((y_idx - 0.5 * box + 0.5) / box, 0.0, gy - 1.0)
    fx = np.clip((x_idx - 0.5 * box + 0.5) / box, 0.0, gx - 1.0)
    iy0 = np.minimum(fy.astype(int), gy - 2) if gy > 1 else np.zeros(len(fy), int)
    ix0 = np.minimum(fx.astype(int), gx - 2) if gx > 1 else np.zeros(len(fx), int)
    wy = (fy - iy0)[:, None] if gy > 1 else np.zeros((len(fy), 1))
    wx = (fx - ix0)[None, :] if gx > 1 else np.zeros((1, len(fx)))
    iy1 = np.minimum(iy0 + 1, gy - 1)
    ix1 = np.minimum(ix0 + 1, gx - 1)
    m00 = mesh[np.ix_(iy0, ix0)]
    m01 = mesh[np.ix_(iy0, ix1)]
    m10 = mesh[np.ix_(iy1, ix0)]
    m11 = mesh[np.ix_(iy1, ix1)]
    out = (m00 * (1 - wy) * (1 - wx) + m01 * (1 - wy) * wx
           + m10 * wy * (1 - wx) + m11 * wy * wx)
    return out.astype(np.float32)


def block_smooth(arr: np.ndarray, box: int, mask: np.ndarray | None = None,
                 exclude_bits: int = 0xFF, clip: float = 3.0) -> np.ndarray:
    """Large-scale surface: clipped box-median mesh, bilinearly expanded."""
    mesh = mesh_medians(arr, mask, box, exclude_bits=exclude_bits, clip=clip)
    return bilinear_expand(mesh, arr.shape[0], arr.shape[1], box)
