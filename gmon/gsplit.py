#!/usr/bin/env python3
"""gmon v2 — 아콘 원시 프레임(4224×1033, 8채널) → 4칩 FITS 분할기 (DESIGN.md §2·§5.1·§6).

칩 k는 세그먼트 (2k, 2k+1)로 구성되며 [chips] order의 방위 이름을 받는다.
각 세그먼트에서 [geometry]의 활성 컬럼 범위만 취해 좌+우로 스티칭하고,
pedestal_match=yes면 접합부 인접 32컬럼 중앙값 차만큼 오른쪽 채널을 보정한다.
산출물은 float32, 원본 헤더 전파 + GCHIP/GSEG1/GSEG2/GGEOMVER/GPED1/GPED2/GRAWFILE.

사용법 (CLI):
    gsplit.py RAW.fits [-c gmon.conf] [-o OUTDIR] [--json]
    (기본 OUTDIR = run/work, 성공 시 stdout에 산출 경로 또는 JSON)

라이브러리 (gwatch가 import):
    split_frame(data, header, cfg)          -> {chip: (ndarray, Header)}
    split_file(raw_path, cfg, outdir=None)  -> {chip: 출력 경로}
"""
import argparse
import json
import logging
import os
import sys
import warnings

import numpy as np
from astropy.io import fits

import gcommon

# 접합부 페데스탈 측정에 쓰는 인접 컬럼 수 (DESIGN.md §2 단차 보정)
PEDESTAL_NCOL = 32


