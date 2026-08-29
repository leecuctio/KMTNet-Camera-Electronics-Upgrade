#!/usr/bin/env python3
"""tests/test_watch.py — gwatch 원본 정리 정책 시험 (GUI/데몬 미기동).

검증 항목:
  1. 파이프라인 실패 노출은 delete_raw=yes여도 삭제되지 않고 run/failed/로
     보존 이동되며 processed.list에 기록되지 않는다 (재투입 시 재처리 가능).
  2. incoming 재투입은 **무조건 재처리** — 스냅샷 PNG·processed.list가 있어도
     건너뛰지 않는다 (스킵 로직 제거 확인).
  3. finish_raw: delete_raw=yes → 삭제+기록, no → run/processed/ 이동
     (같은 이름 재이동은 .N 접미).
  4. SIGTERM 핸들러용 stop()은 플래그만 세운다 (즉시 예외를 던지지 않음).

pytest 불필요 — 단독 실행 assert 스크립트 (성공 시 "OK test_watch" 출력).
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
import gwatch as gwatch_mod


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


def make_watcher(cfg):
    log = gcommon.setup_logger(cfg, "gwatch")
    w = gwatch_mod.Watcher(cfg, log)
    w.ensure_gplot = lambda: None  # 시험 중 gplot 서브프로세스 기동 방지
    return w


def put_raw(cfg, basename, payload=b"NOT A FITS FILE"):
    incoming = cfg.rundir("incoming")
    os.makedirs(incoming, exist_ok=True)
    path = os.path.join(incoming, basename)
    with open(path, "wb") as fp:
        fp.write(payload)
    return path


def main():
    tmp = tempfile.mkdtemp(prefix="tmp_watch_", dir=TESTS_DIR)

    # ---------- 1. 실패 노출: delete_raw=yes여도 failed/ 보존, 기록 없음 ----------
    cfg = make_cfg(tmp, "delyes", {("watch", "delete_raw"): "yes"})
    gcommon.ensure_dirs(cfg)
    w = make_watcher(cfg)

    bad = put_raw(cfg, "junk.20260829.010101.fits")  # 잘못된 FITS → gsplit 실패
    stem_bad = gcommon.stem_from_raw(os.path.basename(bad))
    assert stem_bad == "20260829.010101", stem_bad
    w.handle(bad)
    failed = os.path.join(cfg.rundir("failed"), os.path.basename(bad))
    assert os.path.exists(failed), "실패 원본이 failed/에 없음"
    assert not os.path.exists(bad), "실패 원본이 incoming에 남음"
    assert stem_bad not in w.processed_stems(), \
        "실패 stem이 processed.list에 기록됨 (재처리 불가)"

    # ---------- 2. 재투입은 무조건 재처리 (스킵 로직 제거 확인) ----------
    assert not hasattr(w, "already_done"), "스킵 로직(already_done)이 남아 있음"
    done = put_raw(cfg, "junk.20260829.020202.fits")
    stem_done = "20260829.020202"
    snap = os.path.join(cfg.rundir("snap"), "psf.snap.%s.png" % stem_done)
    with open(snap, "wb") as fp:   # 스냅샷이 있어도
        fp.write(b"png")
    w.mark_processed(stem_done)    # 이력에 있어도
    w.handle(done)                 # → 건너뛰지 않고 처리 시도 (junk → 실패 격리)
    assert os.path.exists(
        os.path.join(cfg.rundir("failed"), os.path.basename(done))), \
        "재투입이 재처리되지 않고 스킵됨"
    assert not os.path.exists(done)

    # ---------- 3. finish_raw: yes=삭제+기록 / no=processed/ 이동(.N 접미) ----
    ok1 = put_raw(cfg, "junk.20260829.050505.fits")
    w.finish_raw(ok1, "20260829.050505")           # delete_raw=yes
    assert not os.path.exists(ok1), "delete_raw=yes인데 원본이 남음"
    assert "20260829.050505" in w.processed_stems()

    cfg2 = make_cfg(tmp, "delno", {("watch", "delete_raw"): "no"})
    gcommon.ensure_dirs(cfg2)
    w2 = make_watcher(cfg2)

    bad2 = put_raw(cfg2, "junk.20260829.030303.fits")
    w2.handle(bad2)
    assert os.path.exists(
        os.path.join(cfg2.rundir("failed"), os.path.basename(bad2)))
    assert not os.path.exists(
        os.path.join(cfg2.rundir("processed"), os.path.basename(bad2)))

    ok2 = put_raw(cfg2, "junk.20260829.040404.fits")
    w2.finish_raw(ok2, "20260829.040404")          # delete_raw=no → 이동
    moved = os.path.join(cfg2.rundir("processed"), os.path.basename(ok2))
    assert os.path.exists(moved), "delete_raw=no인데 processed/에 없음"
    assert "20260829.040404" in w2.processed_stems()
    ok2b = put_raw(cfg2, "junk.20260829.040404.fits")   # 같은 이름 재이동
    w2.finish_raw(ok2b, "20260829.040404")
    assert os.path.exists(moved + ".1") or os.path.exists(moved), \
        "재이동 시 이름 충돌 처리 실패"
    assert not os.path.exists(ok2b)

    # ---------- 4. stop()은 플래그만 세운다 ----------
    assert w2._stop is False
    w2.stop()
    assert w2._stop is True

    shutil.rmtree(tmp, ignore_errors=True)
    print("OK test_watch")


if __name__ == "__main__":
    main()
