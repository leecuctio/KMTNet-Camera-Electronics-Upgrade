#!/usr/bin/env python3
"""시험용 합성 아콘 원시 프레임 생성기 (DESIGN.md §6).

gmon.conf [geometry]에 맞춰 4224×1033 uint16 프레임을 만든다:
채널(세그먼트)별 서로 다른 페데스탈(1000~1100 ADU 상수), 읽기잡음 σ≈5 ADU,
2D 가우시안 별(포아송 잡음 포함). 별은 4칩 모두의 활성 영역에만 배치하며
칩마다 세그 경계(접합부)에 걸치는 별을 일부 포함한다(스티칭 검증용).
셔터 스미어는 넣지 않는다. BZERO=32768 uint16 표준 저장.

--base RAW.fits 를 주면 페데스탈을 합성하는 대신 **실제 아콘 프레임 위에
별을 주입**한다 (헤더도 베이스에서 전파). 베이스가 사실상 무잡음(테스트
패턴)이면 읽기잡음 σ≈5 ADU를 자동 추가한다 (--extra-noise로 지정 가능;
0이면 추가 안 함). 잘린 파일의 zero-padding 꼬리는 아랫줄 값으로 보정.

사용법:
    make_synthetic.py -o OUT.fits [--fwhm-px 3.5] [--nstars 40]
                      [--fwhm-scatter 0.1] [--flux 60000] [--seed 42]
                      [--truth TRUTH.json] [--base RAW.fits]
                      [--extra-noise ADU] [-c gmon.conf]

--fwhm-scatter 0.1 이면 별마다 FWHM을 N(fwhm_px, 0.1·fwhm_px)로 산포
(±50% 절단).

현실감 옵션 (목업 야전 시험용):
  --sat-frac 0.02    포화별 비율 — 피크가 포화(65535)의 1.2~4배가 되는 플럭스
                     로 넣어 클리핑된 평정(flat-top) 별을 만든다
  --faint-frac 0.03  미광성 비율 — 피크가 읽기잡음의 3~8배(15~40 ADU)인 별
  --elong-max 0.3    별별 elongation(장/단축비−1)을 [0, 값]에서 균등 추출,
                     방향각 무작위 — PSF가 완벽한 원형이 아니게 됨
  일반 별의 플럭스는 로그균등 [0.25, 1]×flux 로 산포된다.

truth JSON: {"fwhm_px", "fwhm_scatter",
"stars": [{"chip","x","y","flux","fwhm_px","kind","elong","pa"}]}
(x, y는 분할 후 칩 좌표계 0-기준; kind = normal|sat|faint, pa = 라디안)
"""
import argparse
import datetime
import json
import os
import sys

import numpy as np
from astropy.io import fits

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gcommon  # noqa: E402

READ_NOISE = 5.0     # ADU
PED_LO, PED_HI = 1000.0, 1100.0
N_JUNCTION = 2       # 칩당 접합부에 걸치는 별 수


def _chip_to_raw(geo, k, x, y):
    """칩 좌표 (x, y) → 원시 프레임 좌표 (rx, ry). geo는 gsplit.Geometry 유사 dict."""
    ry = y + geo["y_trim_bottom"]
    la0, la1 = geo["left_active"]
    ra0, ra1 = geo["right_active"]
    left_w = la1 - la0
    segw = geo["seg_width"]
    if x < left_w:
        rx = (2 * k) * segw + la0 + x
    else:
        xr = x - left_w
        if geo["flip_right_x"]:
            rx = (2 * k + 1) * segw + ra0 + (ra1 - ra0 - 1 - xr)
        else:
            rx = (2 * k + 1) * segw + ra0 + xr
    return rx, ry


def _read_geometry(cfg):
    return {
        "raw_nx": cfg.getint("geometry", "raw_nx", fallback=4224),
        "raw_ny": cfg.getint("geometry", "raw_ny", fallback=1033),
        "nseg": cfg.getint("geometry", "nseg", fallback=8),
        "seg_width": cfg.getint("geometry", "seg_width", fallback=528),
        "left_active": cfg.getpair("geometry", "left_active"),
        "right_active": cfg.getpair("geometry", "right_active"),
        "y_trim_bottom": cfg.getint("geometry", "y_trim_bottom", fallback=0),
        "y_trim_top": cfg.getint("geometry", "y_trim_top", fallback=0),
        "flip_right_x": cfg.getbool("geometry", "flip_right_x", fallback=False),
        "order": cfg.getlist("chips", "order"),
    }


