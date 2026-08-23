# -*- coding: utf-8 -*-
"""archon_kmtnet_labtest_v1.1.bigbuf.py 회귀 검증 -- 실기 없이 돌린다.

    python tests/verify_labtest_v11.py      # 0 = 전부 통과, 1 = 실패 있음

**왜 있나.** v1.1 이 넣은 세 가지(STATUS 질의·비ASCII 손편집 값·데이터부
패딩)가 각각 취득을 죽이거나 파일을 통째로 못 읽게 만드는 경로를 열었다 --
전부 감사에서 실측으로 확인됐고, 셋 다 **취득 중에는 아무 경고도 안 뜬다**.
그래서 실기 없이도 매번 확인할 수 있는 자리를 남긴다.

스크립트를 import 하면 모듈 최상단에서 실물 컨트롤러에 접속해 버리므로,
`ast` 로 필요한 정의만 뽑아 실행한다.  가짜 Archon(늦게 답하는 STATUS)은
127.0.0.1:42421 에 뜬다.
"""
import ast, io, os, socket, sys, textwrap, threading, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   os.pardir, 'archon_kmtnet_labtest_v1.1.bigbuf.py')
text = open(SRC, encoding='utf-8-sig').read()
tree = ast.parse(text)


def grab(*names):
    out = []
    for node in tree.body:
        got = None
        if isinstance(node, ast.FunctionDef) and node.name in names:
            got = node
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in names:
                    got = node
        if got is not None:
            out.append(ast.get_source_segment(text, got))
    return '\n\n'.join(out)


WANT = ('RAWCARDS', 'SITE_INFO', 'HDR_NAXIS1', 'HDR_NAXIS2', 'TEMP_NC',
        'VOLT_RAILS', 'TEMP_SLOTS',
        'archoncmd', 'archon_status', '_resync_archon_link', 'status_number',
        'fits_card', 'build_header', 'resolve_pair_number',
        '_check_identity_setup')
G = {'os': os, 'socket': socket, 'time': time, 'select': __import__('select'),
     'msgref': 0, 'msgbuf': b'', 'archon': None,
     'TELEMETRY_ENABLE': True, 'TELEMETRY_TIMEOUT': 3.0,
     'UNIT_IPADDR': '127.0.0.1', 'UNIT_TIMEOUT': 1,
     'SITE_CODE': 'KMTT', 'UNIT_CTRLTAG': 'MK',
     'UNIT_CTRL_ID': 'KMTT-SCI-101', 'UNIT_CTRL_SN': 'STA-0287',
     'OBSERVER_NAME': 'HELab', 'SCRIPT_VERSION': '1.1.0',
     'SCRIPT_BUILD': '2026-08-22T09:00Z', 'DATA_PREFIX': 'AC13A'}
exec(compile(grab(*WANT), SRC, 'exec'), G)
missing = [n for n in WANT if n not in G]
assert not missing, missing

PORT = 42421
fails = []


def check(ok, label, extra=''):
    print(('  PASS  ' if ok else '  FAIL  ') + label
          + (('  -- ' + extra) if extra else ''))
    if not ok:
        fails.append(label)


class FakeArchon(threading.Thread):
    """STATUS 만 늦게(5초) 답하고 나머지는 즉시 답하는 컨트롤러."""

    daemon = True

    def __init__(self):
        super().__init__()
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('127.0.0.1', PORT))
        self.srv.listen(4)
        self.accepts = 0
        self.stop = False

    def run(self):
        while not self.stop:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            self.accepts += 1
            threading.Thread(target=self.serve, args=(c,), daemon=True).start()

    def serve(self, c):
        c.settimeout(30)
        buf = b''
        while True:
            try:
                d = c.recv(4096)
            except Exception:
                return
            if not d:
                return
            buf += d
            while b'\n' in buf:
                line, _, buf = buf.partition(b'\n')
                ref, cmd = line[1:3], line[3:].decode()
                if cmd.startswith('STATUS'):
                    time.sleep(5.0)          # 시한(3초) 초과 -> 늦게 도착
                    c.sendall(b'<' + ref + b'MOD5/TEMP=31.5 P5V_V=5.001\n')
                else:
                    c.sendall(b'<' + ref + ('REPLY_TO_%s' % cmd).encode() + b'\n')


