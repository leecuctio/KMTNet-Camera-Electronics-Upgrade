#!/usr/bin/env python3
"""gmon.py — Tkinter GUI 관제 패널 (DESIGN.md §7·§8, 레거시 old/gmon(wish) 후속).

세 개의 독립 창(패널)으로 구성된다:
  [제어부]      메인 창 — 레거시 버튼 배치: ON(gwatch 기동) / OFF(gwatch·gplot
                정지) / AUTO(period_sec 주기 초점 전송) / MAN(1회 전송) /
                ±step·±big_step(dfocus 증감) + 상태 라벨(dfocus, ref, fw,
                데몬 상태) + SNAP/PLOT(닫은 서브 창 다시 열기)
  [PSF 스냅샷]  별도 창 — run/snap의 최신 psf.snap.*.png를 자동 갱신 표시
  [FWHM 그래프] 별도 창 — gplot --oneshot --term png를 주기 렌더해 표시

서브 창은 닫아도 숨김(withdraw)일 뿐이며 제어부의 SNAP/PLOT 버튼으로 다시
연다. 제어부 창을 닫으면 GUI 전체가 종료된다(데몬은 유지 — 정지는 OFF).
GUI가 떠 있는 동안(run/pid/gmon.pid) gwatch는 외부 gnuplot 라이브 창을
띄우지 않는다(그래프는 패널로 표시). GUI가 없으면 기존처럼 라이브 창 기동.

레거시와 다른 점(주의): 창을 닫아도 gwatch 데몬은 계속 돈다.
데몬 정지는 반드시 OFF 버튼(run/pid/*.pid 기반 SIGTERM)으로 한다. killall 금지.

초점 제어는 GUI와 분리된 FocusController(tests/test_focus.py 대상):
  ref = slope*T − (base + dfocus),
  T = 최신 fw 줄(시각 fwN fwE fwW fwS FOCUS TEMP SECZ)의 TEMP — 공백분리 7번째
  필드. [focus] temp_source=auto면 fw가 없거나 fw_stale_sec보다 오래됐을 때
  TCS auxstatus의 ENS<temp_sensor>로 폴백한다(gtcs.py — 레거시 old/gmon의
  `tc auxstat` 직접 질의 복원). 전송도 gtcs.TcsClient.fttgoto 경유.
안전범위 [safe_min, safe_max] 밖이면 전송하지 않는다(AUTO/MAN 공통).
AUTO는 직전 주기 기준값과 |Δ| ≥ max_jump면 그 주기만 보류(첫 전송은 허용),
MAN은 max_jump 무시. 기준값은 레거시(old/gmon runcmd의 `set dref $ref`)와
동일하게 전송 여부와 무관하게 매 주기 최신 계산값으로 갱신되므로, 점프가
지속돼도 다음 주기에는 전송이 재개된다(영구 보류 없음 — 레거시 의미 유지).
전송은 UDP "abc>tc fttgoto <ref>" (ics.host:port); dry_run=yes면 로그만 남긴다.
dfocus는 run/dfocus.txt에 영속(gcommon.read_dfocus/write_dfocus).

사용법: gmon.py [-c gmon.conf]   (Tk import는 main() 안에서만 — headless import 안전)
"""
import argparse
import glob
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gcommon
import gtcs

GMON_DIR = os.path.dirname(os.path.abspath(__file__))

SNAP_TICK_MS = 3000     # 스냅샷 새 파일 검사 주기
SNAP_SETTLE_SEC = 1.0   # 쓰다 만 PNG 방지: mtime이 이만큼 지난 파일만 로드


def latest_snapshot(cfg):
    """run/snap의 최신 psf.snap.*.png → (경로, mtime). 없으면 (None, 0.0)."""
    snaps = glob.glob(os.path.join(cfg.rundir("snap"), "psf.snap.*.png"))
    best, best_mt = None, 0.0
    for p in snaps:
        try:
            mt = os.path.getmtime(p)
        except OSError:
            continue
        if mt > best_mt:
            best, best_mt = p, mt
    return best, best_mt


