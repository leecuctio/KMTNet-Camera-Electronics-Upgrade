#!/usr/bin/env python3
"""Build a spec-conformant Archon raw PAIR carrying a real star field.

ics_sim writes bias level + read noise only, so there is no raw-level scene
generator in the tree.  This paints stars into the raw Archon pixel layout by
INVERTING the converter's geometry independently of it:

    amp active pixel (i, j)  ->  mosaic (DETSEC.x1 + i-1, DETSEC.y1 + j-1)
                             ->  raw    (RAWDATA.x1 + i-1, RAWY.y1 + j-1)

so if the converter's packing were wrong, the stars would come out of the MEF
discontinuous at the amp seams.

The header is the existing sample's, verbatim, with only the cards a star
field changes (IMAGETYP/OBJECT/EXPTIME/RA/DEC).  That keeps every other card
spec-conformant and keeps the converter's raw cross-checks meaningful.

The TRUE sky differs from the TCS pointing the header reports, so the L1 fit
has a real correction to find.
"""
import sys, numpy as np
from pathlib import Path
from astropy.io import fits
from astropy.wcs import WCS

# --- raw packing geometry (raw spec 4.2/4.3), stated here independently ----
RAW_NX, RAW_NY = 19200, 9400
TILE, ACTIVE_X, OVSC_X = 1200, 1152, 48
ACTIVE_Y = 4616
CCD_COLS, CCD_ROWS = 9216, 9232
GAP_COLS, GAP_ROWS = 460, 933
CHIP_X0 = {"M": 1, "K": CCD_COLS + GAP_COLS + 1, "N": 1, "T": CCD_COLS + GAP_COLS + 1}
CHIP_Y0 = {"M": CCD_ROWS + GAP_ROWS + 1, "K": CCD_ROWS + GAP_ROWS + 1, "N": 1, "T": 1}
PIX_SCALE = 0.395
BORESIGHT_X, BORESIGHT_Y = 9418.0, 9699.0
TAG_CHIPS = {"MK": ("M", "K"), "NT": ("N", "T")}

def strip_id(a): return ((a - 1) % 8) + 1
def is_bias_right(a): return (1 <= a <= 4) or (9 <= a <= 12)

def raw_x_data(chip, amp, second):
    tile0 = (9600 if second else 0) + (strip_id(amp) - 1) * TILE
    return (tile0 + 1, tile0 + ACTIVE_X) if is_bias_right(amp) \
        else (tile0 + OVSC_X + 1, tile0 + TILE)

def raw_y(amp):
    return (RAW_NY - ACTIVE_Y + 1, RAW_NY) if amp <= 8 else (1, ACTIVE_Y)

def detsec(chip, amp):
    x1 = (strip_id(amp) - 1) * ACTIVE_X + 1
    y1 = ACTIVE_Y + 1 if amp <= 8 else 1
    return CHIP_X0[chip] + x1 - 1, CHIP_Y0[chip] + y1 - 1

# --- truth WCS: what the sky really is -------------------------------------
def mosaic_wcs(ra0, dec0, rot_deg=0.0, scale=1.0):
    h = fits.Header()
    h["NAXIS"], h["NAXIS1"], h["NAXIS2"] = 2, 18892, 19397
    h["CTYPE1"], h["CTYPE2"] = "RA---TAN", "DEC--TAN"
    h["CRVAL1"], h["CRVAL2"] = ra0, dec0
    h["CRPIX1"], h["CRPIX2"] = BORESIGHT_X, BORESIGHT_Y
    s = PIX_SCALE / 3600.0 * scale
    r = np.radians(rot_deg)
    cd = np.array([[-s, 0.0], [0.0, s]]) @ np.array([[np.cos(r), -np.sin(r)],
                                                     [np.sin(r),  np.cos(r)]])
    (h["CD1_1"], h["CD1_2"]), (h["CD2_1"], h["CD2_2"]) = cd
    return h

