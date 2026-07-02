"""Amp-boundary harmonization (AMPMATCH).

Even after overscan/bias/gain/flat, adjacent amplifiers can show visible
boundaries: residual gain errors (twilight-flat vs night-sky illumination
mismatch, gain drift since calibration) and residual bias offsets. This step
measures the sky in narrow unmasked zones on both sides of every internal
amp boundary of a CCD and solves a regularized least-squares chain for one
correction per amp, anchored so the CCD-average level is preserved.

Modes
  multiplicative : x_i = log(s_i), constraint x_a - x_b = log(m_b / m_a)
                   (residual scales with sky -> gain-like; the common case)
  additive       : x_i = offset_i, constraint x_a - x_b = m_b - m_a
                   (bias-like; used when the sky is too faint for ratios)
  auto           : multiplicative when the zone sky median >= sky_min_e,
                   else additive.

Fully-masked amps (e.g. a dead video channel) contribute no constraints and
receive no correction; disconnected amps stay at identity. Applied factors
are recorded per amp in the L1 SCI headers (AMC<extname>) and in QA JSON so
the correction is auditable and reversible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from .. import MASK_BAD, MASK_NONLIN, MASK_SAT
from ..geometry import AmpGeom

EXCLUDE_BITS = MASK_BAD | MASK_SAT | MASK_NONLIN
MIN_GOOD_PIX = 200      # minimum unmasked pixels per zone for a usable median
MAX_LOG_CORR = 0.1      # cap multiplicative correction at ~10%
MAX_ADD_CORR = 200.0    # cap additive correction [e-]
LAMBDA = 1e-3           # Tikhonov regularization (handles disconnected amps)


@dataclass
class AmpMatchResult:
    mode: str
    applied: bool
    sky_e: float
    corrections: dict[str, float] = field(default_factory=dict)

    def max_deviation(self) -> float:
        """Largest correction: |factor-1| (multiplicative) or |offset| (additive)."""
        if not self.corrections:
            return 0.0
        if self.mode == "multiplicative":
            return max(abs(v - 1.0) for v in self.corrections.values())
        return max(abs(v) for v in self.corrections.values())


def _overlap(a1, a2, b1, b2) -> bool:
    return not (a2 < b1 or b2 < a1)


def adjacent_pairs(geoms: list[AmpGeom]):
    """(left/lower amp, right/upper amp, axis) for every internal boundary."""
    pairs = []
    for a, b in combinations(geoms, 2):
        ax1, ax2, ay1, ay2 = a.ccdsec
        bx1, bx2, by1, by2 = b.ccdsec
        if ax2 + 1 == bx1 and _overlap(ay1, ay2, by1, by2):
            pairs.append((a, b, "x"))
        elif bx2 + 1 == ax1 and _overlap(ay1, ay2, by1, by2):
            pairs.append((b, a, "x"))
        elif ay2 + 1 == by1 and _overlap(ax1, ax2, bx1, bx2):
            pairs.append((a, b, "y"))
        elif by2 + 1 == ay1 and _overlap(ax1, ax2, bx1, bx2):
            pairs.append((b, a, "y"))
    return pairs


def _zone_median(zone: np.ndarray, zone_mask: np.ndarray) -> float | None:
    good = (zone_mask & EXCLUDE_BITS) == 0
    if np.count_nonzero(good) < MIN_GOOD_PIX:
        return None
    return float(np.median(zone[good]))


def _boundary_medians(a: AmpGeom, b: AmpGeom, axis: str, sci_by, mask_by, width: int):
    sa, sb = sci_by[a.extname], sci_by[b.extname]
    ma, mb = mask_by[a.extname], mask_by[b.extname]
    if axis == "x":
        w = max(2, min(width, sa.shape[1] // 2, sb.shape[1] // 2))
        za, zma = sa[:, -w:], ma[:, -w:]
        zb, zmb = sb[:, :w], mb[:, :w]
    else:
        w = max(2, min(width, sa.shape[0] // 2, sb.shape[0] // 2))
        za, zma = sa[-w:, :], ma[-w:, :]
        zb, zmb = sb[:w, :], mb[:w, :]
    return _zone_median(za, zma), _zone_median(zb, zmb)


def _solve(n: int, cons: list[tuple[int, int, float]], lam: float = LAMBDA,
           anchor_idx: list[int] | None = None) -> np.ndarray:
    if not cons:
        return np.zeros(n)
    A = np.zeros((len(cons), n))
    d = np.zeros(len(cons))
    for k, (i, j, dij) in enumerate(cons):
        A[k, i], A[k, j], d[k] = 1.0, -1.0, dij
    x = np.linalg.solve(A.T @ A + lam * np.eye(n), A.T @ d)
    involved = np.abs(A).sum(axis=0) > 0
    if involved.any():
        # zero-mean over trusted amps (or all involved amps) preserves level
        sel = [i for i in (anchor_idx or []) if involved[i]]
        base = x[sel].mean() if sel else x[involved].mean()
        x[involved] -= base
    x[~involved] = 0.0
    return x


def match_amps(geoms: list[AmpGeom], sci_by: dict, mask_by: dict,
               mode: str = "auto", width: int = 32,
               sky_min_e: float = 100.0, max_add: float = MAX_ADD_CORR,
               anchor: set[str] | None = None) -> AmpMatchResult:
    """Estimate and apply per-amp boundary corrections in place.

    anchor: extnames of trusted amps the zero-mean constraint is taken over
    (e.g. amps whose overscan was healthy); untrusted amps are then corrected
    onto the trusted level instead of dragging it."""
    index = {g.extname: i for i, g in enumerate(geoms)}
    stats = []
    meds = []
    for a, b, axis in adjacent_pairs(geoms):
        m_a, m_b = _boundary_medians(a, b, axis, sci_by, mask_by, width)
        if m_a is None or m_b is None:
            continue
        stats.append((index[a.extname], index[b.extname], m_a, m_b))
        meds += [m_a, m_b]
    if not stats:
        return AmpMatchResult(mode="none", applied=False, sky_e=0.0)

    sky = float(np.median(meds))
    use_mode = mode
    if mode == "auto":
        use_mode = "multiplicative" if sky >= sky_min_e else "additive"

    cons = []
    for i, j, m_a, m_b in stats:
        if use_mode == "multiplicative":
            if m_a > 0 and m_b > 0:
                cons.append((i, j, float(np.log(m_b / m_a))))
        else:
            cons.append((i, j, float(m_b - m_a)))
    if not cons:
        return AmpMatchResult(mode=use_mode, applied=False, sky_e=sky)

    anchor_idx = [index[e] for e in (anchor or set()) if e in index]
    cap = MAX_LOG_CORR if use_mode == "multiplicative" else max_add
    x = np.clip(_solve(len(geoms), cons, anchor_idx=anchor_idx), -cap, cap)

    corrections = {}
    for g in geoms:
        xi = float(x[index[g.extname]])
        if use_mode == "multiplicative":
            factor = float(np.exp(xi))
            if factor != 1.0:
                sci_by[g.extname] *= np.float32(factor)
            corrections[g.extname] = factor
        else:
            if xi != 0.0:
                sci_by[g.extname] += np.float32(xi)
            corrections[g.extname] = xi
    return AmpMatchResult(use_mode, True, sky, corrections)
