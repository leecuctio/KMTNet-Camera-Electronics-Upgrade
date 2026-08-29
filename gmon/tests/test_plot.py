#!/usr/bin/env python3
"""gplot(--oneshot png)·gsnap(--backend mpl) 렌더 시험.

pytest 불필요 — 단독 실행 assert 스크립트. 임시 runroot를 가리키는 gmon.conf
사본을 만들어 gmon/run/ 을 오염시키지 않는다. 성공 시 "OK test_plot" 출력.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GMON = os.path.dirname(HERE)
PY = sys.executable


def make_conf(tmp, name="gmon.conf", refresh_sec=None):
    """runroot/configdir를 절대경로로 돌린 gmon.conf 사본 경로."""
    with open(os.path.join(GMON, "gmon.conf"), encoding="utf-8") as fp:
        text = fp.read()
    runroot = os.path.join(tmp, "run")
    text = re.sub(r"(?m)^runroot\s*=.*$", "runroot   = %s" % runroot, text)
    text = re.sub(r"(?m)^configdir\s*=.*$",
                  "configdir = %s" % os.path.join(GMON, "config"), text)
    if refresh_sec is not None:
        text = re.sub(r"(?m)^refresh_sec\s*=.*$",
                      "refresh_sec = %s" % refresh_sec, text)
    conf = os.path.join(tmp, name)
    with open(conf, "w", encoding="utf-8") as fp:
        fp.write(text)
    return conf


def make_snap(path, fwhm_px=3.0, amp=1.0, seed=0):
    """25×25 가우시안 스냅샷 FITS (psfex snap_* 대역)."""
    from astropy.io import fits
    y, x = np.mgrid[0:25, 0:25]
    sig = fwhm_px / 2.3548
    g = amp * np.exp(-((x - 12.0) ** 2 + (y - 12.0) ** 2) / (2 * sig * sig))
    g += np.random.default_rng(seed).normal(0, 0.005, g.shape)
    fits.PrimaryHDU(g.astype(np.float32)).writeto(path, overwrite=True)


def make_result(tmp, stem, bad_chip=None):
    """합성 result.<stem>.json (DESIGN.md §5.4). 경로 반환."""
    chips = {}
    for i, c in enumerate("nesw"):
        snap = os.path.join(tmp, "snap_KMTNg%s.%s.psfex.fits" % (c, stem))
        make_snap(snap, fwhm_px=3.0 + 0.3 * i, seed=i)
        chips[c] = {"fwhm_px": 3.5 + 0.1 * i, "fwhm_as": 1.82 + 0.05 * i,
                    "sd": 400.0 + 10 * i,
                    "psf_file": "", "snap_file": snap, "ok": True}
    if bad_chip:
        chips[bad_chip] = {"fwhm_px": 0.0, "fwhm_as": 0.0, "sd": 0.0,
                           "psf_file": "", "snap_file": "", "ok": False}
    res = {
        "stem": stem,
        "raw_file": "modtm.%s.fits" % stem,
        "chips": chips,
        "fwavg_as": 1.86,
        "header": {"SECZ": "1.15", "FOCUS": "-5.950", "TILTEW": "0.010",
                   "TILTNS": "0.020", "ESW": "1.1 2.2 3.3",
                   "T123": "10.1 11.2 12.3", "ALT": "45.0", "AZ": "120.0",
                   "DATEOBS": "2026-08-29", "TIMEOBS": "03:14:29"},
    }
    path = os.path.join(tmp, "result.%s.json" % stem)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(res, fp)
    return path


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode, r.stdout.decode(errors="replace")


def main():
    tmp = tempfile.mkdtemp(prefix="tmp_plot_", dir=HERE)
    conf = make_conf(tmp)

    # [1] gplot --oneshot --term png : 레거시 fw 데이터로 PNG 렌더
    fwpng = os.path.join(tmp, "fw.png")
    rc, out = run([PY, os.path.join(GMON, "gplot.py"), "-c", conf,
                   "--oneshot", "--term", "png",
                   "--datafile", os.path.join(GMON, "old", "fw181022.dat"),
                   "--out", fwpng])
    assert rc == 0, "gplot rc=%d\n%s" % (rc, out)
    assert os.path.exists(fwpng), "fw.png 미생성\n%s" % out
    assert os.path.getsize(fwpng) > 10 * 1024, \
        "fw.png too small: %d" % os.path.getsize(fwpng)

    # [1b] --size WxH: 지정 크기로 렌더 (GUI 창 크기 추종 경로)
    import matplotlib.image as mpimg
    fwpng2 = os.path.join(tmp, "fw2.png")
    rc, out = run([PY, os.path.join(GMON, "gplot.py"), "-c", conf,
                   "--oneshot", "--term", "png", "--size", "500x300",
                   "--datafile", os.path.join(GMON, "old", "fw181022.dat"),
                   "--out", fwpng2])
    assert rc == 0, "gplot --size rc=%d\n%s" % (rc, out)
    shape = mpimg.imread(fwpng2).shape
    assert shape[0] == 300 and shape[1] == 500, shape

    # [2] gsnap --backend mpl : 합성 스냅샷 4장 → 3×3 PNG
    res1 = make_result(tmp, "20260829.031429")
    snap1 = os.path.join(tmp, "snap1.png")
    rc, out = run([PY, os.path.join(GMON, "gsnap.py"), res1, "-c", conf,
                   "--backend", "mpl", "--out", snap1])
    assert rc == 0, "gsnap rc=%d\n%s" % (rc, out)
    assert os.path.exists(snap1) and os.path.getsize(snap1) > 10 * 1024, \
        "snap1.png 미생성/과소: %s" % out

    # [2b] --out 없이 기본 경로(run/snap/psf.snap.<stem>.png) 확인
    rc, out = run([PY, os.path.join(GMON, "gsnap.py"), res1, "-c", conf,
                   "--backend", "mpl"])
    assert rc == 0, "gsnap(기본 경로) rc=%d\n%s" % (rc, out)
    defpng = os.path.join(tmp, "run", "snap", "psf.snap.20260829.031429.png")
    assert os.path.exists(defpng) and os.path.getsize(defpng) > 10 * 1024, \
        "기본 경로 PNG 미생성: %s\n%s" % (defpng, out)
    # 재실행 시 생략(레거시 파리티) — 그래도 rc 0
    rc, out = run([PY, os.path.join(GMON, "gsnap.py"), res1, "-c", conf,
                   "--backend", "mpl"])
    assert rc == 0 and "생략" in out, "재실행 생략 실패 rc=%d\n%s" % (rc, out)

    # [2c] gplot 라이브 모드 회귀: refresh 여러 주기 뒤에도 살아 있어야 한다.
    #      (gnuplot 6은 timedata 모드에서 stats가 오류라 loop.plt가 xdata를
    #       해제/복원하지 않으면 첫 refresh에 gnuplot이 즉사한다)
    conf_live = make_conf(tmp, name="gmon_live.conf", refresh_sec="0.5")
    livepng = os.path.join(tmp, "live.png")
    proc = subprocess.Popen(
        [PY, os.path.join(GMON, "gplot.py"), "-c", conf_live,
         "--term", "png", "--out", livepng,
         "--datafile", os.path.join(GMON, "old", "fw181022.dat")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        time.sleep(3.0)  # refresh 0.5s × 최소 4~5주기 경과
        if proc.poll() is not None:
            live_out = proc.stdout.read().decode(errors="replace")
            raise AssertionError("gplot 라이브 모드 조기 종료 rc=%s\n%s"
                                 % (proc.returncode, live_out))
    finally:
        if proc.poll() is None:
            proc.terminate()  # SIGTERM → gplot이 gnuplot 자식을 정리하고 종료
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    # 생성된 loop.plt가 stats를 xdata 해제/복원으로 감싸는지 (회귀 가드)
    with open(os.path.join(tmp, "run", "work", "loop.plt")) as fp:
        loop_text = fp.read()
    body = loop_text.split("while (1) {", 1)[1]
    assert body.index("set xdata") < body.index("stats "), loop_text
    assert "set xdata time" in body, loop_text
    # 라벨 배치 계약: UTC 상단 왼쪽(label 1) / g·F 상단 오른쪽(label 2),
    # 라이브 루프에서 매 주기 갱신 + X축은 Local Time
    assert "set label 1" in loop_text and "at screen 0.01,0.97 left" in loop_text
    assert "set label 2" in loop_text and "at screen 0.99,0.97 right" in loop_text
    assert "set label 2" in body, "라이브 루프에서 g/F 라벨 미갱신"
    assert "Local Time" in loop_text and "Universal Time" not in loop_text

    # [3] 한 칩 ok=false → 예외 없이 PNG 생성 (N/A 타일)
    res2 = make_result(tmp, "20260829.031530", bad_chip="e")
    snap2 = os.path.join(tmp, "snap2.png")
    rc, out = run([PY, os.path.join(GMON, "gsnap.py"), res2, "-c", conf,
                   "--backend", "mpl", "--out", snap2])
    assert rc == 0, "gsnap(N/A) rc=%d\n%s" % (rc, out)
    assert os.path.exists(snap2) and os.path.getsize(snap2) > 5 * 1024, \
        "snap2.png 미생성/과소: %s" % out

    shutil.rmtree(tmp, ignore_errors=True)
    print("OK test_plot")


if __name__ == "__main__":
    main()
