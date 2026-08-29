#!/usr/bin/env python3
"""tcs_sim.py — TCS(TCSAgent) auxstatus 시뮬레이터 (로컬 시험용 UDP 서버).

gmon.conf [ics] host/port(기본 127.0.0.1:6660)에서 ISIS 라우팅
"<from>>tc <명령>" 데이터그램을 받아 TCSAgent commands.c cmd_auxstatus와
같은 필드 순서의 IMPv2 응답을 돌려준다. 상태를 실제로 유지하므로
fttgoto/dtilt가 FAFOCUS·FATILT를 움직이고, 온도(ENS1..7)는 설정한
진폭·주기의 사인 곡선 + 잡음으로 천천히 변한다 — gmon AUTO 초점 보정이
따라가는 것을 로컬에서 관찰할 수 있다.

지원 명령:
  auxstatus | auxstat | astatus   AUX 상태 (온도·초점·틸트·셔터 KEY=VALUE)
  tcsstatus | tstat               포인팅 상태 (RA/DEC/HA/ST, SECZ, ALT, AZ —
                                  SECZ는 ALT에서 1/sin(ALT)로 자동 계산)
  fttgoto <foc> [<tns> <tew>]     절대 초점(/틸트) 이동 → 상태 갱신
  dtilt <dns> <dew>               상대 틸트 이동 → 상태 갱신
  simset KEY=VALUE [...]          (시뮬레이터 전용) 임의 상태 강제
                                  예: simset SHUTTER=CLOSE ENS3=12.5 ALT=35.0

사용법:
  tcs_sim.py [-c gmon.conf] [--port N] [--temp 6.6] [--drift 1.5]
             [--period 3600] [--focus -6.5] [--shutter OPEN] [--quiet]

시뮬레이터 전 체인 시험 절차 (별도 터미널 3개):
  1) tools/tcs_sim.py                      # TCS 시뮬레이터
  2) gmon.py                               # GUI — TCS 라벨에 온도·초점 표시
  3) tools/make_synthetic.py ... → run/incoming/   # 노출 투입
"""
import argparse
import math
import os
import random
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gcommon  # noqa: E402


