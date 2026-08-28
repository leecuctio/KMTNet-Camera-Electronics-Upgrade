#!/usr/bin/env python3
"""gpsf.py — 칩별 SExtractor→PSFEx 실행, FWHM 추출·기록 (레거시 do-sex.psfex 후속).

workdir(기본 run/work)에서 <prefix><p>.<STEM>.fits 4장(p = [chips] order)을 찾아
칩별로 sex → psfex를 돌리고 .psf 헤더의 PSF_FWHM을 읽어 다음을 기록한다:
  - run/data/fw%y%m%d.dat : "YY:MM:DD:HH:MM:SS fwN fwE fwW fwS FOCUS TEMP SECZ" append
    (운용판 2018-11-30 형식; FOCUS/TEMP 결측("___")은 직전 줄 값 계승 — DESIGN §5.2)
    (DESIGN.md §5.2, 시각은 DATE-OBS/TIME-OBS 있으면 그것, 없으면 현재 로컬시각)
  - run/log/logfile.txt   : 레거시 형식 한 줄 + fwAVG (DESIGN.md §5.3·§5.5)
  - workdir/result.<STEM>.json : gsnap 전달용 사이드카 (DESIGN.md §5.4)
stdout 마지막 줄에 result json 경로를 출력한다.

사용법:
  gpsf.py STEM [-c gmon.conf] [--workdir D]
  gpsf.py --raw RAW.fits [-c gmon.conf] [--workdir D]   (STEM은 gcommon.stem_from_raw)

종료코드: 전 칩 성공 0 / 일부 성공 2 / 전부 실패 1
"""
import argparse
import datetime
import glob
import json
import os
import subprocess
import sys

import numpy as np
from astropy.io import fits

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gcommon

SUBPROC_TIMEOUT = 120  # sex/psfex 개별 타임아웃(초)

# 레거시 do-sex.psfex가 gethead로 읽던 헤더 키 (없으면 "___")
HDR_KEYS = ("SECZ", "FAFOCUS", "FATILTEW", "FATILTNS", "FAPOSE", "FAPOSS",
            "FAPOSW", "ENS1", "ENS2", "ENS3", "ALT", "AZ", "DATE-OBS", "TIME-OBS")


def _run(argv, cwd, log, tag):
    """외부 명령 실행. 성공 True. 실패/타임아웃/실행불가는 로그만 남기고 False."""
    try:
        proc = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=SUBPROC_TIMEOUT)
    except subprocess.TimeoutExpired:
        log.error("%s: 타임아웃(%ds): %s", tag, SUBPROC_TIMEOUT, " ".join(argv))
        return False
    except OSError as exc:
        log.error("%s: 실행 불가: %s (%s)", tag, argv[0], exc)
        return False
    if proc.returncode != 0:
        tail = proc.stdout.decode("utf-8", "replace").strip().splitlines()[-5:]
        log.error("%s: 종료코드 %d: %s", tag, proc.returncode, " | ".join(tail))
        return False
    return True


def _read_psf_fwhm(psf_path):
    """PSFEx .psf 파일에서 PSF_FWHM(px). 어느 HDU든 찾는다 (실측: PSF_DATA 확장)."""
    with fits.open(psf_path) as hdul:
        for hdu in hdul:
            if "PSF_FWHM" in hdu.header:
                return float(hdu.header["PSF_FWHM"])
    return None


def _stat_stddev(cfg, data):
    """stat_region(1-기준 FITS x1,x2,y1,y2)의 표준편차. 클리핑 없음(레거시 nclip=0)."""
    x1, x2, y1, y2 = [int(v) for v in cfg.getpair("pipeline", "stat_region")]
    sub = np.asarray(data[y1 - 1:y2, x1 - 1:x2], dtype=np.float64)
    if sub.size < 2:
        return 0.0
    return float(sub.std(ddof=1))


