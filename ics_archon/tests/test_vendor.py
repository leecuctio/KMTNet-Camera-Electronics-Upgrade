#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""내장본(`_vendor/ics_sim`) -- **독립 배포가 실제로 되나, 그리고 갈라지지 않나.**

요구사항 (운영자 확정 2026-08-23): **`ics_sim` 을 설치하지 않고 `ics_archon` 만
두어도 돌아야 한다.**  그래서 `ics_sim` 패키지를 `_vendor` 로 내장한다.

사본을 두면 갈라진다 -- 그것이 종전에 사본을 만들지 않은 이유였다.  그래서
갈라짐을 **기계가** 잡게 한다.  이 파일이 세 겹이다:

1. `test_vendor_matches_its_own_manifest` -- 원천이 없어도 되는 확인.
   배포된 트리에서 내장본이 손상·손편집됐는지 혼자 안다.
2. `test_vendor_matches_the_source` -- **원천과 어긋나면 실패.**  저장소에는
   원천이 항상 있으므로 `ics_sim` 을 고치고 동기화를 안 하면 여기서 걸린다.
   ⚠️ 원천이 없으면 `skip` 이 아니라 **실패**다 -- 저장소에서 그런 상태는 결함
   이고, "실행되지 않는데 초록" 을 다시 만들지 않는다 (DevNote 11.21).
3. `test_runs_standalone_from_the_vendored_copy` -- **`ics_archon/` 만 떼어
   놓고 실제로 노출을 돌린다.**  ①②가 통과해도 배선(`_simpath` 탐색 순서)이
   틀리면 독립 실행은 안 된다.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ics_archon/
PKG = os.path.join(ROOT, 'ics_archon')
VENDOR = os.path.join(PKG, '_vendor')
DEST = os.path.join(VENDOR, 'ics_sim')
MANIFEST = os.path.join(VENDOR, 'MANIFEST.sha256')
SOURCE = os.path.normpath(os.path.join(ROOT, os.pardir, 'ics_sim', 'ics_sim'))


def _digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def _tree(root: str) -> dict[str, str]:
    """`.py` 파일의 상대경로 -> 해시."""
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in
                   {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}]
        for name in files:
            if name.endswith('.py'):
                p = os.path.join(base, name)
                out[os.path.relpath(p, root).replace(os.sep, '/')] = _digest(p)
    return out


def _manifest() -> dict[str, str]:
    rows = {}
    with open(MANIFEST, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith('#'):
                h, _, rel = line.partition('  ')
                rows[rel] = h
    return rows


# ---------------------------------------------------------------------------

def test_vendor_exists_and_is_a_package():
    """내장본이 없으면 독립 배포가 애초에 안 된다."""
    assert os.path.isdir(DEST), (
        '내장본이 없다 -- `python tools/sync_vendor.py` 를 돌려라 (%s)' % DEST)
    assert os.path.isfile(os.path.join(DEST, '__init__.py'))
    assert os.path.isfile(MANIFEST), '매니페스트가 없다 -- 동기화를 다시 돌려라'


def test_vendor_matches_its_own_manifest():
    """**원천 없이도 되는 확인.**  배포된 트리의 자가 진단이다.

    내장본이 손상됐거나 누가 손으로 고쳤으면 여기서 걸린다.
    """
    want, have = _manifest(), _tree(DEST)
    missing = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    changed = sorted(r for r in set(want) & set(have) if want[r] != have[r])
    assert not (missing or extra or changed), (
        '내장본이 매니페스트와 어긋난다 -- 없음 %r / 남음 %r / 변경 %r'
        % (missing, extra, changed))


@pytest.mark.repo_only
def test_vendor_matches_the_source():
    """**원천과 어긋나면 실패.**  개정 누락을 잡는 자리다.

    `ics_sim` 을 고치고 `tools/sync_vendor.py` 를 안 돌리면 여기서 걸린다.
    원천이 없으면 `skip` 이 아니라 실패다 -- 저장소에서 그런 상태는 결함이고,
    skip 은 "확인했다" 가 아니라 "확인하지 않았다" 인데 결과 화면에서 둘이
    구별되지 않는다 (DevNote 11.21).
    """
    assert os.path.isdir(SOURCE), (
        '원천 ics_sim 을 찾을 수 없다 (%s) -- 저장소 배치가 깨졌다.  배포된 '
        '트리에서 이 시험을 돌리고 있다면 그쪽에서는 돌리지 않는 것이 맞다'
        % SOURCE)
    src, dst = _tree(SOURCE), _tree(DEST)
    only_src = sorted(set(src) - set(dst))
    only_dst = sorted(set(dst) - set(src))
    diff = sorted(r for r in set(src) & set(dst) if src[r] != dst[r])
    assert not (only_src or only_dst or diff), (
        '내장본이 원천과 갈라졌다 -- `python tools/sync_vendor.py` 를 돌려라.\n'
        '  원천에만: %r\n  내장본에만: %r\n  내용 다름: %r'
        % (only_src, only_dst, diff))


@pytest.mark.repo_only
def test_sync_check_agrees():
    """도구의 `--check` 도 같은 판정을 내려야 한다 (CI 가 이것을 쓴다)."""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools',
                                                     'sync_vendor.py'), '--check'],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    assert r.returncode == 0, r.stdout + r.stderr