class TcsSim:
    def __init__(self, args, cfg):
        self.name = cfg.get("ics", "tc", fallback="tc")
        self.telid = "KMT" + cfg.get("site", "name", fallback="S")[0]
        self.t0 = time.time()
        self.temp0 = args.temp        # ENS3 기준 온도
        self.drift = args.drift       # 사인 진폭 (°C)
        self.period = args.period     # 사인 주기 (초)
        self.rng = random.Random(42)
        self.quiet = args.quiet
        # 가동 상태 (fttgoto/dtilt/simset이 갱신)
        self.state = {
            "FAFOCUS": args.focus,
            "FATILTNS": -8.7, "FATILTEW": -370.1,
            "FAPOSS": -5.167, "FAPOSE": -6.798, "FAPOSW": -3.663,
            "SHUTTER": args.shutter, "FILTER": "I", "FILNUM": 1,
            "DSALT": 45.0, "DSTEL": 44.9, "MCPOS": 100,
            "CHSET": -15.0, "CHPROC": -14.8,
            # 포인팅 (tcsstatus) — 기준 캡처 psf.snap.20181003 값과 동일
            "RA": "17:45:40.0", "DEC": "-29:00:28", "EQUINOX": "2000.0",
            "HA": "+01:23:45", "ST": "19:09:25",
            "ALT": 51.7, "AZ": -66.7, "TELMOVE": "Idle",
        }
        self.override = {}            # simset 강제값 (온도 포함 최우선)

    # ---- 온도 모델: ENS3 = temp0 + drift·sin(2πt/period) + 잡음 ----
    def _temps(self):
        t = time.time() - self.t0
        base = self.temp0 + self.drift * math.sin(2 * math.pi * t / self.period)
        out = {}
        for i in range(1, 8):
            offs = (i - 3) * 0.4      # 센서별 고정 오프셋 (ENS3이 기준)
            out["ENS%d" % i] = base + offs + self.rng.gauss(0.0, 0.05)
        return out

    def _utc(self):
        g = time.gmtime()
        return ("%04d-%02d-%02d" % g[:3], "%02d:%02d:%02d.000" % g[3:6])

    # ---- 응답 생성 (TCSAgent cmd_auxstatus 필드 순서 재현) ----
    def auxstatus(self):
        d, t = self._utc()
        s = dict(self.state)
        s.update(self._temps())
        s.update(self.override)
        r = ("AUXSTATUS AUXQDATE=%sT%s TIMESYS=UTC TELID=%s AUXLINK=Up"
             " AUXARC=Enabled AUXUDATE=%sT%s" % (d, t, self.telid, d, t))
        r += (" FSSTAT=Connected FILTOP=Idle FILNUM=%d FILTER=%s SHUTOP=Idle"
              " SHUTTER=%s" % (s["FILNUM"], s["FILTER"], s["SHUTTER"]))
        r += (" FASTAT=Connected FAFOCUS=%+.3f FATILTNS=%+.1f FATILTEW=%+.1f"
              " FALIMS=0 FALIME=0 FALIMW=0 FAPOSS=%+.3f FAPOSE=%+.3f"
              " FAPOSW=%+.3f" % (s["FAFOCUS"], s["FATILTNS"], s["FATILTEW"],
                                 s["FAPOSS"], s["FAPOSE"], s["FAPOSW"]))
        r += (" DSSTAT=Connected DSUP=Off DSLW=Off DSSAF=Off DSAUTO=ENABLED"
              " DSALT=%.1f DSTEL=%.1f" % (s["DSALT"], s["DSTEL"]))
        r += " MCSTAT=Connected MCPOS=%d" % s["MCPOS"]
        r += (" CHSTAT=Connected CHOP=ON CHSET=%.1f CHPROC=%.1f"
              % (s["CHSET"], s["CHPROC"]))
        r += " ENSTAT=Connected ENFAN=ON"
        for i in range(1, 8):
            r += " ENS%d=%.1f" % (i, s["ENS%d" % i])
        return r

    def tcsstatus(self):
        """포인팅 상태 — TCSAgent cmd_tcsstatus 필드 순서 재현.

        SECZ는 ALT로부터 1/sin(ALT) 계산 (simset SECZ=...로 강제 가능).
        """
        d, t = self._utc()
        s = dict(self.state)
        s.update(self.override)
        alt = float(s["ALT"])
        secz = s.get("SECZ")
        if not isinstance(secz, float):
            secz = 1.0 / max(1e-6, math.sin(math.radians(max(1.0, alt))))
        return ("TCSSTATUS TCSQDATE=%sT%s TIMESYS=UTC TCSLINK=Up"
                " TCSARC=Enabled TCSUDATE=%sT%s RA=%s DEC=%s EQUINOX=%s"
                " HA=%s ST=%s SECZ=%.2f ALT=%.1f AZ=%.1f TELMOVE=%s"
                % (d, t, d, t, s["RA"], s["DEC"], s["EQUINOX"], s["HA"],
                   s["ST"], secz, alt, float(s["AZ"]), s["TELMOVE"]))

    # ---- 명령 처리 ----
    def handle(self, cmd):
        """명령 본문 → 응답 본문 ("DONE:"/"ERROR:" 뒤에 붙을 문자열)."""
        toks = cmd.split()
        op = toks[0].lower() if toks else ""
        if op in ("auxstatus", "auxstat", "astatus"):
            return "DONE: " + self.auxstatus()
        if op in ("tcsstatus", "tstat"):
            return "DONE: " + self.tcsstatus()
        if op == "fttgoto":
            try:
                foc = float(toks[1])
                if len(toks) >= 4:
                    self.state["FATILTNS"] = float(toks[2])
                    self.state["FATILTEW"] = float(toks[3])
            except (IndexError, ValueError):
                return "ERROR: usage: fttgoto <foc> (<tns> <tew>)"
            self.state["FAFOCUS"] = foc
            return ("DONE: FTTGOTO FAFOCUS=%+.3f FATILTNS=%+.1f FATILTEW=%+.1f"
                    % (self.state["FAFOCUS"], self.state["FATILTNS"],
                       self.state["FATILTEW"]))
        if op == "dtilt":
            try:
                self.state["FATILTNS"] += float(toks[1])
                self.state["FATILTEW"] += float(toks[2])
            except (IndexError, ValueError):
                return "ERROR: usage: dtilt <dns> <dew>"
            return ("DONE: DTILT FATILTNS=%+.1f FATILTEW=%+.1f"
                    % (self.state["FATILTNS"], self.state["FATILTEW"]))
        if op == "simset":                      # 시뮬레이터 전용
            for tok in toks[1:]:
                key, _, val = tok.partition("=")
                if not key or not val:
                    continue
                try:
                    self.override[key] = float(val)
                except ValueError:
                    if key in self.state:
                        self.state[key] = val
                    else:
                        self.override[key] = val
            return "DONE: SIMSET %d field(s)" % (len(toks) - 1)
        return "ERROR: unknown command '%s'" % op

    def serve(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((host, port))
        except OSError as exc:
            print("tcs_sim: %s:%d 바인드 실패 (%s)" % (host, port, exc))
            print("  이미 실행 중인 인스턴스가 있는지 확인하세요:"
                  "  lsof -nP -iUDP:%d" % port)
            print("  이미 떠 있다면 다시 띄울 필요 없이 그대로 사용하면 됩니다"
                  " (확인: gtcs.py auxstatus)")
            return 1
        print("tcs_sim: %s:%d 대기 (name=%s telid=%s, ENS3=%.1f±%.1f°C/%ds,"
              " FAFOCUS=%+.3f) — Ctrl-C로 종료"
              % (host, port, self.name, self.telid, self.temp0, self.drift,
                 self.period, self.state["FAFOCUS"]))
        while True:
            data, addr = sock.recvfrom(8192)
            msg = data.decode("ascii", errors="replace").strip()
            # ISIS 라우팅: "<from>><to> <명령>" — 내 앞이 아니면 무시
            head, _, body = msg.partition(" ")
            src, _, dst = head.partition(">")
            if dst.lower() != self.name.lower() or not body:
                if not self.quiet:
                    print("  무시: %r" % msg)
                continue
            reply = "%s>%s %s" % (self.name.upper(), src.upper(),
                                  self.handle(body))
            sock.sendto(reply.encode("ascii"), addr)
            if not self.quiet:
                body_short = reply if len(reply) < 100 else reply[:97] + "..."
                print("  %s ← %r" % (msg, body_short))


def main(argv=None):
    ap = argparse.ArgumentParser(description="TCS auxstatus 시뮬레이터")
    ap.add_argument("-c", "--config", default=None, help="gmon.conf 경로")
    ap.add_argument("--host", default=None, help="바인드 주소 (기본 [ics] host)")
    ap.add_argument("--port", type=int, default=None, help="포트 (기본 [ics] port)")
    ap.add_argument("--temp", type=float, default=6.6, help="ENS3 기준 온도 °C")
    ap.add_argument("--drift", type=float, default=1.5, help="온도 사인 진폭 °C")
    ap.add_argument("--period", type=float, default=3600.0, help="온도 주기 초")
    ap.add_argument("--focus", type=float, default=-6.5, help="초기 FAFOCUS")
    ap.add_argument("--shutter", default="OPEN", choices=["OPEN", "CLOSE"])
    ap.add_argument("--quiet", action="store_true", help="왕복 로그 생략")
    args = ap.parse_args(argv)

    cfg = gcommon.load_config(args.config)
    host = args.host or cfg.get("ics", "host", fallback="127.0.0.1")
    port = args.port if args.port is not None else cfg.getint(
        "ics", "port", fallback=6660)
    # 단일 실행 가드 (run/pid/tcs_sim.pid) — 중복 기동 시 안내 후 종료
    pf = gcommon.PidFile(cfg, "tcs_sim")
    if not pf.acquire():
        print("tcs_sim이 이미 실행 중입니다 (pid=%s) — 다시 띄울 필요 없이"
              " 그대로 사용하면 됩니다 (확인: gtcs.py auxstatus)"
              % pf.other_pid())
        return 0
    sim = TcsSim(args, cfg)
    try:
        return sim.serve(host, port) or 0
    except KeyboardInterrupt:
        print("\ntcs_sim 종료")
        return 0
    finally:
        pf.release()


if __name__ == "__main__":
    sys.exit(main())
