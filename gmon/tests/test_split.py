#!/usr/bin/env python3
"""gsplit 자체 시험 (pytest 불필요, 단독 실행).

합성 프레임 생성 → split_file 검증(형상/헤더/별 위치/페데스탈 접합),
실제 원시 샘플 7장 분할, stem 규칙 확인. 산출물은 tests/ 아래 임시
디렉토리만 사용하며 성공 시 삭제한다 (run/ 미사용).
"""
import configparser
import glob
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from astropy.io import fits

HERE = os.path.dirname(os.path.abspath(__file__))
GMON = os.path.dirname(HERE)
ROOT = os.path.dirname(GMON)
sys.path.insert(0, GMON)
sys.path.insert(0, os.path.join(GMON, "tools"))

import gcommon            # noqa: E402
import gsplit             # noqa: E402
import make_synthetic     # noqa: E402

PY = "/opt/miniconda3/bin/python"
logging.basicConfig(level=logging.WARNING)

tmpdir = tempfile.mkdtemp(prefix="tmp_split_", dir=HERE)
print("tmpdir:", tmpdir)

# ---- 임시 gmon.conf: runroot만 임시 디렉토리로 돌려 run/ 오염 방지 ----
cp = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
with open(os.path.join(GMON, "gmon.conf"), encoding="utf-8") as fp:
    cp.read_file(fp)
cp.set("paths", "runroot", os.path.join(tmpdir, "run"))
cp.set("paths", "configdir", os.path.join(GMON, "config"))
tmpconf = os.path.join(tmpdir, "gmon.conf")
with open(tmpconf, "w", encoding="utf-8") as fp:
    cp.write(fp)
cfg = gcommon.load_config(tmpconf)

# ---- 1. 합성 프레임 생성 (CLI 경로 시험) ----
raw_syn = os.path.join(tmpdir, "synth.20260829.010203.fits")
truth_json = os.path.join(tmpdir, "truth.json")
r = subprocess.run(
    [PY, os.path.join(GMON, "tools", "make_synthetic.py"),
     "-o", raw_syn, "--truth", truth_json, "--seed", "42",
     "--nstars", "40", "--fwhm-px", "3.5", "--flux", "60000",
     "-c", tmpconf],
    capture_output=True, text=True)
assert r.returncode == 0, "make_synthetic 실패:\n" + r.stdout + r.stderr
assert os.path.exists(raw_syn) and os.path.exists(truth_json)
with fits.open(raw_syn) as hdul:
    assert hdul[0].data.shape == (1033, 4224), hdul[0].data.shape
    assert hdul[0].data.dtype == np.uint16
    assert hdul[0].header["BZERO"] == 32768

# ---- 2. gsplit CLI (--json) ----
splitdir = os.path.join(tmpdir, "split")
r = subprocess.run(
    [PY, os.path.join(GMON, "gsplit.py"), raw_syn,
     "-c", tmpconf, "-o", splitdir, "--json"],
    capture_output=True, text=True)
assert r.returncode == 0, "gsplit CLI 실패:\n" + r.stdout + r.stderr
res = json.loads(r.stdout.strip().splitlines()[-1])
assert res["stem"] == "20260829.010203", res["stem"]
chips = res["chips"]
assert sorted(chips) == ["e", "n", "s", "w"], chips

# ---- 3. 산출물 형상·dtype·헤더 키 ----
imgs = {}
for chip, path in chips.items():
    assert os.path.exists(path), path
    assert os.path.basename(path) == "KMTNg%s.20260829.010203.fits" % chip
    with fits.open(path) as hdul:
        hdr = hdul[0].header
        img = hdul[0].data
    assert img.shape == (1024, 1024), (chip, img.shape)
    assert img.dtype.name == "float32", (chip, img.dtype)   # FITS는 big-endian f4
    assert hdr["BITPIX"] == -32 and "BZERO" not in hdr
    for key in ("GCHIP", "GSEG1", "GSEG2", "GGEOMVER",
                "GPED1", "GPED2", "GRAWFILE"):
        assert key in hdr, (chip, key)
    assert hdr["GCHIP"] == chip
    assert hdr["GGEOMVER"] == gcommon.GEOM_VERSION
    assert hdr["GRAWFILE"] == os.path.basename(raw_syn)
    assert (hdr["GSEG1"], hdr["GSEG2"]) == (
        2 * ["n", "s", "e", "w"].index(chip),
        2 * ["n", "s", "e", "w"].index(chip) + 1)
    assert hdr["SYNTH"] is True     # 원본 헤더 전파
    imgs[chip] = img

# ---- 4. truth 별 위치의 국소 최대 확인 (각 칩 3개 이상) ----
with open(truth_json, encoding="utf-8") as fp:
    truth = json.load(fp)
found = {c: 0 for c in imgs}
for st in truth["stars"]:
    img = imgs[st["chip"]]
    ix, iy = int(round(st["x"])), int(round(st["y"]))
    box = img[max(0, iy - 3):iy + 4, max(0, ix - 3):ix + 4]
    bg = np.median(img[max(0, iy - 12):iy + 13, max(0, ix - 12):ix + 13])
    if box.max() - bg > 300.0:      # 기대 피크 ~1900 ADU (배경 대비)
        found[st["chip"]] += 1
for chip, n in found.items():
    assert n >= 3, "칩 %s: 국소 최대 별 %d개 (<3)" % (chip, n)

