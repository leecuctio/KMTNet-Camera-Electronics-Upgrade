"""Read noise and bias level from bias-frame pairs (+ overscan cross-check).

RN_ADU = MAD-std(B1 - B2) / sqrt(2), median over non-overlapping pairs
(robust variant of the plan's formula; MAD kills CRs/defects). The serial
overscan RMS of the same frames — the quantity the preprocessing pipeline
falls back to when RDNOISE is a placeholder — is measured for cross-check.
"""
from __future__ import annotations

import numpy as np

from .core import mad_std, ovsc_raw, pairs, roi_raw


def measure_readnoise(bias_exps: list, extnames: list[str]) -> dict:
    """{ext: {'rn_adu','rn_adu_err','bias_adu','bias_drift_adu','ovsc_rms_adu'}}"""
    out = {}
    rois = {}       # per frame cache: {ext: roi}
    for ext in extnames:
        rns = []
        levels = []
        ovsc_rms = []
        for k, (e1, e2) in enumerate(pairs(bias_exps)):
            a1 = rois.setdefault((id(e1), ext), roi_raw(e1, ext))
            a2 = rois.setdefault((id(e2), ext), roi_raw(e2, ext))
            rns.append(mad_std(a1 - a2) / np.sqrt(2.0))
            levels += [float(np.median(a1)), float(np.median(a2))]
        for e in bias_exps:
            ov = ovsc_raw(e, ext)
            ovsc_rms.append(mad_std(ov - np.median(ov, axis=1, keepdims=True)))
        rns = np.array(rns)
        out[ext] = {
            "rn_adu": float(np.median(rns)),
            "rn_adu_err": float(1.2533 * np.std(rns, ddof=1)
                                / np.sqrt(len(rns))) if len(rns) > 1 else 0.0,
            "bias_adu": float(np.median(levels)),
            "bias_drift_adu": float(np.ptp(levels)),
            "ovsc_rms_adu": float(np.median(ovsc_rms)),
        }
        for key in list(rois):
            if key[1] == ext:
                del rois[key]
    return out
