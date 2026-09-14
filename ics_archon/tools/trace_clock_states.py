# -*- coding: utf-8 -*-
"""지정한 **경로**를 따라가며 각 줄에서 클록 채널이 실제로 무엇인지 계산한다.

⛔ 손추론 금지 -- ACF 의 `STATEn\\MODm` 을 읽어 `level,slew,keep` 에서 keep=0 만 set.
서브루틴은 알짜 효과(마지막 set)로 접는다.

용법:  python tools/trace_clock_states.py <acf> <채널,채널> <시작라벨>[,<이어붙일라벨>...]
      예)  python tools/trace_clock_states.py acf/KMTC_SCI_101_STA0284_R2613_MK.acf D4,CLAMP Start,Exposure

⚠️ `STATEn\\MODm` 의 값은 **따옴표로 싸여 있다** (`",1,1,,1,1,…,CLAMP_HIGH,1,0"`).
   따옴표를 벗기지 않으면 마지막 채널(8번)의 keep 이 `0"` 로 읽혀 영영 안 잡히고
   첫 채널의 준위엔 `"` 가 붙는다 -- science 의 `D4`·`CLAMP` 가 화면에서 사라졌던 결함
   (DevNote 11.85-(8), 2026-09-14 정정).  `LINEn` 과 같은 꼴(`="?(.*?)"?$`)로 읽는다.
"""
import io
import re
import sys

BS = '\\' + '\\'
CALL = re.compile(r'\bCALL\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?')
LABEL = re.compile(r'^([A-Za-z_]\w*):\s*$')


def load(path):
    s = io.open(path, encoding='latin-1').read()
    labels = {}
    for m in re.finditer('^MOD(\\d+)' + BS + 'LABEL(\\d+)=(.*)$', s, re.M):
        if m.group(3).strip():
            labels[(m.group(1), m.group(2))] = m.group(3).strip()
    idx_of = dict((m.group(2), m.group(1)) for m in
                  re.finditer('^STATE(\\d+)' + BS + 'NAME=(\\S+)', s, re.M))
    states = {}
    for nm, idx in idx_of.items():
        eff = {}
        for mm in re.finditer('^STATE%s%sMOD(\\d+)="?(.*?)"?$' % (idx, BS),
                              s, re.M):
            mod, parts = mm.group(1), mm.group(2).split(',')
            for k in range(len(parts) // 3):
                lvl, _s, keep = parts[k * 3:k * 3 + 3]
                if keep == '0':
                    eff[(mod, str(k + 1))] = lvl or '(빈값)'
        states[nm] = eff
    lines = {}
    for m in re.finditer('^LINE(\\d+)="?(.*?)"?$', s, re.M):
        lines[int(m.group(1))] = m.group(2)

    # ⛔ **파라미터 값**도 읽는다 -- `CALL Sub(Param)` 은 그 값이 0 이면
    #    **호출 자체가 안 된다** (매뉴얼 p.52).  이걸 빼면 돌지도 않는
    #    서브루틴의 효과를 계산해 클록 상태를 틀리게 낸다.
    params = {}
    for m in re.finditer('^PARAMETER\\d+="([A-Za-z_]\\w*)=(-?\\d+)"$', s, re.M):
        params[m.group(1)] = int(m.group(2))
    return labels, states, [lines[i] for i in sorted(lines)], params


def skipped(arg, params):
    """`CALL Sub(arg)` 이 **안 돌** 자리인가 -- 파라미터이고 값이 0 이면 True."""
    if not arg:
        return False                        # 인자 없음 = 1회 실행
    arg = arg.strip()
    if re.fullmatch(r'-?\d+', arg):
        return False                        # 상수 (0 은 매뉴얼이 금지)
    return params.get(arg, None) == 0


def block(label, script, at):
    """라벨부터 RETURN/무조건 GOTO 까지의 줄 번호들."""
    i = at.get(label)
    out = []
    if i is None:
        return out
    for j in range(i + 1, len(script)):
        raw = script[j]
        if LABEL.match(raw.strip()):
            continue                        # 흘러 들어가는 라벨
        out.append(j)
        if re.search(r'\bRETURN\b', raw):
            break
        if re.search(r'\bGOTO\b', raw) and 'IF' not in raw:
            break
    return out


def net(label, script, at, states, params, seen=None):
    seen = (seen or set()) | {label}
    eff = {}
    for j in block(label, script, at):
        raw = script[j]
        head = raw.split(';')[0].strip()
        if head in states:
            eff.update(states[head])
        c = CALL.search(raw)
        if c and c.group(1) not in seen and not skipped(c.group(2), params):
            eff.update(net(c.group(1), script, at, states, params, seen))
    return eff


def main():
    acf, chans, path = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
    labels, states, script, params = load(acf)
    at = {}
    for i, raw in enumerate(script):
        m = LABEL.match(raw.strip())
        if m:
            at[m.group(1)] = i

    ch_of = {}
    for (mod, ch), nm in labels.items():
        for w in chans:
            if re.search(r'\b%s' % re.escape(w), nm):
                ch_of.setdefault(w, []).append((mod, ch))
    print('추적 채널: %s' % {w: ch_of.get(w) for w in chans})
    print()
    hdr = ' | '.join('%-12s' % w for w in chans)
    print('%-5s %-48s %s' % ('LINE', '스크립트 (이 줄의 CALL 이 도는 동안)', hdr))
    print('(주의) [건너뜀] = 파라미터가 0 이라 CALL 이 안 돈다 (매뉴얼 p.52)')
    print('-' * (56 + 15 * len(chans)))

    cur = {}
    for label in path.split(','):
        for j in block(label, script, at):
            raw = script[j]
            head = raw.split(';')[0].strip()
            if head in states:
                cur.update(states[head])
            cells = []
            for w in chans:
                vals = sorted({cur.get(k, '-') for k in ch_of.get(w, [])})
                cells.append('%-12s' % ('/'.join(vals) or '-'))
            c = CALL.search(raw)
            mark = ' [건너뜀]' if (c and skipped(c.group(2), params)) else ''
            print('%-5d %-48s %s' % (j + 1, raw + mark, ' | '.join(cells)))
            if c and not skipped(c.group(2), params):
                cur.update(net(c.group(1), script, at, states, params))


if __name__ == '__main__':          # 시험이 `load()` 를 import 한다
    main()