fake = FakeArchon()
fake.start()


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    s.connect(('127.0.0.1', PORT))
    return s


# _resync_archon_link 는 4242 포트가 박혀 있으니 테스트 포트로만 바꿔 다시 정의
resync_src = ast.get_source_segment(text, [n for n in tree.body
    if isinstance(n, ast.FunctionDef) and n.name == '_resync_archon_link'][0])
exec(compile(resync_src.replace('4242', str(PORT)), SRC, 'exec'), G)

print('\n[T1] STATUS 시한 초과 뒤에도 다음 두 명령이 살아 있나 (수정 후)')
G['archon'] = connect()
G['msgref'] = 0
G['msgbuf'] = b''
G['TELEMETRY_ENABLE'] = True
time.sleep(0.3)                # 서버 스레드가 첫 accept 를 셀 틈을 준다
before = fake.accepts
t0 = time.time()
snap = G['archon_status']()
check(snap == {}, 'STATUS 는 {} 를 돌려준다', repr(snap))
check(2.9 < time.time() - t0 < 6.0, '3초 시한에서 빠져나온다',
      '%.1fs' % (time.time() - t0))
check(G['TELEMETRY_ENABLE'] is False, '이후 질의를 끈다')
for _ in range(40):            # accept 집계는 서버 스레드에서 뒤늦게 오른다
    if fake.accepts >= before + 1:
        break
    time.sleep(0.05)
check(fake.accepts == before + 1, '연결을 새로 열었다',
      'accepts %d -> %d' % (before, fake.accepts))
check(G['msgref'] == 0, 'msgref 가 00 으로 초기화됐다', 'msgref=%d' % G['msgref'])
r1 = G['archoncmd']('WCONFIG0000TEST')
check(r1 == b'REPLY_TO_WCONFIG0000TEST', '다음 명령이 자기 응답을 받는다', repr(r1))
try:
    r2 = G['archoncmd']('APPLYSYSTEM')
    check(r2 == b'REPLY_TO_APPLYSYSTEM', '그 다음 명령도 정상', repr(r2))
except Exception as e:
    check(False, '그 다음 명령도 정상', '%s: %s' % (type(e).__name__, e))
G['archon'].close()

print('\n[T2] 재동기 없이 msgref 만 올리면? (감사가 지적한 순진한 수정)')
G['archon'] = connect()
G['msgref'] = 0
G['msgbuf'] = b''
try:
    G['archoncmd']('STATUS', timeout=3.0)
except TimeoutError:
    pass
G['msgref'] = (G['msgref'] + 1) % 256          # msgref 만 올린다
try:
    r = G['archoncmd']('WCONFIG0000TEST')
    check(r != b'REPLY_TO_WCONFIG0000TEST',
          '순진한 수정은 여전히 깨진다 (남의 응답을 먹는다)', repr(r))
except Exception as e:
    check(True, '순진한 수정은 여전히 깨진다', '%s: %s' % (type(e).__name__, e))
G['archon'].close()

print('\n[T3] 비ASCII 정체 문자열 -- 기동에서 막히나')
for name, val in (('OBSERVER_NAME', 'HELab 차상목'),
                  ('UNIT_CTRL_ID', 'KMTT-과학-101'),
                  ('UNIT_CTRL_SN', 'STA-0287\u00b5')):
    keep = G[name]
    G[name] = val
    try:
        G['_check_identity_setup']()
        check(False, '%s=%r 를 막는다' % (name, val), '통과해버림')
    except SystemExit as e:
        check('비ASCII' in str(e), '%s=%r 를 기동에서 막는다' % (name, val))
    G[name] = keep
try:
    G['_check_identity_setup']()
    check(True, 'ASCII 기본값은 통과한다')
except SystemExit as e:
    check(False, 'ASCII 기본값은 통과한다', str(e))

