#!/usr/bin/env python3
"""tests/test_tcs.py — gtcs TCS 클라이언트 시험 (모의 UDP 서버, DESIGN.md §8).

로컬 UDP 서버가 TCSAgent commands.c cmd_auxstatus 형식의 응답을 돌려주고,
요청 형식(ISIS 라우팅)·파싱·dry_run 차단·타임아웃·FocusController의
temp_source=auto 서버 폴백을 검증한다. pytest 불필요 — 단독 실행 assert.
"""
import configparser
import os
import shutil
import socket
import sys
import tempfile
import threading
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
GMON_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, GMON_DIR)

import gcommon
import gtcs
import gmon as gmon_mod

# TCSAgent cmd_auxstatus 응답 형식 재현 (AUX_UP, 전 계통 연결)
AUXREPLY = (
    "TC>ABC DONE: AUXSTATUS AUXQDATE=2026-08-29T01:00:00.000 TIMESYS=UTC"
    " TELID=KMTS AUXLINK=Up AUXARC=Enabled AUXUDATE=2026-08-29T01:00:00"
    " FSSTAT=Connected FILTOP=Idle FILNUM=1 FILTER=I SHUTOP=Idle SHUTTER=OPEN"
    " FASTAT=Connected FAFOCUS=-6.798 FATILTNS=-8.7 FATILTEW=-370.1"
    " FALIMS=0 FALIME=0 FALIMW=0 FAPOSS=-5.167 FAPOSE=-6.798 FAPOSW=-3.663"
    " DSSTAT=Connected DSUP=Off DSLW=Off DSSAF=Off DSAUTO=ENABLED"
    " DSALT=45.0 DSTEL=44.9 MCSTAT=Connected MCPOS=1"
    " CHSTAT=Connected CHOP=ON CHSET=-15.0 CHPROC=-14.8"
    " ENSTAT=Connected ENFAN=ON ENS1=4.2 ENS2=5.6 ENS3=6.6 ENS4=7.0"
    " ENS5=7.1 ENS6=7.2 ENS7=7.3"
)
REPLIES = {
    "auxstatus": AUXREPLY,
    "fttgoto": "TC>ABC DONE: FTTGOTO",
    "dtilt": "TC>ABC DONE: DTILT",
}


class MockTcs(threading.Thread):
    """수신한 "<from>>tc <명령>"의 첫 단어로 canned 응답을 돌려주는 UDP 서버."""

    def __init__(self):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.2)
        self.port = self.sock.getsockname()[1]
        self.requests = []
        self._halt = threading.Event()  # 이름 주의: Thread._stop과 충돌 금지

    def run(self):
        while not self._halt.is_set():
            try:
                data, addr = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            msg = data.decode("ascii", errors="replace").strip()
            self.requests.append(msg)
            cmd = msg.partition(" ")[2].split()[0] if " " in msg else ""
            reply = REPLIES.get(cmd)
            if reply:
                self.sock.sendto(reply.encode("ascii"), addr)

    def stop(self):
        self._halt.set()
        self.join(timeout=2)
        self.sock.close()


def make_cfg(tmp, name, port, overrides=None):
    cp = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    with open(os.path.join(GMON_DIR, "gmon.conf"), encoding="utf-8") as fp:
        cp.read_file(fp)
    cp.set("paths", "runroot", os.path.join(tmp, name + "_run"))
    cp.set("paths", "configdir", os.path.join(GMON_DIR, "config"))
    cp.set("ics", "host", "127.0.0.1")
    cp.set("ics", "port", str(port))
    cp.set("ics", "timeout_sec", "0.5")
    for (sec, key), val in (overrides or {}).items():
        cp.set(sec, key, val)
    path = os.path.join(tmp, name + ".conf")
    with open(path, "w", encoding="utf-8") as fp:
        cp.write(fp)
    return gcommon.load_config(path)


