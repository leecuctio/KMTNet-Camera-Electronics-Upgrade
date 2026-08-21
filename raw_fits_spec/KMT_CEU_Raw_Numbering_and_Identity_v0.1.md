# KMT-CEU Raw 파일 번호 · 정체성 · 충돌 처리

**v0.1 (Draft)** · 2026-08-21 · 재작성판 Pair Spec 의 2.3/5.2절로 흡수될 조각 규격

> **지위**: 2026-08-20~21 raw 헤더 검토(ACT-011)에서 확정한 설계의 기록이다. 구 규격 `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`(⛔ 재작성중)의 **2.3.1절(이름 충돌 격리)과 5.2절 일부(`UNIQNAME` · `NAMECLSH`)를 대체**한다. DECISION_LOG 등재 전이므로 근거는 8장의 결정문 초안이다 — 등재 시 D-번호를 부여하고 이 문서의 상태를 올린다.

## 1. 파일 번호 공간과 카운터

- `<NNNNNN>`은 6자리 zero-padding(D-011, 불변)이며 유효값은 **000000–099999** 십만 개다(레거시 관례 계승).
- 카운터는 099999 다음(100000 도달 시) **000000으로 초기화**한다.
- 파일명 형식 · `<SITE>` · 관측일 날짜부 규칙은 D-011 · D-014 그대로다. 충돌 처리(2장)는 번호만 바꾸고 형식은 바꾸지 않는다.

## 2. 파일명 충돌 처리 — 번호 증가 (구 2.3.1 `clash/` 격리 대체)

1. 카운터가 후보 번호 N을 제안한다.
2. **쓰기 전에** 후보 N의 MK · NT **두 경로를 모두 존재 검사**한다. 하나라도 점유되어 있으면 N+1로 재검사한다. 099999를 넘으면 000000으로 되감는다.
3. +1 증가가 **100000회를 초과하면 멈추고 ERROR 메시지를 출력하며 저장하지 않는다.** 상한 100000회 = 번호 공간 정확히 한 바퀴 — 초과는 공간 전체 점유 또는 근본 고장을 뜻하므로 조용한 우회는 없다.
4. 둘 다 빈 N을 확정하고 **카운터를 N으로 동기화**한다. 평소 노출 번호 영속화 경로를 그대로 쓰고, 옛값→새값 점프는 경고 로그로 남긴다.
5. MK · NT를 쓴다. 증가가 있었으면 `FILENAME ≠ ORIGNAME`으로 사건이 헤더에 남는다(3장).

- **전제**: 이 저장 디렉토리에 쓰는 주체는 ICS 하나뿐이다 — 선검사와 쓰기 사이의 경쟁은 없다.
- **효과**: 무인 운영에서 방금 취득한 데이터가 격리되지 않고 밤이 계속된다. 카운터 되감김(재시작 등)이 원인이면 충돌 1회로 원인 전체가 자가 치유된다 — 선검사 루프가 점유 구간을 지나 빈 번호에 착지하고 카운터가 따라간다.
- **폐지**: `clash/` 격리 디렉토리, `.clash<UTC>` 접미사.

## 3. 정체성 카드 — `FILENAME` · `ORIGNAME`

```text
FILENAME= 'KMTA.20260821.012345.MK' / Filename assigned by ICS
ORIGNAME= 'KMTA.20260821.012340.MK' / Original filename assigned by ICS counter
```

- 두 카드는 **모든 raw 파일에 항상** 기록한다. 값은 확장자 없는 실명 형식이며 FITS **문자열 카드 필수**다(zero-padding 보존 — 숫자 카드로 쓰면 앞자리 0이 부서진다).
- `FILENAME` = 실제 저장명. **아카이브 · DTS · 색인의 유일 키**다(유일성은 2장의 증가 방식이 구조로 보장한다).
- `ORIGNAME` = 카운터가 이 노출에 **처음 배정한 이름**. 연쇄 증가의 중간값이 아니라 최초 제안 하나만 기록한다.
- **충돌 신호 = `FILENAME ≠ ORIGNAME`** (값 비교). 카드의 존재 여부가 아니다. 평시에는 두 값이 같다.
- `ORIGNAME` 결측은 충돌이 아니라 **헤더 결함**(규격 이전 작성기)으로 분류한다 — 빈 값과의 비교로 가짜 신호를 만들지 않는다.
- pair 규칙: 두 카드 모두 pair 간 서로 다르다(`.MK`/`.NT` 꼬리). 충돌 증가 시 두 파일이 **함께** 같은 번호로 증가하므로, 각 파일 안의 (FILENAME, ORIGNAME) 불일치 여부는 pair 양쪽에서 동일하다.
- `PAIRFILE`은 짝의 **실명**이다. pair가 동시에 증가하므로 구 v1.2의 "PAIRFILE은 명목 이름으로 열화될 수 있다" 조항은 폐지된다.

## 4. 폐지 항목