print('\n[T4] 그래도 새어 들어온 비ASCII -- 헤더 정렬이 유지되나')
card = G['fits_card']('OBSERVER', 'S', 18, 'Observer', 'HELab 차상목')
check(len(card.encode('utf-8')) == 80, '카드가 80바이트다',
      '%dB' % len(card.encode('utf-8')))
vals = {'SIMPLE': True, 'BITPIX': 16, 'NAXIS': 2,
        'NAXIS1': G['HDR_NAXIS1'], 'NAXIS2': G['HDR_NAXIS2'],
        'OBSERVER': 'HELab 차상목'}
head = G['build_header'](vals)
nb = len(head.encode('utf-8'))
check(nb % 2880 == 0, '헤더 전체가 2880B 배수다', '%dB' % nb)

print('\n[T5] 기하/표본 불일치 -- 쓰기 전에 걸리나')
DECL = G['HDR_NAXIS1'] * G['HDR_NAXIS2'] * 2
for label, w, h, sample in (('정상 16bit', 19200, 9400, False),
                            ('samplemode 32bit', 19200, 9400, True),
                            ('guide 기하', 4224, 1033, False)):
    framesize = (4 if sample else 2) * w * h
    caught = framesize != DECL
    want = label != '정상 16bit'
    check(caught == want, '%s -> %s' % (label, '거부' if want else '통과'),
          '%d B vs 선언 %d B' % (framesize, DECL))

print('\n[T6] astropy 로 실제 파일 왕복 (데이터부 축소판)')
try:
    from astropy.io import fits
    import numpy as np
    import warnings
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_t6.fits')
    small = dict(vals)
    small['NAXIS1'] = 4
    small['NAXIS2'] = 2
    h = G['build_header'](small)
    data = np.zeros(8, dtype='>u2')
    pad = (-data.nbytes) % 2880
    with open(tmp, 'wb') as f:
        f.write(bytes(h, 'utf-8'))
        f.write(data.tobytes())
        f.write(b'\x00' * pad)
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        hdr = fits.getheader(tmp)
    check(hdr['OBSERVER'].strip() == 'HELab ???',
          'OBSERVER 가 ? 로 치환돼 읽힌다', repr(hdr['OBSERVER'].strip()))
    check(hdr['NAXIS1'] == 4, '경고 없이 읽힌다')
    os.remove(tmp)
except ImportError:
    print('  SKIP  astropy 없음')

print('\n[T7] ACF 선검사 -- 없는 ACF 를 접속·전원 전에 잡나')
# GetDataset 안의 선검사 블록을 소스에서 그대로 떼어 실행한다 (함수 전체는
# 전역 의존이 많아 못 부른다).
_lines = text.split('\n')
_start = next(i for i, ln in enumerate(_lines)
              if ln.strip() == 'if not os.path.isfile(AcfPath):')
_end = next(i for i in range(_start + 1, len(_lines))
            if _lines[i].strip().startswith('% (AcfPath,'))
GUARD = textwrap.dedent('\n'.join(_lines[_start:_end + 1]))
try:
    exec(compile(GUARD, SRC, 'exec'),
         {'os': os, 'AcfPath': 'acf/does_not_exist_U13.acf'})
    check(False, '없는 ACF 를 거부한다', '통과해버림')
except SystemExit as e:
    _msg = str(e)
    check('ACF not found' in _msg, '없는 ACF 를 거부한다')
    check('does_not_exist_U13.acf' in _msg, '문제의 경로를 찍는다')
    check(os.getcwd() in _msg, 'cwd 를 함께 찍는다 (상대경로 진단)')
except Exception as e:
    check(False, '없는 ACF 를 거부한다', '%s: %s' % (type(e).__name__, e))
try:
    exec(compile(GUARD, SRC, 'exec'),
         {'os': os, 'AcfPath': os.path.abspath(__file__)})
    check(True, '실재하는 파일은 통과한다')
except SystemExit:
    check(False, '실재하는 파일은 통과한다', '멀쩡한 파일을 거부함')

fake.stop = True
fake.srv.close()
print('\n' + '=' * 60)
print('실패 %d 건' % len(fails))
for f in fails:
    print('  -', f)
sys.exit(1 if fails else 0)