class Geometry:
    """[geometry]/[chips] 파싱 + 자기일관성 검증."""

    def __init__(self, cfg):
        g = "geometry"
        self.raw_nx = cfg.getint(g, "raw_nx", fallback=4224)
        self.raw_ny = cfg.getint(g, "raw_ny", fallback=1033)
        self.nseg = cfg.getint(g, "nseg", fallback=8)
        self.seg_width = cfg.getint(g, "seg_width", fallback=528)
        self.left_active = cfg.getpair(g, "left_active")
        self.right_active = cfg.getpair(g, "right_active")
        self.y_trim_bottom = cfg.getint(g, "y_trim_bottom", fallback=0)
        self.y_trim_top = cfg.getint(g, "y_trim_top", fallback=0)
        self.flip_right_x = cfg.getbool(g, "flip_right_x", fallback=False)
        self.pedestal_match = cfg.getbool(g, "pedestal_match", fallback=True)
        self.order = cfg.getlist("chips", "order")

        if self.nseg * self.seg_width != self.raw_nx:
            raise ValueError(
                "gmon.conf [geometry] 불일치: nseg*seg_width=%d != raw_nx=%d"
                % (self.nseg * self.seg_width, self.raw_nx))
        if len(self.order) * 2 != self.nseg:
            raise ValueError(
                "gmon.conf 불일치: [chips] order %d개 != nseg/2=%d"
                % (len(self.order), self.nseg // 2))

    @property
    def left_w(self):
        return self.left_active[1] - self.left_active[0]

    @property
    def right_w(self):
        return self.right_active[1] - self.right_active[0]

    @property
    def out_ny(self):
        return self.raw_ny - self.y_trim_bottom - self.y_trim_top

    @property
    def out_nx(self):
        return self.left_w + self.right_w


def split_frame(data, header, cfg, rawfile=None):
    """원시 2D 배열 → {chip: (float32 ndarray, Header)}.

    입력 크기가 cfg [geometry]와 다르면 ValueError.
    rawfile: GRAWFILE 헤더에 기록할 원본 파일명 (split_file이 채움).
    """
    geo = Geometry(cfg)
    if data.ndim != 2 or data.shape != (geo.raw_ny, geo.raw_nx):
        raise ValueError(
            "원시 프레임 크기 불일치: 입력 %s, 기대 (%d, %d) — gmon.conf [geometry] 확인"
            % (data.shape, geo.raw_ny, geo.raw_nx))

    y0, y1 = geo.y_trim_bottom, geo.raw_ny - geo.y_trim_top
    la0, la1 = geo.left_active
    ra0, ra1 = geo.right_active
    out = {}
    for k, chip in enumerate(geo.order):
        s1, s2 = 2 * k, 2 * k + 1
        left = data[y0:y1, s1 * geo.seg_width + la0: s1 * geo.seg_width + la1]
        right = data[y0:y1, s2 * geo.seg_width + ra0: s2 * geo.seg_width + ra1]
        left = np.asarray(left, dtype=np.float32)
        right = np.asarray(right, dtype=np.float32)
        if geo.flip_right_x:
            right = right[:, ::-1]

        ped2 = 0.0
        if geo.pedestal_match:
            n = min(PEDESTAL_NCOL, geo.left_w, geo.right_w)
            ped2 = float(np.median(left[:, -n:]) - np.median(right[:, :n]))
            right = right + np.float32(ped2)

        img = np.ascontiguousarray(np.hstack((left, right)), dtype=np.float32)

        hdr = header.copy() if header is not None else fits.Header()
        for kk in ("BZERO", "BSCALE"):  # float 저장 — 스케일 키 제거 (§5.1)
            if kk in hdr:
                del hdr[kk]
        hdr["GCHIP"] = (chip, "chip orientation (n/s/e/w)")
        hdr["GSEG1"] = (s1, "raw segment index, left channel")
        hdr["GSEG2"] = (s2, "raw segment index, right channel")
        hdr["GGEOMVER"] = (gcommon.GEOM_VERSION, "gsplit geometry version")
        hdr["GPED1"] = (0.0, "pedestal offset applied, left [ADU]")
        hdr["GPED2"] = (ped2, "pedestal offset applied, right [ADU]")
        hdr["GRAWFILE"] = (rawfile or "", "source raw frame")
        out[chip] = (img, hdr)
    return out


def split_file(raw_path, cfg, outdir=None):
    """원시 FITS 1장 → 4칩 FITS 파일. {chip: 출력 경로} 반환.

    잘린(truncated) 파일은 경고 로그만 내고 계속 처리한다.
    """
    log = logging.getLogger("gsplit")
    raw_path = os.path.abspath(raw_path)
    base = os.path.basename(raw_path)
    stem = gcommon.stem_from_raw(base)
    if outdir is None:
        outdir = cfg.rundir("work")
    os.makedirs(outdir, exist_ok=True)

    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        with fits.open(raw_path, memmap=False) as hdul:
            data = np.asarray(hdul[0].data)
            header = hdul[0].header.copy()
    for w in wlist:
        log.warning("%s: %s", base, w.message)

    paths = {}
    for chip, (img, hdr) in split_frame(data, header, cfg, rawfile=base).items():
        path = os.path.join(outdir, gcommon.chip_filename(cfg, chip, stem))
        fits.PrimaryHDU(data=img, header=hdr).writeto(path, overwrite=True)
        paths[chip] = path
    log.info("split %s -> %d chips (stem=%s, outdir=%s)",
             base, len(paths), stem, outdir)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="아콘 원시 프레임을 4칩 FITS로 분할한다 (DESIGN.md §5.1).")
    ap.add_argument("raw", help="원시 FITS 파일 (4224x1033)")
    ap.add_argument("-c", "--config", default=None, help="gmon.conf 경로")
    ap.add_argument("-o", "--outdir", default=None,
                    help="출력 디렉토리 (기본 run/work)")
    ap.add_argument("--json", action="store_true",
                    help="stdout 마지막 줄에 JSON으로 결과 출력")
    args = ap.parse_args(argv)

    cfg = gcommon.load_config(args.config)
    log = gcommon.setup_logger(cfg, "gsplit")
    try:
        paths = split_file(args.raw, cfg, outdir=args.outdir)
    except Exception as e:
        log.error("분할 실패: %s: %s", os.path.basename(args.raw), e)
        return 1

    if args.json:
        print(json.dumps({
            "raw": os.path.abspath(args.raw),
            "stem": gcommon.stem_from_raw(os.path.basename(args.raw)),
            "chips": paths,
        }))
    else:
        for path in paths.values():
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
