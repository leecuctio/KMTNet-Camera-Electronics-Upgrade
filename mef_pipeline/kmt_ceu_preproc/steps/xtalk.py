"""Crosstalk correction from the L0 XTALKINFO 64x64 coefficient matrix.

Correction model: sci_corr[target] = sci[target] - sum_s coef[s, target] * sci[s],
computed from pre-correction copies. Coupling is confined to amps read by the
same controller, so the pipeline applies this per controller group.

While XTALKCAL=F (placeholder coefficients), this is a recorded no-op."""
from __future__ import annotations

import numpy as np

from .. import MASK_XTALK
from ..geometry import AmpGeom
from . import CalHistRow


def apply_crosstalk(group: list[AmpGeom], sci_by_ext: dict[str, np.ndarray],
                    matrix: np.ndarray | None, enabled: bool,
                    flag_threshold_adu: float = 1.0,
                    mask_by_ext: dict[str, np.ndarray] | None = None) -> CalHistRow:
    if not enabled or matrix is None:
        return CalHistRow("XTALK", False, params="XTALKCAL=F (placeholder coefficients)")
    ids = [g.ampid for g in group]
    sub = matrix[np.ix_([i - 1 for i in ids], [i - 1 for i in ids])]
    if not np.any(sub):
        return CalHistRow("XTALK", False, params="all in-group coefficients zero")
    originals = {g.extname: sci_by_ext[g.extname].copy() for g in group}
    for jt, gt in enumerate(group):
        corr = np.zeros_like(sci_by_ext[gt.extname])
        for js, gs in enumerate(group):
            c = sub[js, jt]
            if c and gs.extname != gt.extname:
                corr += np.float32(c) * originals[gs.extname]
        if np.any(corr):
            sci_by_ext[gt.extname] -= corr
            if mask_by_ext is not None:
                mask_by_ext[gt.extname][np.abs(corr) >= flag_threshold_adu] |= MASK_XTALK
    return CalHistRow("XTALK", True, params=f"in-group 64x64 coefficients, {len(group)} amps")
