"""포화 분류·full well·persistence·셔터 타이밍 (계획서 §8, §13 일부, §15).

saturation_analysis  노출 오름차순 램프 프레임의 (t, mean, var, p99.9)로
    ① plateau 검출·원인 분류: p99.9 plateau가 65535 도달 = ADC 포화,
      65535 미만 plateau = analog front-end 포화
    ② 분산 붕괴점(연속 프레임 간 var 급락 시작 직전 프레임) = full well
      S_fw [bias-sub ADU], Q_fw = S_fw x gain [e-]
    plateau 없이 분산만 붕괴하면 FULLWELL. plateau가 있어도 분산 붕괴가
    plateau 진입 전(다음 프레임에서 코드가 아직 상승 중)에 오면 CCD full
    well이 전자부 클립보다 먼저 닿은 것으로 재분류 — 클립에 의한 분산
    붕괴는 정의상 plateau 진입 프레임에서 일어난다. p99.9가 ADC 풀스케일
    (65535)에 닿은 프레임은 단 1개여도 plateau 진입으로 간주하므로(클립은
    확정적) 램프 상단 간격에 둔감하고, 전 프레임이 포화된 램프(상승 구간
    부재, ramp_note='no-rising-segment')도 ADC/ANALOG로 분류된다.
persistence_decay    포화 직후 연속 bias의 잔류(ROI 중앙값 - 해당 프레임
    overscan 중앙값)를 순번/시각 축으로 늘어놓고 R(t) = A0 exp(-t/tau)
    log-선형 가중 적합. 헤더 DATE-OBS에 시각이 없으면 순번 x dt_sec.
shutter_fit          짧은 노출 flat들의 (t, S)를 S = R (t + dt)로 적합
    -> 셔터/트리거 오프셋 dt [ms], 광원 rate R [ADU/s].
shading_map          짧은/긴 노출 스택 비에서 위치별 유효 노출시간 지도
    [ms] (ROI 내 블록 평균, 기본 16x16 px): t_eff = (S_short/S_long) t_long,
    지도는 중앙값 대비 편차 (셔터 주행 패턴).

모든 픽셀 통계 함수는 roi/ovsc 슬라이스를 인자로 받아 축소 합성 기하
(testkit)에서도 동작한다. core.ovsc_raw는 실물 OVSC_REAL 고정이므로
여기서는 section 직접 슬라이스 + core.unsigned_from_stored 를 쓴다.

ADU 스케일: 이 모듈의 raw ADU는 core 계층(roi_raw/unsigned_from_stored)이
반환하는 BZERO/BSCALE 적용 물리 unsigned 코드(0..65535)다. 물리 코드축은
전체 16-bit 범위에서 단조이므로 CEU 전구간 포화 램프에서도 p99.9/분산이
단조이고 65535 ADC plateau 판정이 그대로 유효하다 (과거의 +32768 인볼루션
복원은 core 수정으로 불필요해져 제거). 신호 S는 프레임별 overscan 중앙값
차감 후.

CLI:
    python satshut.py --ramp 'glob' --persist 'glob' --short 'glob'
        [--long 'glob'] -o OUTDIR --campaign NAME [--gain 1.46]
        [--ampchar amp_characterization.csv] [--config VER]
산출물: OUTDIR/satshut/{satshut_summary.png, amps/<EXT>_satshut.png,
satshut_<CAMPAIGN>.csv}.
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kmt_cam_char import core  # noqa: E402

ADC_FULL_SCALE = 65535.0
PLATEAU_TOL_FRAC = 0.001     # 연속 프레임 p99.9 증가가 이보다 작으면 plateau
PLATEAU_TOL_ADU = 10.0
VAR_DROP_FRAC = 0.3          # 연속 프레임 간 분산 하락률 -> full well 후보
PERSIST_MIN_ADU = 0.05       # 지수 적합에 쓰는 최소 잔류 (중앙값 잡음 바닥)
SHADING_BLOCK = 16


# -- 저수준 접근 (축소 기하 지원: core.ovsc_raw는 OVSC_REAL 고정) ------------
def _sec_raw(exp, ext: str, rows, cols) -> np.ndarray:
    """임의 section을 물리 unsigned raw ADU(float64)로 (core 헬퍼 사용)."""
    hdu = exp.hdul[ext]
    return core.unsigned_from_stored(hdu.section[rows, cols], hdu.header)


def _ovsc_med(exp, ext: str, roi, ovsc) -> float:
    return float(np.median(_sec_raw(exp, ext, roi[0], ovsc)))


def _exptime(exp) -> float:
    return float(exp.primary.get("EXPTIME", 0) or 0)


def _epoch(header) -> float | None:
    """DATE-OBS가 시각을 포함할 때만 epoch [s] (아니면 None -> 순번 축)."""
    s = str(header.get("DATE-OBS", "")).strip()
    if "T" not in s:
        return None
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


# -- ① 포화 분류 + full well -------------------------------------------------
def saturation_analysis(ramp_paths: list, ext: str, roi=core.ROI,
                        ovsc=core.OVSC_REAL, gain: float = 1.46) -> dict:
    """노출 램프 -> plateau 분류(ADC/ANALOG)·분산 붕괴 full well.

    ramp_paths: 포화 램프 L0 경로 목록 (노출 순서 무관 — EXPTIME으로 정렬).
    반환 dict에 프레임 표(t/mean_raw/sig_adu/var_adu2/p999_raw) 포함.
    """
    stats = []
    for p in ramp_paths:
        with core.open_l0(p) as exp:
            a = core.roi_raw(exp, ext, roi=roi)
            b = _ovsc_med(exp, ext, roi, ovsc)
            m = float(np.mean(a))
            stats.append({
                "t": _exptime(exp),
                "mean_raw": m,
                "sig_adu": m - b,
                "var_adu2": core.clipped_var(a),
                "p999_raw": float(np.percentile(a, 99.9)),
                "bias_adu": b,
            })
    stats.sort(key=lambda d: (d["t"], d["mean_raw"]))
    n = len(stats)
    if n < 3:
        return {"status": "TOO_FEW_FRAMES", "n": n}
    p999 = np.array([d["p999_raw"] for d in stats])
    var = np.array([d["var_adu2"] for d in stats])
    sig = np.array([d["sig_adu"] for d in stats])
    bias = float(np.median([d["bias_adu"] for d in stats]))

    # plateau: 램프 꼬리에서 p99.9 증가가 멎은 연속 구간
    tol = np.maximum(PLATEAU_TOL_FRAC * p999[:-1], PLATEAU_TOL_ADU)
    flat_step = (p999[1:] - p999[:-1]) < tol
    k = n - 1
    while k >= 1 and flat_step[k - 1]:
        k -= 1
    # ADC 클립은 plateau 길이와 무관하게 확정적이다: p99.9가 풀스케일에 닿은
    # 첫 프레임부터 plateau 진입으로 본다 — 마지막 1개 프레임만 포화된
    # 램프도 클립으로 잡는다 (없으면 클립 기인 분산 붕괴가 FULLWELL로
    # 오분류된다).
    at_adc = p999 >= ADC_FULL_SCALE - 1.0
    if at_adc.any():
        k = min(k, int(np.argmax(at_adc)))
    plateau_idx = list(range(k, n))
    # k == 0: 상승 구간 부재(전 프레임 포화 램프 포함). plateau 자체는
    # 유효하므로 인정하고 ramp_note로 남긴다 (전 구간 포화 램프를
    # NOT_REACHED로 오분류하지 않는다).
    ramp_note = "no-rising-segment" if k == 0 else ""
    has_plateau = len(plateau_idx) >= 2 or bool(at_adc[k])
    s_plateau = float(np.median(p999[plateau_idx])) if has_plateau else 0.0

    # 분산 붕괴점: 연속 프레임 간 var가 VAR_DROP_FRAC 이상 처음 하락하는 지점
    i_fw = -1
    for i in range(n - 1):
        if var[i] > 0 and var[i + 1] < (1.0 - VAR_DROP_FRAC) * var[i]:
            i_fw = i
            break

    # 붕괴가 plateau 진입 프레임보다 앞이면 진짜 CCD full well (클립 기인
    # 붕괴는 정의상 첫 plateau 프레임 i_fw+1 == k 에서 일어난다)
    fw_first = i_fw >= 0 and (not has_plateau or i_fw + 1 < k)
    if has_plateau and not fw_first:
        kind = "ADC" if s_plateau >= ADC_FULL_SCALE - 1.0 else "ANALOG"
        s_sat = s_plateau
    elif fw_first:
        kind = "FULLWELL"          # CCD full well이 전자부 클립보다 먼저
        s_sat = float(p999[i_fw])
    else:
        kind = "NOT_REACHED"       # 램프가 포화에 못 미침 -> s_sat은 하한
        s_sat = float(p999.max())

    if i_fw >= 0:
        # 과제 정의: 분산 붕괴점 S_fw, Q_fw = S_fw x gain. 클립이 먼저면
        # 마지막 미포화 프레임 기준의 하한(clip-limited)임을 note로 남긴다.
        s_fw = float(sig[i_fw])
        fullwell_e = s_fw * float(gain)
        fw_note = "var-collapse" if fw_first else "clip-limited"
    else:
        s_fw = 0.0
        fullwell_e = max(s_sat - bias, 0.0) * float(gain)
        fw_note = "sat-limited"    # 계획서 8.3: 전자부 포화가 먼저면 상한
    return {
        "status": "OK",
        "n": n,
        "sat_kind": kind,
        "ramp_note": ramp_note,
        "s_sat_adu": s_sat,
        "s_fw_adu": s_fw,
        "fullwell_e": fullwell_e,
        "fullwell_note": fw_note,
        "i_fw": i_fw,
        "n_plateau": len(plateau_idx) if has_plateau else 0,
        "bias_adu": bias,
        "t": [d["t"] for d in stats],
        "mean_raw": [d["mean_raw"] for d in stats],
        "sig_adu": [d["sig_adu"] for d in stats],
        "var_adu2": [d["var_adu2"] for d in stats],
        "p999_raw": [d["p999_raw"] for d in stats],
    }


# -- ② persistence 감쇠 ------------------------------------------------------
def persistence_decay(bias_after_paths: list, ext: str, roi=core.ROI,
                      ovsc=core.OVSC_REAL, t0_epoch: float | None = None,
                      dt_sec: float = 45.0) -> dict:
    """포화 직후 연속 bias의 잔류 감쇠 -> R(t) = A0 exp(-t/tau) 적합.

    잔류 = ROI 중앙값 - 해당 프레임 overscan 중앙값 (bias 준위 자체 소거).
    시각: DATE-OBS에 시각이 있으면 (t0_epoch 또는 첫 프레임) 기준 상대초,
    없으면 순번 x dt_sec (레거시 판독 주기 ~45 s).
    """
    resid, epochs = [], []
    for p in bias_after_paths:
        with core.open_l0(p) as exp:
            a = core.roi_raw(exp, ext, roi=roi)
            b = _ovsc_med(exp, ext, roi, ovsc)
            resid.append(float(np.median(a)) - b)
            epochs.append(_epoch(exp.primary))
    n = len(resid)
    if n < 3:
        return {"status": "TOO_FEW_FRAMES", "n": n}
    if all(e is not None for e in epochs) and len(set(epochs)) == n:
        t0 = float(t0_epoch) if t0_epoch is not None else float(epochs[0])
        t = np.array(epochs, dtype=np.float64) - t0
        taxis = "DATE-OBS"
    else:
        t = np.arange(n, dtype=np.float64) * float(dt_sec)
        taxis = "index*%.1fs" % dt_sec
    r = np.array(resid, dtype=np.float64)
    base = {"n": n, "time_axis": taxis, "t_s": t.tolist(),
            "resid_adu": r.tolist(), "resid_max_adu": float(r.max())}
    use = r > PERSIST_MIN_ADU
    if use.sum() < 3:
        return {"status": "NO_PERSISTENCE", **base}
    tt, rr = t[use], r[use]
    # ln R = ln A0 - t/tau, 가중 w ~ R^2 (log 변환 분산 보정)
    w = rr ** 2
    A = np.column_stack([np.ones(len(tt)), -tt])
    Aw = A * w[:, None]
    try:
        cov = np.linalg.inv(A.T @ Aw)
    except np.linalg.LinAlgError:
        return {"status": "BAD_FIT", **base}
    ln_a0, inv_tau = cov @ (Aw.T @ np.log(rr))
    if inv_tau <= 0:
        return {"status": "NO_DECAY", **base}
    fit = np.exp(ln_a0) * np.exp(-tt * inv_tau)
    return {
        "status": "OK",
        "tau_s": float(1.0 / inv_tau),
        "a0_adu": float(np.exp(ln_a0)),
        "n_fit": int(use.sum()),
        "resid_rms_adu": float(np.sqrt(np.mean((rr - fit) ** 2))),
        **base,
    }


# -- ③ 셔터 타이밍 -----------------------------------------------------------
def shutter_fit(short_paths: list, ext: str, roi=core.ROI,
                ovsc=core.OVSC_REAL) -> dict:
    """짧은 노출 flat들의 (EXPTIME, S) -> S = R (t + dt) 적합.

    S = ROI 평균 - overscan 중앙값 [ADU]. 반환 dt_ms(셔터/트리거 오프셋),
    rate_adu_s(광원 rate R). 서로 다른 EXPTIME 3개 이상 필요.
    """
    ts, ss = [], []
    for p in short_paths:
        with core.open_l0(p) as exp:
            a = core.roi_raw(exp, ext, roi=roi)
            b = _ovsc_med(exp, ext, roi, ovsc)
            ts.append(_exptime(exp))
            ss.append(float(np.mean(a)) - b)
    t = np.array(ts, dtype=np.float64)
    S = np.array(ss, dtype=np.float64)
    if len(set(t.tolist())) < 3:
        return {"status": "TOO_FEW_LEVELS", "n": len(t)}
    A = np.column_stack([t, np.ones(len(t))])
    (rate, c), *_ = np.linalg.lstsq(A, S, rcond=None)
    if rate <= 0:
        return {"status": "BAD_FIT", "n": len(t)}
    fit = rate * t + c
    return {
        "status": "OK",
        "n": len(t),
        "dt_ms": float(c / rate * 1000.0),
        "rate_adu_s": float(rate),
        "resid_pct": float(np.sqrt(np.mean(
            ((S - fit) / np.maximum(np.abs(fit), 1.0)) ** 2)) * 100.0),
        "t_s": t.tolist(),
        "s_adu": S.tolist(),
    }


def _block_mean(a: np.ndarray, block: int) -> np.ndarray:
    by, bx = max(a.shape[0] // block, 1), max(a.shape[1] // block, 1)
    ky, kx = a.shape[0] // by, a.shape[1] // bx
    a = a[:by * ky, :bx * kx]
    return a.reshape(by, ky, bx, kx).mean(axis=(1, 3))


def shading_map(paths_short: list, paths_long: list, ext: str, roi=core.ROI,
                ovsc=core.OVSC_REAL, block: int = SHADING_BLOCK) -> dict:
    """짧은/긴 노출 스택 비 -> 위치별 유효 노출시간 편차 지도 [ms].

    t_eff(x,y) = (S_short/S_long) x t_long (긴 노출에선 셔터 패턴 무시 가능
    가정). map_ms = (t_eff - 중앙값) x 1000 — 셔터 주행 방향의 유효노출
    부족/과잉. ROI를 block x block 픽셀 블록 평균으로 축약해 잡음 억제.
    """
    def stack(paths):
        acc, tsum = None, 0.0
        for p in paths:
            with core.open_l0(p) as exp:
                a = core.roi_raw(exp, ext, roi=roi) - _ovsc_med(exp, ext, roi, ovsc)
                tsum += _exptime(exp)
                acc = a if acc is None else acc + a
        return acc / len(paths), tsum / len(paths)

    if not paths_short or not paths_long:
        return {"status": "NO_DATA"}
    s_short, t_short = stack(paths_short)
    s_long, t_long = stack(paths_long)
    bs = _block_mean(s_short, block)
    bl = _block_mean(s_long, block)
    if t_long <= 0 or float(np.median(bl)) <= 0:
        return {"status": "NO_SIGNAL"}
    t_eff = bs / np.maximum(bl, 1e-9) * t_long          # [s]
    map_ms = (t_eff - float(np.median(t_eff))) * 1000.0
    return {
        "status": "OK",
        "map_ms": map_ms,
        "block": int(block),
        "t_short_s": float(t_short),
        "t_long_s": float(t_long),
        "t_eff_med_ms": float(np.median(t_eff)) * 1000.0,
        "pp_ms": float(np.ptp(map_ms)),
    }


# -- 플롯 (matplotlib은 여기서만) --------------------------------------------
def _no_data(ax, res):
    ax.text(0.5, 0.5, str(res.get("status", "NO_DATA")),
            ha="center", va="center", transform=ax.transAxes, color="gray")


def plot_amp_page(path, ext: str, campaign: str, sat: dict, pers: dict,
                  shut: dict) -> None:
    """앰프별 진단 페이지: 포화 분류 / PTC turnover / persistence / dt 적합."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    fig.suptitle("%s saturation / persistence / shutter — %s"
                 % (ext, campaign))

    ax = axes[0, 0]
    if sat.get("status") == "OK":
        t = np.array(sat["t"])
        ax.plot(t, sat["p999_raw"], "o-", label="p99.9 raw")
        ax.plot(t, sat["mean_raw"], "s--", ms=4, label="mean raw")
        ax.axhline(ADC_FULL_SCALE, color="gray", ls=":", lw=1,
                   label="ADC full scale")
        if sat["sat_kind"] != "NOT_REACHED":
            ax.axhline(sat["s_sat_adu"], color="red", ls="--", lw=1)
        ax.set_title("Saturation: %s  S_sat=%.0f ADU"
                     % (sat["sat_kind"], sat["s_sat_adu"]), fontsize=10)
        ax.legend(fontsize=7)
    else:
        _no_data(ax, sat)
    ax.set_xlabel("EXPTIME [s]")
    ax.set_ylabel("raw ADU")

    ax = axes[0, 1]
    if sat.get("status") == "OK":
        sig = np.array(sat["sig_adu"])
        var = np.array(sat["var_adu2"])
        ax.plot(sig, var, "o-")
        if sat["i_fw"] >= 0:
            i = sat["i_fw"]
            ax.plot([sig[i]], [var[i]], "r*", ms=14,
                    label="full well S_fw=%.0f ADU" % sat["s_fw_adu"])
            ax.legend(fontsize=7)
        ax.set_title("PTC turnover (Q_fw=%.0f e-, %s)"
                     % (sat["fullwell_e"], sat["fullwell_note"]), fontsize=10)
    else:
        _no_data(ax, sat)
    ax.set_xlabel("signal S [ADU, bias-sub]")
    ax.set_ylabel("variance [ADU^2]")

    ax = axes[1, 0]
    if pers.get("t_s"):
        t = np.array(pers["t_s"])
        r = np.array(pers["resid_adu"])
        ax.plot(t, r, "o", label="median residual")
        if pers.get("status") == "OK":
            tg = np.linspace(t.min(), t.max(), 200)
            ax.plot(tg, pers["a0_adu"] * np.exp(-tg / pers["tau_s"]), "r-",
                    label="fit tau=%.1f s A0=%.1f ADU"
                          % (pers["tau_s"], pers["a0_adu"]))
        if (r > 0).all():
            ax.set_yscale("log")
        ax.legend(fontsize=7)
        ax.set_title("Persistence decay (%s)" % pers.get("time_axis", ""),
                     fontsize=10)
    else:
        _no_data(ax, pers)
    ax.set_xlabel("time after saturation [s]")
    ax.set_ylabel("residual [ADU]")

    ax = axes[1, 1]
    if shut.get("status") == "OK":
        t = np.array(shut["t_s"])
        S = np.array(shut["s_adu"])
        ax.plot(t, S, "o")
        tg = np.linspace(min(t.min(), 0), t.max(), 100)
        r = shut["rate_adu_s"]
        ax.plot(tg, r * (tg + shut["dt_ms"] / 1000.0), "r-",
                label="S=R(t+dt): dt=%.1f ms R=%.0f ADU/s"
                      % (shut["dt_ms"], shut["rate_adu_s"]))
        ax.legend(fontsize=7)
        ax.set_title("Shutter offset fit", fontsize=10)
    else:
        _no_data(ax, shut)
    ax.set_xlabel("EXPTIME [s]")
    ax.set_ylabel("signal S [ADU]")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _axis_metric(ax, rows, key, label):
    ampid = np.array([r["ampid"] for r in rows], dtype=float)
    v = np.array([float(r.get(key) or 0.0) for r in rows], dtype=float)
    ok = np.isfinite(v)
    med = float(np.median(v[ok])) if ok.any() else 0.0
    mad = float(1.4826 * np.median(np.abs(v[ok] - med))) if ok.any() else 0.0
    out = ok & (np.abs(v - med) > 5 * mad) if mad > 0 else np.zeros_like(ok)
    ax.plot(ampid[ok & ~out], v[ok & ~out], "o", color="tab:blue", ms=4)
    if out.any():
        ax.plot(ampid[out], v[out], "o", color="red", ms=5)
    ax.axhline(med, color="gray", ls=":", lw=1)
    ax.set_xlabel("AMPID")
    ax.set_ylabel(label)