def _load_base(path, geo):
    """--base 프레임 로드. (float64 ndarray, Header) 반환.

    잘린 파일은 astropy가 꼬리를 0으로 채우므로, 0 픽셀을 바로 아랫줄 값으로
    보정한다 (실제 바이어스에서 정확히 0인 픽셀은 사실상 없음).
    """
    with fits.open(path, memmap=False) as hdul:
        data = np.asarray(hdul[0].data, dtype=np.float64)
        hdr = hdul[0].header.copy()
    if data.shape != (geo["raw_ny"], geo["raw_nx"]):
        raise ValueError("베이스 프레임 크기 %s ≠ [geometry] (%d, %d)"
                         % (data.shape, geo["raw_ny"], geo["raw_nx"]))
    zy, zx = np.nonzero(data == 0)
    if zy.size:
        data[zy, zx] = data[np.maximum(zy - 1, 0), zx]
        print("베이스 zero-padding %d픽셀을 아랫줄 값으로 보정" % zy.size)
    return data, hdr


def generate(cfg, fwhm_px=3.5, nstars=40, flux=60000.0, seed=42,
             base=None, extra_noise=None, fwhm_scatter=0.0,
             sat_frac=0.0, faint_frac=0.0, elong_max=0.0):
    """합성 원시 프레임 생성. (uint16 ndarray, Header, truth dict) 반환.

    base가 주어지면 그 실제 프레임 위에 별을 주입한다 (페데스탈 합성 생략).
    fwhm_scatter > 0 이면 별마다 FWHM을 정규분포 N(fwhm_px, scatter·fwhm_px)로
    산포시킨다 (±50%에서 절단; truth JSON에 별별 fwhm_px 기록).
    sat_frac/faint_frac/elong_max는 모듈 docstring의 현실감 옵션 참조.
    """
    geo = _read_geometry(cfg)
    rng = np.random.default_rng(seed)
    ny, nx = geo["raw_ny"], geo["raw_nx"]
    segw = geo["seg_width"]
    la0, la1 = geo["left_active"]
    ra0, ra1 = geo["right_active"]
    chip_w = (la1 - la0) + (ra1 - ra0)
    chip_h = ny - geo["y_trim_bottom"] - geo["y_trim_top"]
    order = geo["order"]

    sigma = float(fwhm_px) / 2.3548
    stamp_r = int(np.ceil(4.0 * sigma)) + 1
    margin = max(16, stamp_r + 4)          # 시험(국소 최대 박스)까지 여유
    minsep = max(12.0, 4.0 * float(fwhm_px))
    junction_x = float(la1 - la0)          # 좌/우 채널 접합부 (칩 좌표)

    # ---- 별 위치 결정 (칩 좌표) ----
    per_chip = [nstars // len(order) + (1 if k < nstars % len(order) else 0)
                for k in range(len(order))]
    stars = []                             # (chip_idx, x, y)
    for k, n_k in enumerate(per_chip):
        placed = []
        for j in range(n_k):
            for _ in range(2000):
                if j < N_JUNCTION and n_k > N_JUNCTION:
                    x = junction_x + rng.uniform(-2.0, 2.0)
                else:
                    x = rng.uniform(margin, chip_w - margin)
                y = rng.uniform(margin, chip_h - margin)
                if all((x - px) ** 2 + (y - py) ** 2 >= minsep ** 2
                       for px, py in placed):
                    placed.append((x, y))
                    stars.append((k, x, y))
                    break
            else:
                raise RuntimeError("별 배치 실패: nstars가 너무 많음")

    # ---- 별별 FWHM 산포 (fwhm_scatter, ±50% 절단) ----
    n = len(stars)
    fwhms = np.full(n, float(fwhm_px))
    if fwhm_scatter > 0:
        fac = 1.0 + float(fwhm_scatter) * rng.standard_normal(n)
        fwhms *= np.clip(fac, 0.5, 1.5)

    # ---- 별 종류(normal/sat/faint)·elongation·방향각 ----
    kinds = ["normal"] * n
    order_idx = rng.permutation(n)
    nsat = int(round(float(sat_frac) * n))
    nfaint = int(round(float(faint_frac) * n))
    for j in order_idx[:nsat]:
        kinds[j] = "sat"
    for j in order_idx[nsat:nsat + nfaint]:
        kinds[j] = "faint"
    elongs = np.ones(n)
    if elong_max > 0:
        elongs += rng.uniform(0.0, float(elong_max), n)
    pas = rng.uniform(0.0, np.pi, n)      # 장축 방향각 (라디안)

    # ---- 별 신호 (기대값, 타원 가우시안) → 포아송 표본 ----
    sig = np.zeros((ny, nx), dtype=np.float64)
    fluxes = np.empty(n)
    for i, (k, x, y) in enumerate(stars):
        sig_g = fwhms[i] / 2.3548
        root_e = np.sqrt(elongs[i])
        sa, sb = sig_g * root_e, sig_g / root_e   # 기하평균 FWHM 보존
        area = 2.0 * np.pi * sa * sb
        if kinds[i] == "sat":       # 피크가 포화 위로 — 클리핑된 평정 별
            fluxes[i] = rng.uniform(1.2, 4.0) * 65535.0 * area
        elif kinds[i] == "faint":   # 피크 ≈ 읽기잡음의 3~8배
            fluxes[i] = rng.uniform(3.0, 8.0) * READ_NOISE * area
        else:                       # 로그균등 [0.25, 1]×flux
            fluxes[i] = float(flux) * 10.0 ** rng.uniform(-0.6, 0.0)
        peak = fluxes[i] / area
        ct, st = np.cos(pas[i]), np.sin(pas[i])
        qa = ct * ct / (2 * sa * sa) + st * st / (2 * sb * sb)
        qb = st * ct * (1.0 / (2 * sa * sa) - 1.0 / (2 * sb * sb))
        qc = st * st / (2 * sa * sa) + ct * ct / (2 * sb * sb)
        r_i = int(np.ceil(4.0 * sa)) + 1
        rx, ry = _chip_to_raw(geo, k, x, y)
        ix, iy = int(round(rx)), int(round(ry))
        x0, x1 = max(0, ix - r_i), min(nx, ix + r_i + 1)
        y0, y1 = max(0, iy - r_i), min(ny, iy + r_i + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = xx - rx, yy - ry
        sig[y0:y1, x0:x1] += peak * np.exp(
            -(qa * dx * dx + 2.0 * qb * dx * dy + qc * dy * dy))
    photons = rng.poisson(sig).astype(np.float64)

    now = datetime.datetime.now()
    if base is not None:
        # ---- 실제 프레임 위에 별 주입 ----
        img, hdr = _load_base(base, geo)
        if extra_noise is None:
            # 베이스가 무잡음 테스트 패턴이면 sex 배경 rms가 0이 되므로
            # 읽기잡음을 추가한다 (실측 잡음이 이미 있으면 추가 안 함)
            samp = img[ny // 4:ny // 2, la0 + 8:la0 + 400]
            extra_noise = READ_NOISE if float(np.std(samp)) < 1.0 else 0.0
        if extra_noise > 0:
            img = img + rng.normal(0.0, float(extra_noise), size=(ny, nx))
        hdr["SYNTHSRC"] = (os.path.basename(base), "star-injection base frame")
        hdr["SYNNOISE"] = (float(extra_noise), "added read noise (ADU rms)")
        if "DATE-OBS" not in hdr:
            hdr["DATE-OBS"] = (now.strftime("%Y-%m-%d"), "Observation date(Local)")
        if "TIME-OBS" not in hdr:
            hdr["TIME-OBS"] = (now.strftime("%H:%M:%S"), "Observation time(Local)")
    else:
        # ---- 채널별 페데스탈 + 읽기잡음 합성 ----
        img = rng.normal(0.0, READ_NOISE, size=(ny, nx))
        peds = rng.uniform(PED_LO, PED_HI, size=geo["nseg"])
        for s in range(geo["nseg"]):
            img[:, s * segw:(s + 1) * segw] += peds[s]
        hdr = fits.Header()
        hdr["EXPTIME"] = (1.00, "Exposure time in seconds")
        hdr["SHUTOPEN"] = (0, "Shutter trigger output")
        hdr["DATE-OBS"] = (now.strftime("%Y-%m-%d"), "Observation date(Local)")
        hdr["TIME-OBS"] = (now.strftime("%H:%M:%S"), "Observation time(Local)")
    img = img + photons
    data = np.rint(np.clip(img, 0, 65535)).astype(np.uint16)
    hdr["SYNTH"] = (True, "synthetic frame (make_synthetic.py)")

    truth = {
        "fwhm_px": float(fwhm_px),
        "fwhm_scatter": float(fwhm_scatter),
        "sat_frac": float(sat_frac),
        "faint_frac": float(faint_frac),
        "elong_max": float(elong_max),
        "stars": [{"chip": order[k], "x": round(x, 3), "y": round(y, 3),
                   "flux": round(float(fluxes[i]), 1),
                   "fwhm_px": round(float(fwhms[i]), 3),
                   "kind": kinds[i],
                   "elong": round(float(elongs[i]), 3),
                   "pa": round(float(pas[i]), 3)}
                  for i, (k, x, y) in enumerate(stars)],
    }
    return data, hdr, truth


def main(argv=None):
    ap = argparse.ArgumentParser(description="합성 아콘 원시 프레임 생성기")
    ap.add_argument("-o", "--out", required=True, help="출력 FITS 경로")
    ap.add_argument("--fwhm-px", type=float, default=3.5)
    ap.add_argument("--nstars", type=int, default=40)
    ap.add_argument("--flux", type=float, default=60000.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fwhm-scatter", type=float, default=0.0,
                    help="별별 FWHM 산포 비율 (예: 0.1 = 10%%)")
    ap.add_argument("--sat-frac", type=float, default=0.0,
                    help="포화별 비율 (예: 0.02 = 2%%)")
    ap.add_argument("--faint-frac", type=float, default=0.0,
                    help="미광성 비율 (예: 0.03 = 3%%)")
    ap.add_argument("--elong-max", type=float, default=0.0,
                    help="별별 elongation 최대치 (장/단축비−1, 예: 0.3)")
    ap.add_argument("--truth", default=None, help="truth JSON 출력 경로")
    ap.add_argument("--base", default=None,
                    help="실제 원시 프레임 — 이 위에 별을 주입 (페데스탈 합성 생략)")
    ap.add_argument("--extra-noise", type=float, default=None,
                    help="--base에 추가할 읽기잡음 ADU rms (기본: 무잡음이면 5, 아니면 0)")
    ap.add_argument("-c", "--config", default=None, help="gmon.conf 경로")
    args = ap.parse_args(argv)

    cfg = gcommon.load_config(args.config)
    data, hdr, truth = generate(cfg, fwhm_px=args.fwhm_px, nstars=args.nstars,
                                flux=args.flux, seed=args.seed,
                                base=args.base, extra_noise=args.extra_noise,
                                fwhm_scatter=args.fwhm_scatter,
                                sat_frac=args.sat_frac,
                                faint_frac=args.faint_frac,
                                elong_max=args.elong_max)
    outdir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(outdir, exist_ok=True)
    fits.PrimaryHDU(data=data, header=hdr).writeto(args.out, overwrite=True)
    if args.truth:
        with open(args.truth, "w", encoding="utf-8") as fp:
            json.dump(truth, fp, indent=1)
    src = " base=%s" % os.path.basename(args.base) if args.base else ""
    sca = " scatter=%.0f%%" % (args.fwhm_scatter * 100) if args.fwhm_scatter else ""
    print("%s: %dx%d uint16, stars=%d fwhm=%.2fpx%s%s"
          % (args.out, data.shape[1], data.shape[0],
             len(truth["stars"]), args.fwhm_px, sca, src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
