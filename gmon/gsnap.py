#!/usr/bin/env python3
"""gsnap.py — PSF 스냅샷 3×3 PNG 생성기 (DESIGN.md §5.6, 레거시 do-sex.psfex doxpa 후속).

gpsf가 만든 result.<stem>.json을 읽어 칩별 psfex 스냅샷(snap_*.fits)을 나침반
배치로 렌더한다: 중앙=정보 패널, 상=N, 좌=E, 우=W, 하=S, 모서리=빈 칸.
각 타일은 [display] rot_* 회전 + minmax 그레이스케일 + 초록 등고선 5레벨 +
빨간 fw/sd 라벨. snap_file이 없거나 ok=false인 칩은 빈 타일 + "N/A".

사용법:
    gsnap.py RESULT.json [-c gmon.conf] [--backend auto|ds9|mpl] [--out PNG]

backend=ds9는 떠 있는 ds9에 xpaset으로 레거시 시퀀스를 보내며, ds9가 안 떠
있으면 [paths] ds9로 기동을 시도한 뒤 XPA 접속을 기다린다(레거시 do-sex.psfex
파리티). xpaset이 없거나 끝내 접속 실패면 matplotlib(Agg)로 폴백. auto는
xpaset이 있으면 ds9. 출력: run/snap/psf.snap.<stem>.png (--out으로 덮어쓰기).
기본 경로 출력물이 이미 있으면 재처리 생략(레거시 파리티).

종료코드: 0=성공, 2=부분(ok=true 칩의 스냅샷을 읽지 못함), 1=실패.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gcommon

CHIPS = ("n", "e", "w", "s")
# matplotlib 3×3 격자 (row, col): 나침반 배치
MPL_POS = {"n": (0, 1), "e": (1, 0), "w": (1, 2), "s": (2, 1)}
# ds9 프레임 번호 (1-기준, 행 우선)
DS9_FRAME = {"n": 2, "e": 4, "w": 6, "s": 8}
# 레거시 라벨 지오메트리: 회전각 → (fw 좌표, sd 좌표, textangle)
DS9_LABEL = {
    0: ((13, 8), (13, 18), 0),
    90: ((8, 13), (18, 13), 270),
    180: ((13, 18), (13, 8), 180),
    270: ((18, 13), (8, 13), 90),
}


def chip_rot(cfg, chip):
    return cfg.getint("display", "rot_" + chip, fallback=0) % 360


def resolve_path(p, result_dir, cfg):
    """result json의 파일 경로를 절대경로로. 없으면 None."""
    if not p:
        return None
    if os.path.isabs(p):
        return p if os.path.exists(p) else None
    for base in (result_dir, cfg.rundir("work"), os.getcwd()):
        cand = os.path.join(base, p)
        if os.path.exists(cand):
            return os.path.abspath(cand)
    return None


def load_snap(path):
    """snap_*.fits → 2D float 배열. 실패 시 None."""
    from astropy.io import fits
    try:
        with fits.open(path) as hdul:
            for hdu in hdul:
                if hdu.data is None:
                    continue
                data = np.squeeze(np.asarray(hdu.data, dtype=np.float64))
                if data.ndim == 2 and data.size:
                    return data
    except Exception:
        pass
    return None


def chip_tiles(cfg, res, result_dir):
    """칩별 타일 정보 dict와 부분 실패 여부를 만든다."""
    tiles = {}
    partial = False
    chips = res.get("chips", {}) or {}
    for c in CHIPS:
        info = chips.get(c) or {}
        ok = bool(info.get("ok"))
        fw = info.get("fwhm_as")
        sd = info.get("sd")
        fw_lab = ("fw%s=%.2f" % (c.upper(), fw)
                  if ok and isinstance(fw, (int, float)) else "fw%s=N/A" % c.upper())
        sd_lab = ("sd%s=%.1f" % (c.upper(), sd)
                  if ok and isinstance(sd, (int, float)) else "sd%s=N/A" % c.upper())
        path = resolve_path(info.get("snap_file"), result_dir, cfg) if ok else None
        data = load_snap(path) if path else None
        if ok and data is None:
            partial = True  # ok=true인데 스냅샷을 읽지 못함
        tiles[c] = {"data": data, "path": path if data is not None else None,
                    "fw": fw_lab, "sd": sd_lab, "ok": ok and data is not None,
                    "rot": chip_rot(cfg, c)}
    return tiles, partial


def info_lines(res):
    """정보 패널 텍스트 (텍스트, 색) 목록 — 레거시 프레임5 파리티."""
    hdr = res.get("header", {}) or {}

    def h(key):
        v = hdr.get(key, "___")
        return "___" if v is None else str(v)

    fwavg = res.get("fwavg_as")
    fwavg_lab = ("fwAVG=%.2f" % fwavg if isinstance(fwavg, (int, float))
                 else "fwAVG=N/A")
    return [
        # 레거시 캡처의 id 라인은 ".fits"까지 포함 (기준 화면 파리티)
        (str(res.get("stem", "?")) + ".fits", "red"),
        ("SecZ=%s" % h("SECZ"), "red"),
        ("Focus=%s" % h("FOCUS"), "red"),
        ("TiltEW=%s" % h("TILTEW"), "red"),
        ("TiltNS=%s" % h("TILTNS"), "red"),
        ("ESW=%s" % h("ESW"), "red"),
        ("T123=%s" % h("T123"), "red"),
        ("ALT/AZ=%s %s" % (h("ALT"), h("AZ")), "red"),
        (fwavg_lab, "green"),
    ]


# ---------------- matplotlib 백엔드 ----------------
def render_mpl(cfg, res, tiles, out):
    """기준 화면(old/psf.snap.20181003T011100.0001.fits.png) 파리티 렌더.

    600×649: 3×3 타일(각 ~200px, 검은 배경, 밝은 분리선) + 하단 컬러바 스트립.
    각 PSF 타일은 ds9 `zoom to 16`과 같은 효과로 스냅샷 중앙 ~200/zoom 픽셀만
    확대 표시한다 (DESIGN §5.6).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import gridspec

    zoom = max(1, cfg.getint("display", "zoom", fallback=16))
    vis = max(6, int(np.ceil(200.0 / zoom)))  # 타일에 보이는 스냅샷 픽셀 수

    fig = plt.figure(figsize=(6.0, 6.49), dpi=100)
    fig.patch.set_facecolor("white")
    gs = gridspec.GridSpec(4, 3, figure=fig, height_ratios=[200, 200, 200, 49],
                           left=0.004, right=0.996, top=0.997, bottom=0.003,
                           wspace=0.02, hspace=0.02)
    axes = {}
    for r in range(3):
        for cc in range(3):
            ax = fig.add_subplot(gs[r, cc])
            ax.set_facecolor("black")
            ax.set_xticks([])
            ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_visible(False)
            axes[(r, cc)] = ax

    cb_rng = None  # 컬러바 눈금 범위 (마지막으로 그린 칩의 minmax)
    for c in CHIPS:
        t = tiles[c]
        ax = axes[MPL_POS[c]]
        if t["ok"]:
            data = np.rot90(t["data"], k=(t["rot"] // 90) % 4)
            ny, nx = data.shape
            if ny > vis and nx > vis:  # ds9 zoom 파리티: 중앙부 크롭
                y0, x0 = (ny - vis) // 2, (nx - vis) // 2
                data = data[y0:y0 + vis, x0:x0 + vis]
            vmin, vmax = float(np.min(data)), float(np.max(data))
            cb_rng = (vmin, vmax)
            ax.imshow(data, cmap="gray", vmin=vmin, vmax=vmax,
                      origin="lower", interpolation="nearest", aspect="auto")
            if vmax > vmin:
                levels = np.linspace(vmin, vmax, 7)[1:-1]
                ax.contour(data, levels=levels, colors="lime", linewidths=0.9)
            ax.text(0.5, 0.965, t["sd"], transform=ax.transAxes, color="red",
                    ha="center", va="top", fontsize=9)
            ax.text(0.5, 0.035, t["fw"], transform=ax.transAxes, color="red",
                    ha="center", va="bottom", fontsize=9)
        else:
            ax.text(0.5, 0.5, "N/A", transform=ax.transAxes, color="red",
                    ha="center", va="center", fontsize=14)
            ax.text(0.5, 0.035, t["fw"], transform=ax.transAxes, color="red",
                    ha="center", va="bottom", fontsize=9)

    # 중앙 정보 패널 (기준 화면: id 상단, 항목들 중단, fwAVG 하단 초록)
    axc = axes[(1, 1)]
    lines = info_lines(res)
    axc.text(0.5, 0.955, lines[0][0], transform=axc.transAxes, color="red",
             ha="center", va="top", fontsize=8.5)
    y = 0.80
    for text, color in lines[1:-1]:
        axc.text(0.5, y, text, transform=axc.transAxes, color="red",
                 ha="center", va="center", fontsize=8.5)
        y -= 0.082
    axc.text(0.5, 0.10, lines[-1][0], transform=axc.transAxes, color="green",
             ha="center", va="bottom", fontsize=10)

    # 하단 컬러바 스트립 (ds9 캡처 파리티: 그레이 그라데이션 + 눈금 수치)
    axcb = fig.add_subplot(gs[3, :])
    axcb.set_facecolor("white")
    axcb.set_xticks([])
    axcb.set_yticks([])
    for sp in axcb.spines.values():
        sp.set_visible(False)
    grad = np.linspace(0.0, 1.0, 512)[None, :]
    axcb.imshow(grad, cmap="gray", aspect="auto", origin="lower",
                extent=(0.0, 1.0, 0.42, 1.0))
    axcb.set_xlim(0, 1)
    axcb.set_ylim(0, 1)
    lo, hi = cb_rng if cb_rng else (0.0, 0.0)
    nticks = 10
    for i in range(nticks):
        xf = (i + 0.5) / nticks
        val = lo + (hi - lo) * xf
        axcb.plot([xf, xf], [0.42, 0.34], color="black", lw=0.6,
                  clip_on=False)
        axcb.text(xf, 0.02, "%.4g" % val, transform=axcb.transAxes,
                  color="black", ha="center", va="bottom", fontsize=7)

    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)


# ---------------- ds9/XPA 백엔드 ----------------
def _null_fits(cfg):
    """빈 프레임용 null.fits (run/work, 25×25 zeros). 경로 반환."""
    from astropy.io import fits
    path = os.path.join(cfg.rundir("work"), "null.fits")
    if not os.path.exists(path):
        fits.PrimaryHDU(np.zeros((25, 25), dtype=np.float32)).writeto(path)
    return path


def _launch_ds9(cfg, log):
    """레거시 do-sex.psfex 파리티: ds9 미기동 시 [paths] ds9로 기동 시도.

    기동 프로세스를 띄웠으면 True (XPA 접속 가능 여부는 호출부가 재확인).
    """
    ds9 = cfg.tool("ds9")
    exe = shutil.which(ds9)
    if exe is None:
        log.error("ds9 실행 파일 없음(%s) — 기동 생략", ds9)
        return False
    try:
        subprocess.Popen([exe], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as exc:
        log.error("ds9 기동 실패(%s): %s", exe, exc)
        return False
    log.info("ds9 기동: %s", exe)
    return True


def render_ds9(cfg, res, tiles, out, log):
    """레거시 doxpa 시퀀스 포팅. 성공 True, 실패(폴백 필요) False."""
    xpaset = cfg.tool("xpaset")
    exe = shutil.which(xpaset)
    if exe is None:
        log.error("xpaset 없음(%s) — matplotlib으로 폴백", xpaset)
        return False

    def xpa(*args):
        r = subprocess.run([exe, "-p", "ds9"] + [str(a) for a in args],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=20)
        if r.returncode != 0:
            raise RuntimeError("xpaset %s: %s" %
                               (" ".join(str(a) for a in args),
                                r.stderr.decode(errors="replace").strip()))

    def region(x, y, text, color, angle):
        spec = ("image; text %d %d # text={%s} color=%s textangle=%d\n"
                % (x, y, text, color, angle))
        r = subprocess.run([exe, "ds9", "regions"], input=spec.encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=20)
        if r.returncode != 0:
            raise RuntimeError("xpaset regions: %s" %
                               r.stderr.decode(errors="replace").strip())

    try:
        xpa("background", "black")  # 접속 확인 겸 (ds9 미기동이면 여기서 실패)
    except Exception as exc:
        # 레거시 파리티: ds9가 안 떠 있으면 [paths] ds9로 기동 후 접속 재시도
        log.info("ds9/XPA 접속 실패(%s) — ds9 기동 시도", exc)
        if not _launch_ds9(cfg, log):
            log.error("ds9 미기동 — matplotlib으로 폴백")
            return False
        connected = False
        for _ in range(15):  # 최대 ~15초 XPA 준비 대기
            time.sleep(1.0)
            try:
                xpa("background", "black")
                connected = True
                break
            except Exception:
                continue
        if not connected:
            log.error("ds9 기동 후에도 XPA 접속 실패 — matplotlib으로 폴백")
            return False

    try:
        null = _null_fits(cfg)
        zoom = cfg.getint("display", "zoom", fallback=16)
        for a in (("view", "info", "no"), ("view", "panner", "no"),
                  ("view", "magnifier", "no"), ("view", "buttons", "no"),
                  ("width", 600), ("height", 600),
                  ("tile", "grid", "layout", 3, 3), ("tile", "yes"),
                  ("scale", "mode", "minmax")):
            xpa(*a)
        for frame in (1, 3, 7, 9):
            xpa("frame", frame)
            xpa("fits", null)
        for c in CHIPS:
            t = tiles[c]
            xpa("frame", DS9_FRAME[c])
            rot = t["rot"]
            fw_xy, sd_xy, angle = DS9_LABEL.get(rot, DS9_LABEL[0])
            if t["ok"]:
                xpa("fits", t["path"])
                xpa("scale", "mode", "minmax")
                xpa("zoom", "to", zoom, zoom)
                xpa("orient", "none")
                xpa("rotate", "to", rot)
                xpa("contour", "mode", "minmax")
                xpa("contour", "nlevels", 5)
                xpa("contour", "smooth", 1)
                xpa("contour", "yes")
                region(fw_xy[0], fw_xy[1], t["fw"], "red", angle)
                region(sd_xy[0], sd_xy[1], t["sd"], "red", angle)
            else:
                xpa("fits", null)
                xpa("zoom", "to", zoom, zoom)
                xpa("orient", "none")
                xpa("rotate", "to", rot)
                region(13, 13, "N/A", "red", angle)
                region(fw_xy[0], fw_xy[1], t["fw"], "red", angle)
        # 중앙 정보 패널 (frame 5)
        xpa("frame", 5)
        xpa("fits", null)
        xpa("zoom", "to", zoom, zoom)
        xpa("orient", "none")
        xpa("rotate", "to", 0)
        lines = info_lines(res)
        rows = (18, 16, 15, 14, 13, 12, 11, 10, 8)  # 레거시 y좌표
        for (text, color), yy in zip(lines, rows):
            region(13, yy, text, color, 0)
        xpa("frame", 9)
        xpa("saveimage", "png", out)
        return True
    except Exception as exc:
        log.error("ds9 시퀀스 실패(%s) — matplotlib으로 폴백", exc)
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="gmon PSF 스냅샷 PNG (3x3)")
    ap.add_argument("result", help="gpsf가 만든 result.<stem>.json")
    ap.add_argument("-c", "--config", default=None)
    ap.add_argument("--backend", choices=["auto", "ds9", "mpl"], default=None)
    ap.add_argument("--out", default=None, help="출력 PNG (기본 run/snap/psf.snap.<stem>.png)")
    args = ap.parse_args(argv)

    cfg = gcommon.load_config(args.config)
    gcommon.ensure_dirs(cfg)
    log = gcommon.setup_logger(cfg, "gsnap")

    result_path = os.path.abspath(args.result)
    try:
        with open(result_path, encoding="utf-8") as fp:
            res = json.load(fp)
    except (OSError, ValueError) as exc:
        log.error("result json 읽기 실패: %s (%s)", result_path, exc)
        return 1

    stem = res.get("stem") or gcommon.stem_from_raw(res.get("raw_file", "unknown"))
    if args.out:
        out = os.path.abspath(args.out)
    else:
        out = os.path.join(cfg.rundir("snap"), "psf.snap.%s.png" % stem)
        if os.path.exists(out):  # 레거시 파리티: 이미 있으면 재처리 생략
            log.info("이미 존재 — 생략: %s", out)
            return 0

    backend = args.backend or cfg.get("display", "backend", fallback="auto")
    if backend == "auto":
        backend = "ds9" if shutil.which(cfg.tool("xpaset")) else "mpl"

    tiles, partial = chip_tiles(cfg, res, os.path.dirname(result_path))
    done = False
    if backend == "ds9":
        done = render_ds9(cfg, res, tiles, out, log)
    if not done:
        try:
            render_mpl(cfg, res, tiles, out)
        except Exception as exc:
            log.error("렌더 실패: %s", exc)
            return 1
    log.info("스냅샷 저장: %s", out)
    return 2 if partial else 0


if __name__ == "__main__":
    sys.exit(main())
