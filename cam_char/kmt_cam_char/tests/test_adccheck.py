"""adccheck 자체 테스트 — testkit adc_map으로 ADC 결함 주입·회수 검증.

pytest 불필요: 단독 실행, 성공 시 "OK test_adccheck", 실패 시 비0 종료.
  (a) 특정 코드 하나 제거(이웃으로 이동) -> missing code 검출
  (b) 비트 13 강제 0 (code & ~(1<<13)) -> stuck bit 검출
      (bit 13 경계를 넘나드는 flat 레벨 세트 사용 — 커버 대역폭 조건)
  (c) 무결 세트 -> 결함 0 보고, DNL rms 소값/NaN
  (d) run_adccheck 산출물(CSV 행수, PNG > 10KB) 확인
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from kmt_cam_char import adccheck
from kmt_cam_char.testkit import SynthL0


def _flat_levels(kit, prefix, levels, per_level, **kw):
    paths = []
    k = 0
    for lv in levels:
        for _ in range(per_level):
            paths.append(kit.frame("%s%02d" % (prefix, k), level_adu=lv,
                                   exptime=1.0, **kw))
            k += 1
    return paths


def main():
    tmp = tempfile.mkdtemp(prefix="test_adccheck_")

    # testkit은 int16 + BZERO=32768 로 저장하고 core 계층은 헤더 BZERO를
    # 적용하므로, 관측 코드축 = 물리 ADC 코드축(주입 true_code 그대로)이다.

    # (a) missing code: 코드 m 을 이웃 m-1 로 이동 --------------------------
    kit = SynthL0(Path(tmp) / "m", seed=21)
    ext0 = kit.extnames[0]
    m = int(round(kit.bias[0])) + 1             # 앰프0 분포 중심 부근 (true)
    m_obs = m                                   # 관측 코드축 = 물리 코드축
    pa = kit.bias_set(8, prefix="mc",
                      adc_map=lambda c: np.where(c == m, m - 1, c))
    h = adccheck.code_histogram(pa, ext0, roi=kit.roi)
    npix = ((kit.roi[0].stop - kit.roi[0].start)
            * (kit.roi[1].stop - kit.roi[1].start))
    assert h["n_samples"] == 8 * npix, h["n_samples"]
    miss = adccheck.missing_codes(h["counts"])
    assert miss["missing"] == [m_obs], (miss, m_obs)
    occ = adccheck.bit_occupancy(h["counts"])
    assert 0.35 < occ[0] < 0.65, occ[0]         # LSB는 잡음으로 ~50% 토글
    assert adccheck.stuck_bits(h["counts"]) == []   # 좁은 대역: 오검출 없음

    # (b) stuck bit 13: bit 13 경계를 넘는 flat 레벨 세트 -------------------
    kb = SynthL0(Path(tmp) / "s", seed=22)
    mask = 0xFFFF & ~(1 << 13)
    pb = _flat_levels(kb, "sb", (3000.0, 9500.0, 16500.0), 3,
                      adc_map=lambda c: c & mask)
    hb = adccheck.code_histogram(pb, kb.extnames[0], roi=kb.roi)
    st = adccheck.stuck_bits(hb["counts"])
    assert len(st) == 1, st
    assert st[0]["bit"] == 13 and st[0]["stuck_at"] == 0, st
    lo, hi = adccheck.coverage_band(hb["counts"])
    assert hi - lo >= 2 ** 13, (lo, hi)         # 시험 가능 조건 충족 확인

    # (c) 무결 세트 -> 결함 0, DNL 정상 -------------------------------------
    kc = SynthL0(Path(tmp) / "c", seed=23)
    pc = _flat_levels(kc, "cl", (3000.0, 9500.0, 16500.0), 3)
    hc = adccheck.code_histogram(pc, kc.extnames[0], roi=kc.roi)
    assert adccheck.stuck_bits(hc["counts"]) == []
    assert adccheck.missing_codes(hc["counts"])["n_missing"] == 0
    dnl = adccheck.dnl_estimate(hc["counts"])
    assert np.isnan(dnl["dnl_rms"]) or dnl["dnl_rms"] < 0.15, dnl["dnl_rms"]
    # 무결 세트에서는 bit 13 점유율이 실제로 > 0 (b)와 대조)
    assert adccheck.bit_occupancy(hc["counts"])[13] > 0.1

    # bias 단독(좁은 분포) -> DNL 은 NaN 처리 (커버 부족)
    dnl_b = adccheck.dnl_estimate(h["counts"])
    assert np.isnan(dnl_b["dnl_rms"]) or dnl_b["n_codes"] >= 64

    # (d) 드라이버 산출물 — (a) missing 세트로 실행 -------------------------
    out = Path(tmp) / "out"
    res = adccheck.run_adccheck(pa, out, campaign="TEST", roi=kit.roi)
    r0 = res["per_amp"][ext0]
    assert r0["n_missing"] == 1 and r0["missing"] == [m_obs], r0["missing"]
    assert r0["stuck"] == []
    base = Path(res["outdir"])
    lines = (base / "adccheck_TEST.csv").read_text().strip().splitlines()
    assert len(lines) == kit.namps + 1, len(lines)            # 헤더 + 앰프행
    assert (base / "adccheck_summary.png").stat().st_size > 10240
    for ext in kit.extnames:
        p = base / "amps" / ("%s_adccheck.png" % ext)
        assert p.exists() and p.stat().st_size > 10240, p

    shutil.rmtree(tmp, ignore_errors=True)
    print("OK test_adccheck")


if __name__ == "__main__":
    main()