@pytest.mark.repo_only
def test_sync_repairs_a_stale_manifest_instead_of_reporting_green(tmp_path):
    """**파일은 같고 매니페스트만 낡은 상태**를 동기화가 고쳐야 한다.

    ⚠️ 2026-08-26 전수 검사에서 실제로 걸린 결함이다.  `sync_vendor.py` 의
    동기화 경로가 `read_manifest()` 의 **존재 여부**만 보고 "이미 동기 상태다"
    로 빠져나갔다 -- 원천과 내장본을 **둘 다 손으로 같게 고치면**(개정 반영에서
    흔한 일이다) 옮길 파일이 없어 그 경로를 타는데, 그때 매니페스트만 낡은 채로
    남는다.

    그러면 도구는 초록인데 `test_vendor_matches_its_own_manifest` 는 빨갛다.
    **도구가 방금 "할 일 없다" 고 말한 뒤라 원인을 찾기 어려운 것이 요점이다** --
    배포된 트리는 원천이 없어 매니페스트가 유일한 자가 확인 수단인데, 그것이
    낡았다는 사실을 아무도 알려 주지 않는다.

    매니페스트를 되돌려 놓고 나가므로 저장소 상태는 그대로다.
    """
    keep = io.open(MANIFEST, encoding='utf-8').read()
    try:
        # 해시 한 줄을 망가뜨린다 -- 파일 자체는 손대지 않는다.
        rows = keep.splitlines()
        hit = next(i for i, r in enumerate(rows)
                   if r and not r.startswith('#'))
        rows[hit] = '0' * 64 + rows[hit][64:]
        io.open(MANIFEST, 'w', encoding='utf-8', newline='\n').write(
            '\n'.join(rows) + '\n')

        # --check 는 어긋남을 알려야 한다.
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, 'tools', 'sync_vendor.py'),
             '--check'], cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', errors='replace')
        assert r.returncode != 0, (
            '--check 가 낡은 매니페스트를 못 잡았다' + r.stdout)

        # 동기화는 그것을 **고쳐야** 한다 (초록이라고 말하고 넘어가면 안 된다).
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, 'tools', 'sync_vendor.py')],
            cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', errors='replace')
        assert r.returncode == 0, r.stdout + r.stderr

        got = io.open(MANIFEST, encoding='utf-8').read()
        assert '0' * 64 not in got, (
            '동기화가 낡은 매니페스트를 그대로 뒀다 -- 도구는 초록인데 '
            '시험은 빨간 상태가 다시 만들어진다' + r.stdout)

        # 고친 뒤에는 --check 가 조용해야 한다.
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, 'tools', 'sync_vendor.py'),
             '--check'], cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', errors='replace')
        assert r.returncode == 0, r.stdout + r.stderr
    finally:
        io.open(MANIFEST, 'w', encoding='utf-8', newline='\n').write(keep)


# ---------------------------------------------------------------------------

@pytest.mark.repo_only
def test_simpath_prefers_the_sibling_in_the_repo():
    """저장소에서는 **형제 원천이 이긴다** -- 고친 것이 곧바로 반영돼야 한다.

    내장본이 이기면 "`ics_sim` 을 고쳤는데 안 바뀐다" 가 된다.  둘이 갈라졌는지는
    위 `test_vendor_matches_the_source` 가 알려 준다.
    """
    from ics_archon import _simpath
    assert _simpath.CHOSEN, 'ensure() 가 아직 안 불렸다'
    assert os.path.normpath(_simpath.CHOSEN) == os.path.normpath(
        os.path.join(ROOT, os.pardir, 'ics_sim')), _simpath.describe()
    assert '형제' in _simpath.CHOSEN_WHY


def test_missing_everything_names_all_three_fixes(monkeypatch, tmp_path):  # noqa: ANN001
    """아무 데서도 못 찾으면 **고치는 방법 셋을 다 말해야** 한다.

    찾아본 경로를 찍지 않으면 "왜 못 찾나" 를 사람이 추측해야 한다.
    """
    from ics_archon import _simpath
    monkeypatch.setattr(_simpath, 'CHOSEN', '')
    monkeypatch.setattr(_simpath, 'SIM_ROOT', str(tmp_path / 'nope'))
    monkeypatch.setattr(_simpath, '_SIBLING', str(tmp_path / 'nosibling'))
    monkeypatch.setattr(_simpath, '_VENDOR', str(tmp_path / 'novendor'))
    with pytest.raises(ImportError) as exc:
        _simpath.ensure()
    msg = str(exc.value)
    assert 'ICS_SIM_PATH' in msg
    assert 'sync_vendor.py' in msg
    assert '형제' in msg
    assert str(tmp_path) in msg, '찾아본 경로를 찍지 않았다'


