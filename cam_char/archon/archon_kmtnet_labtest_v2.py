#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archon_kmtnet_labtest_v2.py -- KMTNet-CEU lab acquisition script for the
STA Archon controller (rewrite of archon_kmtnet_labtest_v1.0.*.py).

Improvements over v1.0, borrowed from field-proven Archon software
(see ARCHON_LABTEST_V2.md for the full mapping and references):

  from sdss/archon:
    - '?xx' error replies are distinguished from protocol errors
    - POLLOFF/POLLON around bulk WCONFIG upload and RCONFIG verify
    - HOLDTIMING / FASTPREPPARAM / RELEASETIMING deterministic exposure start
    - LOCKn before FETCH, LOCK0 after
    - readout timeout, POWERON gated on POWER=ON + POWERGOOD=1
  from mplesser/azcam:
    - measured exposure time from controller trigger timestamps (10 ns ticks)
    - readout progress from WBUF BUFnPIXELS/BUFnLINES
    - ACF read-back verification (RCONFIG diff after WCONFIG)
    - IntMS 20-bit range validation with a clear error
  from karpov-sv/ccdlab:
    - protocol simulator (archon_simulator.py) + unittest coverage
  v1.0 fixes:
    - FITS geometry taken from the frame status (no hard-coded NAXIS)
    - FITS data padded to 2880-byte blocks
    - campaign configuration in an INI file instead of source edits
    - POWEROFF guaranteed on abort (finally / KeyboardInterrupt)

Runtime dependencies: Python 3.8+ stdlib + NumPy only.

Usage:
    python3 archon_kmtnet_labtest_v2.py campaign.ini [--dry-run] [--run NAME]

