"""KMT-CEU L0 64-amplifier MEF -> L1 CCD-level preprocessing pipeline.

Input : L0 amp raw MEF (kmt_ceu_archon_mknt_to_l0_amp_mef v2.1.x products,
        or mock64 products from kmt_ceu_legacy32_to_l0amp_mef v2.x).
Output: L1 CCD-level calibrated MEF
        PRIMARY + SCI_x for x in CHIPLIST + CALHIST table.
        The variance plane is fully reconstructible from SCI + calibration
        references (var = (RDNOISE^2 + SCI*flat)/flat^2), so it is omitted
        by default; --with-var re-enables it. MASK planes go to a separate
        .mask.mef.fits file, produced only with --mask-file (D-007).

Processing order follows KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md section 12:
overscan -> bias -> (dark) -> linearity/saturation -> crosstalk -> gain ->
flat -> bad pixel mask -> amp-boundary match (AMPMATCH) -> CCD assembly ->
astrometry against a reference catalog (WCSSOLVE flag on failure;
provenance in CALHIST).

All amplifier geometry is taken from the L0 headers/AMPINFO table
(DATASEC/BIASSEC/CCDSEC/DETSEC), so mock uniform DATA_LEFT packing and the
real ICD packing are both handled without code changes.
"""

VERSION = "v1.5"
PIPENAME = "kmt_ceu_preproc"

# L1 MASK bit definitions
MASK_BAD = 1        # bit0: bad pixel (BPM / unusable flat response)
MASK_SAT = 2        # bit1: at or above saturation level in raw ADU
MASK_NONLIN = 4     # bit2: above linearity limit (correction applied or not)
MASK_XTALK = 8      # bit3: significantly affected by crosstalk correction
MASK_SEAM = 16      # bit4: amplifier boundary pixel
MASK_NOOVSC = 32    # bit5: overscan fit unavailable for this row

MASK_BIT_DOC = [
    "MASK bits: 1=BAD 2=SATURATED 4=NONLINEAR 8=XTALK",
    "MASK bits: 16=AMP_SEAM 32=NO_OVERSCAN_FIT",
]
