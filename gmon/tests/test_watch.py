#!/usr/bin/env python3
"""tests/test_watch.py — gwatch 원본 정리 정책 시험 (GUI/데몬 미기동).

검증 항목:
  1. 파이프라인 실패 노출은 delete_raw=yes여도 삭제되지 않고 run/failed/로
     보존 이동되며 processed.list에 기록되지 않는다 (재투입 시 재처리 가능).
  2. 이미 처리된 노출(스냅샷 PNG 존재)은 finish_raw 경로: delete_raw=yes면
     삭제 + processed.list 기록.
  3. delete_raw=no면 성공/스킵 원본은 run/processed/로 이동.
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

    # 재투입하면 다시 처리 대상이 된다 (already_done 아님)
    assert not w.already_done(stem_bad)

    # ---------- 2. 스킵(이미 처리) 노출: delete_raw=yes → 삭제 + 기록 ----------
    done = put_raw(cfg, "junk.20260829.020202.fits")
    stem_done = "20260829.020202"
    snap = os.path.join(cfg.rundir("snap"), "psf.snap.%s.png" % stem_done)
    with open(snap, "wb") as fp:  # 스냅샷 존재 → already_done
        fp.write(b"png")
    w.handle(done)
    assert not os.path.exists(done), "스킵 원본이 삭제되지 않음"
    assert stem_done in w.processed_stems(), "스킵 stem 미기록"
    assert not os.path.exists(
        os.path.join(cfg.rundir("failed"), os.path.basename(done)))

    # ---------- 3. delete_raw=no: 실패는 failed/, 스킵은 processed/ ----------
    cfg2 = make_cfg(tmp, "delno", {("watch", "delete_raw"): "no"})
    gcommon.ensure_dirs(cfg2)
    w2 = make_watcher(cfg2)

    bad2 = put_raw(cfg2, "junk.20260829.030303.fits")
    w2.handle(bad2)
    assert os.path.exists(
        os.path.join(cfg2.rundir("failed"), os.path.basename(bad2)))
    assert not os.path.exists(
        os.path.join(cfg2.rundir("processed"), os.path.basename(bad2)))

    done2 = put_raw(cfg2, "junk.20260829.040404.fits")
    stem_done2 = "20260829.040404"
    snap2 = os.path.join(cfg2.rundir("snap"), "psf.snap.%s.png" % stem_done2)
    with open(snap2, "wb") as fp:
        fp.write(b"png")
    w2.handle(done2)
    assert os.path.exists(
        os.path.join(cfg2.rundir("processed"), os.path.basename(done2)))
    assert stem_done2 in w2.processed_stems()

    # ---------- 4. stop()은 플래그만 세운다 ----------
    assert w2._stop is False
    w2.stop()
    assert w2._stop is True

    shutil.rmtree(tmp, ignore_errors=True)
    print("OK test_watch")


if __name__ == "__main__":
    main()
