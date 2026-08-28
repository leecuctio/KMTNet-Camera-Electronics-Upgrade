#!/usr/bin/env python3
"""gmon v2 공용 유틸리티 — 설정 로더, 밤 파일명, pidfile, 로깅, stem 규칙.

모든 gmon 컴포넌트는 이 모듈을 통해서만 설정/경로/단일실행을 다룬다 (DESIGN.md §4·§6).
"""
import configparser
import datetime as _dt
import fnmatch
import logging
import os
import shutil
import signal
import sys

GEOM_VERSION = "GMON-GEOM-v1"


class Config:
    """gmon.conf 래퍼. 경로는 conf 파일 위치 기준으로 절대경로화한다."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.basedir = os.path.dirname(self.path)
        cp = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
        with open(self.path, encoding="utf-8") as fp:
            cp.read_file(fp)
        self.cp = cp

    # ---- 기본 getter ----
    def get(self, sec, key, fallback=None):
        return self.cp.get(sec, key, fallback=fallback)

    def getint(self, sec, key, fallback=None):
        return self.cp.getint(sec, key, fallback=fallback)

    def getfloat(self, sec, key, fallback=None):
        return self.cp.getfloat(sec, key, fallback=fallback)

    def getbool(self, sec, key, fallback=False):
        return self.cp.getboolean(sec, key, fallback=fallback)

    def getpair(self, sec, key):
        """"a,b" → (a, b) 정수/실수 자동 판별 튜플."""
        raw = self.cp.get(sec, key)
        parts = [p.strip() for p in raw.split(",")]
        out = []
        for p in parts:
            try:
                out.append(int(p))
            except ValueError:
                out.append(float(p))
        return tuple(out)

    def getlist(self, sec, key):
        return [p.strip() for p in self.cp.get(sec, key).split(",") if p.strip()]

    # ---- 경로 ----
    def _abspath(self, p):
        return p if os.path.isabs(p) else os.path.join(self.basedir, p)

    @property
    def runroot(self):
        return self._abspath(self.get("paths", "runroot", fallback="run"))

    @property
    def configdir(self):
        return self._abspath(self.get("paths", "configdir", fallback="config"))

    def rundir(self, sub):
        return os.path.join(self.runroot, sub)

    def tool(self, name):
        """[paths]의 외부 도구 실행 파일. 상대 이름이면 PATH에서 찾는다."""
        val = self.get("paths", name, fallback=name)
        if os.path.sep in val:
            return self._abspath(val)
        return shutil.which(val) or val


def load_config(path=None):
    """path가 없으면 이 모듈 옆의 gmon.conf."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gmon.conf")
    return Config(path)


def ensure_dirs(cfg):
    for sub in ("incoming", "processed", "work", "snap", "data", "log", "pid"):
        os.makedirs(cfg.rundir(sub), exist_ok=True)


# ---- 밤 파일명 (레거시: date --date='-8 hours' +fw%y%m%d.dat) ----
def night_date(cfg, when=None):
    when = when or _dt.datetime.now()
    off = cfg.getfloat("site", "night_offset_hours", fallback=-8.0)
    return when + _dt.timedelta(hours=off)


def fw_path(cfg, when=None):
    d = night_date(cfg, when)
    return os.path.join(cfg.rundir("data"), d.strftime("fw%y%m%d.dat"))


# ---- stem 규칙 (DESIGN.md §5.1) ----
def stem_from_raw(basename):
    """원시 파일명 → stem. 'modtm.20260527.195724.fits' → '20260527.195724'.

    .fits 제거 후 첫 토큰이 숫자로 시작하지 않으면 첫 토큰을 제거한다.
    결과가 비면 전체 stem을 그대로 쓴다.
    """
    stem = os.path.basename(basename)
    for ext in (".fits", ".fit", ".fts"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    toks = stem.split(".")
    if len(toks) > 1 and toks[0] and not toks[0][0].isdigit():
        rest = ".".join(toks[1:])
        if rest:
            return rest
    return stem


def chip_filename(cfg, chip, stem):
    return "%s%s.%s.fits" % (cfg.get("chips", "prefix", fallback="KMTNg"), chip, stem)


def matches_pattern(cfg, basename):
    return fnmatch.fnmatch(basename, cfg.get("watch", "pattern", fallback="*.fits"))


# ---- pidfile 단일 실행 (DESIGN.md §6: ps|grep 금지) ----
class PidFile:
    """pidfile 형식: 1행=pid, 2행=식별 토큰(컴포넌트 이름).

    토큰은 PID 재사용 방어용 — 기록된 pid가 살아 있어도 그 프로세스의 명령줄에
    토큰이 없으면 무관한 프로세스로 보고 stale 처리한다(재부팅 후 잔존 pidfile이
    acquire를 영구 차단하거나 terminate가 남의 프로세스를 죽이는 것을 방지).
    """

    def __init__(self, cfg, name):
        self.name = name
        self.path = os.path.join(cfg.rundir("pid"), name + ".pid")

    @staticmethod
    def _cmdline(pid):
        import subprocess
        try:
            out = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5,
            ).stdout.decode(errors="replace").strip()
            return out or None
        except Exception:
            return None

    def _unlink(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def other_pid(self):
        """살아있는 같은 컴포넌트 인스턴스의 pid, 없으면 None (stale은 정리)."""
        try:
            with open(self.path) as fp:
                rec = fp.read().splitlines()
            pid = int(rec[0].strip())
        except (OSError, ValueError, IndexError):
            return None
        if pid == os.getpid():
            return None
        alive = True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            alive = False
        except PermissionError:
            pass  # 살아 있으나 권한 밖 — 아래 명령줄 검사로 동일성 판정
        if alive:
            token = rec[1].strip() if len(rec) > 1 else ""
            cmd = self._cmdline(pid)
            if not token or cmd is None or token in cmd:
                return pid  # 판정 불가하면 보수적으로 '실행 중' 취급
        self._unlink()
        return None

    def acquire(self):
        """획득 성공 True. 이미 실행 중이면 False. O_EXCL로 원자적 생성."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        payload = "%d\n%s\n" % (os.getpid(), self.name)
        for _ in range(2):  # stale 정리 후 1회 재시도
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                if self.other_pid() is not None:
                    return False
                continue
            with os.fdopen(fd, "w") as fp:
                fp.write(payload)
            return True
        return False

    def release(self):
        try:
            with open(self.path) as fp:
                if int(fp.read().splitlines()[0].strip()) == os.getpid():
                    self._unlink()
        except (OSError, ValueError, IndexError):
            pass

    def terminate(self, sig=signal.SIGTERM):
        """실행 중인 인스턴스에 시그널. 보냈으면 True."""
        pid = self.other_pid()
        if pid is None:
            return False
        try:
            os.kill(pid, sig)
            return True
        except OSError:
            return False


# ---- 로깅 ----
def setup_logger(cfg, name):
    ensure_dirs(cfg)
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    fh = logging.FileHandler(os.path.join(cfg.rundir("log"), name + ".log"))
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)
    return log


# ---- dfocus 영속 (DESIGN.md §8) ----
def read_dfocus(cfg):
    path = os.path.join(cfg.runroot, "dfocus.txt")
    try:
        with open(path) as fp:
            return float(fp.read().strip())
    except (OSError, ValueError):
        return cfg.getfloat("focus", "dfocus", fallback=0.0)


def write_dfocus(cfg, value):
    path = os.path.join(cfg.runroot, "dfocus.txt")
    os.makedirs(cfg.runroot, exist_ok=True)
    with open(path, "w") as fp:
        fp.write("%.3f" % value)
