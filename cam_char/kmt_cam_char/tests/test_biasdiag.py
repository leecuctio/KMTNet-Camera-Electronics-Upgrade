"""biasdiag 자체 테스트 — testkit 합성 프레임으로 정량 회수 검증.

pytest 불필요: 단독 실행, 성공 시 "OK test_biasdiag", 실패 시 비0 종료.
  (a) pickup(1.5 ADU, 8 cycles/row) 주입 -> PSD 피크 주파수 회수
  (b) shared_rms=2.0 주입 -> 같은 ctrl 상관 > 0.2, 다른 ctrl < 0.1
  (c) 앰프 하나에 고정 패턴(std 4 ADU) 주입 -> FPN 정량 회수
  (d) run_biasdiag 산출물(CSV 행수, PNG > 10KB) 확인
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from kmt_cam_char import biasdiag
from kmt_cam_char.testkit import SynthL0


def main():
    tmp = tempfile.mkdtemp(prefix="test_biasdiag_")

    # (a) 주기적 pickup -> PSD 피크 주파수 회수 ----------------------------
    kit = SynthL0(Path(tmp) / "a", seed=11)
    cyc = 8.0                                   # cycles per (full nx) row
    pa = kit.bias_set(6, prefix="pk", pickup=(1.5, cyc))
    psd = biasdiag.noise_psd(pa, kit.extnames[0], roi=kit.roi)
    assert psd["peaks"], "no PSD peak detected"
    f_true = cyc / kit.nx                       # cycles/pixel
    df = 1.0 / psd["ncols"]                     # bin width
    f_got = psd["peaks"][0]["freq_cpp"]
    assert abs(f_got - f_true) <= 1.5 * df, (f_got, f_true, df)
    # 피크 진폭도 대략적 회수 (Hann 스캘럽 손실 고려, 느슨한 창)
    a_got = psd["peaks"][0]["amp_rms_adu"]
    assert 0.7 < a_got < 2.2, a_got

    # (b) 컨트롤러 공통모드 -> 상관행렬 블록 -------------------------------
    kitb = SynthL0(Path(tmp) / "b", seed=12)
    pb = kitb.bias_set(6, prefix="sh", shared_rms=2.0)
    cm = biasdiag.corr_matrix(pb, exts=kitb.extnames, roi=kitb.roi)
    C = cm["corr"]
    n = kitb.namps
    h = n // 2
    assert np.allclose(np.diag(C), 1.0, atol=1e-6)
    within, cross = [], []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            ((within if (i < h) == (j < h) else cross).append(C[i, j]))
    assert np.mean(within) > 0.2, np.mean(within)
    assert np.max(np.abs(cross)) < 0.1, np.max(np.abs(cross))
    assert cm["ctrlid"] == [1] * h + [2] * (n - h), cm["ctrlid"]

    # (c) 한 앰프에 고정 패턴 주입 -> FPN 분리 회수 -------------------------
    kitc = SynthL0(Path(tmp) / "c", seed=13)
    target = 2
    pat = np.round(np.random.default_rng(7)
                   .standard_normal((kitc.ny, kitc.nx)) * 4.0)  # std ~4 ADU
    state = {"i": 0}

    def amap(code):
        i = state["i"]
        state["i"] += 1
        if i % kitc.namps == target:            # frame()이 앰프 순서로 호출
            return np.clip(code.astype(np.int64) + pat.astype(np.int64),
                           0, 65535)
        return code

    pc = kitc.bias_set(10, prefix="fp", adc_map=amap)
    prof_t = biasdiag.bias_profiles(pc, kitc.extnames[target],
                                    roi=kitc.roi, ovsc=kitc.ovsc)
    prof_c = biasdiag.bias_profiles(pc, kitc.extnames[0],
                                    roi=kitc.roi, ovsc=kitc.ovsc)
    assert 3.2 < prof_t["fpn_adu"] < 4.8, prof_t["fpn_adu"]   # 4 ADU 회수
    assert prof_c["fpn_adu"] < 0.8, prof_c["fpn_adu"]         # 무결 앰프
    assert abs(prof_c["rn_adu"] - 3.5) < 0.5, prof_c["rn_adu"]
    # testkit은 int16 + BZERO=32768 로 저장하고 core 계층은 헤더 BZERO를
    # 적용한 물리 unsigned ADU를 반환하므로, 합성 bias가 그대로 읽힌다.
    expect_bias = float(kitc.bias[0])
    assert abs(prof_c["bias_adu"] - expect_bias) < 1.5, \
        (prof_c["bias_adu"], expect_bias)
    assert prof_c["n_frames"] == 10
    assert len(prof_c["row_profile"]) == kitc.roi[0].stop - kitc.roi[0].start
    assert len(prof_c["col_profile"]) == kitc.roi[1].stop - kitc.roi[1].start
    # 계획서 §5.4 산출물: bias difference image(첫 쌍차분 축소 영상)와
    # drift plot 축(프레임별 중앙값 시계열)
    assert prof_c["diff_img"] is not None and prof_c["diff_img"].ndim == 2
    assert max(prof_c["diff_img"].shape) <= 320
    assert abs(float(np.mean(prof_c["diff_img"]))) < 1.0   # 쌍차분 ~0 중심
    assert len(prof_c["levels_adu"]) == prof_c["n_frames"]
    lv = np.asarray(prof_c["levels_adu"])
    assert float(np.ptp(lv)) == prof_c["bias_drift_adu"]   # drift = ptp(시계열)

    # noise_psd: 빈 입력은 불명확한 TypeError 대신 명시적 ValueError
    try:
        biasdiag.noise_psd([], kitc.extnames[0], roi=kitc.roi)
    except ValueError as e:
        assert "empty" in str(e), e
    else:
        raise AssertionError("noise_psd accepted an empty path list")

    # (d) 드라이버 산출물 ---------------------------------------------------
    out = Path(tmp) / "out"
    res = biasdiag.run_biasdiag(pc, out, campaign="TEST",
                                roi=kitc.roi, ovsc=kitc.ovsc)
    base = Path(res["outdir"])
    lines = (base / "biasdiag_TEST.csv").read_text().strip().splitlines()
    assert len(lines) == kitc.namps + 1, len(lines)           # 헤더 + 앰프행
    clines = (base / "corr_matrix_TEST.csv").read_text().strip().splitlines()
    assert len(clines) == kitc.namps + 1, len(clines)
    assert len(clines[1].split(",")) == kitc.namps + 1
    assert (base / "biasdiag_summary.png").stat().st_size > 10240
    for ext in kitc.extnames:
        p = base / "amps" / ("%s_biasdiag.png" % ext)
        assert p.exists() and p.stat().st_size > 10240, p
    # 드라이버 결과의 FPN도 직접 호출과 일치
    assert abs(res["per_amp"][kitc.extnames[target]]["profiles"]["fpn_adu"]
               - prof_t["fpn_adu"]) < 1e-9

    shutil.rmtree(tmp, ignore_errors=True)
    print("OK test_biasdiag")


if __name__ == "__main__":
    main()