def _num(val):
    """헤더 값 → float. "___"/없음/비수치는 0.0 (레거시 파리티)."""
    try:
        return float(str(val).strip())
    except (TypeError, ValueError):
        return 0.0


def _last_fw_fields(fwfile):
    """fw파일 마지막 줄의 수치 필드 [fwN,fwE,fwW,fwS,FOCUS,TEMP,SECZ]. 없으면 None."""
    try:
        with open(fwfile) as fp:
            lines = [ln for ln in fp.read().splitlines() if ln.strip()]
        if not lines:
            return None
        return [float(x) for x in lines[-1].split()[1:]]
    except (OSError, ValueError, IndexError):
        return None


def _parse_obstime(dateobs, timeobs):
    """DATE-OBS(/TIME-OBS) → datetime(로컬로 간주). 해석 불가면 None."""
    if not dateobs or dateobs == "___":
        return None
    s = str(dateobs).strip()
    if "T" in s:
        d, t = s.split("T", 1)
    else:
        d = s
        t = str(timeobs).strip() if timeobs and timeobs != "___" else "00:00:00"
    t = t.split(".")[0]
    try:
        return datetime.datetime.strptime(d + " " + t, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def process_chip(cfg, log, workdir, chip, stem):
    """한 칩: sd 측정 → sex → psfex → PSF_FWHM. 항상 dict 반환(실패 시 ok=False)."""
    res = {"fwhm_px": 0.0, "fwhm_as": 0.0, "sd": 0.0,
           "psf_file": None, "snap_file": None, "ok": False}
    name = gcommon.chip_filename(cfg, chip, stem)
    path = os.path.join(workdir, name)
    if not os.path.exists(path):
        log.warning("[%s] 칩 파일 없음: %s", chip, path)
        return res

    try:
        with fits.open(path) as hdul:
            res["sd"] = _stat_stddev(cfg, hdul[0].data)
    except Exception as exc:
        log.warning("[%s] sd 측정 실패: %s", chip, exc)

    cfgdir = cfg.configdir
    cat = os.path.join(workdir, name + ".psfex.cat")
    sex_cmd = [cfg.tool("sex"), path,
               "-c", os.path.join(cfgdir, "default.sex"),
               "-PARAMETERS_NAME", os.path.join(cfgdir, "default.param.psfex"),
               "-FILTER_NAME", os.path.join(cfgdir, "default.conv"),
               "-STARNNW_NAME", os.path.join(cfgdir, "default.nnw"),
               "-CATALOG_NAME", cat, "-CATALOG_TYPE", "FITS_LDAC"]
    if not _run(sex_cmd, workdir, log, "[%s] sex" % chip) or not os.path.exists(cat):
        return res

    psfex_cmd = [cfg.tool("psfex"), cat,
                 "-c", os.path.join(cfgdir, "default.psfex"),
                 "-PSF_DIR", workdir,
                 "-CHECKIMAGE_TYPE", "SNAPSHOTS",
                 "-CHECKIMAGE_NAME", "snap.fits",
                 "-WRITE_XML", "N"]
    if not _run(psfex_cmd, workdir, log, "[%s] psfex" % chip):
        return res

    # 산출물 이름 (psfex 3.24 실측): <cat이름 .cat→.psf>, snap_<cat이름-확장자>.fits
    psf = cat[:-len(".cat")] + ".psf"
    if not os.path.exists(psf):
        cand = sorted(glob.glob(os.path.join(workdir, name + "*.psf")))
        psf = cand[-1] if cand else None
    snap = os.path.join(workdir, "snap_" + name + ".psfex.fits")
    if not os.path.exists(snap):
        cand = sorted(glob.glob(os.path.join(workdir, "snap*" + name + "*.fits")))
        snap = cand[-1] if cand else None
    if psf is None:
        log.error("[%s] .psf 산출물 없음", chip)
        return res
    res["psf_file"] = psf
    res["snap_file"] = snap

    try:
        fwhm_px = _read_psf_fwhm(psf)
    except Exception as exc:
        log.error("[%s] PSF_FWHM 읽기 실패: %s", chip, exc)
        return res
    if fwhm_px is None:
        log.error("[%s] PSF_FWHM 헤더 없음: %s", chip, psf)
        return res

    res["fwhm_px"] = float(fwhm_px)
    res["fwhm_as"] = float(fwhm_px) * cfg.getfloat("pipeline", "pixel_scale", fallback=0.52)
    min_fwhm = cfg.getfloat("pipeline", "min_fwhm_px", fallback=1.0)
    if fwhm_px < min_fwhm:
        log.warning("[%s] fwhm_px=%.3f < min_fwhm_px=%.2f → 실패 처리", chip, fwhm_px, min_fwhm)
        return res
    res["ok"] = True
    log.info("[%s] fwhm=%.3f px = %.3f arcsec, sd=%.1f", chip, res["fwhm_px"], res["fwhm_as"], res["sd"])
    return res


def read_chip_header(cfg, workdir, order, stem):
    """order 순서로 처음 존재하는 칩 FITS의 HDR_KEYS(+GRAWFILE). 없으면 "___"."""
    vals = dict((k, "___") for k in HDR_KEYS)
    vals["GRAWFILE"] = "___"
    for chip in order:
        path = os.path.join(workdir, gcommon.chip_filename(cfg, chip, stem))
        if not os.path.exists(path):
            continue
        try:
            hdr = fits.getheader(path, 0)
        except Exception:
            continue
        for k in list(vals):
            if k in hdr:
                vals[k] = str(hdr[k]).strip()
        return vals
    return vals


def main(argv=None):
    ap = argparse.ArgumentParser(description="칩별 sex→psfex→FWHM 추출·기록 (DESIGN.md §5.2~§5.5)")
    ap.add_argument("stem", nargs="?", help="노출 STEM (예: 20260527.195724)")
    ap.add_argument("--raw", help="원시 FITS 경로 — STEM을 gcommon.stem_from_raw로 산출")
    ap.add_argument("-c", "--config", default=None, help="gmon.conf 경로")
    ap.add_argument("--workdir", default=None, help="칩 FITS 디렉토리 (기본 run/work)")
    args = ap.parse_args(argv)
    if not args.stem and not args.raw:
        ap.error("STEM 또는 --raw 중 하나는 필요합니다")

    cfg = gcommon.load_config(args.config)
    gcommon.ensure_dirs(cfg)
    log = gcommon.setup_logger(cfg, "gpsf")
    stem = args.stem or gcommon.stem_from_raw(args.raw)
    workdir = os.path.abspath(args.workdir or cfg.rundir("work"))
    order = cfg.getlist("chips", "order")
    log.info("gpsf 시작: stem=%s workdir=%s chips=%s", stem, workdir, ",".join(order))

    chips = {}
    for chip in order:
        try:
            chips[chip] = process_chip(cfg, log, workdir, chip, stem)
        except Exception as exc:  # 한 칩 실패해도 나머지 계속
            log.error("[%s] 예외: %s", chip, exc)
            chips[chip] = {"fwhm_px": 0.0, "fwhm_as": 0.0, "sd": 0.0,
                           "psf_file": None, "snap_file": None, "ok": False}

    hv = read_chip_header(cfg, workdir, order, stem)

    # fwAVG = 유효한 칩들의 산술평균 (레거시 W 2회/S 누락 버그 수정 — DESIGN §5.5)
    ok_as = [c["fwhm_as"] for c in chips.values() if c["ok"]]
    fwavg = sum(ok_as) / len(ok_as) if ok_as else 0.0

    def fw_of(chip):
        c = chips.get(chip)
        return c["fwhm_as"] if c and c["ok"] else 0.0

    def sd_of(chip):
        c = chips.get(chip)
        return c["sd"] if c else 0.0

    # (a) fw 데이터 파일 append — DESIGN §5.2 (운용판 시각형식·결측 계승)
    ts = _parse_obstime(hv["DATE-OBS"], hv["TIME-OBS"]) or datetime.datetime.now()
    fwfile = gcommon.fw_path(cfg, when=ts)
    focus_v, temp_v = _num(hv["FAFOCUS"]), _num(hv["ENS3"])
    if hv["FAFOCUS"] == "___" or hv["ENS3"] == "___":
        prev = _last_fw_fields(fwfile)
        if prev is not None and len(prev) >= 6:
            if hv["FAFOCUS"] == "___":
                focus_v = prev[4]
            if hv["ENS3"] == "___":
                temp_v = prev[5]
    fwline = "%s %.2f %.2f %.2f %.2f %.3f %.1f %.2f" % (
        ts.strftime("%y:%m:%d:%H:%M:%S"), fw_of("n"), fw_of("e"), fw_of("w"),
        fw_of("s"), focus_v, temp_v, _num(hv["SECZ"]))
    with open(fwfile, "a") as fp:
        fp.write(fwline + "\n")
    log.info("fw append → %s : %s", fwfile, fwline)

    # (b) 상세 로그 — 레거시 do-sex.psfex 형식 + fwAVG (DESIGN §5.3)
    logline = ("'%s' 'SecZ=%s' 'fwN=%.2f' 'fwE=%.2f' 'fwW=%.2f' 'fwS=%.2f' "
               "'sdN=%.1f' 'sdE=%.1f' 'sdW=%.1f' 'sdS=%.1f' 'Focus=%s' "
               "'TiltEW=%s' 'TiltNS=%s' 'ESW=%s %s %s' 'T123=%s %s %s' "
               "'ALT/AZ=%s %s' 'fwAVG=%.2f'") % (
        stem, hv["SECZ"], fw_of("n"), fw_of("e"), fw_of("w"), fw_of("s"),
        sd_of("n"), sd_of("e"), sd_of("w"), sd_of("s"), hv["FAFOCUS"],
        hv["FATILTEW"], hv["FATILTNS"], hv["FAPOSE"], hv["FAPOSS"], hv["FAPOSW"],
        hv["ENS1"], hv["ENS2"], hv["ENS3"], hv["ALT"], hv["AZ"], fwavg)
    with open(os.path.join(cfg.rundir("log"), "logfile.txt"), "a") as fp:
        fp.write(logline + "\n")

    # (c) result 사이드카 — DESIGN §5.4
    if args.raw:
        raw_file = os.path.basename(args.raw)
    elif hv["GRAWFILE"] != "___":
        raw_file = hv["GRAWFILE"]
    else:
        raw_file = "___"
    result = {
        "stem": stem,
        "chips": chips,
        "fwavg_as": fwavg,
        "header": {
            "SECZ": hv["SECZ"], "FOCUS": hv["FAFOCUS"],
            "TILTEW": hv["FATILTEW"], "TILTNS": hv["FATILTNS"],
            "ESW": "%s %s %s" % (hv["FAPOSE"], hv["FAPOSS"], hv["FAPOSW"]),
            "T123": "%s %s %s" % (hv["ENS1"], hv["ENS2"], hv["ENS3"]),
            "ALT": hv["ALT"], "AZ": hv["AZ"],
            "DATEOBS": hv["DATE-OBS"], "TIMEOBS": hv["TIME-OBS"]},
        "raw_file": raw_file,
    }
    result_path = os.path.join(workdir, "result.%s.json" % stem)
    with open(result_path, "w") as fp:
        json.dump(result, fp, indent=2)

    n_ok = sum(1 for c in chips.values() if c["ok"])
    log.info("완료: %d/%d 칩 성공, fwAVG=%.2f arcsec", n_ok, len(order), fwavg)
    print(result_path)
    if n_ok == len(order) and n_ok > 0:
        return 0
    return 2 if n_ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
