"""satshut 모듈 단독 테스트 (pytest 불필요 — assert 스크립트).

testkit 합성 L0로 결함을 주입하고 정량 회수를 검증한다:
  (a) adc_map으로 61500 plateau 주입 -> ANALOG 분류, S_sat 회수
  (b) 65535 클리핑 -> ADC 분류
  (b2) full well 소프트 압축(분산 붕괴, plateau 없음) -> FULLWELL 분류
  (b3) 전 프레임 포화 램프 -> ADC + ramp_note='no-rising-segment'
       (NOT_REACHED 오분류 회귀 방지)
  (b4) 마지막 1개 프레임만 포화 -> ADC + fullwell_note='clip-limited'
       (FULLWELL/var-collapse 오분류 회귀 방지)
  (c) persist_adu = 38 exp(-k/3) 시퀀스 -> tau = 3 x dt_sec ± 20% 회수
  (d) 실제 노출 t+0.023 s로 생성한 short 세트 -> dt = 23 ms ± 3 ms
  (e) run_satshut 전체 실행 -> CSV 행 수/값, PNG 존재·크기(>10 KB)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kmt_cam_char import satshut                      # noqa: E402
from kmt_cam_char.testkit import SynthL0              # noqa: E402

GAIN = 1.46
RATE = 2000.0        # 합성 광원 rate [ADU/s]
DT_TRUE_S = 0.023    # 주입 셔터 오프셋
TAU_FRAMES = 3.0
DT_SEC = 45.0

tmp = tempfile.mkdtemp(prefix="satshut_synth_")
outdir = tempfile.mkdtemp(prefix="satshut_out_")
kit = SynthL0(tmp, seed=5)
ext = kit.extnames[0]

# -- (a) analog plateau 61500 주입 -------------------------------------------
levels_a = [20000, 30000, 40000, 48000, 54000, 58000, 62000, 64500]
ramp_a = [kit.frame("ra%02d" % i, lv, exptime=lv / RATE,
                    adc_map=lambda c: np.minimum(c, 61500))
          for i, lv in enumerate(levels_a)]
sat_a = satshut.saturation_analysis(ramp_a, ext, roi=kit.roi, ovsc=kit.ovsc,
                                    gain=GAIN)
assert sat_a["status"] == "OK", sat_a
assert sat_a["sat_kind"] == "ANALOG", sat_a["sat_kind"]
assert abs(sat_a["s_sat_adu"] - 61500.0) <= 50.0, sat_a["s_sat_adu"]
# 분산 붕괴는 마지막 미포화 레벨(58000)에서: full well 추정 sanity
assert sat_a["i_fw"] >= 0, sat_a
assert abs(sat_a["s_fw_adu"] - 58000.0) <= 1500.0, sat_a["s_fw_adu"]
assert abs(sat_a["fullwell_e"] - 58000.0 * GAIN) <= 1500.0 * GAIN
print("  (a) ANALOG: S_sat=%.0f ADU, S_fw=%.0f ADU"
      % (sat_a["s_sat_adu"], sat_a["s_fw_adu"]))

# -- (b) ADC 클리핑 65535 ------------------------------------------------------
levels_b = [20000, 33000, 44000, 52000, 58000, 61000, 65000, 67000]
ramp_b = [kit.frame("rb%02d" % i, lv, exptime=lv / RATE)
          for i, lv in enumerate(levels_b)]
sat_b = satshut.saturation_analysis(ramp_b, ext, roi=kit.roi, ovsc=kit.ovsc,
                                    gain=GAIN)
assert sat_b["status"] == "OK", sat_b
assert sat_b["sat_kind"] == "ADC", sat_b["sat_kind"]
assert sat_b["s_sat_adu"] >= 65534.0, sat_b["s_sat_adu"]
print("  (b) ADC: S_sat=%.0f ADU" % sat_b["s_sat_adu"])

# -- (b2) CCD full well: 48000 ADU 위 분산 붕괴 + 완만한 코드 상승 ------------
FW_ADU = 48000.0


def _fullwell(s):
    return np.where(s < FW_ADU, s, FW_ADU + 0.05 * (s - FW_ADU))


levels_f = [30000, 40000, 46000, 50000, 54000, 58000]
ramp_f = [kit.frame("rf%02d" % i, lv, exptime=lv / RATE, nonlin=_fullwell)
          for i, lv in enumerate(levels_f)]
sat_f = satshut.saturation_analysis(ramp_f, ext, roi=kit.roi, ovsc=kit.ovsc,
                                    gain=GAIN)
assert sat_f["status"] == "OK", sat_f
assert sat_f["sat_kind"] == "FULLWELL", sat_f["sat_kind"]
assert abs(sat_f["s_fw_adu"] - 46000.0) <= 1500.0, sat_f["s_fw_adu"]
assert sat_f["fullwell_note"] == "var-collapse", sat_f["fullwell_note"]
print("  (b2) FULLWELL: S_fw=%.0f ADU, Q_fw=%.0f e-"
      % (sat_f["s_fw_adu"], sat_f["fullwell_e"]))

# -- (b3) 전 프레임 포화 램프 -> NOT_REACHED가 아니라 ADC + 상승구간 부재 ----
levels_g = [70000, 75000, 80000, 85000]
ramp_g = [kit.frame("rg%02d" % i, lv, exptime=lv / RATE)
          for i, lv in enumerate(levels_g)]
sat_g = satshut.saturation_analysis(ramp_g, ext, roi=kit.roi, ovsc=kit.ovsc,
                                    gain=GAIN)
assert sat_g["status"] == "OK", sat_g
assert sat_g["sat_kind"] == "ADC", sat_g["sat_kind"]
assert sat_g["s_sat_adu"] >= 65534.0, sat_g["s_sat_adu"]
assert sat_g["fullwell_note"] == "sat-limited", sat_g["fullwell_note"]
assert sat_g["ramp_note"] == "no-rising-segment", sat_g["ramp_note"]
print("  (b3) all-saturated ramp: %s (%s)"
      % (sat_g["sat_kind"], sat_g["ramp_note"]))

# -- (b4) 마지막 1개 프레임만 포화 -> FULLWELL(var-collapse) 오분류 회귀 -----
levels_h = [20000, 26000, 32000, 38000, 44000, 50000, 56000, 70000]
ramp_h = [kit.frame("rh%02d" % i, lv, exptime=lv / RATE)
          for i, lv in enumerate(levels_h)]
sat_h = satshut.saturation_analysis(ramp_h, ext, roi=kit.roi, ovsc=kit.ovsc,
                                    gain=GAIN)
assert sat_h["status"] == "OK", sat_h
assert sat_h["sat_kind"] == "ADC", sat_h["sat_kind"]
assert sat_h["fullwell_note"] == "clip-limited", sat_h["fullwell_note"]
# S_fw는 마지막 미포화 프레임(56000) 기준의 클립 하한
assert abs(sat_h["s_fw_adu"] - 56000.0) <= 1500.0, sat_h["s_fw_adu"]
print("  (b4) single saturated tail frame: %s (%s), S_fw=%.0f ADU"
      % (sat_h["sat_kind"], sat_h["fullwell_note"], sat_h["s_fw_adu"]))

# -- (c) persistence 감쇠 tau 회수 ---------------------------------------------
persist = [kit.frame("pa%02d" % k, 0.0,
                     persist_adu=38.0 * float(np.exp(-k / TAU_FRAMES)))
           for k in range(8)]
pd = satshut.persistence_decay(persist, ext, roi=kit.roi, ovsc=kit.ovsc,
                               dt_sec=DT_SEC)
assert pd["status"] == "OK", pd
tau_true = TAU_FRAMES * DT_SEC                      # 135 s (순번 축 폴백)
assert abs(pd["tau_s"] - tau_true) <= 0.20 * tau_true, pd["tau_s"]
assert abs(pd["a0_adu"] - 38.0) <= 0.30 * 38.0, pd["a0_adu"]
print("  (c) persistence: tau=%.1f s (true %.1f), A0=%.1f ADU"
      % (pd["tau_s"], tau_true, pd["a0_adu"]))

# -- (d) 셔터 오프셋 dt = 23 ms 회수 -----------------------------------------
shorts = []
for j, t in enumerate([0.1, 0.2, 0.5, 1.0, 2.0]):
    for r in range(2):
        shorts.append(kit.frame("sh%02d%d" % (j, r),
                                RATE * (t + DT_TRUE_S), exptime=t))
sf = satshut.shutter_fit(shorts, ext, roi=kit.roi, ovsc=kit.ovsc)
assert sf["status"] == "OK", sf
assert abs(sf["dt_ms"] - DT_TRUE_S * 1000.0) <= 3.0, sf["dt_ms"]
assert abs(sf["rate_adu_s"] - RATE) <= 0.02 * RATE, sf["rate_adu_s"]
print("  (d) shutter: dt=%.2f ms (true %.1f), R=%.1f ADU/s"
      % (sf["dt_ms"], DT_TRUE_S * 1000.0, sf["rate_adu_s"]))

# -- (e) 전체 파이프라인: CSV + PNG -------------------------------------------
longs = [kit.frame("lo%02d" % r, RATE * (30.0 + DT_TRUE_S), exptime=30.0)
         for r in range(2)]
res = satshut.run_satshut(ramp_b, persist, shorts, longs, outdir, "TEST",
                          gain=GAIN, roi=kit.roi, ovsc=kit.ovsc)
csv_path = Path(res["csv"])
assert csv_path.exists(), csv_path
lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
assert len(lines) == 1 + kit.namps, len(lines)
assert lines[0].split(",") == satshut.CSV_FIELDS, lines[0]
row0 = dict(zip(satshut.CSV_FIELDS, lines[1].split(",")))
assert row0["extname"] == ext and row0["sat_kind"] == "ADC", row0
assert abs(float(row0["shutter_dt_ms"]) - 23.0) <= 3.0, row0
assert abs(float(row0["persist_tau_s"]) - tau_true) <= 0.20 * tau_true, row0
# 캠페인 식별 컬럼 + 사용 gain 기록
assert row0["campaign"] == "TEST", row0["campaign"]
assert row0["date"] == "2026-09-04", row0["date"]       # testkit DATE-OBS
assert float(row0["gain_e_adu"]) == GAIN, row0["gain_e_adu"]

# ampchar 주입: 앰프별 gain이 Q_fw와 gain_e_adu에 반영되는지
ac_csv = Path(outdir) / "ampchar.csv"
ac_gain = 2.0
ac_csv.write_text("EXTNAME,GAIN,RDNOISE\n%s,%s,7.0\n" % (ext, ac_gain),
                  encoding="utf-8")
res_ac = satshut.run_satshut(ramp_b, [], [], None, str(Path(outdir) / "ac"),
                             "TESTAC", gain=GAIN, roi=kit.roi, ovsc=kit.ovsc,
                             ampchar=satshut.load_ampchar(ac_csv))
rows_ac = {r["extname"]: r for r in res_ac["rows"]}
assert float(rows_ac[ext]["gain_e_adu"]) == ac_gain, rows_ac[ext]
other = kit.extnames[1]
assert float(rows_ac[other]["gain_e_adu"]) == GAIN, rows_ac[other]
q_ratio = rows_ac[ext]["fullwell_e"] / max(rows_ac[other]["fullwell_e"], 1.0)
assert abs(q_ratio - ac_gain / GAIN) < 0.05, q_ratio

summary = Path(res["outdir"]) / "satshut_summary.png"
amp_png = Path(res["outdir"]) / "amps" / ("%s_satshut.png" % ext)
assert summary.exists() and summary.stat().st_size > 10240, summary
assert amp_png.exists() and amp_png.stat().st_size > 10240, amp_png
assert res["shading"] is not None and res["shading"]["status"] == "OK"
assert res["shading"]["pp_ms"] < 10.0, res["shading"]["pp_ms"]
print("  (e) pipeline: %d CSV rows, shading p-p %.2f ms"
      % (len(lines) - 1, res["shading"]["pp_ms"]))

print("OK test_satshut")
