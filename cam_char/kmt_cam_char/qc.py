"""Legacy 32-amp frame QC and selection for the camera-characterization
baseline campaign (LEGACY-2026-06/07).

Runs on the ORIGINAL legacy MEFs (fast memmap section reads — no conversion
needed for screening). Per frame and per amplifier it measures a small
central band and the serial overscan, then classifies frames into roles
(bias / PTC ramp / repeat set / saturation probe) and produces the
selection + pathology census consumed by the measurement stage:

  - per-amp signal level, saturated fraction (band estimate)
  - per-amp overscan mean/rms, and after the scan a per-amp regression of
    overscan level vs signal level -> overscan-flooding census (the known
    legacy pathology: overscan follows the sky on some chips)
  - dead/weak channel census (flat response << chip median)
  - pair drift |ratio-1| between same-exposure consecutive flats (PTC pair
    usability)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits

BAND = (4500, 4700)          # rows of the measurement band (full-height strips)
SAT_ADU = 65000.0            # raw saturation screen level
DEAD_FRACTION = 0.10         # response < 10% of chip median -> DEAD
FLOOD_ADU_AT_50K = 5.0       # |overscan shift| at 50k ADU signal -> FLOODING
PAIR_DRIFT_MAX = 0.01        # |ratio-1| beyond this: pair unusable for PTC

_SEC = re.compile(r"\[(\d+):(\d+),(\d+):(\d+)\]")


def _sec(text):
    return tuple(int(v) for v in _SEC.match(str(text).replace(" ", "")).groups())


def scan_frame(path) -> dict:
    """Header info + per-amp band statistics from memmap section reads."""
    rec = {"file": str(path), "amps": {}}
    with fits.open(path, memmap=True, do_not_scale_image_data=True) as hdul:
        ph = hdul[0].header
        rec.update({
            "imagetyp": str(ph.get("IMAGETYP", "")).strip().upper(),
            "exptime": float(ph.get("EXPTIME", 0) or 0),
            "dateobs": str(ph.get("DATE-OBS", "")),
            "observat": str(ph.get("OBSERVAT", "")).strip().upper(),
            "n_ext": len(hdul) - 1,
        })
        y0, y1 = BAND
        for hdu in hdul[1:]:
            ext = str(hdu.header.get("EXTNAME", "")).strip()
            if len(ext) != 3 or ext[0] not in "MKNT":
                continue
            dx0, dx1, _, _ = _sec(hdu.header["DATASEC"])
            bx0, bx1, _, _ = _sec(hdu.header["BIASSEC"])
            band = np.asarray(hdu.section[y0:y1, dx0 - 1 + 60:dx1 - 60],
                              dtype=np.float64) % 65536      # unsigned view
            ovsc = np.asarray(hdu.section[y0:y1, bx0 - 1:bx1],
                              dtype=np.float64) % 65536
            # flooding metric uses the LAST overscan columns: the first
            # columns legitimately carry EPER deferred charge (~CTI*N*S,
            # tens of ADU at high signal) and must not be mistaken for the
            # overscan-follows-signal pathology
            tail = ovsc[:, -10:]
            rec["amps"][ext] = {
                "level": float(np.median(band)),
                "sat_frac": float(np.mean(band >= SAT_ADU)),
                "p999": float(np.percentile(band, 99.9)),
                "ovsc_mean": float(np.mean(ovsc)),
                "ovsc_tail": float(np.mean(tail)),
                "ovsc_rms": float(1.4826 * np.median(
                    np.abs(ovsc - np.median(ovsc)))),
                "gain_hdr": float(hdu.header.get("GAIN", 0) or 0),
                "rdnoise_hdr": float(hdu.header.get("RDNOISE", 0) or 0),
            }
    return rec


def analyze_night(frames: list[dict]) -> dict:
    """Classification, pathology census and selection for one site/night."""
    biases = [f for f in frames if f["imagetyp"] == "BIAS" or f["exptime"] == 0]
    flats = sorted([f for f in frames if f["imagetyp"] == "FLAT"
                    and f["exptime"] > 0], key=lambda f: (f["exptime"], f["file"]))
    by_exp: dict[float, list[dict]] = {}
    for f in flats:
        by_exp.setdefault(f["exptime"], []).append(f)
    repeat_exp = max(by_exp, key=lambda e: len(by_exp[e])) if by_exp else None

    amp_names = sorted(frames[0]["amps"]) if frames else []

    # dead/weak channels: response in the brightest usable flat, judged at
    # the frame with the highest LEVEL (max exptime can be the faint-lamp
    # regime in these dome sets)
    dead = []
    if flats:
        def lamp_of(f):
            return float(np.mean([f["amps"][a]["level"] for a in amp_names]))
        top = max(flats, key=lamp_of)
        meds = {c: np.median([top["amps"][a]["level"] for a in amp_names
                              if a.startswith(c)]) for c in "MKNT"}
        for a in amp_names:
            if top["amps"][a]["level"] < DEAD_FRACTION * meds[a[0]]:
                dead.append(a)

    # overscan-flooding census: per amp slope of the overscan TAIL level
    # (last columns; EPER-free) vs signal
    flooding = {}
    if len(flats) >= 4 and biases:
        for a in amp_names:
            sig = np.array([f["amps"][a]["level"] for f in flats])
            ovs = np.array([f["amps"][a]["ovsc_tail"] for f in flats])
            b0 = float(np.median([b["amps"][a]["ovsc_tail"] for b in biases]))
            ok = sig < SAT_ADU
            if ok.sum() >= 4 and np.ptp(sig[ok]) > 1000:
                slope = float(np.polyfit(sig[ok], ovs[ok] - b0, 1)[0])
                shift50k = slope * 5e4
                if abs(shift50k) > FLOOD_ADU_AT_50K:
                    flooding[a] = round(shift50k, 2)

    # pair drift within each exposure level (chip-M mean as lamp proxy)
    def lamp(f):
        vals = [f["amps"][a]["level"] for a in amp_names if a.startswith("M")]
        return float(np.mean(vals))

    pair_drift = {}
    for e, fl in by_exp.items():
        drifts = [abs(lamp(fl[i]) / lamp(fl[i + 1]) - 1.0)
                  for i in range(len(fl) - 1) if lamp(fl[i + 1]) > 0]
        pair_drift[e] = round(float(np.max(drifts)), 5) if drifts else None

    # saturation reach: does the ramp top saturate anywhere?
    sat_reached = bool(flats and any(
        f["amps"][a]["sat_frac"] > 1e-4 for f in by_exp[max(by_exp)]
        for a in amp_names))

    # selection: keep all structurally sound frames; roles by class
    def keep(f):
        return f["n_ext"] >= 32 and len(f["amps"]) >= 32

    # saturation probe = the highest-LEVEL exposure group (the max-exptime
    # group can be the faint-lamp regime in these two-regime dome sets)
    def group_level(e):
        return float(np.median([lamp(f) for f in by_exp[e]]))

    probe_exp = max(by_exp, key=group_level) if by_exp else None
    sel = {
        "bias": [f["file"] for f in biases if keep(f)],
        "ptc": [f["file"] for e, fl in by_exp.items() for f in fl if keep(f)],
        "repeat": [f["file"] for f in by_exp.get(repeat_exp, []) if keep(f)],
        "saturation_probe": [f["file"] for f in by_exp.get(probe_exp, [])
                             if keep(f)],
    }
    dropped = [f["file"] for f in frames if not keep(f)]
    return {
        "site": frames[0]["observat"] if frames else "",
        "n_frames": len(frames),
        "n_bias": len(biases),
        "exp_levels": {str(e): len(v) for e, v in sorted(by_exp.items())},
        "repeat_exp": repeat_exp,
        "levels_adu": {str(e): round(float(np.median(
            [lamp(f) for f in v])), 1) for e, v in sorted(by_exp.items())},
        "sat_reached": sat_reached,
        "dead_amps": dead,
        "flooding_amps": flooding,
        "pair_drift_max": pair_drift,
        "selection": sel,
        "dropped": dropped,
    }


def run_qc(night_dir, out_json) -> dict:
    files = sorted(Path(night_dir).glob("*.fits"))
    frames = []
    for p in files:
        try:
            frames.append(scan_frame(p))
        except Exception as err:
            frames.append({"file": str(p), "imagetyp": "UNREADABLE",
                           "exptime": -1, "n_ext": 0, "amps": {},
                           "error": str(err)[:80], "observat": "?",
                           "dateobs": ""})
    result = analyze_night([f for f in frames if f["amps"]])
    result["unreadable"] = [f["file"] for f in frames if not f["amps"]]
    result["frame_stats"] = frames
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


if __name__ == "__main__":
    night, out = sys.argv[1], sys.argv[2]
    r = run_qc(night, out)
    print(f"{night}: {r['n_frames']} frames, bias {r['n_bias']}, "
          f"levels {r['levels_adu']}, sat_reached={r['sat_reached']}, "
          f"dead={r['dead_amps']}, flooding={list(r['flooding_amps'])}")