# ---- 5. 페데스탈 매칭: 접합부 좌우 16열 중앙값 차 < 3 ADU ----
for chip, img in imgs.items():
    dm = abs(float(np.median(img[:, 496:512]) - np.median(img[:, 512:528])))
    assert dm < 3.0, "칩 %s 접합부 단차 %.2f ADU" % (chip, dm)

# ---- 6. 실제 샘플 7장: 예외 없이 분할 완료 ----
# 실측 원본 7장 화이트리스트 — raw/에 계속 생기는 합성(.sim/.mock 등)과 무관
REAL_NAMES = (
    "modtm.20260527.195724.fits", "modtm.20260527.195925.fits",
    "modtm.20260527.214204.fits", "modtm.20260527.214420.fits",
    "temp_4224x1033_27.fits", "temp_4224x1033_51.fits",
    "temp_4224x1033_66.fits",
)
real = [os.path.join(ROOT, "raw", n) for n in REAL_NAMES]
missing = [f for f in real if not os.path.exists(f)]
assert not missing, "실샘플 없음: %s" % missing
realdir = os.path.join(tmpdir, "real")
for f in real:
    paths = gsplit.split_file(f, cfg, outdir=realdir)
    assert sorted(paths) == ["e", "n", "s", "w"]
    for path in paths.values():
        with fits.open(path) as hdul:
            assert hdul[0].data.shape == (1024, 1024)
            assert hdul[0].data.dtype.name == "float32"

# ---- 7. stem 규칙: modtm.20260527.195724 → 20260527.195724 ----
assert gcommon.stem_from_raw("modtm.20260527.195724.fits") == "20260527.195724"
p = gsplit.split_file(os.path.join(ROOT, "raw", "modtm.20260527.195724.fits"),
                      cfg, outdir=realdir)
for chip, path in p.items():
    assert "20260527.195724" in os.path.basename(path), path
    assert os.path.basename(path) == "KMTNg%s.20260527.195724.fits" % chip

# ---- 8. 크기 불일치 입력 → split_frame ValueError / CLI exit 1 ----
try:
    gsplit.split_frame(np.zeros((100, 100), np.uint16), fits.Header(), cfg)
    raise SystemExit("크기 불일치가 거부되지 않음")
except ValueError:
    pass
bad = os.path.join(tmpdir, "bad.fits")
fits.PrimaryHDU(data=np.zeros((10, 10), np.uint16)).writeto(bad)
r = subprocess.run([PY, os.path.join(GMON, "gsplit.py"), bad,
                    "-c", tmpconf, "-o", splitdir],
                   capture_output=True, text=True)
assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)

# ---- 9. --base 별 주입: 실프레임 페데스탈 보존 + 별 회수 ----
base_real = os.path.join(ROOT, "raw", "modtm.20260527.214204.fits")
raw_inj = os.path.join(tmpdir, "inj.20260527.214204.fits")
truth_inj = os.path.join(tmpdir, "inj.truth.json")
r = subprocess.run(
    [PY, os.path.join(GMON, "tools", "make_synthetic.py"),
     "-o", raw_inj, "--base", base_real, "--truth", truth_inj,
     "--seed", "7", "--nstars", "24", "--fwhm-px", "3.8",
     "--fwhm-scatter", "0.1", "-c", tmpconf],
    capture_output=True, text=True)
assert r.returncode == 0, "make_synthetic --base 실패:\n" + r.stdout + r.stderr
with fits.open(raw_inj) as hdul:
    inj = np.asarray(hdul[0].data, dtype=np.float64)
    assert hdul[0].data.shape == (1033, 4224)
    assert hdul[0].header["SYNTHSRC"] == "modtm.20260527.214204.fits"
with fits.open(base_real, memmap=False) as hdul:
    basedat = np.asarray(hdul[0].data, dtype=np.float64)
# 실프레임 페데스탈 보존: 세그먼트별 중앙값 차 < 1 ADU (별·잡음은 중앙값에 무영향)
for s in range(8):
    d = abs(np.median(inj[100:900, s * 528 + 50:s * 528 + 450])
            - np.median(basedat[100:900, s * 528 + 50:s * 528 + 450]))
    assert d < 1.0, "세그%d 페데스탈 변형 %.2f ADU" % (s, d)
# 분할 후 truth 별 회수 (각 칩 3개 이상 국소 최대)
paths9 = gsplit.split_file(raw_inj, cfg, outdir=os.path.join(tmpdir, "inj"))
imgs9 = dict((c, fits.getdata(p).astype(float)) for c, p in paths9.items())
with open(truth_inj, encoding="utf-8") as fp:
    t9 = json.load(fp)
found9 = dict((c, 0) for c in imgs9)
for st in t9["stars"]:
    img = imgs9[st["chip"]]
    ix, iy = int(round(st["x"])), int(round(st["y"]))
    box = img[max(0, iy - 3):iy + 4, max(0, ix - 3):ix + 4]
    bg = np.median(img[max(0, iy - 12):iy + 13, max(0, ix - 12):ix + 13])
    if box.max() - bg > 300.0:
        found9[st["chip"]] += 1
for chip, n in found9.items():
    assert n >= 3, "칩 %s: --base 별 회수 %d개 (<3)" % (chip, n)

shutil.rmtree(tmpdir)
print("OK test_split")
