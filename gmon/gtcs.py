#!/usr/bin/env python3
"""gtcs.py — TCS/ICS UDP(ISIS 허브) 클라이언트 (레거시 `nc -w 1 -u` 파리티).

레거시 old/gmon·do-Monitoring·tcon이 셸+nc로 하던 서버 질의/이동을 제공한다.
프로토콜은 ISIS 라우팅 "<from>><to> <명령>" 텍스트 데이터그램이며, 응답은
IMPv2 형식 "<to>><FROM> DONE: <KEY=VALUE ...>" 한 줄이다
(TCSAgent/TCSAgent.latest/KMTNet/commands.c cmd_auxstatus 근거).

질의 (읽기 — dry_run과 무관, 서버 무응답이면 timeout 후 None):
  auxstatus  : 온도 ENS1..7, 초점 FAFOCUS, 틸트 FATILTNS/EW, 셔터 SHUTTER,
               액추에이터 FAPOSS/E/W, 돔 DSALT/DSTEL 등 KEY=VALUE dict
이동 (쓰기 — [ics] dry_run=yes면 로그만 남기고 전송하지 않음):
  fttgoto <foc> [<tns> <tew>] : 절대 초점(/틸트) 이동 (레거시 gmon runcmd)
  dtilt <dns> <dew>           : 상대 틸트 이동 (레거시 tcon)

CLI (현장 점검용):
  gtcs.py auxstatus [-c CONF]          파싱된 상태 출력
  gtcs.py fttgoto FOC [TNS TEW]        초점(/틸트) 이동 (dry_run 존중)
  gtcs.py dtilt DNS DEW                상대 틸트 (dry_run 존중)
  gtcs.py raw "임의 명령"               원문 전송·응답 출력 (dry_run 존중)
"""
import argparse
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gcommon


def parse_kv(reply):
    """IMPv2 응답에서 KEY=VALUE 토큰을 dict로. 숫자는 float 변환을 시도한다.

    라우팅 머리("TC>ABC DONE: AUXSTATUS")처럼 '='이 없는 토큰은 건너뛴다.
    """
    out = {}
    if not reply:
        return out
    for tok in reply.split():
        if "=" not in tok:
            continue
        key, _, val = tok.partition("=")
        if not key:
            continue
        try:
            out[key] = float(val)
        except ValueError:
            out[key] = val
    return out


