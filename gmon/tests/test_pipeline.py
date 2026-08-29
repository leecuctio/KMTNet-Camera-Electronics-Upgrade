#!/usr/bin/env python3
"""test_pipeline.py — gpsf.py 종단 시험 (실제 sex/psfex 구동).

합성 4칩 FITS(가우시안 별밭)를 임시 workdir에 만들고, runroot를 임시 디렉토리로
돌린 gmon.conf 사본으로 gpsf.py를 서브프로세스 실행한 뒤:
  - 종료코드 0, 4칩 모두 |fwhm_px-기준|/3.5 < 0.15
  - fw 파일 한 줄 append: 시각/7수치 형식, FOCUS/TEMP/SECZ 반영
  - result.<STEM>.json 스키마(DESIGN.md §5.4)와 fwavg_as = 유효 칩 산술평균
    (레거시 W 2회/S 누락 버그 수정 검증 — W·S의 FWHM을 다르게 심음)
을 검증한다. pytest 불필요 — 단독 실행, 실패 시 비0 종료.
"""
import configparser
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from astropy.io import fits

TESTS = os.path.dirname(os.path.abspath(__file__))
GMON = os.path.dirname(TESTS)
sys.path.insert(0, GMON)
import gcommon

STEM = "20260829.120000"
# W·S를 3.5에서 살짝 벗어나게 심어 fwAVG 평균 버그(W 2회/S 누락)를 검출 가능하게 함
TRUE_FWHM = {"n": 3.5, "e": 3.5, "w": 3.35, "s": 3.65}


def make_chip(path, fwhm_px, seed):
    """1024x1024 float32: 배경 1000 + 읽기잡음 5, 가우시안 별 64개."""
    rng = np.random.default_rng(seed)
    ny = nx = 1024
    img = 1000.0 + rng.normal(0.0, 5.0, (ny, nx))
    sigma = fwhm_px / 2.35482
    yy, xx = np.mgrid[0:ny, 0:nx]
    for gy in range(8):
        for gx in range(8):
            x0 = 80.0 + gx * 120.0 + rng.uniform(-15, 15)
            y0 = 80.0 + gy * 120.0 + rng.uniform(-15, 15)
            amp = rng.uniform(3000.0, 30000.0)
            r2 = (xx - x0) ** 2 + (yy - y0) ** 2
            m = r2 < (10.0 * sigma) ** 2
            img[m] += amp * np.exp(-r2[m] / (2.0 * sigma * sigma))
    hdr = fits.Header()
    hdr["SECZ"] = 1.20
    hdr["ENS3"] = 15.5
    hdr["FAFOCUS"] = -5.50
    hdr["DATE-OBS"] = "2026-08-29"
    hdr["TIME-OBS"] = "12:00:00"
    fits.PrimaryHDU(img.astype(np.float32), header=hdr).writeto(path, overwrite=True)


