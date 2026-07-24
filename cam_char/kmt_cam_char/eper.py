"""Serial CTE via EPER (Extended Pixel Edge Response) and the saturation
level from the ramp-top frames.

EPER on the mock64 layout: data columns [0:1152] preserve the legacy
readout column order and the first 32 overscan columns are the REAL serial
overscan, so the deferred-charge staircase right after the last data column
is intact. CTI = Q_deferred / (Q_last_col * N_transfer), N_transfer = 1179
(1152 data + 27 legacy prescan transfers to the sense node).

SATURAT: from the saturation-probe frames (ramp top): per amp the plateau
value of the top 0.1% pixels when the amp actually saturates; otherwise an
upper bound (not reached) so the placeholder stays.
"""
from __future__ import annotations

import numpy as np

from .core import N_TRANSFER_SERIAL, OVSC_REAL

EPER_DEFER_COLS = 3          # overscan columns summed as deferred charge
EPER_BASE_COLS = 10          # trailing real-overscan columns = baseline
SAT_PLATEAU_MIN = 63000.0    # raw p99.9 above this: amp saturated in frame


def eper_serial(exp, extname: str) -> dict:
    """Serial EPER from one bright (non-saturated) flat frame."""
    arr = np.asarray(exp.hdul[extname].section[:, 1100:1184], dtype=np.float64)
    arr = np.where(arr < 0, arr + 65536.0, arr)
    prof = arr.mean(axis=0)                       # cols 1100..1183
    data_last = float(prof[51])                   # col 1151 (last data col)
    ovsc = prof[52:52 + (OVSC_REAL.stop - OVSC_REAL.start)]   # 32 real cols
    base = float(np.mean(ovsc[-EPER_BASE_COLS:]))
    q_def = float(np.sum(ovsc[:EPER_DEFER_COLS] - base))
    q_img = data_last - base
    if q_img <= 0:
        return {"status": "NO_SIGNAL"}
    cti = max(q_def, 0.0) / (q_img * N_TRANSFER_SERIAL)
    return {
        "status": "OK",
        "cti_serial": float(cti),
        "cte_serial": float(1.0 - cti),
        "q_deferred_adu": q_def,
        "q_lastcol_adu": q_img,
    }


def saturation_level(exps: list, extname: str) -> dict:
    """Per-amp saturation plateau from the ramp-top frames (raw ADU)."""
    p999s = []
    plateaus = []
    for e in exps:
        a = np.asarray(e.hdul[extname].section[500:4100, 100:1050],
                       dtype=np.float64)
        a = np.where(a < 0, a + 65536.0, a)
        p999 = float(np.percentile(a, 99.9))
        p999s.append(p999)
        if p999 >= SAT_PLATEAU_MIN:
            top = a[a >= p999]
            plateaus.append(float(np.median(top)))
    if plateaus:
        sat = float(np.median(plateaus))
        return {"status": "MEASURED", "saturat_raw_adu": sat,
                "saturat_98pct": float(np.floor(0.98 * sat))}
    return {"status": "NOT_REACHED",
            "saturat_lower_bound_adu": float(max(p999s)) if p999s else 0.0}
