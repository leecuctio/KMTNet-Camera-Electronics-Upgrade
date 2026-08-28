#!/usr/bin/env python3
"""tests/test_focus.py — FocusController 단독 시험 (GUI 미기동, DESIGN.md §8).

임시 runroot를 가리키는 gmon.conf 사본을 만들어 시험한다. pytest 불필요 —
단독 실행 assert 스크립트 (실패 시 비0 종료, 성공 시 "OK test_focus" 출력).
"""
import configparser
import os
import shutil
import sys
import tempfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
GMON_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, GMON_DIR)

import gcommon
import gmon as gmon_mod

# gmon import는 headless 안전해야 한다 (Tk는 main() 안에서만)
assert "tkinter" not in sys.modules, "gmon import가 tkinter를 끌어들임"


def make_cfg(tmp, name, overrides=None):
    """gmon.conf 사본을 만들어 runroot만 임시 디렉토리로 교체."""
    cp = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    with open(os.path.join(GMON_DIR, "gmon.conf"), encoding="utf-8") as fp:
        cp.read_file(fp)
    cp.set("paths", "runroot", os.path.join(tmp, name + "_run"))
    cp.set("paths", "configdir", os.path.join(GMON_DIR, "config"))
    for (sec, key), val in (overrides or {}).items():
        cp.set(sec, key, val)
    path = os.path.join(tmp, name + ".conf")
    with open(path, "w", encoding="utf-8") as fp:
        cp.write(fp)
    return gcommon.load_config(path)


def write_fw(cfg, *lines):
    path = gcommon.fw_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fp:
        for ln in lines:
            fp.write(ln + "\n")


