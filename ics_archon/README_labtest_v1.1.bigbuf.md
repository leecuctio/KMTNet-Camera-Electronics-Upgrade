# archon_kmtnet_labtest_v1.1.bigbuf.py — 실행 안내

**실험실 취득 스크립트를 돌리기 전에 읽는 문서.** 무엇이 바뀌었나(변경 내역)는
[README.md](README.md), 왜 그렇게 정했나(경위·판단)는
[`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 11.19~11.21 에 있다.

## 이 판이 무엇인가

`v1.0.bigbuf` 는 **실제로 돌려서 쓰던 검증된 코드**다. v1.1 은 거기에 raw spec
적용 개정을 얹은 것이므로, 판단해야 할 것은 하나다:

> **내 개정이 그 검증된 취득 경로를 건드렸나?**

컨트롤러와의 왕복 기준으로 v1.1 이 **추가한 프로토콜 명령은 `STATUS` 하나뿐**
이다(나머지 변경은 파일명·헤더·패딩 등 호스트 쪽 일이라 컨트롤러와 무관).
그래서 **`TELEMETRY_ENABLE = False` 로 두면 왕복이 v1.0 과 완전히 같아진다** —
문제가 보일 때 원인을 가르는 가장 빠른 수단이다.

## 검증 상태 (2026-08-22)

| 항목 | 상태 |
|---|---|
| 헤더 144카드가 견본 v1.0 pair 와 **바이트 단위 일치** | ✅ 확인 (불일치 0) |
| 헤더 2880B × 4블록 정렬 · 데이터부 패딩 | ✅ 확인 |
| 문법·컴파일 | ✅ 확인 |
| STATUS 상한·실패 시 자동 차단 | ✅ 가짜 컨트롤러로 실측 |
| **실기 왕복** (POWERON → LOADPARAMS → FRAME 폴링 → FETCH) | ❌ **미검증** |
| 실제 픽셀이 담긴 FITS 를 converter 에 투입 | ❌ 미검증 |

즉 **하드웨어로는 한 번도 돌리지 않았다.** 첫 실행은 그 전제로 볼 것.

## 돌리기 전에 손볼 자리

행 번호는 2026-08-22 기준이다. 옮겨졌으면 이렇게 찾는다:

```bash
grep -n "Set this\|^TELEMETRY_\|^SITE_CODE\|^TestRunNum\|^GetDataset" archon_kmtnet_labtest_v1.1.bigbuf.py
```

| 행 | 항목 | 지금 값 | 비고 |
|---:|---|---|---|
| 34 | `DATA_PREFIX` | `'AC13A'` | 로그·SMS 표시용 라벨 |
| 36 | `UNIT_ID` | `7` | |
| 37 | `UNIG_IP` → `UNIT_IP` | `'13'` | 주소는 `10.0.0.<UNIT_IP>` |
| **53** | `SITE_CODE` | `'KMTT'` | 테스트베드. 관측소 반입 시 `KMTC`/`KMTS`/`KMTA` — **`OBSERVAT`/`ORIGIN`/`TELESCOP` 이 여기서 유도된다** |
| **54** | `UNIT_CTRLTAG` | `'MK'` | **신설.** 이 유닛이 담당하는 detector pair. `MK`/`NT` 가 아니면 기동 시 거부 |
| **56** | `UNIT_CTRL_ID` | `'KMTT-SCI-101'` | **신설.** FITS `CTRL<n>ID` |
| **57** | `UNIT_CTRL_SN` | `'STA-0287'` | **신설.** 백플레인 시리얼 |
| 66 | `TELEMETRY_ENABLE` | `True` | 문제가 보이면 `False` (아래 참조) |
| 67 | `TELEMETRY_TIMEOUT` | `3.0` | STATUS 응답 대기 상한 [s] |
| 1394~1410 | 실행부 3블록 | — | 앞 2블록은 `'''` 로 묶여 있고 **1407~1410 이 활성**(`3211`/`3511`/`3811`, 2025-04-13 자). **그대로 돌리면 그 데이터셋을 다시 찍는다** |

그 밖에 확인할 것:

- `acf/KMTNet_Sci_{fast,comp,slow}_med_U<IP>.acf` 가 실제로 있는지 (30~32행)
- `DATA_STORAGE_A`/`_B`/`_C` 경로가 마운트돼 있는지 (23~25행)
- `TEMP_SLOTS` (535행 근처) — 지금은 `BACKPLANE_TEMP` + AD 모듈 4장(MOD5~8).
  카드 폭(51자)을 넘으면 잘리고 경고가 난다. **모듈 나열 순서의 정본 명세는
  규격 수록 예정**이라 확정되면 교체한다

## 첫 실행에서 볼 것

**기동 즉시** — 컨트롤러에 붙기 **전에** 정체성을 검사하고 배너를 찍는다.
틀리면 여기서 멈춘다(오타가 노출 도중에 터지지 않게 하려는 것):

```
Identity: SITE=KMTT  DETID=MK  CTRL1=KMTT-SCI-101 (STA-0287)
          OBSERVAT=TESTBED  ORIGIN=KASI  TELESCOP=Sim
```

**노출마다** — 파일명 형식이 바뀌었다:

```
v1.0:  AC13A.<YYYYMMDD>.<NNNNNN>.fits
v1.1:  KMTT.<YYYYMMDD>.<NNNNNN>.MK.fits      <SITE>.<날짜>.<번호>.<MK|NT>
```

**경고가 뜨면** 이 둘만 눈에 담으면 된다:

| 메시지 | 뜻 · 대처 |
|---|---|
| `WARNING: STATUS query failed (...) -- telemetry cards go NC for the rest of this run` | 텔레메트리만 포기하고 **취득은 계속된다.** 설계된 동작이다 — `Cn_*` 카드가 `'NC'` 로 실린다 |
| `WARNING: FITS card C1_TEMP value too long (N > M) -- truncated` | `TEMP_SLOTS` 를 줄인다. 카드는 유효한 상태로 유지된다 |
| `WARNING: filename clash -- number bumped NNNNNN -> MMMMMM (D-016)` | 같은 이름이 있어 번호를 올려 저장했다. 헤더에 `FILENAME ≠ ORIGNAME` 으로 남는다 |

**첫 프레임이 나오면** 확인:

```bash
python -c "from astropy.io import fits; h=fits.open('KMTT.20260822.321100.MK.fits'); print(h[0].data.shape, repr(h[0].header['DETID']), repr(h[0].header['C1_TEMP']), repr(h[0].header['DATE-OBS']))"
```

기대: `(9400, 19200)` · `'MK'` · 온도 나열(또는 `'NC'`) · UTC 밀리초.

## 이상할 때 — 원인을 가르는 순서

1. **`TELEMETRY_ENABLE = False`** (66행). 이러면 컨트롤러와의 왕복이 v1.0 과
   동일해진다. 그래도 문제가 남으면 **원인은 내 개정 밖**이다(헤더·파일명은
   호스트 쪽이라 취득에 관여하지 않는다).
2. 그래도 재현되면 `__ref_archon_control/archon_kmtnet_labtest_v1.0.bigbuf.py`
   로 되돌려 같은 조건을 돌려 본다. v1.0 에서도 나면 v1.1 과 무관하다.
3. 헤더만 이상하면 취득은 이미 끝난 뒤의 일이다 — 프레임은 살아 있다.

## v1.1 이 취득 경로에서 유일하게 손댄 곳

`STATUS` 질의 하나이고, **놓는 위치를 두 번 고쳤다.** 처음엔 프레임 fetch
직후·파일 쓰기 직전에 두었는데, `archoncmd` 에 타임아웃이 없어서 컨트롤러가
답하지 않으면 그 자리에서 무한히 돌고 **이미 다 읽어낸 노출을 잃었다**
(`try/except` 로는 안 잡힌다 — 무한 루프는 예외가 아니다). 지금은:

- **노출 개시 전**에 스냅샷을 뜬다 → 실패해도 잃을 프레임이 없다
- `archoncmd(cmd, timeout=)` 로 상한을 준다 — **기본값 `None` 이라 기존
  호출(`APPLYALL` 등 오래 걸리는 것)의 동작은 바뀌지 않는다.** STATUS 만 3초
- 한 번 실패하면 `TELEMETRY_ENABLE` 을 끈다 — 늦게 도착한 응답이 다음 명령의
  프레임을 오염시켜 `Invalid command packet header` 로 취득을 죽이는 것을 막는다

## 첫 실행 결과 (기록용 — 돌린 뒤 채운다)

```
날짜 :
유닛 :
데이터셋 :
결과 :
```
