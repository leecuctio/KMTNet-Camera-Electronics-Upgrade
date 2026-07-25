#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archon_simulator.py -- minimal STA Archon protocol simulator for testing
archon_kmtnet_labtest_v2.py without hardware (idea from karpov-sv/ccdlab).

Implements just enough of the text/binary protocol for the acquisition
script: reference-tagged replies, '?xx' errors, STATUS/FRAME, config
upload/read-back, parameter staging (FASTPREPPARAM/RELEASETIMING and the
LOADPARAMS fallback), POWERON gating, triple buffering with trigger
timestamps, and 1 KiB binary FETCH blocks.

Standalone use:  python3 archon_simulator.py [port]
Test use:        with ArchonSimulator(time_scale=0.01) as sim: ... sim.port
"""

from __future__ import annotations

import socket
import sys
import threading
import time

import numpy as np

BURST_LEN = 1024
TICKS_PER_SEC = 1.0e8

POWER_OFF = 2
POWER_ON = 4

BUF_BASES = (0xA0000000, 0xC0000000, 0xE0000000)


class ArchonSimulator:
    """Single-client Archon protocol simulator running in a thread."""

    def __init__(self, host='127.0.0.1', port=0, width=128, height=64,
                 time_scale=1.0, readout_time=0.05):
        self.host = host
        self.width = width
        self.height = height
        self.time_scale = time_scale      # IntMS is scaled by this for tests
        self.readout_time = readout_time  # simulated readout duration [s]

        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None

        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind((host, port))
        self._listener.listen(1)
        self._listener.settimeout(0.2)
        self.port = self._listener.getsockname()[1]

        self._reset_state()

    def _reset_state(self):
        self.config = {}            # line number -> 'KEY=VALUE'
        self.params = {}            # active timing-core parameters
        self.staged = {}            # FASTPREPPARAM staging area
        self.holding = False
        self.power = POWER_OFF
        self.frameno = 0
        self.wbuf = 1
        self.bufs = [dict(frame=-1, complete=0, width=0, height=0, sample=0,
                          base=BUF_BASES[i], pixels=0, lines=0,
                          timestamp=0, re=0, fe=0)
                     for i in range(3)]
        self.framedata = {}         # buffer index -> bytes

    # --- lifecycle ------------------------------------------------------------

    def start(self):
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._listener.close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # --- server loop ------------------------------------------------------------

    def _serve(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with conn:
                conn.settimeout(0.2)
                buf = b''
                while not self._stop.is_set():
                    try:
                        chunk = conn.recv(65536)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        reply = self._handle_line(line.strip())
                        if reply:
                            try:
                                conn.sendall(reply)
                            except OSError:
                                break

    def _handle_line(self, line):
        if len(line) < 3 or line[0:1] != b'>':
            return b''
        ref = line[1:3].decode('ascii', 'replace')
        cmd = line[3:].decode('ascii', 'replace')
        try:
            payload = self._dispatch(cmd)
        except _SimCommandError:
            return ('?%s\n' % ref).encode('ascii')
        if isinstance(payload, bytes):      # binary FETCH blocks
            out = bytearray()
            for off in range(0, len(payload), BURST_LEN):
                out += ('<%s:' % ref).encode('ascii')
                out += payload[off:off + BURST_LEN]
            return bytes(out)
        return ('<%s%s\n' % (ref, payload)).encode('ascii')

    # --- command dispatch --------------------------------------------------------

    def _dispatch(self, cmd):
        with self._lock:
            if cmd == 'STATUS':
                return ('VALID=1 POWER=%d POWERGOOD=%d BACKPLANE_TEMP=25.3 '
                        'P5V_V=5.02 P5V_I=0.51'
                        % (self.power, 1 if self.power == POWER_ON else 0))
            if cmd == 'SYSTEM':
                return 'BACKPLANE_TYPE=1 BACKPLANE_REV=5 BACKPLANE_ID=SIM'
            if cmd == 'FRAME':
                return self._frame_payload()
            if cmd == 'CLEARCONFIG':
                self.config.clear()
                self.params.clear()
                return ''
            if cmd.startswith('WCONFIG'):
                lineno = int(cmd[7:11], 16)
                self.config[lineno] = cmd[11:]
                return ''
            if cmd.startswith('RCONFIG'):
                lineno = int(cmd[7:11], 16)
                return self.config.get(lineno, '')
            if cmd in ('APPLYALL', 'APPLYSYSTEM', 'APPLYCDS', 'LOADTIMING'):
                if cmd == 'APPLYALL':
                    self._load_params_from_config()
                return ''
            if cmd == 'POWERON':
                self.power = POWER_ON
                return ''
            if cmd == 'POWEROFF':
                self.power = POWER_OFF
                return ''
            if cmd in ('POLLON', 'POLLOFF'):
                return ''
            if cmd == 'HOLDTIMING':
                self.holding = True
                return ''
            if cmd == 'RELEASETIMING':
                self.holding = False
                self.params.update(self.staged)
                self.staged.clear()
                self._maybe_trigger()
                return ''
            if cmd.startswith('FASTPREPPARAM'):
                name, value = cmd.split()[1:3]
                self.staged[name] = int(value)
                return ''
            if cmd.startswith('FASTLOADPARAM'):
                name, value = cmd.split()[1:3]
                self.params[name] = int(value)
                self._maybe_trigger()
                return ''
            if cmd == 'LOADPARAMS':
                self._load_params_from_config()
                self._maybe_trigger()
                return ''
            if cmd.startswith('LOCK'):
                if cmd[4:] in ('0', '1', '2', '3'):
                    return ''
                raise _SimCommandError()
            if cmd.startswith('FETCH'):
                return self._fetch(int(cmd[5:13], 16), int(cmd[13:21], 16))
            raise _SimCommandError()

    def _frame_payload(self):
        fields = ['RBUF=%d' % (self.frameno % 3 + 1), 'WBUF=%d' % self.wbuf]
        for i, buf in enumerate(self.bufs, start=1):
            fields += [
                'BUF%dFRAME=%d' % (i, buf['frame']),
                'BUF%dCOMPLETE=%d' % (i, buf['complete']),
                'BUF%dWIDTH=%d' % (i, buf['width']),
                'BUF%dHEIGHT=%d' % (i, buf['height']),
                'BUF%dSAMPLE=%d' % (i, buf['sample']),
                'BUF%dBASE=%d' % (i, buf['base']),
                'BUF%dPIXELS=%d' % (i, buf['pixels']),
                'BUF%dLINES=%d' % (i, buf['lines']),
                'BUF%dTIMESTAMP=%X' % (i, buf['timestamp']),
                'BUF%dRETIMESTAMP=%X' % (i, buf['re']),
                'BUF%dFETIMESTAMP=%X' % (i, buf['fe']),
            ]
        return ' '.join(fields)

    def _load_params_from_config(self):
        """Parse PARAMETERn="Name=Value" config lines into active params."""
        for text in self.config.values():
            key, _, value = text.partition('=')
            if key.startswith('PARAMETER') and '=' in value:
                name, _, num = value.replace('"', '').partition('=')
                try:
                    self.params[name.strip()] = int(num)
                except ValueError:
                    pass

    def _maybe_trigger(self):
        if self.holding or self.power != POWER_ON:
            return
        if self.params.get('Exposures', 0) >= 1:
            self.params['Exposures'] = 0
            intms = self.params.get('IntMS', 0)
            threading.Thread(target=self._run_exposure, args=(intms,),
                             daemon=True).start()

    def _run_exposure(self, intms):
        exp_s = intms / 1000.0 * self.time_scale
        ts_rising = int(time.monotonic() * TICKS_PER_SEC)
        time.sleep(exp_s)
        ts_falling = ts_rising + int(intms / 1000.0 * TICKS_PER_SEC)

        with self._lock:
            index = self.frameno % 3
            self.wbuf = index + 1
            buf = self.bufs[index]
            buf.update(complete=0, width=self.width, height=self.height,
                       sample=0, pixels=0, lines=0)

        # crude readout ramp so BUFnLINES progress is observable
        steps = 4
        for step in range(1, steps + 1):
            time.sleep(self.readout_time / steps)
            with self._lock:
                buf['lines'] = self.height * step // steps
                buf['pixels'] = self.width * buf['lines']

        with self._lock:
            self.frameno += 1
            pattern = ((np.arange(self.width * self.height, dtype=np.uint32)
                        + self.frameno * 7) & 0x3FFF).astype('<u2')
            self.framedata[index] = pattern.tobytes()
            buf.update(frame=self.frameno, complete=1,
                       pixels=self.width * self.height, lines=self.height,
                       timestamp=int(time.monotonic() * TICKS_PER_SEC),
                       re=ts_rising, fe=ts_falling)

    def _fetch(self, addr, blocks):
        for index, buf in enumerate(self.bufs):
            if buf['base'] == addr:
                data = self.framedata.get(index, b'')
                need = blocks * BURST_LEN
                return data[:need] + b'\x00' * max(0, need - len(data))
        raise _SimCommandError()

    def expected_pattern(self, frameno):
        """Raw pixel pattern the simulator stored for a given frame number."""
        return ((np.arange(self.width * self.height, dtype=np.uint32)
                 + frameno * 7) & 0x3FFF).astype('<u2')


class _SimCommandError(Exception):
    """Internal marker: reply with '?xx'."""


if __name__ == '__main__':
    listen_port = int(sys.argv[1]) if len(sys.argv) > 1 else 4242
    sim = ArchonSimulator(port=listen_port)
    print('Archon simulator listening on %s:%d' % (sim.host, sim.port))
    sim.start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        sim.stop()
