#!/usr/bin/env python3
"""gplot.py — gnuplot 실시간 FWHM 그래프 (운용판 do-plotFWHM 후속).

fw 데이터 파일(DESIGN.md §5.2: YY:MM:DD:HH:MM:SS fwN fwE fwW fwS FOCUS TEMP
SECZ)을 gnuplot으로 그린다. 구형 파일(2018판 DD:HH:MM:SS 등)은 1열 콜론 수로
자동 판별한다. 플롯 요소는 운용판 파리티 + 기준 화면(old/kmtnet_saao_fw.png)
표기: dT(주황), North/East/West/South(red/magenta/green/blue), Airmass(빨강 원,
(SecZ-1)x10), Estimate(회색, y2), Focus(갈색 굵은 선, y2), 마지막 점의
"g=… F=…" 라벨, 좌상단 파란 UTC 타임스탬프.

사용법:
    gplot.py [-c gmon.conf] [--oneshot] [--term qt|x11|png] [--out PNG]
             [--datafile F]

기본 데이터는 오늘 밤 파일(gcommon.fw_path). 라이브 모드는 run/work/loop.plt를
생성해 gnuplot -persist로 주기(refresh_sec) 갱신하며, pidfile(gplot)로 단일
실행을 보장한다. --oneshot은 1회 렌더(term png이면 --out, 기본 run/snap/
fwplot.png). gnuplot 6에서 reread가 제거되어 loop.plt는 while 루프로
pause+replot을 수행한다(의미 동일). stats는 timedata 모드에서 실행할 수 없으므로
루프 안에서는 xdata를 잠시 해제하고 stats를 돌린 뒤 복원한다(레거시 loop.plt의
reset→stats→set xdata time 순서와 같은 효과).
"""
import argparse
import datetime
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gcommon


def _detect_timefmt(datafile):
    """fw 파일 1열의 콜론 수로 시각 형식 판별 (DESIGN §5.2).

    5개=운용판 %y:%m:%d:%H:%M:%S, 3개=2018판 %d:%H:%M:%S, 그 외=%H:%M:%S.
    """
    try:
        with open(datafile) as fp:
            for ln in fp:
                tok = ln.split()
                if tok:
                    n = tok[0].count(":")
                    return {5: "%y:%m:%d:%H:%M:%S",
                            3: "%d:%H:%M:%S"}.get(n, "%H:%M:%S")
    except OSError:
        pass
    return "%y:%m:%d:%H:%M:%S"


def _settings(cfg, datafile, term, out=None):
    """공통 gnuplot 설정 라인들 (stats 포함, plot 제외)."""
    ymax = cfg.getfloat("plot", "y_fwhm_max", fallback=12.0)
    y2 = cfg.getpair("plot", "y2_range")
    try:
        size = cfg.getpair("plot", "size")
    except Exception:
        size = (800, 380)
    site = cfg.get("site", "name", fallback="")
    dd = datetime.datetime.now().strftime("%Y-%m-%d")
    lines = ["reset", 'stats "%s" u 7 nooutput' % datafile]
    if term == "png":
        lines.append("set term pngcairo size %d,%d" % (size[0], size[1]))
        lines.append('set output "%s"' % out)
    else:
        lines.append("set term %s size %d,%d" % (term, size[0], size[1]))
    lines += [
        "set title '%s FFT (FWHM-FOCUS-TEMP) Monitoring'" % site,
        "set xdata time",
        "set timefmt '%s'" % _detect_timefmt(datafile),
        "set format x '%H:%M'",
        "set autoscale xfix",
        "set yrange [0:%g]" % ymax,
        "set y2tics %g,0.5,%g" % (y2[0], y2[1]),
        "set y2range [%g:%g]" % (y2[0], y2[1]),
        "set key left top",
        "set xlabel 'Universal Time (%s)'" % dd,
        "set ylabel 'FWHM (arcsec) or T (C)'",
        "set y2label 'Focus (mm)'",
        "set grid",
        # 좌상단 파란 타임스탬프 (기준 화면 파리티; 라이브 루프에서 매 주기 갱신)
        _stamp_line(),
    ]
    return lines


def _stamp_line():
    return ('set label 1 strftime("%Y%m%dT%H:%M:%S UTC", time(0.0))'
            ' at screen 0.01,0.97 tc rgb "blue" font ",11"')