class TcsClient:
    """UDP 1왕복 질의/명령 클라이언트. 상태 없음 — 호출마다 소켓을 새로 연다."""

    def __init__(self, cfg, log=None):
        self.cfg = cfg
        self.log = log or gcommon.setup_logger(cfg, "gtcs")
        self.host = cfg.get("ics", "host", fallback="127.0.0.1")
        self.port = cfg.getint("ics", "port", fallback=6660)
        self.timeout = cfg.getfloat("ics", "timeout_sec", fallback=1.0)
        self.me = cfg.get("ics", "from", fallback="abc")
        self.tc = cfg.get("ics", "tc", fallback="tc")
        self.dry_run = cfg.getbool("ics", "dry_run", fallback=True)

    # ---- 저수준 ----
    def _exchange(self, msg, wait_reply=True):
        """데이터그램 1건 전송 후 응답 1건 수신. 무응답/오류는 None."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        try:
            sock.sendto(msg.encode("ascii"), (self.host, self.port))
            if not wait_reply:
                return ""
            data, _ = sock.recvfrom(8192)
            return data.decode("ascii", errors="replace").strip()
        except (socket.timeout, OSError) as exc:
            self.log.warning("TCS no reply (%s): %s", msg, exc)
            return None
        finally:
            sock.close()

    def query(self, cmd):
        """읽기 질의 — dry_run과 무관하게 전송. 응답 원문 또는 None."""
        return self._exchange("%s>%s %s" % (self.me, self.tc, cmd))

    def command(self, cmd):
        """쓰기 명령 — dry_run=yes면 로그만 남기고 "dry-run" 반환."""
        msg = "%s>%s %s" % (self.me, self.tc, cmd)
        if self.dry_run:
            self.log.info("dry_run: %s (UDP not sent)", msg)
            return "dry-run"
        reply = self._exchange(msg)
        self.log.info("sent: %s -> %s:%d reply=%s", msg, self.host, self.port,
                      reply)
        return reply if reply is not None else "sent-noreply"

    # ---- 질의 ----
    def auxstatus(self):
        """auxstatus KEY=VALUE dict (응답에 원문 '_raw' 포함). 무응답이면 None."""
        reply = self.query("auxstatus")
        if reply is None:
            return None
        kv = parse_kv(reply)
        kv["_raw"] = reply
        return kv

    def temperature(self, status=None, sensor=None):
        """ENS<n> 온도 (기본 [focus] temp_sensor=3 — fw 파일 TEMP와 동일 센서)."""
        if sensor is None:
            sensor = self.cfg.getint("focus", "temp_sensor", fallback=3)
        kv = status if status is not None else self.auxstatus()
        if not kv:
            return None
        val = kv.get("ENS%d" % sensor)
        return val if isinstance(val, float) else None

    def focus(self, status=None):
        kv = status if status is not None else self.auxstatus()
        if not kv:
            return None
        val = kv.get("FAFOCUS")
        return val if isinstance(val, float) else None

    def shutter(self, status=None):
        kv = status if status is not None else self.auxstatus()
        return kv.get("SHUTTER") if kv else None

    def tilt(self, status=None):
        """(FATILTNS, FATILTEW) — 없으면 (None, None)."""
        kv = status if status is not None else self.auxstatus()
        if not kv:
            return None, None
        ns, ew = kv.get("FATILTNS"), kv.get("FATILTEW")
        return (ns if isinstance(ns, float) else None,
                ew if isinstance(ew, float) else None)

    # ---- 이동 ----
    def fttgoto(self, foc, tns=None, tew=None):
        """절대 초점(/틸트) 이동 — 레거시 "abc>tc fttgoto <ref>" 파리티."""
        cmd = "fttgoto %.3f" % foc
        if tns is not None and tew is not None:
            cmd += " %+.1f %+.1f" % (tns, tew)
        return self.command(cmd)

    def dtilt(self, dns, dew):
        """상대 틸트 이동 — 레거시 tcon "abc>tc dtilt <dNS> <dEW>" 파리티."""
        return self.command("dtilt %+.1f %+.1f" % (dns, dew))


def main(argv=None):
    ap = argparse.ArgumentParser(description="gmon TCS/ICS UDP 클라이언트")
    ap.add_argument("-c", "--config", default=None)
    sub = ap.add_subparsers(dest="op", required=True)
    sub.add_parser("auxstatus")
    p = sub.add_parser("fttgoto")
    p.add_argument("foc", type=float)
    p.add_argument("tns", type=float, nargs="?")
    p.add_argument("tew", type=float, nargs="?")
    p = sub.add_parser("dtilt")
    p.add_argument("dns", type=float)
    p.add_argument("dew", type=float)
    p = sub.add_parser("raw")
    p.add_argument("cmd")
    args = ap.parse_args(argv)

    cfg = gcommon.load_config(args.config)
    cli = TcsClient(cfg)
    if args.op == "auxstatus":
        kv = cli.auxstatus()
        if kv is None:
            print("no reply from %s:%d" % (cli.host, cli.port))
            return 1
        for key in sorted(k for k in kv if k != "_raw"):
            print("%-10s %s" % (key, kv[key]))
        return 0
    if args.op == "fttgoto":
        print(cli.fttgoto(args.foc, args.tns, args.tew))
    elif args.op == "dtilt":
        print(cli.dtilt(args.dns, args.dew))
    elif args.op == "raw":
        print(cli.command(args.cmd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