class FocusController:
    """초점 자동/수동 전송 로직 (GUI 비의존, DESIGN.md §8).

    sender(ref: float)와 fw_reader() -> dict|None 을 주입할 수 있다(시험용).
    기본 sender는 UDP "abc>tc fttgoto <ref>" 전송(dry_run=yes면 로그만).
    """

    def __init__(self, cfg, sender=None, fw_reader=None):
        self.cfg = cfg
        self.log = gcommon.setup_logger(cfg, "gmon")
        self.slope = cfg.getfloat("focus", "slope", fallback=-0.067)
        self.base = cfg.getfloat("focus", "base", fallback=4.7)
        self.step = cfg.getfloat("focus", "step", fallback=0.005)
        self.big_step = cfg.getfloat("focus", "big_step", fallback=0.5)
        self.safe_min = cfg.getfloat("focus", "safe_min", fallback=-8.0)
        self.safe_max = cfg.getfloat("focus", "safe_max", fallback=-3.0)
        self.max_jump = cfg.getfloat("focus", "max_jump", fallback=0.1)
        self.period_sec = cfg.getfloat("focus", "period_sec", fallback=120.0)
        self.host = cfg.get("ics", "host", fallback="127.0.0.1")
        self.port = cfg.getint("ics", "port", fallback=6660)
        self.dry_run = cfg.getbool("ics", "dry_run", fallback=True)
        # 온도 출처: fw=오늘 밤 fw파일(운용판 파리티) / tcs=서버 auxstatus /
        # auto=fw 우선, 없거나 fw_stale_sec보다 오래되면 서버로 폴백
        self.temp_source = cfg.get("focus", "temp_source", fallback="auto")
        self.temp_sensor = cfg.getint("focus", "temp_sensor", fallback=3)
        self.fw_stale_sec = cfg.getfloat("focus", "fw_stale_sec", fallback=900.0)
        self.tcs = gtcs.TcsClient(cfg, log=self.log)
        self.dfocus = gcommon.read_dfocus(cfg)
        self.last_ref = None   # 직전 주기 계산 ref (레거시 dref — AUTO max_jump 기준)
        self.last_fw = None    # 최신 fw 줄 파싱 dict (표시용)
        self._sender = sender if sender is not None else self._udp_send
        self._fw_reader = fw_reader if fw_reader is not None else self._read_fw_last

    # ---- fw 데이터 (DESIGN.md §5.2: 시각 fwN fwE fwW fwS FOCUS TEMP SECZ) ----
    def _read_fw_last(self):
        """오늘 밤 fw 파일의 마지막 유효 줄 파싱. 없으면 None."""
        path = gcommon.fw_path(self.cfg)
        try:
            with open(path) as fp:
                lines = [ln.strip() for ln in fp if ln.strip()]
        except OSError:
            return None
        if not lines:
            return None
        parts = lines[-1].split()
        if len(parts) < 8:
            return None
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None
        try:
            return {
                "time": parts[0],
                "fwn": float(parts[1]),
                "fwe": float(parts[2]),
                "fww": float(parts[3]),
                "fws": float(parts[4]),
                "focus": float(parts[5]),
                "temp": float(parts[6]),  # 공백분리 7번째 필드 = TEMP
                "secz": float(parts[7]),
                "line": lines[-1],
                "source": "fw",
                "mtime": mtime,  # temp_source=auto의 신선도 판정용
            }
        except ValueError:
            return None

    def _is_stale(self, rec):
        """fw 레코드가 fw_stale_sec보다 오래됐는가 (mtime 없으면 신선 취급)."""
        mtime = rec.get("mtime")
        return mtime is not None and (time.time() - mtime) > self.fw_stale_sec

    # ---- 계산·전송 ----
    def compute_ref(self):
        """ref = slope*T − (base + dfocus). 온도를 못 구하면 None.

        온도 출처(temp_source): fw=오늘 밤 fw파일 마지막 줄의 TEMP(=ENS3,
        운용판 파리티), tcs=TCS auxstatus의 ENS<temp_sensor>, auto=fw 우선이되
        fw가 없거나 fw_stale_sec보다 오래되면 서버로 폴백 (레거시 old/gmon의
        주석 처리된 `tc auxstat` 직접 질의를 복원한 것 — 밤 시작 등 fw가 아직
        없을 때도 초점 보정이 동작한다).
        """
        rec = None
        if self.temp_source in ("fw", "auto"):
            rec = self._fw_reader()
            if (rec is not None and self.temp_source == "auto"
                    and self._is_stale(rec)):
                self.log.info("fw stale (> %.0fs) — TCS 온도로 폴백",
                              self.fw_stale_sec)
                rec = None
        if rec is None and self.temp_source in ("tcs", "auto"):
            t = self.tcs.temperature()
            if t is not None:
                rec = {"temp": t, "source": "tcs",
                       "line": "TCS ENS%d=%.1f" % (self.temp_sensor, t)}
        self.last_fw = rec
        if not rec or rec.get("temp") is None:
            return None
        return self.slope * float(rec["temp"]) - (self.base + self.dfocus)

    def try_send(self, manual=False):
        """(sent, reason). 안전범위는 항상 검사, max_jump는 AUTO에서만.

        레거시 파리티: 비교 기준(last_ref)은 old/gmon runcmd 끝의 `set dref $ref`
        처럼 전송 여부와 무관하게 매 주기 최신 계산값으로 갱신한다. 따라서
        점프로 보류돼도 다음 주기에는 새 기준과 비교해 전송이 재개된다
        (한 주기만 건너뜀 — 영구 보류 없음).
        """
        ref = self.compute_ref()
        if ref is None:
            return False, "no-fw"
        prev = self.last_ref
        self.last_ref = ref  # 레거시 dref: 전송 여부와 무관하게 매회 갱신
        if ref < self.safe_min or ref > self.safe_max:
            self.log.warning("focus unsafe: ref=%.4f not in [%.3f, %.3f]",
                             ref, self.safe_min, self.safe_max)
            return False, "unsafe ref=%.4f" % ref
        if (not manual and prev is not None
                and abs(ref - prev) >= self.max_jump):
            self.log.warning("focus jump held: |%.4f - %.4f| >= %.3f",
                             ref, prev, self.max_jump)
            return False, "jump |%.4f - %.4f| >= %.3f" % (ref, prev, self.max_jump)
        self._sender(ref)
        return True, "sent %.3f" % ref

    def _udp_send(self, ref):
        """기본 sender — TCS fttgoto (gtcs가 dry_run·전송·응답 처리)."""
        return self.tcs.fttgoto(ref)

    # ---- dfocus 증감 (run/dfocus.txt 영속) ----
    def _shift(self, delta):
        self.dfocus = round(self.dfocus + delta, 6)
        gcommon.write_dfocus(self.cfg, self.dfocus)
        return self.dfocus

    def incr(self):
        return self._shift(self.step)

    def decr(self):
        return self._shift(-self.step)

    # 운용판 2021-01 "big adjust" (±big_step, 기본 0.5)
    def incr_big(self):
        return self._shift(self.big_step)

    def decr_big(self):
        return self._shift(-self.big_step)