def main():
    tmp = tempfile.mkdtemp(prefix="tmp_tcs_", dir=TESTS_DIR)
    srv = MockTcs()
    srv.start()

    # ---------- 1. auxstatus 질의: 요청 형식 + 파싱 ----------
    cfg = make_cfg(tmp, "q", srv.port)
    cli = gtcs.TcsClient(cfg)
    kv = cli.auxstatus()
    assert kv is not None
    assert srv.requests[-1] == "abc>tc auxstatus", srv.requests[-1]
    assert cli.temperature(status=kv) == 6.6              # ENS3 (fw TEMP 파리티)
    assert cli.temperature(status=kv, sensor=1) == 4.2
    assert cli.focus(status=kv) == -6.798
    assert cli.shutter(status=kv) == "OPEN"
    assert cli.tilt(status=kv) == (-8.7, -370.1)
    assert kv["FAPOSS"] == -5.167 and kv["TELID"] == "KMTS"
    # 레거시 do-Monitoring `awk $15` 파리티: 15번째 토큰이 SHUTTER=...
    assert AUXREPLY.split()[14].startswith("SHUTTER="), AUXREPLY.split()[14]

    # ---------- 2. dry_run=yes → 이동 명령 미전송 ----------
    n0 = len(srv.requests)
    assert cli.dry_run is True
    assert cli.fttgoto(-6.598) == "dry-run"
    assert cli.dtilt(0.1, -0.5) == "dry-run"
    time.sleep(0.1)
    assert len(srv.requests) == n0, "dry_run인데 서버로 전송됨"

    # ---------- 3. dry_run=no → 이동 명령 전송 (레거시 명령 형식) ----------
    cfg2 = make_cfg(tmp, "live", srv.port, {("ics", "dry_run"): "no"})
    cli2 = gtcs.TcsClient(cfg2)
    r = cli2.fttgoto(-6.598)
    assert srv.requests[-1] == "abc>tc fttgoto -6.598", srv.requests[-1]
    assert r == "TC>ABC DONE: FTTGOTO"
    cli2.fttgoto(-6.5, tns=-8.7, tew=-370.1)
    assert srv.requests[-1] == "abc>tc fttgoto -6.500 -8.7 -370.1", srv.requests[-1]
    cli2.dtilt(0.1, -0.5)
    assert srv.requests[-1] == "abc>tc dtilt +0.1 -0.5", srv.requests[-1]

    # ---------- 4. 무응답 서버 → None (timeout 내) ----------
    dead = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dead.bind(("127.0.0.1", 0))
    dead_port = dead.getsockname()[1]
    dead.close()  # 아무도 안 듣는 포트
    cfg3 = make_cfg(tmp, "dead", dead_port)
    cli3 = gtcs.TcsClient(cfg3)
    t0 = time.time()
    assert cli3.auxstatus() is None
    assert time.time() - t0 < 2.0

    # ---------- 5. FocusController temp_source=auto: fw 없음 → 서버 폴백 ----
    cfgf = make_cfg(tmp, "fc", srv.port)   # temp_source=auto (기본)
    ctrl = gmon_mod.FocusController(cfgf)
    ref = ctrl.compute_ref()
    want = -0.067 * 6.6 - (5.56 + 0.0)     # ENS3=6.6, base=5.56
    assert ref is not None and abs(ref - want) < 1e-9, (ref, want)
    assert ctrl.last_fw["source"] == "tcs"
    sent, reason = ctrl.try_send(manual=True)  # -6.0022 ∈ [-8,-5] → 전송(dry-run)
    assert sent is True, reason

    # fw 파일이 생기면 fw가 우선 (운용판 파리티)
    fwp = gcommon.fw_path(cfgf)
    os.makedirs(os.path.dirname(fwp), exist_ok=True)
    with open(fwp, "w") as fp:
        fp.write("26:08:29:01:00:00 2.0 2.0 2.0 2.0 -6.000 10.0 1.20\n")
    ref = ctrl.compute_ref()
    assert abs(ref - (-0.067 * 10.0 - 5.56)) < 1e-9, ref
    assert ctrl.last_fw["source"] == "fw"

    # ---------- 6. temp_source=fw: fw 없으면 서버 질의 없이 None ----------
    cfg6 = make_cfg(tmp, "fwonly", srv.port,
                    {("focus", "temp_source"): "fw"})
    ctrl6 = gmon_mod.FocusController(cfg6)
    n0 = len(srv.requests)
    assert ctrl6.compute_ref() is None
    assert len(srv.requests) == n0, "temp_source=fw인데 서버 질의 발생"

    # ---------- 7. tools/tcs_sim.py 실물 왕복: 상태가 실제로 움직인다 ----------
    import subprocess
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    sim_port = probe.getsockname()[1]
    probe.close()
    cfg7 = make_cfg(tmp, "sim", sim_port, {("ics", "dry_run"): "no"})
    proc = subprocess.Popen(
        [sys.executable, os.path.join(GMON_DIR, "tools", "tcs_sim.py"),
         "-c", cfg7.path, "--port", str(sim_port), "--temp", "6.6",
         "--drift", "0", "--focus", "-6.5", "--quiet"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        cli7 = gtcs.TcsClient(cfg7)
        kv7 = None
        for _ in range(30):                       # 기동 대기 (~3s)
            kv7 = cli7.auxstatus()
            if kv7 is not None:
                break
            time.sleep(0.1)
        assert kv7 is not None, "tcs_sim 무응답"
        assert kv7["FAFOCUS"] == -6.5 and kv7["SHUTTER"] == "OPEN"
        t = cli7.temperature(status=kv7)
        assert t is not None and 6.0 < t < 7.2, t  # drift 0, 잡음 ±0.05
        # fttgoto → FAFOCUS 갱신 확인
        assert cli7.fttgoto(-6.123).startswith("TC>ABC DONE: FTTGOTO")
        assert cli7.focus() == -6.123
        # dtilt → 틸트 누적 확인
        ns0, ew0 = cli7.tilt()
        cli7.dtilt(0.1, -0.5)
        ns1, ew1 = cli7.tilt()
        assert abs(ns1 - (ns0 + 0.1)) < 1e-9 and abs(ew1 - (ew0 - 0.5)) < 1e-9
        # simset(시뮬레이터 전용) → 셔터 상태 강제
        cli7.command("simset SHUTTER=CLOSE")
        assert cli7.shutter() == "CLOSE"
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    srv.stop()
    shutil.rmtree(tmp, ignore_errors=True)
    print("OK test_tcs")


if __name__ == "__main__":
    main()
