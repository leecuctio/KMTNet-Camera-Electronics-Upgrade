"""QA JSON records per exposure and a batch summary in markdown."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def write_qa(qa: dict, qa_dir) -> Path:
    qa_dir = Path(qa_dir)
    qa_dir.mkdir(parents=True, exist_ok=True)
    name = str(qa.get("l1_file", qa.get("l0_file", "exposure"))).replace(".fits", "")
    path = qa_dir / f"{name}.qa.json"
    path.write_text(json.dumps(_jsonable(qa), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def batch_summary(qa_dir, out_path=None) -> Path:
    """Aggregate all *.qa.json in qa_dir into a markdown summary table."""
    qa_dir = Path(qa_dir)
    records = []
    for p in sorted(qa_dir.glob("*.qa.json")):
        records.append(json.loads(p.read_text(encoding="utf-8")))
    out_path = Path(out_path) if out_path else qa_dir / "qa_summary.md"

    lines = [
        "# KMT-CEU L1 preprocessing QA summary",
        "",
        f"Exposures: {len(records)}",
        "",
        "| L1 file | type | filter | exptime | sky med [e-] | sky rms [e-] | max seam [e-] | sat px | bad px | ovsc rms [ADU] | sec |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in records:
        ccds = r.get("ccds", {})
        amps = r.get("amps", {})
        sky = np.median([c["median_e"] for c in ccds.values()]) if ccds else 0.0
        rms = np.median([c["mad_std_e"] for c in ccds.values()]) if ccds else 0.0
        seam = max((c["seam_max_abs_e"] for c in ccds.values()), default=0.0)
        nsat = sum(c["n_sat"] for c in ccds.values())
        nbad = sum(c["n_bad"] for c in ccds.values())
        ovsc = np.median([a["ovsc_rms_adu"] for a in amps.values()]) if amps else 0.0
        lines.append(
            f"| {r.get('l1_file','')} | {r.get('imagetyp','')} | {r.get('filter','')} "
            f"| {r.get('exptime',0):.0f} | {sky:.1f} | {rms:.1f} | {seam:.2f} "
            f"| {nsat} | {nbad} | {ovsc:.2f} | {r.get('runtime_s',0):.0f} |")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