class GmonApp:
    """Tkinter 관제 패널. tk 모듈을 주입받아 headless import를 깨지 않는다.

    구성: 메인 창=제어부(레거시 배치), 별도 Toplevel 창 2개=PSF 스냅샷·FWHM
    그래프. 서브 창은 닫으면 숨김 — 제어부 SNAP/PLOT 버튼으로 다시 연다.
    """

    def __init__(self, tk, root, cfg, ctrl):
        self.tk = tk
        self.root = root
        self.cfg = cfg
        self.ctrl = ctrl
        self.log = ctrl.log
        py = cfg.tool("python")
        self.python = py if (py and os.path.exists(py)) else sys.executable
        self._auto_after = None
        self._snap_state = (None, 0.0)   # (경로, mtime) — 표시 중인 스냅샷
        self._snap_img = None            # PhotoImage 참조 유지 (GC 방지)
        self._plot_img = None
        self._plot_proc = None           # 진행 중인 gplot oneshot 렌더
        self._plot_out = os.path.join(cfg.rundir("work"), "gui_fwplot.png")
        self.plot_refresh = max(3.0, cfg.getfloat("plot", "refresh_sec",
                                                  fallback=10.0))

        # ---- 좌상단: 제어부 (레거시 old/gmon grid 배치) ----
        ctrlf = tk.Frame(root)
        self.l1 = tk.Label(ctrlf, width=14, text="gwatch", bg="red")
        self.l2 = tk.Label(ctrlf, width=14, text="AutoAdjust")
        self.l3 = tk.Label(ctrlf, width=14, text="%.3f" % ctrl.dfocus,
                           fg="yellow", bg="blue")
        self.l4 = tk.Label(ctrlf, width=14, text="ref: -")
        self.l5 = tk.Label(ctrlf, width=14, text="OFF")
        self.l6 = tk.Label(ctrlf, width=14, text="-")

        self.b1 = tk.Button(ctrlf, width=12, text="ON", command=self.do_on)
        self.b2 = tk.Button(ctrlf, width=12, text="OFF", command=self.do_off)
        self.b3 = tk.Button(ctrlf, width=12, text="AUTO", command=self.do_auto)
        self.b4 = tk.Button(ctrlf, width=12, text="MAN", command=self.do_man)
        self.b5 = tk.Button(ctrlf, width=10, text="+%g" % ctrl.step,
                            command=self.do_incr)
        self.b6 = tk.Button(ctrlf, width=10, text="-%g" % ctrl.step,
                            command=self.do_decr)
        # 운용판 2021-01 big adjust 버튼 (±0.5)
        self.b7 = tk.Button(ctrlf, width=4, text="+%g" % ctrl.big_step,
                            command=self.do_incr_big)
        self.b8 = tk.Button(ctrlf, width=4, text="-%g" % ctrl.big_step,
                            command=self.do_decr_big)

        self.l1.grid(row=0, column=0)
        self.b1.grid(row=0, column=1)
        self.b2.grid(row=0, column=2)
        self.l2.grid(row=1, column=0)
        self.b3.grid(row=1, column=1)
        self.b4.grid(row=1, column=2)
        self.l3.grid(row=2, column=0)
        self.b5.grid(row=2, column=1)
        self.b6.grid(row=2, column=2)
        self.b7.grid(row=2, column=3)
        self.b8.grid(row=2, column=4)
        self.l4.grid(row=3, column=0)
        self.l5.grid(row=3, column=1)
        self.l6.grid(row=3, column=2)

        # 서브 창 다시 열기 버튼 (닫기=숨김이므로)
        self.b9 = tk.Button(ctrlf, width=12, text="SNAP",
                            command=lambda: self._show_win(self.snap_win))
        self.b10 = tk.Button(ctrlf, width=12, text="PLOT",
                             command=lambda: self._show_win(self.plot_win))
        self.b9.grid(row=3, column=3)
        self.b10.grid(row=3, column=4)

        # v2 추가 상태 라벨: 최신 fw 줄 요약 + gwatch/gplot 실행 상태
        self.lfw = tk.Label(ctrlf, anchor="w", text="fw: -")
        self.lproc = tk.Label(ctrlf, anchor="w", text="gwatch: ? / gplot: ?")
        self.lfw.grid(row=4, column=0, columnspan=5, sticky="we")
        self.lproc.grid(row=5, column=0, columnspan=5, sticky="we")

        # TCS 서버 상태 (auxstatus): 온도·초점·틸트·셔터 — 백그라운드 질의
        self.ltcs = tk.Label(ctrlf, anchor="w", text="TCS: -")
        self.ltcs.grid(row=6, column=0, columnspan=5, sticky="we")
        self._tcs_status = None
        if cfg.getbool("ics", "status_query", fallback=True):
            threading.Thread(target=self._tcs_poll, daemon=True).start()

        ctrlf.grid(row=0, column=0, sticky="nw", padx=6, pady=6)

        # ---- 별도 창 1: PSF 스냅샷 ----
        self.snap_win = tk.Toplevel(root)
        self.snap_win.title("gmon — PSF snapshot")
        self.snap_title = tk.Label(self.snap_win, anchor="w",
                                   text="PSF snapshot: -")
        self.snap_panel = tk.Label(self.snap_win,
                                   text="PSF 스냅샷 대기 중\n(run/snap)",
                                   bg="black", fg="gray70",
                                   width=60, height=20)
        self.snap_title.pack(side="top", anchor="w", padx=4, pady=2)
        self.snap_panel.pack(side="top", padx=4, pady=4)
        self.snap_win.protocol("WM_DELETE_WINDOW", self.snap_win.withdraw)

        # ---- 별도 창 2: FWHM 그래프 ----
        self.plot_win = tk.Toplevel(root)
        self.plot_win.title("gmon — FWHM monitor")
        self.plot_panel = tk.Label(self.plot_win,
                                   text="FWHM 그래프 대기 중 (fw 데이터 필요)",
                                   bg="white", fg="gray40",
                                   width=80, height=10)
        self.plot_panel.pack(padx=4, pady=4)
        self.plot_win.protocol("WM_DELETE_WINDOW", self.plot_win.withdraw)

        # 초기 배치: 제어부 우측에 스냅샷, 제어부 아래에 그래프
        root.after(200, self._place_windows)

        self._status_tick()
        self._snap_tick()
        self._plot_tick()

    def _place_windows(self):
        try:
            self.root.update_idletasks()
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            self.snap_win.geometry("+%d+%d" % (rx + rw + 24, ry))
            self.plot_win.geometry("+%d+%d" % (rx, ry + rh + 56))
        except Exception:
            pass  # 창이 이미 닫혔거나 미매핑 — 배치는 편의 기능일 뿐

    def _show_win(self, win):
        win.deiconify()
        win.lift()

    # ---- 데몬 제어 (pidfile 기반, killall 금지) ----
    def _launch_daemon(self, name):
        """gwatch/gplot 스크립트를 백그라운드로 기동 (pidfile 중복 검사 후 호출)."""
        script = os.path.join(GMON_DIR, name + ".py")
        if not os.path.exists(script):
            self.log.error("%s.py not found; launch skipped", name)
            return
        subprocess.Popen(
            [self.python, script, "-c", self.cfg.path],
            cwd=GMON_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.log.info("%s launched", name)

    def do_on(self):
        """ON: gwatch와 gplot 모두 기동 (DESIGN §7 — OFF와 대칭).

        fw 데이터 파일이 아직 없으면 gplot은 로그를 남기고 곧 종료하며,
        첫 노출 처리 후 gwatch.ensure_gplot()이 다시 기동한다.
        """
        for name in ("gwatch", "gplot"):
            if gcommon.PidFile(self.cfg, name).other_pid() is not None:
                self.log.info("%s already running; ON ignored", name)
            else:
                self._launch_daemon(name)
        self.l5.config(text="MON")
        self.l1.config(fg="black", bg="green")

    def do_off(self):
        for name in ("gwatch", "gplot"):
            if gcommon.PidFile(self.cfg, name).terminate():
                self.log.info("%s terminated (SIGTERM)", name)
        self.l5.config(text="OFF")
        self.l1.config(fg="black", bg="red")

    # ---- 초점 (AUTO: after 루프 / MAN: 1회) ----
    def _cancel_auto(self):
        if self._auto_after is not None:
            self.root.after_cancel(self._auto_after)
            self._auto_after = None

    def do_auto(self):
        self._cancel_auto()
        self.l2.config(fg="black", bg="green")
        self.l6.config(text="AUTO")
        self._auto_tick()

    def _auto_tick(self):
        sent, reason = self.ctrl.try_send(manual=False)
        self._show_result(sent, reason)
        self._auto_after = self.root.after(
            int(self.ctrl.period_sec * 1000), self._auto_tick)

    def do_man(self):
        self._cancel_auto()
        self.l2.config(fg="black", bg="yellow")
        self.l6.config(text="MAN")
        sent, reason = self.ctrl.try_send(manual=True)
        self._show_result(sent, reason)

    def _show_result(self, sent, reason):
        if reason == "no-fw":
            self.l4.config(text="NO fwdat", fg="yellow", bg="red")
        elif sent:
            self.l4.config(text="ref %.3f" % self.ctrl.last_ref,
                           fg="black", bg="green")
        else:
            self.l4.config(text=reason[:24], fg="black", bg="orange")
        self.log.info("focus try_send: sent=%s %s", sent, reason)

    def do_incr(self):
        self.l3.config(text="%.3f" % self.ctrl.incr())
        self._preview_ref()

    def do_decr(self):
        self.l3.config(text="%.3f" % self.ctrl.decr())

    def do_incr_big(self):
        self.l3.config(text="%.3f" % self.ctrl.incr_big())

    def do_decr_big(self):
        self.l3.config(text="%.3f" % self.ctrl.decr_big())
        self._preview_ref()

    def _preview_ref(self):
        ref = self.ctrl.compute_ref()
        if ref is None:
            self.l4.config(text="NO fwdat", fg="yellow", bg="red")
        else:
            self.l4.config(text="ref %.3f" % ref, fg="black", bg="green")

    # ---- 주기 상태 갱신 ----
    def _tcs_poll(self):
        """백그라운드 TCS auxstatus 질의 — 결과 저장만, 표시는 _status_tick."""
        period = max(2.0, self.cfg.getfloat("ics", "status_sec", fallback=10.0))
        while True:
            self._tcs_status = self.ctrl.tcs.auxstatus()
            time.sleep(period)

    def _status_tick(self):
        gw = gcommon.PidFile(self.cfg, "gwatch").other_pid()
        gp = gcommon.PidFile(self.cfg, "gplot").other_pid()
        self.lproc.config(text="gwatch: %s / gplot: %s"
                          % (gw or "stopped", gp or "embedded"))
        self.l1.config(bg="green" if gw else "red")
        rec = self.ctrl._fw_reader()
        self.ctrl.last_fw = rec
        self.lfw.config(text="fw: %s" % (rec["line"] if rec else "-"))
        kv = self._tcs_status
        if kv:
            def fv(key, fmt):
                v = kv.get(key)
                return (fmt % v) if isinstance(v, float) else "-"
            sensor = self.ctrl.temp_sensor
            self.ltcs.config(text="TCS: T(ENS%d)=%s F=%s tiltNS/EW=%s/%s shut=%s"
                             % (sensor, fv("ENS%d" % sensor, "%.1f"),
                                fv("FAFOCUS", "%+.3f"), fv("FATILTNS", "%+.1f"),
                                fv("FATILTEW", "%+.1f"), kv.get("SHUTTER", "-")))
        else:
            self.ltcs.config(text="TCS: 무응답")
        self.root.after(2000, self._status_tick)

    # ---- 우측 패널: 최신 PSF 스냅샷 자동 표시 ----
    def _snap_tick(self):
        path, mtime = latest_snapshot(self.cfg)
        if (path is not None and (path, mtime) != self._snap_state
                and time.time() - mtime > SNAP_SETTLE_SEC):
            try:
                img = self.tk.PhotoImage(file=path)
            except Exception as exc:  # 쓰다 만 파일 등 — 다음 틱에 재시도
                self.log.warning("snapshot load failed (%s): %s", path, exc)
            else:
                self._snap_img = img
                self.snap_panel.config(image=img, text="", width=img.width(),
                                       height=img.height())
                self.snap_title.config(text="PSF snapshot: %s"
                                       % os.path.basename(path))
                self._snap_state = (path, mtime)
        self.root.after(SNAP_TICK_MS, self._snap_tick)

    # ---- 하단 패널: FWHM 그래프 내장 렌더 (gplot --oneshot --term png) ----
    def _plot_tick(self):
        """렌더 시작 → _plot_poll이 완료를 감시. 중복 렌더는 시작하지 않는다."""
        if self._plot_proc is None:
            if os.path.exists(gcommon.fw_path(self.cfg)):
                try:
                    self._plot_proc = subprocess.Popen(
                        [self.python, os.path.join(GMON_DIR, "gplot.py"),
                         "-c", self.cfg.path, "--oneshot", "--term", "png",
                         "--out", self._plot_out],
                        cwd=GMON_DIR, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, start_new_session=True)
                    self.root.after(300, self._plot_poll)
                except OSError as exc:
                    self.log.error("gplot render launch failed: %s", exc)
            else:
                self.plot_panel.config(
                    text="FWHM 그래프 대기 중 — 오늘 밤 fw 데이터 없음 (%s)"
                    % os.path.basename(gcommon.fw_path(self.cfg)), image="")
                self._plot_img = None
        self.root.after(int(self.plot_refresh * 1000), self._plot_tick)

    def _plot_poll(self):
        proc = self._plot_proc
        if proc is None:
            return
        if proc.poll() is None:          # 아직 렌더 중
            self.root.after(300, self._plot_poll)
            return
        self._plot_proc = None
        if proc.returncode == 0 and os.path.exists(self._plot_out):
            try:
                img = self.tk.PhotoImage(file=self._plot_out)
            except Exception as exc:
                self.log.warning("plot load failed: %s", exc)
                return
            self._plot_img = img
            self.plot_panel.config(image=img, text="", width=img.width(),
                                   height=img.height())
        else:
            self.log.warning("gplot oneshot rc=%s", proc.returncode)


def main(argv=None):
    ap = argparse.ArgumentParser(description="gmon v2 GUI 관제탑")
    ap.add_argument("-c", "--config", default=None, help="gmon.conf 경로")
    args = ap.parse_args(argv)

    cfg = gcommon.load_config(args.config)
    gcommon.ensure_dirs(cfg)

    # GUI 단일 실행 + gwatch가 외부 gnuplot 창 생략 판단에 쓰는 표지
    pf = gcommon.PidFile(cfg, "gmon")
    if not pf.acquire():
        print("gmon GUI가 이미 실행 중입니다 (pid=%s)" % pf.other_pid())
        return 1

    import tkinter as tk  # headless import 안전을 위해 여기서만 import

    try:
        ctrl = FocusController(cfg)
        root = tk.Tk()
        root.title("gmon v2 — %s" % cfg.get("site", "name", fallback=""))
        GmonApp(tk, root, cfg, ctrl)
        # 창을 닫아도 데몬(gwatch)은 유지된다 — 정지는 OFF 버튼으로.
        root.mainloop()
    finally:
        pf.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