def main():
    tmp = tempfile.mkdtemp(prefix="tmp_pipeline_", dir=TESTS)
    try:
        run_test(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK test_pipeline")


def run_test(tmp):
    runroot = os.path.join(tmp, "run")
    workdir = os.path.join(runroot, "work")
    os.makedirs(workdir)

    # runroot만 임시로 돌린 gmon.conf 사본 (configdir는 실제 config/ 절대경로)
    cp = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    with open(os.path.join(GMON, "gmon.conf"), encoding="utf-8") as fp:
        cp.read_file(fp)
    cp.set("paths", "runroot", runroot)
    cp.set("paths", "configdir", os.path.join(GMON, "config"))
    conf = os.path.join(tmp, "gmon.conf")
    with open(conf, "w", encoding="utf-8") as fp:
        cp.write(fp)
    cfg = gcommon.load_config(conf)
    pixscale = cfg.getfloat("pipeline", "pixel_scale")

    for i, chip in enumerate(("n", "s", "e", "w")):
        make_chip(os.path.join(workdir, "KMTNg%s.%s.fits" % (chip, STEM)),
                  TRUE_FWHM[chip], seed=100 + i)

    proc = subprocess.run(
        [sys.executable, os.path.join(GMON, "gpsf.py"), STEM, "-c", conf],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    out = proc.stdout.decode()
    assert proc.returncode == 0, "gpsf 종료코드 %d\n%s\n%s" % (
        proc.returncode, out, proc.stderr.decode())

    # stdout 마지막 줄 = result json 경로
    result_path = out.strip().splitlines()[-1]
    assert result_path == os.path.join(workdir, "result.%s.json" % STEM), result_path
    assert os.path.exists(result_path), result_path
    with open(result_path) as fp:
        result = json.load(fp)

    # ---- result json 스키마 (DESIGN §5.4) ----
    assert set(result) == {"stem", "chips", "fwavg_as", "header", "raw_file"}, set(result)
    assert result["stem"] == STEM
    assert set(result["chips"]) == {"n", "s", "e", "w"}
    for chip, c in result["chips"].items():
        assert set(c) == {"fwhm_px", "fwhm_as", "sd", "psf_file", "snap_file", "ok"}, (chip, set(c))
        assert c["ok"] is True, (chip, c)
        rel = abs(c["fwhm_px"] - 3.5) / 3.5
        assert rel < 0.15, "칩 %s fwhm_px=%.3f (편차 %.1f%%)" % (chip, c["fwhm_px"], rel * 100)
        assert abs(c["fwhm_as"] - c["fwhm_px"] * pixscale) < 1e-9, chip
        assert c["sd"] > 0.0, chip
        assert os.path.exists(c["psf_file"]), c["psf_file"]
        assert os.path.exists(c["snap_file"]), c["snap_file"]
    for k in ("SECZ", "FOCUS", "TILTEW", "TILTNS", "ESW", "T123", "ALT", "AZ",
              "DATEOBS", "TIMEOBS"):
        assert k in result["header"], k
    assert float(result["header"]["SECZ"]) == 1.20
    assert float(result["header"]["FOCUS"]) == -5.50

    # fwavg_as = 4칩 산술평균 (W 2회/S 누락 버그면 ±0.005를 벗어남)
    mean4 = sum(result["chips"][p]["fwhm_as"] for p in ("n", "s", "e", "w")) / 4.0
    assert abs(result["fwavg_as"] - mean4) < 0.005, (result["fwavg_as"], mean4)
    buggy = (result["chips"]["n"]["fwhm_as"] + result["chips"]["e"]["fwhm_as"]
             + 2 * result["chips"]["w"]["fwhm_as"]) / 4.0
    assert abs(mean4 - buggy) > 0.005, "합성 칩들이 평균 버그를 구분하지 못함"

    # ---- fw 파일 (DESIGN §5.2) ----
    # fw_time=arrival(기본): 도착·처리 시각으로 오늘 밤 파일에 기록·자동 생성
    fwfile = gcommon.fw_path(cfg)               # when=now → 오늘 밤 파일
    assert os.path.exists(fwfile), fwfile
    with open(fwfile) as fp:
        lines = fp.read().splitlines()
    assert len(lines) == 1, lines
    # 운용판 시각형식 YY:MM:DD:HH:MM:SS (DESIGN §5.2)
    m = re.match(r"^(\d{2}(?::\d{2}){5})((?: [-+]?\d+\.\d+){7})$", lines[0])
    assert m, "fw 형식 불일치: %r" % lines[0]
    rec_ts = datetime.datetime.strptime(m.group(1), "%y:%m:%d:%H:%M:%S")
    dt = abs((datetime.datetime.now() - rec_ts).total_seconds())
    assert dt < 300, "fw 시각이 처리 시각과 다름 (%.0fs 차이)" % dt
    # 관측시각 파싱 자체는 dateobs 모드용으로 계속 유효해야 함
    import gpsf as _gpsf
    assert (_gpsf._parse_obstime("2026-08-29", "12:00:00")
            == datetime.datetime(2026, 8, 29, 12, 0, 0))
    nums = [float(v) for v in m.group(2).split()]
    for i, chip in enumerate(("n", "e", "w", "s")):  # fwN fwE fwW fwS
        assert abs(nums[i] - result["chips"][chip]["fwhm_as"]) < 0.006, (chip, nums[i])
    assert nums[4] == -5.50, nums[4]   # FOCUS = FAFOCUS
    assert nums[5] == 15.5, nums[5]    # TEMP  = ENS3
    assert nums[6] == 1.20, nums[6]    # SECZ

    # ---- logfile.txt (DESIGN §5.3: 레거시 형식 + fwAVG) ----
    logfile = os.path.join(runroot, "log", "logfile.txt")
    assert os.path.exists(logfile), logfile
    with open(logfile) as fp:
        logline = fp.read().splitlines()[-1]
    assert ("'%s'" % STEM) in logline, logline
    assert "'fwAVG=%.2f'" % result["fwavg_as"] in logline, logline

    # runroot 밖(실제 run/)을 오염시키지 않았는지
    assert not os.path.exists(os.path.join(GMON, "run", "work", "result.%s.json" % STEM))


if __name__ == "__main__":
    main()
