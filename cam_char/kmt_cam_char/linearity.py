"""Linearity from the exposure-time ramp — adapted to what the legacy dome
sets actually contain (QC finding):

  - the lamp runs in TWO regimes (bright for the short exposures, faint for
    the long ones), so exptime -> signal is NOT one relation across the set;
  - the bright regime carries a large t-independent pedestal (illumination
    accumulated during the slow legacy readout), so the model is
        S(t) = A + R t          (A = pedestal, NOT a shutter offset)

The fit therefore uses only the longest contiguous run of levels (sorted by
exptime) whose signal increases monotonically — the bright-lamp ramp — and
the derived nonlinearity is valid over that signal range only (recorded as
[s_range_lo, s_range_hi]; for LINMAX purposes this is the range that
matters, the top end). A true shutter-offset measurement needs the lab
campaign's dedicated procedure; dome sets cannot provide it.

    NL(S) = S_meas / S_fit - 1
    NL(S) ~ a1 S + a2 S^2          correction-form fit (through origin)
    S_true = S_meas (1 - a1 S_meas - a2 S_meas^2)

LINMAX (raw ADU) = bias + largest bias-subtracted S with |NL| <= 1%.
"""
from __future__ import annotations

import numpy as np

NL_LIMIT = 0.01
SAT_GUARD_ADU = 60000.0
MIN_RUN_LEVELS = 4


def _bright_run(levels: list[dict]) -> list[dict]:
    """Longest contiguous monotonically-increasing-S run in exptime order."""
    by_t = sorted(levels, key=lambda d: d["exptime"])
    best: list[dict] = []
    run: list[dict] = []
    for d in by_t:
        if not run or d["S"] > run[-1]["S"]:
            run.append(d)
        else:
            if len(run) > len(best):
                best = run
            run = [d]
    if len(run) > len(best):
        best = run
    return best


def fit_linearity(levels: list[dict], bias_adu: float) -> dict:
    """levels: [{'exptime', 'S' (bias-sub mean ADU), 'p999_raw'}] per level."""
    usable = [d for d in levels if d["S"] > 0]
    run = [d for d in _bright_run(usable) if d["p999_raw"] < SAT_GUARD_ADU]
    if len(run) < MIN_RUN_LEVELS:
        return {"status": "TOO_FEW_LEVELS", "n_levels": len(run)}
    S = np.array([d["S"] for d in run])
    t = np.array([d["exptime"] for d in run])
    # S = A + R t (A: readout-illumination pedestal of the dome setup)
    A = np.column_stack([np.ones(len(t)), t])
    (ped, rate), *_ = np.linalg.lstsq(A, S, rcond=None)
    if rate <= 0:
        return {"status": "BAD_FIT", "n_levels": len(run)}
    fit = ped + rate * t
    nl = S / fit - 1.0
    B = np.column_stack([S, S ** 2])
    (a1, a2), *_ = np.linalg.lstsq(B, nl, rcond=None)
    grid = np.linspace(S.min(), S.max(), 2048)
    nl_grid = np.abs(a1 * grid + a2 * grid ** 2)
    ok = nl_grid <= NL_LIMIT
    linmax_sub = float(grid[ok][-1]) if ok.any() else float(S.min())
    return {
        "status": "OK",
        "n_levels": len(run),
        "rate_adu_s": float(rate),
        "pedestal_adu": float(ped),
        "lin_a1": float(a1),
        "lin_a2": float(a2),
        "nl_max_pct": float(np.max(np.abs(nl)) * 100.0),
        "resid_pct": float(np.std(nl) * 100.0),   # incl. lamp-drift systematic
        "linmax_raw_adu": float(linmax_sub + bias_adu),
        "linmax_note": "ramp-limited" if bool(ok.all()) else "measured",
        "s_range_lo": float(S.min() + bias_adu),
        "s_range_hi": float(S.max() + bias_adu),
    }