def plot_summary(path, campaign: str, rows: list[dict],
                 shading: dict | None) -> None:
    """카메라 요약: 지표 vs AMPID (outlier 빨강) + shading map 1장."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.5))
    fig.suptitle("Saturation / persistence / shutter summary — %s" % campaign)
    _axis_metric(axes[0, 0], rows, "s_sat_adu", "S_sat [raw ADU]")
    axes[0, 0].set_title("saturation level", fontsize=10)
    _axis_metric(axes[0, 1], rows, "fullwell_e", "full well [e-]")
    axes[0, 1].set_title("full well", fontsize=10)
    _axis_metric(axes[0, 2], rows, "persist_tau_s", "persistence tau [s]")
    axes[0, 2].set_title("persistence decay", fontsize=10)
    _axis_metric(axes[1, 0], rows, "shutter_dt_ms", "shutter dt [ms]")
    axes[1, 0].set_title("shutter offset", fontsize=10)
    _axis_metric(axes[1, 1], rows, "rate_adu_s", "rate R [ADU/s]")
    axes[1, 1].set_title("lamp rate (shutter set)", fontsize=10)
    ax = axes[1, 2]
    if shading and shading.get("status") == "OK":
        im = ax.imshow(shading["map_ms"], origin="lower", aspect="auto",
                       cmap="coolwarm")
        fig.colorbar(im, ax=ax, label="t_eff - median [ms]")
        ax.set_title("shutter shading map (%dx%d px blocks, p-p %.2f ms)"
                     % (shading["block"], shading["block"], shading["pp_ms"]),
                     fontsize=9)
        ax.set_xlabel("block X")
        ax.set_ylabel("block Y")
    else:
        _no_data(ax, shading or {})
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=110)
    plt.close(fig)


# -- 오케스트레이션 + CSV ----------------------------------------------------
CSV_FIELDS = ["extname", "ampid", "sat_kind", "s_sat_adu", "fullwell_e",
              "gain_e_adu", "persist_tau_s", "persist_a0_adu",
              "shutter_dt_ms", "rate_adu_s", "campaign", "date", "config"]


def load_ampchar(path) -> dict:
    """amp characterization CSV (results/README.md §1 스키마) ->
    {EXTNAME: {'gain' [e-/ADU]}}. 무효(<=0/결측) 값은 생략."""
    import csv as _csv
    out: dict = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            ext = str(row.get("EXTNAME", "")).strip()
            try:
                g = float(row.get("GAIN", ""))
            except (TypeError, ValueError):
                continue
            if ext and g > 0:
                out[ext] = {"gain": g}
    return out


def run_satshut(ramp_paths: list, persist_paths: list, short_paths: list,
                long_paths: list | None, outdir, campaign: str,
                gain: float = 1.46, roi=core.ROI,
                ovsc=core.OVSC_REAL, ampchar: dict | None = None,
                config: str = "") -> dict:
    """전 앰프 실행 -> satshut/ 아래 summary/amp PNG + CSV. dict 반환.

    ampchar: {EXTNAME: {'gain'}} — Q_fw 계산용 앰프별 실측 gain 주입
    (load_ampchar 참조). 없는 앰프는 스칼라 ``gain`` 폴백."""
    out = Path(outdir) / "satshut"
    (out / "amps").mkdir(parents=True, exist_ok=True)
    with core.open_l0(ramp_paths[0]) as exp:
        extnames = list(exp.amp_names)
        ampids = {g.extname: g.ampid for g in exp.amps}
        date = str(exp.primary.get("DATE-OBS", "")).strip()

    rows, per_amp = [], {}
    for ext in extnames:
        g_amp = float((ampchar or {}).get(ext, {}).get("gain", 0) or 0)
        if g_amp <= 0:
            g_amp = float(gain)
        sat = saturation_analysis(ramp_paths, ext, roi=roi, ovsc=ovsc,
                                  gain=g_amp)
        pers = (persistence_decay(persist_paths, ext, roi=roi, ovsc=ovsc)
                if persist_paths else {"status": "NO_DATA"})
        shut = (shutter_fit(short_paths, ext, roi=roi, ovsc=ovsc)
                if short_paths else {"status": "NO_DATA"})
        plot_amp_page(out / "amps" / ("%s_satshut.png" % ext), ext, campaign,
                      sat, pers, shut)
        rows.append({
            "extname": ext,
            "ampid": ampids.get(ext, 0),
            "sat_kind": sat.get("sat_kind", sat.get("status", "NO_DATA")),
            "s_sat_adu": round(float(sat.get("s_sat_adu", 0.0)), 1),
            "fullwell_e": round(float(sat.get("fullwell_e", 0.0)), 1),
            "gain_e_adu": round(g_amp, 4),
            "persist_tau_s": round(float(pers.get("tau_s", 0.0)), 2),
            "persist_a0_adu": round(float(pers.get("a0_adu", 0.0)), 2),
            "shutter_dt_ms": round(float(shut.get("dt_ms", 0.0)), 2),
            "rate_adu_s": round(float(shut.get("rate_adu_s", 0.0)), 2),
            "campaign": campaign,
            "date": date,
            "config": config,
        })
        per_amp[ext] = {"sat": sat, "pers": pers, "shut": shut}

    shading = (shading_map(short_paths, long_paths, extnames[0], roi=roi,
                           ovsc=ovsc)
               if short_paths and long_paths else None)
    plot_summary(out / "satshut_summary.png", campaign, rows, shading)

    csv_path = out / ("satshut_%s.csv" % campaign)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return {"rows": rows, "per_amp": per_amp, "shading": shading,
            "csv": str(csv_path), "outdir": str(out)}


def main(argv=None) -> int:
    import argparse
    import glob

    ap = argparse.ArgumentParser(
        description="Saturation classification / full well / persistence / "
                    "shutter timing (plan sections 8, 13, 15)")
    ap.add_argument("--ramp", required=True,
                    help="saturation ramp L0 glob (exptime ascending set)")
    ap.add_argument("--persist", required=True,
                    help="post-saturation consecutive bias L0 glob")
    ap.add_argument("--short", required=True,
                    help="short-exposure shutter flat L0 glob")
    ap.add_argument("--long", default=None,
                    help="long reference flat L0 glob (shading map)")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--config", default="",
                    help="Archon config version recorded in the config column")
    ap.add_argument("--gain", type=float, default=1.46,
                    help="fallback e-/ADU for Q_fw when --ampchar is absent "
                         "or lacks an amp")
    ap.add_argument("--ampchar", default=None,
                    help="amp characterization CSV (EXTNAME/GAIN) for "
                         "per-amp measured gain in Q_fw")
    a = ap.parse_args(argv)

    ramp = sorted(glob.glob(a.ramp))
    persist = sorted(glob.glob(a.persist))
    short = sorted(glob.glob(a.short))
    long_ = sorted(glob.glob(a.long)) if a.long else None
    if not ramp:
        ap.error("--ramp matched no files")
    ampchar = load_ampchar(a.ampchar) if a.ampchar else None
    res = run_satshut(ramp, persist, short, long_, a.outdir, a.campaign,
                      gain=a.gain, ampchar=ampchar, config=a.config)
    print("[%s] wrote %s (%d amps) -> %s"
          % (a.campaign, res["csv"], len(res["rows"]), res["outdir"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
