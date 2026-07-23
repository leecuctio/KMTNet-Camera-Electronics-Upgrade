"""Per-CCD sky background model (measure by default, subtract on request).

A mesh of clipped box medians (background.py) models the smooth sky across
the assembled CCD. The default mode only *measures* (SKYLVL/SKYRMS/SKYGRADX/
SKYGRADY keywords + QA) and leaves the sky in the science pixels, preserving
Poisson statistics for downstream difference imaging; --sky sub subtracts the
model (SKYSUB=T). Crowded-bulge caveat: in KMTNet bulge fields the "sky"
includes unresolved starlight, so the model is a background estimate, not a
zodiacal/airglow measurement."""
from __future__ import annotations

import numpy as np

from .. import MASK_BAD, MASK_CR, MASK_NONLIN, MASK_SAT
from ..background import bilinear_expand, mesh_medians
from . import CalHistRow

SKY_BOX = 256
SKY_EXCLUDE = MASK_BAD | MASK_SAT | MASK_NONLIN | MASK_CR


def sky_model(sci: np.ndarray, mask: np.ndarray | None, box: int = SKY_BOX,
              subtract: bool = False) -> dict:
    """Measure (and optionally subtract, in place) the mesh sky model.

    Returns {'sky_med_e', 'sky_rms_e', 'grad_x_e', 'grad_y_e',
             'mesh_min_e', 'mesh_max_e', 'subtracted'}."""
    ny, nx = sci.shape
    mesh = mesh_medians(sci, mask, box, exclude_bits=SKY_EXCLUDE)
    med = float(np.median(mesh))
    # residual RMS about the model, on a sparse pixel grid
    rows = np.arange(0, ny, 16)
    model_rows = bilinear_expand(mesh, ny, nx, box, rows=rows)
    resid = sci[rows][:, ::16].astype(np.float64) - model_rows[:, ::16]
    if mask is not None:
        good = (mask[rows][:, ::16] & SKY_EXCLUDE) == 0
        resid = resid[good] if good.any() else resid.ravel()
    rms = float(1.4826 * np.median(np.abs(resid - np.median(resid))))
    # large-scale gradient: median first-vs-last mesh column/row difference
    grad_x = float(np.median(mesh[:, -1] - mesh[:, 0])) if mesh.shape[1] > 1 else 0.0
    grad_y = float(np.median(mesh[-1, :] - mesh[0, :])) if mesh.shape[0] > 1 else 0.0
    if subtract:
        # materialize the model in row blocks to bound memory
        step = 1024
        for y0 in range(0, ny, step):
            rr = np.arange(y0, min(y0 + step, ny))
            sci[rr, :] -= bilinear_expand(mesh, ny, nx, box, rows=rr)
    return {
        "sky_med_e": med,
        "sky_rms_e": rms,
        "grad_x_e": grad_x,
        "grad_y_e": grad_y,
        "mesh_min_e": float(mesh.min()),
        "mesh_max_e": float(mesh.max()),
        "subtracted": bool(subtract),
    }


def sky_calhist(mode: str, chip_stats: dict[str, dict]) -> CalHistRow:
    if mode == "off" or not chip_stats:
        return CalHistRow("SKYMODEL", False, params="disabled")
    med = np.median([s["sky_med_e"] for s in chip_stats.values()])
    sub = any(s["subtracted"] for s in chip_stats.values())
    return CalHistRow("SKYMODEL", True,
                      params=f"mesh box={SKY_BOX}, median sky {med:.1f} e-, "
                             f"{'subtracted' if sub else 'measured only'}")
