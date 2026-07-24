"""Per site-night measurement driver: mock64 frames -> amp characterization
CSV (results/README.md schema, LEGACY baseline campaign).

Usage:
    python3 cam_char/kmt_cam_char/runner.py QC_JSON MOCK64_DIR OUT_CSV

Reads the QC selection (legacy file paths), maps each legacy file to its
converted mock64 twin in MOCK64_DIR, and measures per mock amp (64 = 32
physical legacy amplifiers split TOP/BOT):
    read noise (bias pairs + overscan cross-check), PTC gain + curvature,
    linearity (bright-regime ramp), saturation, serial EPER CTE, PRNU,
    within-night gain stability.
STATUS carries the QC census (DEAD/FLOOD) and measurement health.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kmt_cam_char.core import open_l0, roi_raw          # noqa: E402
from kmt_cam_char.eper import eper_serial, saturation_level  # noqa: E402
from kmt_cam_char.linearity import fit_linearity        # noqa: E402
from kmt_cam_char.prnu import gain_series, measure_prnu  # noqa: E402
from kmt_cam_char.ptc import fit_gain, ptc_points       # noqa: E402
from kmt_cam_char.readnoise import measure_readnoise    # noqa: E402

CAMPAIGN_FMT = "LEGACY-{site}-{night}"
_DIGITS = re.compile(r"(\d{8})\.(\d{6})")


def mock_path(legacy_file: str, mockdir: Path) -> Path | None:
    """Converted twin of a legacy frame (robust to prefix renaming: the
    converter keeps the stem when the name is non-standard, e.g. 'xkmta.*',
    and rebuilds the site prefix otherwise)."""
    stem = Path(legacy_file).stem
    p = mockdir / f"{stem}.ceu.l0amp.mock64.mef.fits"
    if p.exists():
        return p
    m = _DIGITS.search(Path(legacy_file).name)
    if m:
        hits = sorted(mockdir.glob(
            f"*{m.group(1)}.{m.group(2)}.ceu.l0amp.mock64.mef.fits"))
        if hits:
            return hits[0]
    return None


def main(qc_json: str, mock_dir: str, out_csv: str) -> int:
    qc = json.loads(Path(qc_json).read_text(encoding="utf-8"))
    mockdir = Path(mock_dir)
    sel = qc["selection"]

    def exps(role):
        out = []
        for f in sel.get(role, []):
            p = mock_path(f, mockdir)
            if p is not None:
                out.append(open_l0(p))
        return out

    biases = exps("bias")
    flats = exps("ptc")
    repeat = exps("repeat")
    satprobe = exps("saturation_probe")
    if not biases or not flats:
        print(f"ERROR: missing frames (bias {len(biases)}, flats {len(flats)})",
              file=sys.stderr)
        return 1

    geoms = biases[0].amps
    extnames = [g.extname for g in geoms]
    site = qc.get("site", "?")
    night = Path(qc_json).stem.split("_")[-1]
    campaign = CAMPAIGN_FMT.format(site=site, night=night)

    print(f"[{campaign}] bias {len(biases)}, flats {len(flats)}, "
          f"repeat {len(repeat)}, satprobe {len(satprobe)}", flush=True)

    rn = measure_readnoise(biases, extnames)
    print(f"[{campaign}] read noise done", flush=True)

    # group flats into same-exposure pairs
    by_exp: dict[float, list] = {}
    for e in flats:
        by_exp.setdefault(float(e.primary.get("EXPTIME", 0) or 0), []).append(e)
    flat_pairs = []
    for t, group in sorted(by_exp.items()):
        group.sort(key=lambda e: str(e.path))
        flat_pairs += [(group[i], group[i + 1])
                       for i in range(0, len(group) - 1, 2)]

    # brightest non-saturated flats for EPER (levels computed once)
    flat_levels = {id(e): float(np.mean(roi_raw(e, extnames[0])[::8, ::8]))
                   for e in flats}
    bright = [e for e in flats if 40000 < flat_levels[id(e)] < 59000]
    eper_frame = max(bright, key=lambda e: flat_levels[id(e)]) if bright else None

    rows = []
    dead = set(qc.get("dead_amps", []))
    flood = qc.get("flooding_amps", {})
    for gi, g in enumerate(geoms, 1):
        ext = g.extname
        strip = (g.ampid - 1) % 16 % 8 + 1
        r = rn[ext]
        pts = ptc_points(flat_pairs, ext, r["bias_adu"], r["rn_adu"])
        pfit = fit_gain(pts)
        # per-level means for linearity (reuse PTC points; S is pair mean)
        levels = {}
        for p in pts:
            levels.setdefault(p["exptime"], []).append(p)
        lin_levels = [{"exptime": t,
                       "S": float(np.mean([q["S"] for q in ps])),
                       "p999_raw": float(np.max([q["p999_raw"] for q in ps]))}
                      for t, ps in levels.items()]
        lin = fit_linearity(lin_levels, r["bias_adu"])
        sat = saturation_level(satprobe, ext) if satprobe else {"status": "NONE"}
        ep = eper_serial(eper_frame, ext) if eper_frame is not None \
            else {"status": "NO_FRAME"}
        pr = measure_prnu(repeat, ext, r["bias_adu"]) if repeat \
            else {"status": "NONE"}
        gs = gain_series(repeat, ext, r["bias_adu"], r["rn_adu"]) if repeat \
            else {"status": "NONE"}

        gain = pfit.get("gain", 0.0)
        # QC census keys are LEGACY labels. On the K and N chips the legacy
        # numbering runs opposite to the physical strip (legacy K01 = strip 8,
        # verified in the mock-converter work), so map mock strip -> label:
        if g.chip in ("K", "N"):
            legacy_label = f"{g.chip}{9 - strip:02d}"
        else:
            legacy_label = f"{g.chip}{strip:02d}"
        status = []
        if pfit.get("status") != "OK":
            status.append(pfit.get("status", "?"))
        hdr = biases[0].hdul[ext].header
        if legacy_label in dead:
            status.append("DEAD")
        if legacy_label in flood:
            status.append(f"FLOOD({flood[legacy_label]})")
        rows.append({
            "AMPID": g.ampid, "EXTNAME": ext,
            "GAIN": round(gain, 4), "GAIN_ERR": round(pfit.get("gain_err", 0), 4),
            "RDNOISE": round(r["rn_adu"] * gain, 3) if gain else 0.0,
            "RDNOISE_ERR": round(r["rn_adu_err"] * gain, 3) if gain else 0.0,
            "SATURAT": (round(sat.get("saturat_98pct", 0))
                        if sat.get("status") == "MEASURED" else -1),
            "LINMAX": (round(lin.get("linmax_raw_adu", 0))
                       if lin.get("status") == "OK" else -1),
            "READDIR": "na",
            "STATUS": ";".join(status) or "OK",
            "CAMPAIGN": campaign, "DATE": night,
            "CONFIG": "legacy-OSU-32amp",
            # extras (schema allows appended columns)
            "RN_ADU": round(r["rn_adu"], 3),
            "OVSC_RMS_ADU": round(r["ovsc_rms_adu"], 3),
            "BIAS_ADU": round(r["bias_adu"], 1),
            "BIAS_DRIFT_ADU": round(r["bias_drift_adu"], 2),
            "PTC_CURV_A": f"{pfit.get('curv_a', 0):.3e}",
            "PTC_NPTS": pfit.get("n_pts", 0),
            "PTC_RESID_PCT": round(pfit.get("resid_rms_pct", 0), 2),
            "LIN_RATE_ADU_S": round(lin.get("rate_adu_s", 0), 1),
            "LIN_PEDESTAL_ADU": round(lin.get("pedestal_adu", 0), 1),
            "LIN_A1": f"{lin.get('lin_a1', 0):.3e}",
            "LIN_A2": f"{lin.get('lin_a2', 0):.3e}",
            "LIN_RANGE_LO": round(lin.get("s_range_lo", 0)),
            "LIN_RANGE_HI": round(lin.get("s_range_hi", 0)),
            "LIN_NOTE": lin.get("linmax_note", lin.get("status", "")),
            "CTE_SERIAL": (f"{ep.get('cte_serial', 0):.7f}"
                           if ep.get("status") == "OK" else ""),
            "PRNU_PCT": (round(pr.get("prnu_pct", 0), 3)
                         if pr.get("status") == "OK" else ""),
            "GAIN_STAB_PCT": (round(gs.get("gain_stab_pct", 0), 3)
                              if gs.get("status") == "OK" else ""),
            "GAIN_HDR": round(float(hdr.get("GAIN", 0) or 0), 3),
            "RDNOISE_HDR": round(float(hdr.get("RDNOISE", 0) or 0), 3),
        })
        if gi % 16 == 0:
            print(f"[{campaign}] {gi}/64 amps", flush=True)

    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for e in biases + flats + repeat + satprobe:
        e.close()
    print(f"[{campaign}] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
