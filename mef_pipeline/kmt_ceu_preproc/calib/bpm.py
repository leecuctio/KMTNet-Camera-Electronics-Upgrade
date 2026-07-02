"""Bad pixel mask built from a master flat's normalized response."""
from __future__ import annotations

import numpy as np
from astropy.io import fits

from .. import MASK_BAD, PIPENAME, VERSION
from ..io_l1 import IncrementalMEFWriter, utcnow_iso
from .caldb import CalDB, MasterFile

LOW_RESPONSE = 0.5
HIGH_RESPONSE = 2.0


def build_bpm(flat_path, out_path, caldb: CalDB,
              low: float = LOW_RESPONSE, high: float = HIGH_RESPONSE,
              calver: str = "") -> dict:
    with MasterFile(flat_path) as flat:
        calver = calver or f"BPM-{flat.calver}"
        phdr = fits.Header()
        phdr["IMAGETYP"] = ("BPM", "bad pixel mask")
        phdr["CALTYPE"] = ("BPM", "calibration product type")
        phdr["CALVER"] = (calver, "calibration product version")
        phdr["CREATOR"] = (f"{PIPENAME}_{VERSION}", "creation program")
        phdr["DATE"] = (utcnow_iso(), "creation date")
        phdr["FLATFILE"] = (flat.name, "master flat used")
        phdr["RESPLOW"] = (low, "response below this is bad")
        phdr["RESPHIGH"] = (high, "response above this is bad")
        for k in ("OBSERVAT", "SITEID", "MOCKDATA"):
            if k in flat.header:
                phdr[k] = flat.header[k]
        counts = {}
        with IncrementalMEFWriter(out_path, phdr) as writer:
            for ext in flat.extnames():
                resp = flat.plane(ext)
                bad = ((resp < low) | (resp > high)).astype(np.uint8) * MASK_BAD
                hdr = fits.Header()
                hdr["EXTNAME"] = ext
                hdr["NBAD"] = (int(np.count_nonzero(bad)), "flagged pixels")
                writer.append_image(bad, hdr)
                counts[ext] = int(hdr["NBAD"])
            writer.finalize()
        site = str(flat.header.get("OBSERVAT", ""))
        dateobs = str(flat.header.get("DATE-OBS", ""))
        caldb.register(out_path, "BPM", site=site, dateobs=dateobs, calver=calver)
    return {"calver": calver, "n_bad": counts}