def main():
    tmp = tempfile.mkdtemp(prefix="tmp_focus_", dir=TESTS_DIR)

    # ---------- 1. compute_ref 공식 + fw 파일 파싱 ----------
    cfg = make_cfg(tmp, "default")  # slope=-0.067 base=5.56 dfocus=0 (운용판 기본값)
    captured = []
    c1 = gmon_mod.FocusController(cfg, sender=captured.append)

    # fw 파일 없음 → None / try_send는 no-fw
    assert c1.compute_ref() is None
    sent, reason = c1.try_send(manual=True)
    assert sent is False and reason == "no-fw"

    # fw 줄: 시각 fwN fwE fwW fwS FOCUS TEMP SECZ — TEMP는 공백분리 7번째 필드
    write_fw(cfg, "22:23:35:21 1.50 1.60 1.70 1.80 -5.950 15.5 1.15")
    ref = c1.compute_ref()
    assert ref is not None and abs(ref - (-0.067 * 15.5 - 5.56)) < 1e-9, ref
    # FOCUS(-5.95)가 아니라 TEMP(15.5)를 썼는지 파싱 필드로 재확인
    assert abs(c1.last_fw["temp"] - 15.5) < 1e-12
    assert abs(c1.last_fw["focus"] - (-5.95)) < 1e-12
    assert abs(c1.last_fw["secz"] - 1.15) < 1e-12

    # 여러 줄이면 마지막 줄 사용
    with open(gcommon.fw_path(cfg), "a") as fp:
        fp.write("22:23:40:00 1.0 1.0 1.0 1.0 -5.900 16.0 1.20\n")
    ref = c1.compute_ref()
    assert abs(ref - (-0.067 * 16.0 - 5.56)) < 1e-9, ref

    # ---------- 2. 안전범위 (양쪽 모두) + 경계값 ----------
    # 이진 소수로 정확한 값이 나오도록 slope=-0.5, base=5.0 사용 (안전범위는
    # 운용판 기본 -8.0~-5.0): ref = -0.5*T - 5.0
    # → T=6.5:-8.25, T=6.0:-8.0, T=0.0:-5.0, T=-1.5:-4.25
    cfg2 = make_cfg(tmp, "bound", {("focus", "slope"): "-0.5",
                                   ("focus", "base"): "5.0"})
    state = {"temp": 0.0}
    got = []
    c2 = gmon_mod.FocusController(cfg2, sender=got.append,
                                  fw_reader=lambda: {"temp": state["temp"]})
    state["temp"] = 6.5     # ref=-8.25 < safe_min(-8.0) → 차단
    sent, reason = c2.try_send(manual=True)
    assert sent is False and reason.startswith("unsafe") and not got

    state["temp"] = -1.5    # ref=-4.25 > safe_max(-5.0) → 차단
    sent, reason = c2.try_send(manual=True)
    assert sent is False and reason.startswith("unsafe") and not got

    state["temp"] = 6.0     # ref=-8.0 경계 → 허용 (범위는 포함)
    sent, reason = c2.try_send(manual=True)
    assert sent is True and abs(got[-1] - (-8.0)) < 1e-12

    state["temp"] = 0.0     # ref=-5.0 경계 → 허용
    sent, reason = c2.try_send(manual=True)
    assert sent is True and abs(got[-1] - (-5.0)) < 1e-12
    assert len(got) == 2

    # ---------- 3. AUTO: 첫 전송 허용, |Δ| >= max_jump(0.1)면 그 주기만 보류 ----
    # 레거시(old/gmon runcmd) 의미: 비교 기준(dref)은 전송 여부와 무관하게 매 주기
    # 최신 계산값으로 갱신 → 점프는 한 주기만 건너뛰고 다음 주기에 전송 재개.
    state3 = {"temp": 2.0}
    got3 = []
    c3 = gmon_mod.FocusController(cfg2, sender=got3.append,
                                  fw_reader=lambda: {"temp": state3["temp"]})
    sent, reason = c3.try_send()            # 첫 AUTO 전송 → 허용
    assert sent is True and abs(got3[-1] - (-6.0)) < 1e-12

    state3["temp"] = 2.4                    # ref=-6.2, Δ=0.2 → 보류
    sent, reason = c3.try_send()
    assert sent is False and reason.startswith("jump") and len(got3) == 1
    assert abs(c3.last_ref - (-6.2)) < 1e-12  # 보류해도 기준은 갱신 (레거시 dref)

    sent, reason = c3.try_send()            # 같은 온도 다음 주기: Δ=0 → 전송 재개
    assert sent is True and abs(got3[-1] - (-6.2)) < 1e-9 and len(got3) == 2

    state3["temp"] = 2.5                    # ref=-6.25, Δ=0.05 < 0.1 → 전송
    sent, reason = c3.try_send()
    assert sent is True and abs(got3[-1] - (-6.25)) < 1e-9 and len(got3) == 3

    # ---------- 4. MAN은 max_jump 무시 (안전범위만 검사) ----------
    state3["temp"] = 4.0                    # ref=-7.0, 직전 -6.25에서 Δ=0.75
    sent, reason = c3.try_send(manual=True)
    assert sent is True and abs(got3[-1] - (-7.0)) < 1e-9
    assert abs(c3.last_ref - (-7.0)) < 1e-9  # MAN 전송도 last_ref 갱신

    state3["temp"] = 4.02                   # ref=-7.01, Δ=0.01 → AUTO 재개 가능
    sent, reason = c3.try_send()
    assert sent is True and abs(got3[-1] - (-7.01)) < 1e-9

    # ---------- 4b. 안전범위 밖·보류에서도 기준 갱신 (영구 보류 없음) ----------
    state3["temp"] = 7.0                    # ref=-8.5 < safe_min → 차단
    sent, reason = c3.try_send()
    assert sent is False and reason.startswith("unsafe")
    assert abs(c3.last_ref - (-8.5)) < 1e-9  # unsafe여도 기준 갱신 (레거시 dref)

    state3["temp"] = 5.9                    # ref=-7.95 (안전), Δ=0.55 → 한 주기 보류
    sent, reason = c3.try_send()
    assert sent is False and reason.startswith("jump")

    sent, reason = c3.try_send()            # 다음 주기: Δ=0 → 전송 재개
    assert sent is True and abs(got3[-1] - (-7.95)) < 1e-9

    # ---------- 5. 기본 sender + dry_run=yes → 소켓을 열지 않음 ----------
    c4 = gmon_mod.FocusController(cfg)      # sender 미주입 → _udp_send
    assert c4.dry_run is True               # gmon.conf 기본값
    assert c4._sender == c4._udp_send
    real_socket = gmon_mod.socket.socket
    def _no_socket(*a, **k):
        raise AssertionError("dry_run인데 socket이 열림")
    gmon_mod.socket.socket = _no_socket
    try:
        sent, reason = c4.try_send(manual=True)  # fw temp=16.0 → ref=-6.632 (안전)
    finally:
        gmon_mod.socket.socket = real_socket
    assert sent is True
    # dry_run 분기 직접 확인: 마커 반환, 전송 없음
    assert c4._udp_send(-5.0) == "dry-run"

    # ---------- 6. incr/decr ↔ gcommon.read_dfocus 라운드트립 ----------
    c5 = gmon_mod.FocusController(cfg)
    assert abs(c5.dfocus - 0.0) < 1e-12     # dfocus.txt 없음 → conf 기본 0.0
    v = c5.incr()
    assert abs(v - 0.005) < 1e-9              # 운용판 step=0.005
    assert abs(gcommon.read_dfocus(cfg) - 0.005) < 1e-9
    c5.decr()
    c5.decr()
    assert abs(c5.dfocus - (-0.005)) < 1e-9
    assert abs(gcommon.read_dfocus(cfg) - (-0.005)) < 1e-9
    # big adjust (운용판 2021-01): ±big_step(0.5)
    c5.incr_big()
    assert abs(c5.dfocus - 0.495) < 1e-9
    c5.decr_big()
    assert abs(c5.dfocus - (-0.005)) < 1e-9
    # dfocus가 공식에 반영: ref = -0.067*16.0 - (5.56 - 0.005)
    ref = c5.compute_ref()
    assert abs(ref - (-0.067 * 16.0 - 5.555)) < 1e-9, ref
    # 새 컨트롤러도 영속값을 읽음
    c6 = gmon_mod.FocusController(cfg)
    assert abs(c6.dfocus - (-0.005)) < 1e-9

    # ---------- 7. latest_snapshot: run/snap의 최신 PNG 선택 ----------
    cfg7 = make_cfg(tmp, "snap")
    gcommon.ensure_dirs(cfg7)
    p, m = gmon_mod.latest_snapshot(cfg7)
    assert p is None and m == 0.0
    snapdir = cfg7.rundir("snap")
    pa = os.path.join(snapdir, "psf.snap.aaa.png")
    pb = os.path.join(snapdir, "psf.snap.bbb.png")
    for path in (pa, pb):
        with open(path, "wb") as fp:
            fp.write(b"png")
    os.utime(pa, (1000, 1000))
    os.utime(pb, (2000, 2000))
    p, m = gmon_mod.latest_snapshot(cfg7)
    assert p == pb and m == 2000.0, (p, m)

    shutil.rmtree(tmp, ignore_errors=True)
    print("OK test_focus")


if __name__ == "__main__":
    main()