# ---------------------------------------------------------------------------

DRIVER = textwrap.dedent('''
    """ics_archon 만 떼어 놓은 트리에서 노출 1회를 돌린다."""
    import asyncio, glob, json, os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'tests'))
    from fake_archon import FakeArchon
    from ics_archon import _simpath, config as acfg_mod
    from ics_archon.app import IcsArchon
    from ics_sim import config as simcfg

    NX, NY = 12, 4
    out = {}
    acf = os.path.join(sys.argv[1], 'test.acf')
    open(acf, 'w').write('[CONFIG]\\nTRIGOUTFORCE=0\\n'
                         'PARAMETER1="Exposures=1"\\nPARAMETER2="IntMS=0"\\n')

    ini = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'ics_archon.ini')
    cfg = simcfg.load(ini)
    cfg.timing.time_scale = 0.02
    cfg.transport.bind_host = '127.0.0.1'; cfg.transport.bind_port = 0
    cfg.transport.send_gap_ms = 0.0
    cfg.behavior.console = False; cfg.logging.wire = False
    cfg.paths.data_dir = os.path.join(sys.argv[1], 'rawdata')
    cfg.paths.expnum_file = os.path.join(sys.argv[1], 'expnum')
    cfg.hardware.backend = 'archon'

    acfg = acfg_mod.load(ini)
    acfg.naxis1, acfg.naxis2 = NX, NY
    acfg.poweron_wait = 0.0; acfg.frame_poll = 0.01

    mk = FakeArchon(width=NX, height=NY); nt = FakeArchon(width=NX, height=NY)
    mk.start(); nt.start()
    acfg.hosts = {'MK': '127.0.0.1', 'NT': '127.0.0.1'}
    acfg.acf = {'MK': acf, 'NT': acf}
    acfg.port = mk.port

    async def main():
        app = IcsArchon(cfg, acfg)
        app.backend.ctrls['NT'].link.port = nt.port
        await app.start()
        try:
            for line in ('OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go'):
                app.transport.feed(line); await asyncio.sleep(0.02)
            await app.seq.wait(); await asyncio.sleep(0.8)
            return list(app.transport.sent_log)
        finally:
            await app.stop()

    try:
        sent = asyncio.run(main())
    finally:
        mk.shutdown(); nt.shutdown()

    out['sim_root'] = _simpath.CHOSEN
    out['why'] = _simpath.CHOSEN_WHY
    out['acq'] = sum('Acquisition Complete.' in m for m in sent)
    out['wrote'] = sum('Wrote' in m for m in sent)
    out['files'] = sorted(os.path.basename(p) for p in
                          glob.glob(os.path.join(cfg.paths.data_dir, '*.fits')))
    print('RESULT ' + json.dumps(out))
''')


def test_runs_standalone_from_the_vendored_copy(tmp_path):  # noqa: ANN001
    """**`ics_archon/` 만 떼어 놓고 실제로 노출을 돌린다.**

    이것이 요구사항의 직접 확인이다 -- `ics_sim` 이 어디에도 없는 트리에서
    가짜 컨트롤러 2대로 프레임을 받아 raw pair 를 쓴다.

    ①②가 통과해도 `_simpath` 의 탐색 순서가 틀리면 독립 실행은 안 된다.
    그래서 파일 존재 확인이 아니라 **끝까지 돌려** 본다.
    """
    tree = tmp_path / 'deployed' / 'ics_archon'
    shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns(
        '__pycache__', '.pytest_cache', '*.pyc', '__ref_archon_control'))
    # 형제 원천이 **없는** 트리다 -- 내장본만 남는다
    assert not (tmp_path / 'deployed' / 'ics_sim').exists()

    driver = tree / 'standalone_probe.py'
    driver.write_text(DRIVER, encoding='utf-8')
    work = tmp_path / 'work'
    work.mkdir()

    env = dict(os.environ)
    env.pop('ICS_SIM_PATH', None)          # 환경변수 탈출구를 막는다
    env['PYTHONIOENCODING'] = 'utf-8'
    r = subprocess.run([sys.executable, str(driver), str(work)],
                       cwd=str(tree), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, timeout=300)
    assert 'RESULT ' in r.stdout, (
        '독립 트리에서 돌지 않았다\n--- stdout ---\n%s\n--- stderr ---\n%s'
        % (r.stdout[-3000:], r.stderr[-3000:]))
    got = json.loads(r.stdout.split('RESULT ', 1)[1].splitlines()[0])

    # **내장본을 썼다** -- 형제가 없으므로
    assert '_vendor' in got['sim_root'].replace('\\', '/'), got
    assert '내장본' in got['why'], got
    # 그리고 규약대로 끝까지 돌았다
    assert got['acq'] == 4, got
    assert got['wrote'] == 8, got            # CB 4 + ICS 중계 4
    assert len(got['files']) == 2, got
    assert got['files'][0].endswith('.MK.fits'), got
