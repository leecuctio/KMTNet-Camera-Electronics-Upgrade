"""KMTNet-CEU camera characterization analysis package (lab campaign).

Modules land here alongside the lab campaign (PTC/read noise/linearity/
crosstalk/EPER/stability). Import the preprocessing package for all L0
access instead of re-implementing readers:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mef_pipeline"))
    from kmt_ceu_preproc.io_l0 import L0Exposure
    from kmt_ceu_preproc.steps.overscan import correct_overscan

Deliverable formats: see ../results/README.md; measurement plan: see
../KMTNet_CCD_Lab_Characterization_Plan_v1.0.md.
"""

VERSION = "v0.1"