def main():
    out_dir = Path(sys.argv[1]); out_dir.mkdir(parents=True, exist_ok=True)
    src = Path(sys.argv[2])                      # sample MK raw, header donor
    nstar = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
    rng = np.random.default_rng(20260923)

    # TRUE pointing, and the TCS pointing the header will claim (offset).
    ra_true, dec_true = 198.150000, 1.400000
    truth = mosaic_wcs(ra_true, dec_true, rot_deg=0.18, scale=1.003)
    wt = WCS(truth)
    d_ra, d_dec = 26.0 / 3600.0, -19.0 / 3600.0      # TCS error, arcsec -> deg
    ra_tcs = ra_true + d_ra / np.cos(np.radians(dec_true))
    dec_tcs = dec_true + d_dec

    # --- catalogue over the mosaic, in TRUE sky coordinates ---------------
    mx = rng.uniform(1, 18892, nstar); my = rng.uniform(1, 19397, nstar)
    ra, dec = wt.all_pix2world(mx, my, 1)
    # power-law-ish brightness, a few bright and many faint
    flux = 10 ** rng.uniform(2.6, 4.7, nstar)
    gmag = 25.0 - 2.5 * np.log10(flux)
    cat = Path(sys.argv[1]) / "refcat_truth.fits"
    fits.BinTableHDU.from_columns([
        fits.Column(name="RA", format="D", array=ra),
        fits.Column(name="DEC", format="D", array=dec),
        fits.Column(name="GMAG", format="E", array=gmag)]).writeto(cat, overwrite=True)

    hdr_src = fits.getheader(src)
    BIAS, RON, SKY, FWHM = 1000.0, 7.5, 420.0, 3.4
    sig = FWHM / 2.3548
    half = int(np.ceil(4 * sig))

    for tag in ("MK", "NT"):
        chips = TAG_CHIPS[tag]
        raw = np.empty((RAW_NY, RAW_NX), dtype=np.float32)
        raw[:] = rng.normal(BIAS, RON, raw.shape)          # overscan + all
        for ci, chip in enumerate(chips):
            for amp in range(1, 17):
                dx1, dy1 = detsec(chip, amp)
                # stars whose mosaic position lands in this amp (+ margin)
                sel = ((mx >= dx1 - half) & (mx <= dx1 + ACTIVE_X - 1 + half) &
                       (my >= dy1 - half) & (my <= dy1 + ACTIVE_Y - 1 + half))
                blk = rng.normal(BIAS + SKY, np.sqrt(RON ** 2 + SKY),
                                 (ACTIVE_Y, ACTIVE_X)).astype(np.float32)
                if sel.any():
                    lx = mx[sel] - dx1          # 0-based local float coords
                    ly = my[sel] - dy1
                    lf = flux[sel]
                    for x0, y0, f in zip(lx, ly, lf):
                        i0, i1 = int(max(0, np.floor(x0) - half)), int(min(ACTIVE_X, np.ceil(x0) + half + 1))
                        j0, j1 = int(max(0, np.floor(y0) - half)), int(min(ACTIVE_Y, np.ceil(y0) + half + 1))
                        if i1 <= i0 or j1 <= j0:
                            continue
                        gx = np.exp(-((np.arange(i0, i1) - x0) ** 2) / (2 * sig ** 2))
                        gy = np.exp(-((np.arange(j0, j1) - y0) ** 2) / (2 * sig ** 2))
                        blk[j0:j1, i0:i1] += (f / (2 * np.pi * sig ** 2)) * np.outer(gy, gx)
                rx1, rx2 = raw_x_data(chip, amp, second=(ci == 1))
                ry1, ry2 = raw_y(amp)
                raw[ry1 - 1:ry2, rx1 - 1:rx2] = blk
        data = np.clip(raw, 0, 65535).astype(np.uint16)

        h = hdr_src.copy()
        h["IMAGETYP"] = "OBJECT"
        h["OBJECT"] = "CEU-ASTROM-TEST"
        h["EXPTIME"] = 120
        h["RA"] = "%02d:%02d:%05.2f" % _hms(ra_tcs / 15.0)
        h["DEC"] = "%+03d:%02d:%04.1f" % _dms(dec_tcs)
        h["DETID"] = tag
        h["FILENAME"] = "KMTK.20260923.000501.%s" % tag
        h["EXPID"] = "KMTK.20260923.000501"
        # CHMAP_* must come from the member that owns those chips - raw spec
        # 5.9 lists it among the six cards that differ across the pair.
        own = fits.getheader(str(src).replace(".MK.", ".NT.") if tag == "NT" else src)
        for k in ("CHMAP_LT", "CHMAP_LB", "CHMAP_RT", "CHMAP_RB"):
            h[k] = own[k]
        p = out_dir / ("KMTK.20260923.000501.%s.fits" % tag)
        fits.PrimaryHDU(data=data, header=h).writeto(p, overwrite=True)
        print("wrote %s  (%d stars painted over the mosaic)" % (p.name, nstar))

    print("truth  : RA %.6f Dec %+.6f  rot 0.18 deg  scale 1.003" % (ra_true, dec_true))
    print("TCS hdr: RA %s DEC %s  (offset %+.1f\", %+.1f\")"
          % (h["RA"], h["DEC"], d_ra * 3600 * np.cos(np.radians(dec_true)), d_dec * 3600))
    print("refcat : %s" % cat.name)

def _hms(hours):
    h = int(hours); m = int((hours - h) * 60); s = (hours - h - m / 60) * 3600
    return h, m, s

def _dms(deg):
    sign = -1 if deg < 0 else 1; deg = abs(deg)
    d = int(deg); m = int((deg - d) * 60); s = (deg - d - m / 60) * 3600
    return sign * d, m, s

if __name__ == "__main__":
    main()