| 폐지 | 사유 | 대신 보는 것 |
| --- | --- | --- |
| `UNIQNAME` | "불변 정본 키"라는 뜻이 이탈했다 — 유일성은 증가 방식이 `FILENAME`에 구조로 보장한다. 뜻이 바뀐 이름은 계승하지 않는다(D-013 원칙) | `FILENAME`(유일 키) + `ORIGNAME`(사건 기록) |
| `NAMECLSH` | 신호가 카드 존재에서 값 비교로 이동했다 | `FILENAME ≠ ORIGNAME` |
| `clash/` · `.clash` 접미사 | 격리 방식 자체가 번호 증가로 대체됐다 | 2장 |

- ics_sim의 RETIRED(부활 금지) 목록에 `UNIQNAME` · `NAMECLSH`를 추가한다.
- D-010 · D-012의 "아카이브 근거 삼총사 `UNIQNAME`/`FILENAME`/`CTRLTAG`" 문구는 **`FILENAME`(+`ORIGNAME`)/`CTRLTAG`**로 개정한다.

## 5. 하류 도구 요구사항

- 충돌 필터는 **raw 헤더 층**(아카이브 색인 · DTS · QL)에서 `FILENAME ≠ ORIGNAME`으로 돈다.
- 같은 노출의 재저장(유령 중복)은 fail-open이다 — 위 필터가 걸러낸다는 전제를 **요구사항**으로 둔다.
- MEF 층 필터가 필요해지면 converter 변경점에 `ORIGNAME` pass-through를 추가한다(→ `KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.2.md`).
- OBSAgent `Wrote` 논리 이름의 번호는 **실제 저장 번호**를 쓴다(D-010 형식 불변).

## 6. MEF / converter 연동

converter(v2.2.0)는 raw `UNIQNAME`을 읽어 MEF `UNIQNAME`으로 옮긴다(`v2_1.py:405`). `UNIQNAME` 폐지 후 이 값은 **오류 없이 빈 문자열**이 된다 — 대응은 C-항목으로 LEECU에 이관한다. 상세: `KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.2.md` 1장.

## 7. ics_sim 구현 영향

| 파일 | 변경 |
| --- | --- |
| `rawpair.py` | 선검사 루프(되감음 · 상한 100000회) 신설, clash 격리 로직 제거, `UNIQNAME` 제거, `ORIGNAME` 항상 기록 |
| `state.py` | 확정 N으로 카운터 동기화, 000000–099999 순환 |
| `sequencer._store()` | 확정된 이름만 수령(이름 결정은 rawpair 몫) |
| `tests/test_raw_header.py` | `UNIQNAME` 필수 목록에서 제거하고 RETIRED에 추가, `NAMECLSH` 시험 교체, 평시 `FILENAME`==`ORIGNAME` 불변식, 충돌 시나리오 · 되감음 · 상한 시험 신설 |

## 8. 결정문 초안 (DECISION_LOG 등재용)

> **D-0XX: raw 파일명 충돌 시 노출 번호를 증가시켜 저장한다** / 날짜: 2026-08-21 / 관련: D-010 · D-011 · D-012(일부 대체) · D-013 · D-014 / 상태: **Draft**
>
> **결정**: (1) 파일 번호 공간은 000000–099999이며 카운터는 100000 도달 시 000000으로 초기화한다(레거시 관례). (2) 쓰기 전 후보 N의 MK · NT 두 경로를 선검사하고, 점유 시 N+1(099999 넘으면 000000)로 재검사한다. +1이 100000회를 초과하면 멈추고 ERROR를 출력하며 저장하지 않는다. (3) 확정 N으로 카운터를 동기화한다. (4) `UNIQNAME`을 폐지한다. `FILENAME` = 실제 저장명이자 아카이브 유일 키, `ORIGNAME` = 카운터가 처음 배정한 이름이며 두 카드를 모든 파일에 항상 기록한다 — `FILENAME ≠ ORIGNAME`이 충돌 신호다. `NAMECLSH` · `clash/` 격리를 폐지한다. (5) 재저장 유령 중복은 fail-open이며 raw 헤더 층 필터가 거른다. (6) OBSAgent Wrote 논리 이름은 실제 번호를 쓴다. (7) 단일 쓰기 주체(ICS) 전제.
>
> **근거**: 무인 운영에서 취득 데이터가 격리되지 않는다. 충돌 1회로 카운터 되감김이 자가 치유된다. 신호는 두 정체 카드의 값 비교로 남기며, 카드 구성이 모든 파일에서 균일해 쓰기 분기가 없다. 상한 100000회 = 번호 공간 한 바퀴로 종료가 보장된다.
>
> **영향**: 구 규격 2.3.1 전면 대체 · 5.2(`UNIQNAME` · `NAMECLSH` 폐지, `ORIGNAME` 신설) · 5.11(pair 규칙) · D-012 삼총사 문구 / ics_sim `rawpair.py` · `state.py` · `test_raw_header.py` / converter C-항목 신설(MEF `UNIQNAME` 공급원) / 하류 필터 요구사항 명문화.

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| MEF 쪽 개정 사항 | [`KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.2.md`](KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.2.md) |
| 구 규격 (대체 대상) | [`KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`](KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md) ⛔ ((재작성중)) |
| 검토 진행 상태 | [`SMC_CLAUDE.md`](SMC_CLAUDE.md) |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