def _plot_command(cfg, datafile):
    """레거시 do-plotFWHM 파리티 plot 명령 한 줄."""
    slope = cfg.getfloat("focus", "slope", fallback=-0.067)
    base = cfg.getfloat("focus", "base", fallback=4.7)
    dfocus = gcommon.read_dfocus(cfg)
    ymax = cfg.getfloat("plot", "y_fwhm_max", fallback=12.0)
    guess = "(%.6g*$7-(%.6g))" % (slope, base + dfocus)
    f = datafile
    parts = [
        '"%s" u 1:($7-STATS_median+6) pt 5 ps 2 lc rgb "orange" title "dT"' % f,
        '"%s" u 1:2 pt 4 ps 2 lc rgb "red" title "North"' % f,
        '"%s" u 1:3 pt 4 ps 2 lc rgb "magenta" title "East"' % f,
        '"%s" u 1:4 pt 4 ps 2 lc rgb "green" title "West"' % f,
        '"%s" u 1:5 pt 4 ps 2 lc rgb "blue" title "South"' % f,
        '"%s" u 1:(($8-1)*10) pt 7 ps 2 lc rgb "red" title "Airmass"' % f,
        '"%s" u 1:%s axes x1y2 pt 5 ps 2 lc rgb "grey" title "Estimate"' % (f, guess),
        '"%s" u 1:6 axes x1y2 w li lw 3 lc rgb "brown" title "Focus"' % f,
        # tail 경로는 셸을 거치므로 공백 경로 대비 작은따옴표로 인용한다
        '"< tail -n 1 \'%s\'" u 1:($2*0+%g):(sprintf("g=%%.3f  F=%%.3f", %s, $6))'
        ' w labels offset char -10,1 tc rgb "blue" notitle' % (f, ymax, guess),
    ]
    return "plot " + ", ".join(parts)


def run_oneshot(cfg, log, datafile, term, out):
    lines = _settings(cfg, datafile, term, out) + [_plot_command(cfg, datafile)]
    script = "\n".join(lines) + "\n"
    cmd = [cfg.tool("gnuplot")]
    if term != "png":
        cmd.append("-persist")
    r = subprocess.run(cmd, input=script.encode())
    if r.returncode != 0:
        log.error("gnuplot 실패 (rc=%d)", r.returncode)
        return 1
    if term == "png":
        log.info("그래프 저장: %s", out)
    return 0


def run_live(cfg, log, datafile, term, out):
    pf = gcommon.PidFile(cfg, "gplot")
    if not pf.acquire():
        log.info("이미 실행 중 (pid=%s) — 종료", pf.other_pid())
        return 0
    try:
        refresh = cfg.getfloat("plot", "refresh_sec", fallback=10.0)
        lines = _settings(cfg, datafile, term, out)
        plot = _plot_command(cfg, datafile)
        loop = lines + [plot, "while (1) {", "  pause %g" % refresh]
        # gnuplot 6에서 reread 제거 → while 루프로 stats 갱신 + replot (의미 동일).
        # 단 stats는 timedata 모드에서 오류("Stats command not available in
        # timedata mode")로 gnuplot이 죽으므로 xdata를 잠시 해제하고 실행 후 복원.
        loop += ["  set xdata"]
        loop += ["  " + l for l in lines if l.startswith("stats ")]
        loop += ["  set xdata time", "  " + _stamp_line(), "  replot", "}"]
        loop_path = os.path.join(cfg.rundir("work"), "loop.plt")
        with open(loop_path, "w") as fp:
            fp.write("\n".join(loop) + "\n")
        log.info("라이브 플롯 시작: %s (refresh %gs)", datafile, refresh)
        child = subprocess.Popen([cfg.tool("gnuplot"), "-persist", loop_path])

        def _stop(signum, frame):
            child.terminate()

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
        rc = child.wait()
        log.info("gnuplot 종료 (rc=%s)", rc)
        return 0
    finally:
        pf.release()


def main(argv=None):
    ap = argparse.ArgumentParser(description="gmon FWHM 그래프 (gnuplot)")
    ap.add_argument("-c", "--config", default=None)
    ap.add_argument("--oneshot", action="store_true", help="1회 렌더 후 종료")
    ap.add_argument("--term", choices=["qt", "x11", "png"], default=None)
    ap.add_argument("--out", default=None, help="term png일 때 출력 PNG 경로")
    ap.add_argument("--datafile", default=None, help="fw 데이터 파일(기본: 오늘 밤)")
    args = ap.parse_args(argv)

    cfg = gcommon.load_config(args.config)
    gcommon.ensure_dirs(cfg)
    log = gcommon.setup_logger(cfg, "gplot")

    term = args.term or cfg.get("plot", "term", fallback="qt")
    datafile = os.path.abspath(args.datafile) if args.datafile else gcommon.fw_path(cfg)
    out = None
    if term == "png":
        out = os.path.abspath(args.out) if args.out else os.path.join(
            cfg.rundir("snap"), "fwplot.png")

    if not os.path.exists(datafile):
        log.error("데이터 파일 없음: %s", datafile)
        return 1

    if args.oneshot:
        return run_oneshot(cfg, log, datafile, term, out)
    return run_live(cfg, log, datafile, term, out)


if __name__ == "__main__":
    sys.exit(main())
