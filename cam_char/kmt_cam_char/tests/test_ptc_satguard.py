"""ptc/linearity 포화 가드 검증 (pytest 불필요 — 단독 assert 스크립트).

core 계층이 물리 unsigned ADU(0..65535)로 통일되면서 SAT_GUARD_ADU=60000은
레거시 변환 데이터의 클립(물리 ~29-30k ADU)을 더 이상 거르지 못한다.
testkit adc_map으로 29800 ADU 하드 클립을 주입해:
  (a) fit_gain: 부분 클립 쌍(분산 붕괴, V>0)이 섞여도 분산-붕괴 기각이
      동작해 gain을 ±3%로 회수 (기각 없으면 ~16% 오차 — 회귀 기준)
  (b) 클린 세트에서는 기각이 발동하지 않아 n_pts가 전체 쌍 수와 같음
  (c) fit_linearity: 공유 p99.9 ceiling 레벨들이 제외되어 LINMAX가 클립
      plateau(29800)가 아닌 실측 상단으로 남고 NL 오염이 없음
을 확인한다. runner.py는 가드 인자를 넘기지 못하므로(하위호환 고정)
세 경로 모두 기본 인자만으로 검증한다.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kmt_cam_char import core, linearity, ptc            # noqa: E402
from kmt_cam_char.testkit import SynthL0                 # noqa: E402

GAIN_TRUE = 1.46
RN_ADU = 3.5
RATE = 2000.0
CLIP = 29800.0          # 레거시 변환본의 물리 코드축 클립 수준을 모사
# 상단 4레벨이 클립을 걸친다 (완전 클립 2 + 부분 클립 2)
LEVELS = [2000, 5000, 10000, 16000, 22000, 26000, 27500,
          28300, 28600, 28800, 29500, 31000]


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="test_satguard_"))
    kit = SynthL0(tmp, seed=9)
    ext = kit.extnames[0]
    clipmap = lambda c: np.minimum(c, CLIP)               # noqa: E731

    flats = []
    for k, lv in enumerate(LEVELS):
        for j in range(2):
            flats.append(kit.frame("g%02d%d" % (k, j), lv,
                                   exptime=lv / RATE, adc_map=clipmap))
    exps = [core.open_l0(p) for p in flats]
    try:
        prs = [(exps[i], exps[i + 1]) for i in range(0, len(exps), 2)]
        bias_adu = float(kit.bias[0])
        pts = ptc.ptc_points(prs, ext, bias_adu, RN_ADU,
                             roi=kit.roi, ovsc=kit.ovsc)

        # (a) 클립 쌍 혼입 세트에서 gain 회수 (기본 인자 = runner 경로)
        fit = ptc.fit_gain(pts)
        assert fit["status"] == "OK", fit
        assert abs(fit["gain"] - GAIN_TRUE) / GAIN_TRUE < 0.03, \
            "clip pairs polluted the PTC fit: gain %.4f" % fit["gain"]
        n_clip = sum(1 for p in pts if p["p999_raw"] >= CLIP - 1.0)
        assert n_clip >= 2, n_clip                        # 시나리오 유효성
        assert fit["n_pts"] <= len(pts) - n_clip, \
            (fit["n_pts"], len(pts), n_clip)

        # (b) 클린 부분집합에서는 기각이 발동하지 않는다
        clean = [p for p in pts if p["p999_raw"] < CLIP - 50.0]
        fit_c = ptc.fit_gain(clean)
        assert fit_c["n_pts"] == len(clean), (fit_c["n_pts"], len(clean))
        assert abs(fit_c["gain"] - GAIN_TRUE) / GAIN_TRUE < 0.03
        # 오염 세트의 gain이 클린 적합과 일치
        assert abs(fit["gain"] - fit_c["gain"]) / fit_c["gain"] < 0.01, \
            (fit["gain"], fit_c["gain"])

        # (c) fit_linearity: ceiling 레벨 제외 (runner의 레벨 집계 규약)
        byt: dict = {}
        for p in pts:
            byt.setdefault(p["exptime"], []).append(p)
        lin_levels = [{"exptime": t,
                       "S": float(np.mean([q["S"] for q in ps])),
                       "p999_raw": float(np.max([q["p999_raw"] for q in ps]))}
                      for t, ps in byt.items()]
        lin = linearity.fit_linearity(lin_levels, bias_adu)
        assert lin["status"] == "OK", lin
        # 클립 plateau가 적합/LINMAX에 들어가면 linmax_raw ~ 29800 + NL 폭주
        assert lin["nl_max_pct"] < 0.5, lin["nl_max_pct"]
        assert lin["s_range_hi"] < CLIP - 50.0, lin["s_range_hi"]
        assert lin["linmax_raw_adu"] < CLIP - 50.0, lin["linmax_raw_adu"]
    finally:
        for e in exps:
            e.close()

    print("OK test_ptc_satguard (gain %.4f, clean %.4f, linmax %.0f raw)"
          % (fit["gain"], fit_c["gain"], lin["linmax_raw_adu"]))


if __name__ == "__main__":
    main()
