"""Aggregate the LEGACY baseline campaign results into the characterization
report (markdown): per-site tables, cross-validation (TOP/BOT halves, header
values, June<->July drift), pathology census, and placeholder guidance.

Usage: python3 cam_char/kmt_cam_char/report.py RESULTS_DIR OUT_MD
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np

_CSV = re.compile(r"amp_characterization_LEGACY-([A-Z]+)-(\d{8})\.csv$")


def load_all(results_dir: Path):
    runs = {}
    for p in sorted(results_dir.glob("amp_characterization_LEGACY-*.csv")):
        m = _CSV.search(p.name)
        if not m:
            continue
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        runs[(m.group(1), m.group(2))] = rows
    qc = {}
    for p in sorted(results_dir.glob("qc_legacy_*.json")):
        parts = p.stem.split("_")
        qc[(parts[2].upper(), parts[3])] = json.loads(p.read_text(encoding="utf-8"))
    return runs, qc


def f(rows, key):
    out = []
    for r in rows:
        try:
            v = float(r[key])
        except (KeyError, TypeError, ValueError):
            continue
        if v > 0:
            out.append(v)
    return np.array(out)


def med(a, fmt="{:.3f}"):
    return fmt.format(np.median(a)) if len(a) else "—"


def topbot(rows, key="GAIN"):
    pair = {}
    for r in rows:
        try:
            v = float(r[key])
        except (TypeError, ValueError):
            continue
        if v > 0:
            pair.setdefault(r["EXTNAME"][:3], {})[r["EXTNAME"][3]] = v
    d = [abs(v["T"] - v["B"]) / ((v["T"] + v["B"]) / 2) * 100
         for v in pair.values() if "T" in v and "B" in v]
    return np.array(d)


def main(results_dir: str, out_md: str) -> int:
    rdir = Path(results_dir)
    runs, qc = load_all(rdir)
    if not runs:
        print("no result CSVs found", file=sys.stderr)
        return 1

    L = []
    L.append("# KMTNet 카메라 특성 — 구형 전자부 기준선 보고서 (LEGACY-2026-06/07)")
    L.append("")
    L.append(f"최종 갱신일: {date.today().isoformat()}")
    L.append("")
    L.append("## 1. 목적과 지위")
    L.append("")
    L.append("본 보고서는 3개 사이트(SSO/SAAO/CTIO)에서 2026-06/07 두 달에 걸쳐 취득한")
    L.append("**구형(OSU 32-amp) 전자부**의 돔플랫·바이어스 세트를 mock 64-amp 형식으로")
    L.append("변환한 뒤, `cam_char/kmt_cam_char` 측정 코드로 산출한 카메라 특성값이다.")
    L.append("")
    L.append("- 이 값들은 **신규(CEU) 전자부의 최종 파라미터가 아니다** — 실험실")
    L.append("  캠페인의 **신구 비교 기준선**이자, 측정 코드의 실전 검증이며, mock64")
    L.append("  파이프라인용 실측형 placeholder다 (`CAMPAIGN=LEGACY-*` 라벨).")
    L.append("- mock 64-amp의 TOP/BOT은 같은 물리 앰프의 분할이므로 독립 전자 체인은")
    L.append("  사이트당 32개다. TOP/BOT 일치도는 측정 코드의 자체 검증 지표다.")
    L.append("")
    L.append("## 2. 자료와 QC 요약")
    L.append("")
    L.append("| 사이트/야간 | 프레임 | Bias | 램프 | 포화 도달 | 침수 amp | 특이 |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    for (site, night), q in sorted(qc.items()):
        n_fl = len(q.get("flooding_amps", {}))
        worst = max(map(abs, q.get("flooding_amps", {}).values()), default=0)
        L.append(f"| {site} {night} | {q['n_frames']} | {q['n_bias']} | "
                 f"{len(q['exp_levels'])}단계 | "
                 f"{'예' if q['sat_reached'] else '아니오'} | "
                 f"{n_fl} (max {worst:.0f} ADU@50k) | "
                 f"dead {len(q.get('dead_amps', []))} |")
    L.append("")
    L.append("돔램프는 **두 밝기 체제**(단노출=밝음 38–62k ADU, 장노출=어두움)로")
    L.append("운용되었고, 밝은 체제에는 판독 중 누적광에 의한 큰 t=0 페데스탈이 있다.")
    L.append("따라서 선형성은 밝은 체제의 연속 램프 구간에서만 유효하다(§4 한계).")
    L.append("")
    L.append("## 3. 사이트별 핵심 결과 (중앙값, mock 64-amp 기준)")
    L.append("")
    L.append("| 사이트/야간 | GAIN [e-/ADU] | RN [e-] | RN(hdr) | PRNU [%] | "
             "CTE(serial) | gain 안정도 [%] | SATURAT | LINMAX |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for (site, night), rows in sorted(runs.items()):
        g = f(rows, "GAIN")
        rn = f(rows, "RDNOISE")
        rnh = f(rows, "RDNOISE_HDR")
        pr = f(rows, "PRNU_PCT")
        cte = f(rows, "CTE_SERIAL")
        gs = f(rows, "GAIN_STAB_PCT")
        sat = f(rows, "SATURAT")
        lm = f(rows, "LINMAX")
        L.append(f"| {site} {night} | {med(g)} | {med(rn, '{:.2f}')} | "
                 f"{med(rnh, '{:.2f}')} | {med(pr)} | {med(cte, '{:.7f}')} | "
                 f"{med(gs)} | {med(sat, '{:.0f}') if len(sat) else '미도달'} | "
                 f"{med(lm, '{:.0f}')} |")
    L.append("")
    L.append("주: ① CTE(serial)는 EPER 기준이며, overscan 침수가 심한 사이트(특히")
    L.append("SAAO)에서는 침수가 EPER baseline을 오염시켜 **상한으로만** 해석해야")
    L.append("한다 — 깨끗한 측정은 SSO 값이 대표. ② SATURAT은 해당 야간 램프가")
    L.append("포화에 도달한 앰프에서만 측정(-1 = 미도달, placeholder 유지).")
    L.append("")
    L.append("## 4. 교차검증")
    L.append("")
    L.append("| 사이트/야간 | 측정 amp | TOP/BOT gain 차 (med/max %) | "
             "gain/헤더 비 (med) |")
    L.append("| --- | --- | --- | --- |")
    for (site, night), rows in sorted(runs.items()):
        g = f(rows, "GAIN")
        tb = topbot(rows)
        gh = []
        for r in rows:
            try:
                gv, hv = float(r["GAIN"]), float(r["GAIN_HDR"])
                if gv > 0 and hv > 0:
                    gh.append(gv / hv)
            except (TypeError, ValueError):
                pass
        L.append(f"| {site} {night} | {len(g)}/64 | "
                 f"{med(tb, '{:.2f}')} / {np.max(tb):.2f} | "
                 f"{np.median(gh):.3f} |")
    L.append("")
    L.append("주: CTIO의 gain/헤더 비 ~1.16은 측정 오류가 아니라 **헤더 공칭값(소수")
    L.append("1자리)이 낡았음**을 뜻한다 — TOP/BOT 일치(0.1%)와 두 달 재현성(0.2%)이")
    L.append("측정을 지지한다. legacy 헤더 gain은 절대 기준으로 쓰지 말 것.")
    L.append("")
    # June<->July gain drift per site
    L.append("### 6월 ↔ 7월 gain 재현성")
    L.append("")
    L.append("| 사이트 | amp별 gain 변화 (med / max %) |")
    L.append("| --- | --- |")
    sites = sorted({s for s, _ in runs})
    for s in sites:
        nights = sorted(n for ss, n in runs if ss == s)
        if len(nights) != 2:
            continue
        g1 = {r["EXTNAME"]: float(r["GAIN"]) for r in runs[(s, nights[0])]
              if float(r["GAIN"]) > 0}
        g2 = {r["EXTNAME"]: float(r["GAIN"]) for r in runs[(s, nights[1])]
              if float(r["GAIN"]) > 0}
        d = [abs(g2[k] - g1[k]) / g1[k] * 100 for k in g1 if k in g2]
        L.append(f"| {s} | {np.median(d):.2f} / {np.max(d):.2f} |")
    L.append("")
    L.append("## 5. 병리 census (legacy 기준선의 핵심 소견)")
    L.append("")
    for (site, night), q in sorted(qc.items()):
        fl = q.get("flooding_amps", {})
        if not fl:
            continue
        worst = sorted(fl.items(), key=lambda kv: -abs(kv[1]))[:5]
        L.append(f"- **{site} {night}**: overscan 침수 {len(fl)} amp — 상위: "
                 + ", ".join(f"{a} ({v:+.0f} ADU@50k)" for a, v in worst))
    L.append("")
    L.append("SAAO의 일부 앰프는 50k 신호에서 overscan이 **~1,500 ADU(3%)** 이동하는")
    L.append("심각한 침수를 보인다 — 전처리 파이프라인의 overscan 오염 가드(>100 ADU)가")
    L.append("발동하는 수준이며, CEU 전자부에서 이 병리의 소멸 여부가 신구 비교의")
    L.append("핵심 판정 항목이다 (실험실 계획서 §23).")
    L.append("")
    L.append("## 6. Placeholder 반영")
    L.append("")
    L.append("측정 CSV는 `results/README.md` 스키마를 따르며, 변환기 옵션으로 mock64")
    L.append("헤더에 스탬프할 수 있다:")
    L.append("")
    L.append("```bash")
    L.append("python3 mef_converter/kmt_ceu_legacy32_to_l0amp_mef_v2.py legacy.fits \\")
    L.append("  --ampchar cam_char/results/amp_characterization_LEGACY-CTIO-20260611.csv -d out -f")
    L.append("```")
    L.append("")
    L.append("주의: 이 값은 `CONFIG=legacy-OSU-32amp` 기준선이다. CEU 실측(실험실")
    L.append("캠페인) 후 동일 스키마의 CEU 캠페인 CSV로 대체한다.")
    L.append("")
    L.append("## 7. 이 자료로 측정하지 못한 것 (실험실 캠페인 필요)")
    L.append("")
    L.append("- crosstalk 64×64 (스팟 마스크 필요), dark/DSNU (다크 없음),")
    L.append("  parallel CTE (legacy에 병렬 overscan 없음), READDIR (mock 기하는")
    L.append("  변환이 정의), shutter timing 맵 (돔 세트는 페데스탈이 지배)")
    L.append("- 선형성은 밝은 램프 체제의 신호 구간(LIN_RANGE_LO–HI)에서만 유효하고,")
    L.append("  램프 드리프트가 잔차에 포함된다 (기준노출 삽입 없는 세트의 한계)")
    L.append("")
    out = Path(out_md)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
