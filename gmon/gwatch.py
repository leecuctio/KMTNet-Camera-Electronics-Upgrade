#!/usr/bin/env python3
"""gwatch.py — 수신 디렉토리 감시 데몬 (DESIGN.md §7, 레거시 do-Monitoring 후속).

run/incoming/에서 [watch] pattern 파일을 감시하다가 (size,mtime)이 settle_sec
간격 2회 연속 동일할 때만 처리한다(쓰다 만 파일 방지). 처리 순서:
gsplit.split_file → gpsf.py(서브프로세스, 종료코드 0/2 허용) → gsnap.py
(종료코드 0/2 허용, 2는 부분 성공 경고) → gplot 라이브 확인(pidfile) 후 없으면
기동. 어느 단계가 실패해도 로그만 남기고 다음 파일 처리를 계속한다.

원본 정리: 처리 성공(또는 이미 처리됨 건너뜀) 시 delete_raw=no면
run/processed/로 이동, yes면 삭제하고 run/work/processed.list에 stem을 기록해
재처리를 막는다(스냅샷 PNG 존재 검사와 함께 — DESIGN.md §5.6 파리티).
파이프라인이 실패한 노출의 원본은 delete_raw 설정과 무관하게 삭제하지 않고
run/failed/로 보존 이동하며 processed.list에도 기록하지 않는다 — 장애 해소 후
run/incoming/으로 되돌리면 재처리된다.

사용법:
    gwatch.py [-c gmon.conf] [--once] [--foreground]

  --once        대기 중인 파일들을 1회 처리하고 종료 (시험용)
  --foreground  포그라운드 실행 표시 플래그 (데몬화하지 않으므로 동작은 동일)

pidfile(run/pid/gwatch.pid)로 단일 실행을 보장한다. SIGTERM/SIGINT는 정지
플래그만 세우고, 진행 중인 노출 처리를 끝낸 뒤 루프 경계에서 종료한다
(파이프라인 도중 중단으로 fw/logfile 중복 기록·원본 미정리가 생기지 않도록).

[ics] mode=legacy-udp일 때는 레거시 노출 트리거(guideexp/icg go —
old/do-Monitoring의 노출 루프 참고)를 UDP로 전송한다: 기동 시 1회
"guideexp 10"+"icg go"를 보내고, 이후 감시 루프에서 노출을 처리할 때마다
(또는 RETRIGGER_SEC 동안 파일이 오지 않으면) "icg go"를 재전송해 연속 노출을
유지한다. dry_run=yes면 로그만 남긴다. 기본 mode=file은 순수 파일 감시만 한다.
"""
import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gcommon

GMON_DIR = os.path.dirname(os.path.abspath(__file__))

# legacy-udp: 마지막 트리거 후 이 시간(초) 안에 처리된 노출이 없으면 "icg go" 재전송
# (레거시 do-Monitoring은 exposure 10s + sleep 30s 주기로 반복 전송했다)
RETRIGGER_SEC = 60.0


def _ics_send(cfg, log, msgs):
    """[ics] host:port로 UDP 메시지들 전송. dry_run=yes면 로그만."""
    host = cfg.get("ics", "host", fallback="127.0.0.1")
    port = cfg.getint("ics", "port", fallback=6660)
    if cfg.getbool("ics", "dry_run", fallback=True):
        for m in msgs:
            log.info("ics dry_run: %s -> %s:%d (not sent)", m.decode(), host, port)
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for m in msgs:
            sock.sendto(m, (host, port))
            log.info("ics sent: %s -> %s:%d", m.decode(), host, port)
    finally:
        sock.close()


def ics_trigger(cfg, log):
    """레거시 노출 초기 트리거 — [ics] mode=legacy-udp 기동 시 1회.

    old/do-Monitoring의 "abc>g.ic guideexp 10" / "abc>icg go" UDP 전송을 재현.
    """
    _ics_send(cfg, log, (b"abc>g.ic guideexp 10", b"abc>icg go"))


def ics_go(cfg, log):
    """레거시 노출 재트리거 — 감시 루프에서 노출마다 "icg go"를 재전송한다.

    (old/do-Monitoring은 셔터 폴링 루프에서 매 노출 "icg go"를 반복 전송했다.)
    """
    _ics_send(cfg, log, (b"abc>icg go",))