See campaign_example.ini for the campaign file format.
"""

from __future__ import annotations

import argparse
import configparser
import json
import logging
import os
import socket
import sys
import time
import urllib.request
from dataclasses import dataclass

import numpy as np

__version__ = '2.0.0'

# ------------------------------------------------------------------------
# Protocol constants

ARCHON_PORT = 4242
BURST_LEN = 1024              # binary payload bytes per FETCH block
BIN_HEADER_LEN = 4            # '<XX:'
INTMS_MAX = 0x000FFFFE        # 1,048,574 ms -- 20-bit IntMS limit (v1.0 note)
TICKS_PER_SEC = 1.0e8         # controller timestamps count 10 ns ticks
FITS_BLOCK = 2880

# STATUS 'POWER' field values (sdss/archon ArchonPower enum)
POWER_UNKNOWN = 0
POWER_NOT_CONFIGURED = 1
POWER_OFF = 2
POWER_INTERMEDIATE = 3
POWER_ON = 4
POWER_STANDBY = 5


# ------------------------------------------------------------------------
# Exceptions

class ArchonError(Exception):
    """Base class for all controller-related failures."""


class ArchonProtocolError(ArchonError):
    """Reply framing/reference mismatch or unexpected disconnect."""


class ArchonCommandError(ArchonError):
    """The controller answered '?xx' -- the command itself was rejected."""

    def __init__(self, cmd, raw):
        super().__init__("controller rejected command %r (reply %r)" % (cmd, raw))
        self.cmd = cmd
        self.raw = raw


class ArchonTimeoutError(ArchonError):
    """A reply or a frame did not arrive within the allotted time."""


# ------------------------------------------------------------------------
# Frame status

@dataclass
class FrameInfo:
    frame: int
    buf: int                  # 0-based buffer index
    width: int
    height: int
    sample: int               # 0: 16-bit, else 32-bit
    base: int                 # FETCH base address (BUFnBASE)
    complete: bool
    pixels: int = 0
    lines: int = 0
    timestamp: int = 0        # BUFnTIMESTAMP (10 ns ticks, hex on the wire)
    ts_rising: int = 0        # BUFnRETIMESTAMP -- trigger rising edge
    ts_falling: int = 0       # BUFnFETIMESTAMP -- trigger falling edge

    @property
    def bytes_per_pixel(self):
        return 4 if self.sample else 2

    @property
    def framesize(self):
        return self.bytes_per_pixel * self.width * self.height


# ------------------------------------------------------------------------
# Low-level client: framing, references, batching, binary fetch

class ArchonClient:
    """Synchronous socket client for the Archon text/binary protocol.

    Replies are matched against the 8-bit rolling reference of the request;
    '?xx' replies raise ArchonCommandError with the offending command text
    (sdss/archon pattern) instead of a generic header mismatch.
    """

    def __init__(self, host, port=ARCHON_PORT, connect_timeout=2.0,
                 command_timeout=5.0, log=None):
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout
        self.log = log or logging.getLogger('archon')
        self.sock = None
        self._ref = 0
        self._rxbuf = b''

    # --- connection -------------------------------------------------------

    def connect(self, retries=4, backoff=2.0):
        delay = backoff
        for attempt in range(retries + 1):
            try:
                sock = socket.create_connection(
                    (self.host, self.port), timeout=self.connect_timeout)
                sock.settimeout(self.connect_timeout)
                self.sock = sock
                self._rxbuf = b''
                self.log.info('connected to Archon at %s:%d', self.host, self.port)
                return
            except OSError as exc:
                self.log.warning('connect attempt %d/%d to %s:%d failed: %s',
                                 attempt + 1, retries + 1, self.host, self.port, exc)
                if attempt == retries:
                    raise
                time.sleep(delay)
                delay *= 2

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def reconnect(self):
        self.close()
        self.connect()

    # --- receive helpers ----------------------------------------------------

    def _recv_more(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ArchonTimeoutError('timed out waiting for controller reply')
        self.sock.settimeout(min(remaining, 1.0))
        try:
            chunk = self.sock.recv(65536)
        except socket.timeout:
            return
        if not chunk:
            raise ArchonProtocolError('connection closed by controller')
        self._rxbuf += chunk

    def _read_line(self, timeout):
        deadline = time.monotonic() + timeout
        while b'\n' not in self._rxbuf:
            self._recv_more(deadline)
        line, self._rxbuf = self._rxbuf.split(b'\n', 1)
        return line.rstrip(b'\r')

    def _read_exact(self, nbytes, timeout):
        deadline = time.monotonic() + timeout
        while len(self._rxbuf) < nbytes:
            self._recv_more(deadline)
        out, self._rxbuf = self._rxbuf[:nbytes], self._rxbuf[nbytes:]
        return out

    # --- command primitives ---------------------------------------------------

    def _next_ref(self):
        ref = self._ref
        self._ref = (self._ref + 1) % 256
        return ref

    @staticmethod
    def _check_reply(cmd, ref, line):
        head = line[:3].decode('ascii', 'replace')
        if head == '<%02X' % ref:
            return line[3:].decode('ascii', 'replace')
        if head == '?%02X' % ref:
            raise ArchonCommandError(cmd, line.decode('ascii', 'replace'))
        raise ArchonProtocolError(
            'reply/reference mismatch for %r: expected <%02X, got %r'
            % (cmd, ref, bytes(line[:16])))

    def command(self, cmd, timeout=None):
        """Send one command and return its reply payload."""
        timeout = timeout if timeout is not None else self.command_timeout
        ref = self._next_ref()
        self.sock.sendall(('>%02X%s\n' % (ref, cmd)).encode('ascii'))
        return self._check_reply(cmd, ref, self._read_line(timeout))

    def batch(self, cmds, chunk=100, timeout=None):
        """Pipelined send of many commands, replies read per chunk.

        sdss/archon send_many() pattern: keeps bulk WCONFIG/RCONFIG fast
        while every reply is still matched to its command.
        """
        timeout = timeout if timeout is not None else self.command_timeout
        replies = []
        for base in range(0, len(cmds), chunk):
            group = cmds[base:base + chunk]
            refs = []
            wire = []
            for cmd in group:
                ref = self._next_ref()
                refs.append(ref)
                wire.append('>%02X%s\n' % (ref, cmd))
            self.sock.sendall(''.join(wire).encode('ascii'))
            for cmd, ref in zip(group, refs):
                replies.append(self._check_reply(cmd, ref, self._read_line(timeout)))
        return replies

    def fetch(self, base_addr, nbytes, timeout=120.0):
        """FETCH nbytes from base_addr; returns a bytearray of exactly nbytes.

        All binary blocks of one FETCH carry the reference of the FETCH
        command itself ('<XX:' + 1024 bytes, no newline).
        """
        blocks = (nbytes + BURST_LEN - 1) // BURST_LEN
        ref = self._next_ref()
        self.sock.sendall(('>%02XFETCH%08X%08X\n' % (ref, base_addr, blocks))
                          .encode('ascii'))
        expected = ('<%02X:' % ref).encode('ascii')
        out = bytearray()
        for i in range(blocks):
            block = self._read_exact(BIN_HEADER_LEN + BURST_LEN, timeout)
            if block[:BIN_HEADER_LEN] != expected:
                raise ArchonProtocolError(
                    'bad binary header in block %d/%d: %r'
                    % (i + 1, blocks, bytes(block[:8])))
            out += block[BIN_HEADER_LEN:]
        return out[:nbytes]

    # --- status parsing ------------------------------------------------------

    @staticmethod
    def _parse_kv(payload):
        pairs = {}
        for token in payload.split():
            if '=' in token:
                key, value = token.split('=', 1)
                pairs[key] = value
        return pairs

    def get_status(self):
        return self._parse_kv(self.command('STATUS'))

    def get_frame(self):
        return self._parse_kv(self.command('FRAME'))

    def newest(self, framestatus=None):
        """Newest *complete* frame across the three buffers, or None.

        Timestamp fields are hex on the wire; everything else is decimal.
        """
        fs = framestatus if framestatus is not None else self.get_frame()

        def geti(key, default=0):
            return int(fs.get(key, default))

        def geth(key):
            return int(fs.get(key, '0'), 16)

        best = None
        for i in (1, 2, 3):
            info = FrameInfo(
                frame=geti('BUF%dFRAME' % i, -1),
                buf=i - 1,
                width=geti('BUF%dWIDTH' % i),
                height=geti('BUF%dHEIGHT' % i),
                sample=geti('BUF%dSAMPLE' % i),
                base=geti('BUF%dBASE' % i),
                complete=geti('BUF%dCOMPLETE' % i) == 1,
                pixels=geti('BUF%dPIXELS' % i),
                lines=geti('BUF%dLINES' % i),
                timestamp=geth('BUF%dTIMESTAMP' % i),
                ts_rising=geth('BUF%dRETIMESTAMP' % i),
                ts_falling=geth('BUF%dFETIMESTAMP' % i),
            )
            if info.complete and (best is None or info.frame > best.frame):
                best = info
        return best


# ------------------------------------------------------------------------
# ACF handling

def load_acf(path):
    """Parse an ACF into an ordered list of 'KEY=VALUE' config lines.

    Same normalization as v1.0: keys upper-cased with '\\' -> '/',
    double quotes stripped from values.
    """
    parser = configparser.RawConfigParser(strict=False)
    if not parser.read(path):
        raise FileNotFoundError('ACF not found or unreadable: %s' % path)
    lines = []
    for key, value in parser.items('CONFIG'):
        lines.append('%s=%s' % (key.upper().replace('\\', '/'),
                                value.replace('"', '')))
    return lines


# ------------------------------------------------------------------------
# Mid-level controller wrapper

@dataclass
class LabOptions:
    verify_acf: bool = True         # RCONFIG read-back diff after upload
    acf_retries: int = 4            # re-upload attempts (with reconnect)
    use_fast_params: bool = True    # HOLDTIMING/FASTPREPPARAM/RELEASETIMING;
                                    # False falls back to v1-style LOADPARAMS
    poll_interval: float = 0.5      # FRAME polling period [s]
    readout_timeout: float = 240.0  # max wait beyond IntMS for a frame [s]
    power_timeout: float = 20.0     # max wait for POWERGOOD after POWERON [s]
    progress: bool = True           # single-line progress on stdout


class LabArchon:
    """Exposure/dataset-level operations on top of ArchonClient."""

    def __init__(self, client, log=None, opts=None):
        self.client = client
        self.log = log or logging.getLogger('labtest')
        self.opts = opts or LabOptions()
        self.acf_path = None
        self.config_lines = []
        self.config_index = {}

    # --- configuration ------------------------------------------------------

    def apply_acf(self, path):
        """Upload an ACF (CLEARCONFIG + WCONFIG), verify it, APPLYALL.

        POLLOFF is issued around the bulk transfer (sdss/archon) and the
        whole upload is retried with a reconnect on failure (v1.0 behavior,
        but with the actual controller error in the log).
        """
        lines = load_acf(path)
        for attempt in range(self.opts.acf_retries + 1):
            try:
                self._upload_config(lines)
                self.client.command('APPLYALL', timeout=30.0)
                break
            except ArchonError as exc:
                self.log.warning('ACF apply attempt %d/%d failed: %s',
                                 attempt + 1, self.opts.acf_retries + 1, exc)
                if attempt == self.opts.acf_retries:
                    raise
                time.sleep(1.0)
                self.client.reconnect()
        self.acf_path = path
        self.config_lines = list(lines)
        self.config_index = {l.split('=', 1)[0]: i for i, l in enumerate(lines)}
        self.log.info('ACF applied: %s (%d lines%s)', path, len(lines),
                      ', verified' if self.opts.verify_acf else '')

    def _upload_config(self, lines):
        self.client.command('CLEARCONFIG')
        self.client.command('POLLOFF')
        try:
            self.client.batch(['WCONFIG%04X%s' % (i, line)
                               for i, line in enumerate(lines)])
            if self.opts.verify_acf:
                self._verify_config(lines)
        finally:
            self.client.command('POLLON')

    def _verify_config(self, lines):
        """Read every line back with RCONFIG and diff (azcam mode-0 idea)."""
        replies = self.client.batch(['RCONFIG%04X' % i for i in range(len(lines))])
        bad = [i for i, (want, got) in enumerate(zip(lines, replies))
               if want != got.strip()]
        if bad:
            i = bad[0]
            raise ArchonProtocolError(
                'ACF verify failed on %d line(s); first mismatch at %04X: '
                'wrote %r, read back %r' % (len(bad), i, lines[i], replies[i]))

    def set_key(self, key, value, apply_cmd=None):
        """Rewrite a single config line by key; optionally APPLY*."""
        if key not in self.config_index:
            raise KeyError('config key %r not present in the loaded ACF' % key)
        lineno = self.config_index[key]
        self.config_lines[lineno] = '%s=%s' % (key, value)
        self.client.command('WCONFIG%04X%s=%s' % (lineno, key, value))
        if apply_cmd:
            self.client.command(apply_cmd)

    def _set_param_line(self, name, value):
        """v1-compatible parameter write: rewrite the PARAMETERn line whose
        value starts with '<name>='."""
        for key, lineno in self.config_index.items():
            current = self.config_lines[lineno].split('=', 1)[1]
            if key.startswith('PARAMETER') and current.startswith(name + '='):
                self.set_key(key, '%s=%d' % (name, value))
                return
        raise KeyError('no PARAMETERn line found for %r in the loaded ACF' % name)

    # --- power ------------------------------------------------------------

    def power_on(self):
        """POWERON gated on POWER=ON and POWERGOOD=1 (sdss/azcam pattern)."""
        self.client.command('POWERON', timeout=10.0)
        deadline = time.monotonic() + self.opts.power_timeout
        while time.monotonic() < deadline:
            st = self.client.get_status()
            if (int(st.get('POWER', -1)) == POWER_ON
                    and int(st.get('POWERGOOD', 0)) == 1):
                self.log.info('CCD power ON (POWERGOOD=1, backplane %s C)',
                              st.get('BACKPLANE_TEMP', '?'))
                return st
            time.sleep(0.5)
        raise ArchonTimeoutError(
            'POWERON did not reach POWER=ON/POWERGOOD=1 within %.0f s'
            % self.opts.power_timeout)

    def power_off(self):
        try:
            self.client.command('POWEROFF', timeout=10.0)
            self.log.info('CCD power OFF')
        except ArchonError as exc:
            self.log.error('POWEROFF failed: %s', exc)

    # --- exposure ------------------------------------------------------------

    def expose(self, exptime_ms, shutter_open):
        """One exposure; returns (raw uint16 ndarray [h*w], meta dict).

        Start sequence (sdss/archon): HOLDTIMING -> FASTPREPPARAM IntMS /
        Exposures -> RELEASETIMING, so the integration begins at a defined
        instant instead of 'sometime after LOADPARAMS' (the cause of the
        hand-tuned SWSET_EXPWAIT values in v1.0).
        """
        if not 0 <= exptime_ms <= INTMS_MAX:
            raise ValueError(
                'IntMS=%d outside 0..%d (20-bit limit); longer darks need '
                'azcam-style NoIntMS splitting, not implemented yet'
                % (exptime_ms, INTMS_MAX))

        self.set_key('TRIGOUTFORCE', '0' if shutter_open else '1',
                     apply_cmd='APPLYSYSTEM')

        last = self.client.newest()
        last_frame = last.frame if last else -1

        if self.opts.use_fast_params:
            self.client.command('HOLDTIMING')
            self.client.command('FASTPREPPARAM IntMS %d' % exptime_ms)
            self.client.command('FASTPREPPARAM Exposures 1')
            date_obs = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())
            date_loc = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
            started = time.monotonic()
            self.client.command('RELEASETIMING')
        else:
            self._set_param_line('IntMS', exptime_ms)
            self._set_param_line('Exposures', 1)
            date_obs = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())
            date_loc = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
            started = time.monotonic()
            self.client.command('LOADPARAMS')

        info = self._wait_frame(last_frame, exptime_ms, started)

        if info.sample:
            raise ArchonError(
                '32-bit sample mode frames are not supported by the FITS '
                'writer (BUF%dSAMPLE=1)' % (info.buf + 1))

        raw = self._fetch_locked(info)

        exp_measured = None
        if info.ts_falling > info.ts_rising > 0:
            exp_measured = (info.ts_falling - info.ts_rising) / TICKS_PER_SEC

        meta = {
            'frame': info.frame,
            'buf': info.buf,
            'width': info.width,
            'height': info.height,
            'exptime_ms': exptime_ms,
            'exp_measured_s': exp_measured,
            'shutter_open': shutter_open,
            'date_obs': date_obs,
            'date_loc': date_loc,
            'elapsed_s': time.monotonic() - started,
        }
        self.log.info(
            'frame %d done: %dx%d, IntMS=%d, measured=%s, elapsed=%.1fs',
            info.frame, info.width, info.height, exptime_ms,
            ('%.3fs' % exp_measured) if exp_measured is not None else 'n/a',
            meta['elapsed_s'])
        pixels = np.frombuffer(bytes(raw), dtype='<u2')
        return pixels, meta

    def _wait_frame(self, last_frame, exptime_ms, started):
        """Poll FRAME until a new complete frame appears.

        Progress (azcam idea): the write buffer's BUFnLINES against its
        height gives real readout progress instead of a wall-clock dot bar.
        """
        timeout = exptime_ms / 1000.0 + self.opts.readout_timeout
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            fs = self.client.get_frame()
            info = self.client.newest(fs)
            if info is not None and info.frame != last_frame:
                self._progress_end()
                return info
            self._progress_update(fs, exptime_ms, started)
            time.sleep(self.opts.poll_interval)
        self._progress_end()
        raise ArchonTimeoutError(
            'no new frame within %.0f s (IntMS=%d + readout_timeout=%.0f); '
            'last FRAME: %s'
            % (timeout, exptime_ms, self.opts.readout_timeout,
               self.client.command('FRAME')))

    def _progress_update(self, framestatus, exptime_ms, started):
        if not (self.opts.progress and sys.stdout.isatty()):
            return
        elapsed = time.monotonic() - started
        line = '  elapsed %6.1fs / integration %6.1fs' % (elapsed,
                                                          exptime_ms / 1000.0)
        wbuf = framestatus.get('WBUF', '0')
        if wbuf in ('1', '2', '3'):
            lines_read = int(framestatus.get('BUF%sLINES' % wbuf, 0))
            height = int(framestatus.get('BUF%sHEIGHT' % wbuf, 0))
            if height > 0 and lines_read > 0:
                line += '  readout %5.1f%%' % (100.0 * lines_read / height)
        sys.stdout.write('\r' + line)
        sys.stdout.flush()

    def _progress_end(self):
        if self.opts.progress and sys.stdout.isatty():
            sys.stdout.write('\r' + ' ' * 60 + '\r')
            sys.stdout.flush()

    def _fetch_locked(self, info):
        """LOCK the buffer during FETCH, always unlock (sdss/azcam order)."""
        self.client.command('LOCK%d' % (info.buf + 1))
        try:
            return self.client.fetch(info.base, info.framesize)
        finally:
            self.client.command('LOCK0')


# ------------------------------------------------------------------------
# FITS output (stdlib-only writer, standard-conformant padding)

def _fits_format_value(value):
    if isinstance(value, bool):
        return '%20s' % ('T' if value else 'F')
    if isinstance(value, int):
        return '%20d' % value
    if isinstance(value, float):
        return '%20.6f' % value
    text = str(value).replace("'", "''")
    return "'%-8s'" % text if len(text) <= 8 else "'%s'" % text


def fits_card(key, value=None, comment=''):
    if key == 'END':
        return 'END'.ljust(80)
    body = '%-8s= %s' % (key[:8].upper(), _fits_format_value(value))
    if comment:
        body += ' / %s' % comment
    return body[:80].ljust(80)


def write_fits(path, pixels, width, height, cards):
    """Write a single-HDU 16-bit FITS with BZERO=32768 unsigned convention.

    NAXIS1/2 come from the frame status (v1.0 hard-coded 19200x9400), and
    both header and data units are padded to 2880-byte blocks (v1.0 left
    the data unit unpadded).
    """
    if pixels.size != width * height:
        raise ValueError('pixel count %d != %dx%d' % (pixels.size, width, height))

    header_cards = [
        fits_card('SIMPLE', True, 'Conforms to FITS standard'),
        fits_card('BITPIX', 16, 'Signed 16-bit with BZERO offset'),
        fits_card('NAXIS', 2, 'Number of axes'),
        fits_card('NAXIS1', width, 'Image width from frame status'),
        fits_card('NAXIS2', height, 'Image height from frame status'),
        fits_card('BZERO', 32768, 'Offset for unsigned 16-bit'),
        fits_card('BSCALE', 1, 'Default scaling factor'),
    ]
    header_cards += [fits_card(k, v, c) for (k, v, c) in cards]
    header_cards.append(fits_card('END'))
    ncards = len(header_cards)
    if ncards % 36:
        header_cards += [' ' * 80] * (36 - ncards % 36)
    header = ''.join(header_cards).encode('ascii')

    data = pixels.astype('<u2', copy=True)
    data += 0x8000                       # unsigned -> signed bit pattern
    payload = data.byteswap().tobytes()  # FITS is big-endian
    if len(payload) % FITS_BLOCK:
        payload += b'\x00' * (FITS_BLOCK - len(payload) % FITS_BLOCK)

    with open(path, 'wb') as handle:
        handle.write(header)
        handle.write(payload)


# ------------------------------------------------------------------------
# Dataset definitions (values identical to v1.0)

@dataclass(frozen=True)
class DatasetSpec:
    name: str
    shutter_open: bool
    frames_per_step: int
    exptimes: tuple
    ref_enable: bool = False
    ref_exptime: int = 0
    dark_enable: bool = False
    dark_exptime: int = 0


@dataclass(frozen=True)
class FrameJob:
    kind: str            # 'obj' | 'ref' | 'dark'
    exptime_ms: int
    shutter_open: bool

    @property
    def imagetyp(self):
        if self.kind == 'ref':
            return 'REF'
        if self.kind == 'dark' or not self.shutter_open:
            return 'BIAS' if self.exptime_ms == 0 else 'DARK'
        return 'BIAS' if self.exptime_ms == 0 else 'FLAT'


XTALK = DatasetSpec('xTalk', True, 3, (0, 1000, 4000, 0, 16000, 32000, 0))

DARK = DatasetSpec('Dark', False, 3,
                   (0,)
                   + (2395, 12123, 61371, 310689, 0)
                   + (3592, 18184, 92056, 466033, 0)
                   + (5388, 27276, 138084, 699049, 0)
                   + (8082, 40914, 207126, 1048574, 0))

IFLAT = DatasetSpec('iFlat', True, 3,
                    (0,)
                    + tuple(range(1000, 13001, 1000)) + (0,)
                    + tuple(range(14000, 25001, 1000)) + (0,),
                    ref_enable=True, ref_exptime=12000,
                    dark_enable=True, dark_exptime=25000)

GXT = DatasetSpec('GxT', False, 15, (0,))

# dataset type = DatasetId % 10 (same file-numbering convention as v1.0;
# type digits 3 and 4 are both iFlat per the v1.0 numbering notes)
DATASET_SPECS = {1: XTALK, 2: DARK, 3: IFLAT, 4: IFLAT, 5: GXT}


def build_plan(spec):
    """Frame sequence for a dataset -- same ordering as v1.0 GetDataset()."""
    plan = []
    if spec.ref_enable:
        plan.append(FrameJob('ref', spec.ref_exptime, spec.shutter_open))
    for exptime in spec.exptimes:
        for _ in range(spec.frames_per_step):
            plan.append(FrameJob('obj', exptime, spec.shutter_open))
        if spec.dark_enable and exptime == 0:
            plan.append(FrameJob('dark', spec.dark_exptime, False))
        if spec.ref_enable:
            plan.append(FrameJob('ref', spec.ref_exptime, spec.shutter_open))
    return plan


# ------------------------------------------------------------------------
# Notification (generic webhook; replaces the dead Twilio stub of v1.0)

class Notifier:
    def __init__(self, webhook_url=None, log=None):
        self.url = webhook_url or None
        self.log = log or logging.getLogger('notify')

    def send(self, message):
        self.log.info('NOTIFY: %s', message)
        if not self.url:
            return
        try:
            body = json.dumps({'text': message}).encode('utf-8')
            req = urllib.request.Request(
                self.url, data=body,
                headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=5.0).read()
        except Exception as exc:  # notification must never kill a run
            self.log.warning('webhook notification failed: %s', exc)


# ------------------------------------------------------------------------
# Campaign configuration and runner

@dataclass
class RunConfig:
    name: str
    acf_path: str
    dataset_id: int
    storage: str
    start_num: int = 0


@dataclass
class Campaign:
    prefix: str
    unit_id: int
    host: str
    runs: list
    opts: LabOptions
    webhook: str = ''


def load_campaign(path):
    parser = configparser.ConfigParser()
    if not parser.read(path):
        raise FileNotFoundError('campaign file not found: %s' % path)

    unit = parser['unit']
    storages = dict(parser.items('storage')) if parser.has_section('storage') else {}
    acfs = dict(parser.items('acf')) if parser.has_section('acf') else {}

    opts = LabOptions()
    if parser.has_section('options'):
        sec = parser['options']
        opts.verify_acf = sec.getboolean('verify_acf', opts.verify_acf)
        opts.acf_retries = sec.getint('acf_retries', opts.acf_retries)
        opts.use_fast_params = sec.getboolean('use_fast_params', opts.use_fast_params)
        opts.poll_interval = sec.getfloat('poll_interval', opts.poll_interval)
        opts.readout_timeout = sec.getfloat('readout_timeout', opts.readout_timeout)
        opts.power_timeout = sec.getfloat('power_timeout', opts.power_timeout)
        opts.progress = sec.getboolean('progress', opts.progress)

    webhook = ''
    if parser.has_section('notify'):
        webhook = parser['notify'].get('webhook', '').strip()

    runs = []
    for section in parser.sections():
        if not section.startswith('run:'):
            continue
        sec = parser[section]
        acf_key = sec['acf']
        storage_key = sec.get('storage', 'default')
        runs.append(RunConfig(
            name=section.split(':', 1)[1],
            acf_path=acfs.get(acf_key, acf_key),
            dataset_id=sec.getint('dataset_id'),
            storage=storages.get(storage_key, storage_key),
            start_num=sec.getint('start_num', 0),
        ))
    if not runs:
        raise ValueError('campaign file defines no [run:*] sections: %s' % path)

    return Campaign(
        prefix=unit['prefix'],
        unit_id=unit.getint('id'),
        host=unit['host'],
        runs=runs,
        opts=opts,
        webhook=webhook,
    )


def run_dataset(lab, run, prefix, unit_id, notifier, log):
    """Acquire one dataset: ACF -> power on -> frames -> power off."""
    dstype = run.dataset_id % 10
    spec = DATASET_SPECS.get(dstype)
    if spec is None:
        raise ValueError('DatasetId %d: unknown dataset type digit %d'
                         % (run.dataset_id, dstype))
    plan = build_plan(spec)

    datadir = os.path.join(run.storage, 'DS%04d' % run.dataset_id)
    os.makedirs(datadir, exist_ok=True)

    log.info('=== DS%04d (%s, %d frames) -> %s ===',
             run.dataset_id, spec.name, len(plan), datadir)
    notifier.send('HELab: %s DS%04d (%s) start, %d frames'
                  % (prefix, run.dataset_id, spec.name, len(plan)))

    lab.apply_acf(run.acf_path)
    lab.power_on()
    written = []
    try:
        date_tag = time.strftime('%Y%m%d', time.localtime())
        for index, job in enumerate(plan):
            filenum = run.dataset_id * 100 + run.start_num + index
            log.info('[%d/%d] #%06d %s IntMS=%d shutter=%s',
                     index + 1, len(plan), filenum, job.imagetyp,
                     job.exptime_ms, 'open' if job.shutter_open else 'closed')
            pixels, meta = lab.expose(job.exptime_ms, job.shutter_open)

            status = lab.client.get_status()
            cards = [
                ('EXPTIME', job.exptime_ms / 1000.0, 'Requested integration [s]'),
                ('EXPMEAS', meta['exp_measured_s']
                 if meta['exp_measured_s'] is not None else -1.0,
                 'Measured from trigger timestamps [s]'),
                ('SHUTOPEN', job.shutter_open, 'Shutter trigger enabled'),
                ('IMAGETYP', job.imagetyp, 'Frame type in dataset plan'),
                ('DATE-OBS', meta['date_obs'], 'Exposure start (UTC, host clock)'),
                ('DATE-LOC', meta['date_loc'], 'Exposure start (local)'),
                ('FRAMENO', meta['frame'], 'Controller frame counter'),
                ('BUFNO', meta['buf'] + 1, 'Archon frame buffer used'),
                ('UNITID', unit_id, 'KMTNet CEU unit ID'),
                ('DATASET', run.dataset_id, 'Dataset ID [Unit][Setup][Type]'),
                ('FILENUM', filenum, 'File number [DatasetID][FrameSN]'),
                ('ACFFILE', os.path.basename(run.acf_path), 'Applied ACF'),
                ('BCKTEMP', float(status.get('BACKPLANE_TEMP', -999)),
                 'Backplane temperature [C]'),
                ('SWVER', 'labtest v%s' % __version__, 'Acquisition script'),
                ('ORIGIN', 'KASI/KMTNet-CEU', ''),
            ]
            path = os.path.join(datadir, '%s.%s.%06d.fits'
                                % (prefix, date_tag, filenum))
            write_fits(path, pixels, meta['width'], meta['height'], cards)
            written.append(path)
            log.info('wrote %s', path)
    finally:
        lab.power_off()

    notifier.send('HELab: %s DS%04d done, %d frames'
                  % (prefix, run.dataset_id, len(written)))
    return written


def print_plan(run, log):
    spec = DATASET_SPECS.get(run.dataset_id % 10)
    if spec is None:
        log.error('DS%04d: unknown dataset type digit %d',
                  run.dataset_id, run.dataset_id % 10)
        return
    plan = build_plan(spec)
    log.info('--- DS%04d (%s): %d frames, ACF=%s, storage=%s ---',
             run.dataset_id, spec.name, len(plan), run.acf_path, run.storage)
    for index, job in enumerate(plan):
        filenum = run.dataset_id * 100 + run.start_num + index
        log.info('  #%06d  %-4s  %8.1fs  shutter %s',
                 filenum, job.imagetyp, job.exptime_ms / 1000.0,
                 'open' if job.shutter_open else 'closed')


def run_campaign(campaign, dry_run=False, only_runs=None, log=None):
    log = log or logging.getLogger('labtest')
    runs = [r for r in campaign.runs
            if not only_runs or r.name in only_runs]
    if not runs:
        raise ValueError('no runs selected (available: %s)'
                         % ', '.join(r.name for r in campaign.runs))

    if dry_run:
        for run in runs:
            print_plan(run, log)
        return []

    notifier = Notifier(campaign.webhook, log)
    client = ArchonClient(campaign.host, log=log)
    lab = LabArchon(client, log=log, opts=campaign.opts)
    written = []
    client.connect()
    try:
        notifier.send('HELab: %s campaign start (%d runs)'
                      % (campaign.prefix, len(runs)))
        for run in runs:
            written += run_dataset(lab, run, campaign.prefix,
                                   campaign.unit_id, notifier, log)
        notifier.send('HELab: %s campaign complete, %d frames total'
                      % (campaign.prefix, len(written)))
    except KeyboardInterrupt:
        log.warning('interrupted by user -- powering CCD off')
        lab.power_off()
        notifier.send('HELab: %s campaign ABORTED by user' % campaign.prefix)
        raise
    except ArchonError as exc:
        log.error('campaign failed: %s', exc)
        lab.power_off()
        notifier.send('HELab: %s campaign FAILED: %s' % (campaign.prefix, exc))
        raise
    finally:
        client.close()
    return written


# ------------------------------------------------------------------------
# CLI

def _setup_logging(log_file=None):
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-7s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers)
    return logging.getLogger('labtest')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='KMTNet-CEU Archon lab acquisition v%s' % __version__)
    parser.add_argument('campaign', help='campaign INI file (see campaign_example.ini)')
    parser.add_argument('--dry-run', action='store_true',
                        help='print the frame plan without touching hardware')
    parser.add_argument('--run', action='append', metavar='NAME',
                        help='execute only the named [run:NAME] section(s)')
    parser.add_argument('--log-file', default=None,
                        help='also write the log to this file')
    args = parser.parse_args(argv)

    log = _setup_logging(args.log_file)
    campaign = load_campaign(args.campaign)
    run_campaign(campaign, dry_run=args.dry_run, only_runs=args.run, log=log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