class Watcher:
    def __init__(self, cfg, log):
        self.cfg = cfg
        self.log = log
        self.poll_sec = cfg.getfloat("watch", "poll_sec", fallback=2.0)
        self.settle_sec = cfg.getfloat("watch", "settle_sec", fallback=2.0)
        self._seen = {}  # path -> (size, mtime, 최초 관측 시각)
        self._stop = False
        self._last_trigger = 0.0  # legacy-udp 마지막 트리거 시각
        py = cfg.tool("python")
        self.python = py if (py and os.path.exists(py)) else sys.executable

    # ---- 감시 ----
    def scan(self):
        """incoming을 훑고, settle_sec 이상 (size,mtime) 불변인 파일 목록 반환."""
        incoming = self.cfg.rundir("incoming")
        now = time.time()
        ready = []
        try:
            names = sorted(os.listdir(incoming))
        except OSError:
            return ready
        current = set()
        for name in names:
            if not gcommon.matches_pattern(self.cfg, name):
                continue
            path = os.path.join(incoming, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            current.add(path)
            prev = self._seen.get(path)
            if prev is not None and prev[0] == st.st_size and prev[1] == st.st_mtime:
                if now - prev[2] >= self.settle_sec:
                    ready.append(path)
            else:
                self._seen[path] = (st.st_size, st.st_mtime, now)
        for path in list(self._seen):
            if path not in current:
                del self._seen[path]
        return ready

    # ---- 중복 방지 (DESIGN.md §5.6) ----
    def _processed_list_path(self):
        return os.path.join(self.cfg.rundir("work"), "processed.list")

    def processed_stems(self):
        try:
            with open(self._processed_list_path()) as fp:
                return set(ln.strip() for ln in fp if ln.strip())
        except OSError:
            return set()

    def mark_processed(self, stem):
        if stem in self.processed_stems():
            return
        os.makedirs(self.cfg.rundir("work"), exist_ok=True)
        with open(self._processed_list_path(), "a") as fp:
            fp.write(stem + "\n")

    def already_done(self, stem):
        snap = os.path.join(self.cfg.rundir("snap"), "psf.snap.%s.png" % stem)
        return os.path.exists(snap) or stem in self.processed_stems()

    # ---- 처리 ----
    def _run(self, cmd):
        try:
            return subprocess.call(cmd, cwd=GMON_DIR)
        except OSError as exc:
            self.log.error("exec failed %s: %s", cmd[:2], exc)
            return -1

    def ensure_gplot(self):
        """gplot 라이브 인스턴스가 없으면 기동 (pidfile 검사, killall 금지).

        gmon GUI 패널이 떠 있으면(run/pid/gmon.pid) 그래프는 패널에 내장
        표시되므로 외부 gnuplot 라이브 창을 띄우지 않는다.
        """
        if gcommon.PidFile(self.cfg, "gmon").other_pid() is not None:
            return
        if gcommon.PidFile(self.cfg, "gplot").other_pid() is not None:
            return
        script = os.path.join(GMON_DIR, "gplot.py")
        if not os.path.exists(script):
            self.log.warning("gplot.py not found; launch skipped")
            return
        try:
            subprocess.Popen(
                [self.python, script, "-c", self.cfg.path],
                cwd=GMON_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.log.info("gplot launched")
        except OSError as exc:
            self.log.error("gplot launch failed: %s", exc)

    def _move_unique(self, raw, sub):
        """raw를 run/<sub>/로 이동 (이름 충돌 시 .N 접미). 목적지 경로 반환."""
        dest_dir = self.cfg.rundir(sub)
        os.makedirs(dest_dir, exist_ok=True)
        base = os.path.basename(raw)
        dest = os.path.join(dest_dir, base)
        n = 1
        while os.path.exists(dest):
            dest = os.path.join(dest_dir, "%s.%d" % (base, n))
            n += 1
        shutil.move(raw, dest)
        return dest

    def finish_raw(self, raw, stem):
        """처리 성공(또는 건너뜀)한 원본 정리: 이동/삭제 + processed.list 기록."""
        try:
            if self.cfg.getbool("watch", "delete_raw", fallback=False):
                os.unlink(raw)
                self.log.info("raw deleted: %s", os.path.basename(raw))
            else:
                dest = self._move_unique(raw, "processed")
                self.log.info("raw moved: %s", dest)
        except OSError as exc:
            self.log.error("raw cleanup failed %s: %s", raw, exc)
        try:
            self.mark_processed(stem)
        except OSError as exc:
            self.log.error("processed.list append failed: %s", exc)
        self._seen.pop(raw, None)

    def quarantine_raw(self, raw, stem):
        """파이프라인이 실패한 원본 보존: run/failed/로 이동.

        delete_raw=yes여도 삭제하지 않고(유일한 원본 소실 방지), stem을
        processed.list에 기록하지 않는다 — 장애 해소 후 run/incoming/으로
        되돌리면 재처리된다. (DESIGN §4 delete_raw는 '처리 후 원본' 정리 규정.)
        """
        try:
            dest = self._move_unique(raw, "failed")
            self.log.error("raw quarantined (pipeline failed): %s (stem=%s)",
                           dest, stem)
        except OSError as exc:
            self.log.error("raw quarantine failed %s: %s", raw, exc)
        self._seen.pop(raw, None)

    def handle(self, raw):
        base = os.path.basename(raw)
        stem = gcommon.stem_from_raw(base)
        if self.already_done(stem):
            self.log.info("skip %s (already processed: %s)", base, stem)
            self.finish_raw(raw, stem)
            return
        self.log.info("processing %s (stem=%s)", base, stem)
        ok = True
        # (1) 분할 — 라이브러리 호출
        try:
            import gsplit
            gsplit.split_file(raw, self.cfg)
        except Exception:
            self.log.exception("gsplit failed: %s", base)
            ok = False
        # (2) sex+psfex — 종료코드 0(성공)/2(부분 실패) 허용
        if ok:
            script = os.path.join(GMON_DIR, "gpsf.py")
            if not os.path.exists(script):
                self.log.error("gpsf.py not found")
                ok = False
            else:
                rc = self._run([self.python, script, stem, "-c", self.cfg.path])
                if rc == 2:
                    self.log.warning("gpsf partial (rc=2): %s", stem)
                elif rc != 0:
                    self.log.error("gpsf rc=%s: %s", rc, stem)
                    ok = False
        # (3) 스냅샷 PNG — 종료코드 0(성공)/2(부분: 일부 타일 스냅 누락) 허용
        if ok:
            script = os.path.join(GMON_DIR, "gsnap.py")
            rjson = os.path.join(self.cfg.rundir("work"), "result.%s.json" % stem)
            if not os.path.exists(script):
                self.log.error("gsnap.py not found")
                ok = False
            else:
                rc = self._run([self.python, script, rjson, "-c", self.cfg.path])
                if rc == 2:
                    self.log.warning("gsnap partial (rc=2): %s", stem)
                elif rc != 0:
                    self.log.error("gsnap rc=%s: %s", rc, stem)
                    ok = False
        # (4) gplot 기동 확인
        self.ensure_gplot()
        # (5) 원본 정리: 성공 시 processed/(또는 삭제)+기록, 실패 시 failed/ 보존
        if ok:
            self.finish_raw(raw, stem)
        else:
            self.quarantine_raw(raw, stem)
        self.log.info("%s: %s", "done" if ok else "FAILED (see log)", base)

    # ---- 루프 ----
    def stop(self):
        """SIGTERM/SIGINT 핸들러용: 정지 플래그만 세운다 (루프 경계에서 종료)."""
        self._stop = True

    def run(self, once=False):
        legacy = (self.cfg.get("ics", "mode", fallback="file")
                  .strip().lower() == "legacy-udp")
        if legacy:
            ics_trigger(self.cfg, self.log)
            self._last_trigger = time.time()
        if once:
            self.scan()  # 1차 관측 기록
            time.sleep(self.settle_sec)
            for path in self.scan():
                if self._stop:
                    break
                self.handle(path)
            return 0
        self.log.info("watch loop start (poll=%.1fs settle=%.1fs)",
                      self.poll_sec, self.settle_sec)
        while not self._stop:
            handled = 0
            for path in self.scan():
                if self._stop:
                    break
                self.handle(path)
                handled += 1
            if legacy and not self._stop:
                # 레거시 do-Monitoring 파리티: 노출마다 "icg go"를 재전송해
                # 연속 노출을 유지 (파일이 오지 않으면 RETRIGGER_SEC마다 재시도)
                now = time.time()
                if handled or (now - self._last_trigger) >= RETRIGGER_SEC:
                    ics_go(self.cfg, self.log)
                    self._last_trigger = now
            time.sleep(self.poll_sec)
        self.log.info("watch loop stop requested — exiting")
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="gmon v2 수신 감시 데몬")
    ap.add_argument("-c", "--config", default=None, help="gmon.conf 경로")
    ap.add_argument("--once", action="store_true", help="1회 처리 후 종료")
    ap.add_argument("--foreground", action="store_true",
                    help="포그라운드 실행 (데몬화하지 않으므로 동작 동일)")
    args = ap.parse_args(argv)

    cfg = gcommon.load_config(args.config)
    gcommon.ensure_dirs(cfg)
    log = gcommon.setup_logger(cfg, "gwatch")

    pidfile = gcommon.PidFile(cfg, "gwatch")
    if not pidfile.acquire():
        log.error("gwatch already running (pid %s)", pidfile.other_pid())
        return 1

    watcher = Watcher(cfg, log)

    # 플래그만 세우고 루프 경계에서 종료한다 — 파이프라인 도중 중단으로
    # fw/logfile 중복 append·원본 미정리 반쪽 상태가 생기지 않도록.
    def _on_signal(signum, frame):
        watcher.stop()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    try:
        return watcher.run(once=args.once)
    finally:
        pidfile.release()


if __name__ == "__main__":
    sys.exit(main())
