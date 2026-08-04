# ICS 시뮬레이터 개발 노트 (DevNote)

> KMTNet 카메라 통합제어 프로그램 `ics_sim` — 설계 사양 · 판단 근거 · 조사 이력

---

## 0. 이 문서의 성격과 갱신 규칙

이 문서는 **사양서이면서 동시에 결정 기록이고 조사 이력**이다. "무엇을 만드는가"만이 아니라 **왜 그렇게 정했는지, 무엇을 측정해서 알아냈는지, 무엇을 도중에 정정했는지**를 함께 남긴다. 레거시 ICS 는 1998년 ICIMACS 에서 출발해 25년 넘게 운용된 시스템이고, 그 동작의 상당 부분은 문서가 아니라 **로그와 소스에만** 남아 있다. 같은 조사를 두 번 하지 않으려면 과정을 적어 두는 편이 낫다.

- 코드가 바뀌면 이 문서도 같이 바꾼다. 특히 3장(OBSAgent 규약)과 7장(설정)은 코드와 1:1로 대응한다.
- 12장(정정 이력)에는 **틀렸다가 바로잡은 것**을 남긴다. 지우지 않는다 — 왜 그렇게 착각했는지가 다음 사람에게 유용하다.
- 절 번호는 코드 주석이 참조한다. 번호를 바꾸면 주석도 같이 고친다.

**관련 문서**

| 문서 | 내용 |
|---|---|
| [`../ics_legacy/ics_legacy_report.md`](../ics_legacy/ics_legacy_report.md) | 레거시 ICS/XIS 전체 분석. IMPv2.5 프로토콜, 명령어, 실측 트랜잭션 |
| [`../ics_legacy/icg_legacy_report.md`](../ics_legacy/icg_legacy_report.md) | 가이드 채널(ICG) 전용 분석 |
| [`../OBSAgent/obsagent_report.md`](../OBSAgent/obsagent_report.md) | 관측자 콘솔(OBS Agent) 분석 — CamStatus 상태머신 |
| [`../TCSAgent/tcsagent_report.md`](../TCSAgent/tcsagent_report.md) | 망원경 제어 브리지(TC) 분석 |
| [`README.md`](README.md) | 설치·실행 방법 |

---

## 1. 목적과 로드맵

### 1.1 왜 만드는가

레거시 조사는 끝났고 신규 Python `ics`/`icg` 의 구조도 확정됐다. 그런데 **신규 `ics` 가 반드시 지켜야 할 OBSAgent 호환 규약**(`ics_legacy_report.md` 8.0.1절)은 소스를 정독해 도출한 것일 뿐 **한 번도 실행으로 검증된 적이 없었다**. 카메라 하드웨어가 없으면 검증할 방법도 없었다.

`ics_sim` 은 그 간극을 메운다.

- **바깥으로는** 레거시 ICS 와 호환되는 메시지를 낸다 → 하드웨어 없이 실제 OBSAgent·GMON 을 물려 규약을 실증할 수 있다.
- **안으로는** 확정된 신규 구조(`ICS` + `K/M/T/N.IC` + `K/M/T/N.CB` = 9노드 통합)로 짠다.
- **레거시의 메시지 오염 버그는 재현하지 않는다**(5장). 시뮬이 그 버그의 부재를 스스로 증명한다.

### 1.2 로드맵

| 단계 | 산출물 | 완료 기준 | 상태 |
|---|---|---|---|
| **1. 시뮬레이터** | `ics_sim` (이 단계) | 전체 노출 사이클이 OBSAgent 규약 테스트를 통과<br>골든 대조에서 레거시 시퀀스와 일치<br>메시지 오염 0건 | **완료** |
| **2. 실기 구동** | `hardware/archon.py` 구현 | 실제 CCD 로 영상 획득 → FITS 저장<br>시퀀서·명령 처리부·메시지 규약은 **무개정** | 예정 (9장) |
| **3. 운영 전환** | `ics` 로 개명·배포 | 실제 XIS 허브에 물려 OBSAgent 와 야간 관측 | 예정 |

2단계에서 시퀀서를 고칠 일이 없도록 처음부터 **하드웨어 추상화 계층**을 뒀다(9장). `[hardware] backend = sim | archon` 한 줄로 전환한다.

### 1.3 범위

**대상**: ICS 만. 과학 CCD 4대(K/M/T/N)의 통합 제어.

**범위 밖**: XIS 허브 · TC 스텁 · OBS 드라이버 · ICG/ABC 가이드 계통 · 시리얼 트랜스포트. 이유는 15장.

---

## 2. 조사 방법과 근거

### 2.1 무엇을 근거로 삼았나

| 자료 | 규모 | 커밋 여부 | 용도 |
|---|---|---|---|
| `OBSAgent/OBSAgent.latest/KMTObs/{commands.c, main.c, obstool.h}` | ~450KB C 소스 | 커밋됨 | **OBSAgent 규약의 1차 출처.** 행 번호까지 인용 |
| `ics_legacy/__sample_isislog/` | 9개월 × 3사이트, ~4GB | `*.log` 비커밋 | 노출 사이클 실측, 골든 픽스처 원본 |
| `ics_legacy/__sample_isislog/samples_for_bug.txt` | 2,755행 | **커밋 대상** | 사용자가 직접 추린 오염 버그 샘플 |
| `…/samples_for_bug_integrat.txt` | 3,061행 | **커밋 대상** | 노출 국면(`INTEGRATING`)·카운트다운 구간 발췌. 3.2.2 와 5.1 의 근거 |
| `…/samples_for_bug_pctread.txt` | 2,940행 | **커밋 대상** | readout 진행률 발췌(노출 294회분). 7장 `[readout]` 모델의 근거 |
| `__localonly_isislogs/ISIS.ICSci.{CTIO,SAAO,SSO}.*` | **48GB, 1,113일분** | `__localonly_*` 비커밋 | 전량 스캔 — 샘플에 없던 시퀀스 발굴 |
| `ics_legacy/__dts_legacy/dts.icsci.*/` | 2,800 파일 / 24.7 MB | **커밋됨** | icsci 서버 `dts` 백업에서 소스·설정만 선별. **ISIS/XIS 서버 소스**(`EXEC_ISIS/server/`)가 12.9 의 등록 방식 확정 근거 |
| `__localonly_osc_legacy/` | 10,291 파일 / 16.6 GB | `__localonly_*` 비커밋 | 위 백업의 원본 전량 + **`IC2.img` 2개(CTIO/SAAO, 각 8 GB)**. VDOS IC 실행파일이 들어 있어 5장 오염 버그의 코드 위치를 확정할 수 있는 유일한 자료 |

전량 스캔 내역: CTIO 634일 28GB (2024-01-01 ~ 2025-09-30) / SAAO 273일 11GB (2025) / SSO 206일 8.6GB (2024-01-01 ~ 2024-07-25).

### 2.2 재현 방법

원본 로그가 있는 컴퓨터에서 `tools/scan_legacy_logs.py` 로 언제든 재검증할 수 있다.

```bash
# 커맨드워드 슬롯 분류 -- 오염의 직접 증거 (5장)
python tools/scan_legacy_logs.py slots  <logdir> -o slots.txt

# 메시지 형태 목록 -- 두 스캔을 diff 하면 새 시퀀스가 드러난다 (6장)
python tools/scan_legacy_logs.py shapes <logdir> -o shapes.txt

# OBSAgent CamStatus 재생 -- 상태 전이 실측 (3.2.1)
python tools/scan_legacy_logs.py camstatus <logdir>

# 오염 패턴만 추려 테스트 픽스처로 (8장)
python tools/scan_legacy_logs.py patterns <logdir> -o tests/fixtures/bug_patterns.txt
```

골든 픽스처 생성:

```bash
python tools/extract_golden.py <logfile> \
    --start 2024-03-03T22:22:15 --end 2024-03-03T22:25:05 \
    -o tests/fixtures/golden_dark_ctio_20240303.txt

python tools/extract_golden.py <logfile> \
    --around 'Image 1 of 5 complete' --before 120 --after 2000 \
    -o tests/fixtures/golden_gon5_ctio_20240102.txt
```

**`IC2.img` 에서 ICS 소스 꺼내기 (5.5·6.8·6.9 의 근거)**

이미지는 raw MBR + FAT32 단일 파티션(LBA 63)이라 **마운트도 관리자 권한도 필요 없다.** 7-Zip 이 MBR → FAT 를 자동으로 파고든다:

```bash
# 안에 뭐가 있는지 (22,000행 남짓)
7z l "__localonly_osc_legacy/IC2_KX20160323.1381_ICSci_CTIO/IC2.img"

# 소스 트리만 꺼낸다 -- 8GB 이미지지만 0.3초, 31MB
7z x "…/IC2.img" -o<대상> -y -r \
   'FREEBASI\KMTX\*' 'FREEBASI\SHARE\*' 'FREEBASI\KMTS\*' 'FREEBASI\KMTG\*'
```

읽어야 할 것은 `KMTX\PAP7KX.{BAS,CMD,CCD}` 와 `SHARE\PAP7{.INC,COM.INC,.CMD,.DEC}` 다. `PAP3`~`PAP7` 세대가 모두 남아 있으니 **버전 간 diff 로 개정 의도**도 볼 수 있다. 배포 빌드는 `PAP7` — `PAP7KX.EXE` 타임스탬프(2016-03-23 18:59)가 이미지 이름·로그의 `ICSBUILD=KX2016-03-23:1381` 과 일치하는 것으로 확인했다.

> **주의**: 소스는 `__localonly_*` 안에 있으므로 **커밋 대상이 아니다.** 문서에는 인용과 행 번호만 남긴다. 다른 컴퓨터에서 확인하려면 위 절차로 다시 꺼내면 된다.

### 2.3 자료 취급 규약

- `__localonly_*` 로 시작하는 폴더는 **git 에 올리지 않는다**(사용자 규약).
- `*.log` 는 `.gitignore` 로 제외된다.
- 따라서 **발췌본(`tests/fixtures/golden_*.txt`, `bug_patterns.txt`)을 커밋**해 원본 없는 환경에서도 테스트가 돈다. 8장 참고.

---

## 3. OBSAgent 인터페이스 규약

근거: `commands.c` `SocketCommand()` 748~1021행, ICS 명령 핸들러 1889~2098행, 기본값 7236~7250행; `main.c` 650~708행.

> **공백에 관하여**: 이 장의 예시는 로그 원문이라 공백 개수가 들쭉날쭉하다. 수신측(ISISclient·OBSAgent 모두)은 공백을 토큰 구분자로만 쓰고 개수는 무시하므로 **기능적 의미가 없다**. 실제 제약은 `Acquisition Complete.` 의 **마침표**, `" STATUS"` 의 **앞 공백 1개 이상**, `Filename=` / `KMTN…` 의 **문자 위치**뿐이다.

### 3.1 수신 — 9개 노드 ID 전부로 등록해야 한다

OBSAgent 는 명령마다 수신 노드를 달리 지정한다:

| OBSAgent 명령 | 보내는 곳 | 메시지 | 소스 |
|---|---|---|---|
| `status` | `ICS` | `STATUS` | 2015행 |
| `acqstatus` · `filename` · `expnum`<br>`ledflash` · `observer` · `projid`<br>`object` · `bias` · `dark` · `flat`<br>`sky` · `domeflat` · `standard` | `ICS` | `<CMD> <args>` | 1889 `cmd_ics` |
| `exp` | `ICS` | `EXP <x>` | 1939 `cmd_ics_exp` |
| `go` | `ICS` | `GO <n>` | 1915 `cmd_ics_go` |
| `kstatus` · `mstatus` · `tstatus` · `nstatus` | `K.IC` · `M.IC` · `T.IC` · `N.IC` | `STATUS` | 2015~2080 |
| `dmawait` | `K.IC` | `DMAWAIT <n>` | 1968 |
| `datasource` | `K.IC` · `M.IC` · `T.IC` · `N.IC` (4회) | `DATASOURCE <adc\|ctc>` | 1987 |
| `gstatus` | `G.IC` | `STATUS` | 2087 (범위 밖 — 무응답) |

→ **`ICS` 하나로만 등록하면 `kstatus`/`dmawait`/`datasource` 가 도달조차 하지 않는다.**

반대로 **발신** 쪽은 자유롭다. 3.2 의 CamStatus 필터는 발신자가 `ICS` / `{K,M,T,N}.IC` / `{K,M,T,N}.CB` 중 하나이기만 하면 통과시키므로, 통합 노드가 전부 `ICS` 이름으로 보내도 된다.

> **이 수신/발신 비대칭이 기존 8.0.1절에 빠져 있었다.** (1)항이 "발신은 전부 ICS 여도 OK" 만 서술하고 수신 쪽을 다루지 않았다.

구현: [`ics_sim/nodes.py`](ics_sim/nodes.py) `NodeRouter`. 검증: `test_obsagent_contract.py::test_per_node_commands_are_received`.

**미상 노드**: `CHA`(6.3) 처럼 문서에 없는 노드에서 오는 명령도 프로토콜 그대로 처리하고 요청자에게 응답한다. 발신자 화이트리스트를 두지 않는다 — IMPv2 에 노드 인증 개념이 없고 레거시도 그랬다.

### 3.1.1 XIS 노드 등록 — 1안/2안과 미해결 질문

> **상태 (2026-08-04): 1안으로 구현·커밋. XIS 서버 소스를 확보하면 재검토한다.**
>
> 이 절은 결론만이 아니라 **어떻게 여기까지 왔는지**를 남긴다. 중간에 내가 근거 없이 단언한 지점이 있었고 사용자가 그걸 짚어서 바로잡았다. 같은 착각을 반복하지 않으려면 과정이 필요하다.

#### (1) 문제 발견 — 수신 9노드를 절반만 구현했다

3.1절에서 "수신은 9개 노드 ID 전부"라고 정해 놓고, 코드는 절반만 하고 있었다. `NodeRouter` 는 9개 ID를 내부 라우팅했지만 기동 시 발신하는 건 **`ICS>AL PING` 한 줄뿐**이었다.

IMPv2에는 등록 API가 없다. 노드가 **자기 이름으로** 아무 메시지나 보내면 XIS가 "노드ID → 그 데이터그램의 (IP,port)"를 기억하는 것이 전부다(`ics_legacy_report.md` 1.2절). 따라서 `ICS` 이름으로만 보내면 XIS는 `ICS` 하나만 안다. 결과:

- `OBS>K.IC STATUS`(kstatus), `OBS>K.IC DMAWAIT`, `OBS>*.IC DATASOURCE` → XIS가 `K.IC` 를 모르니 **라우팅 실패**
- `emit_node_mode=legacy` 면 첫 노출 때 `K.IC>ICS DONE: …` 가 나가면서 그제야 등록 → **기동 직후~첫 노출 전에는 안 됨**
- `emit_node_mode=merged` 면 모든 발신이 `ICS` 이름이라 **영영 등록 안 됨**

**테스트가 이걸 못 잡은 이유**: 테스트는 `transport.feed()` 로 메시지를 직접 주입해 **XIS 라우팅 단계를 통째로 건너뛴다.** direct-reply 모드(기본)에서도 상대가 우리 주소로 직접 쏘므로 드러나지 않는다. **XIS 경유 모드로 바꾸는 순간에만 드러나는 종류의 결함**이다.

#### (2) 근거 없는 단언과 그 정정

처음에 나는 해법으로 *"9개 ID 각각 PING을 보내면 된다. XIS는 노드ID→주소 매핑이라 9개가 같은 주소를 가리켜도 문제없다"* 고 했다. **근거가 부족한 단언이었다.**

사용자가 곧바로 물었다 — *"XIS가 동일 IP와 포트로 들어온 ping에 잘 대응할 수 있을까? 동일 IP/port의 노드는 ID가 덮어씌워지는 것은 아닐까?"* 매핑이 반대 방향((IP,port) → 노드ID)이면 나중 등록이 앞 등록을 덮어쓴다. 타당한 지적이다.

#### (3) 로그 실측 — 방향은 확인됐다

CTIO 하루치 로그에서 노드별 주소 사용을 집계했다:

| 노드 | 대표 주소 | 사용한 주소 개수 |
|---|---|---:|
| `K.IC` | 192.168.14.102:6600 | 1 |
| `K.CB` | 192.168.14.102:**10601** | 1 |
| `ICG` | 192.168.14.108:6600 | 1 |
| `TC` | 192.168.14.108:**6606** | 1 |
| `OBS` | 192.168.14.109:6650 | 1 |
| `ICS` | `/dev/ttyS0` | 1 |
| **`ABC`** | 192.168.14.108:39026 … | **4,077** |
| **`GMON`** | 192.168.14.108:42731 … | **8,134** |

**새로 확인된 사실 두 가지:**

**(a) `ABC`/`GMON` 은 포트를 고정하지 않는다.** 매 메시지를 ephemeral 포트로 보낸다 — 하루에 주소가 각각 4,077개, 8,134개다. 그런데도 `TC>'ABC DONE: goto focus and tip-tilt commanded`, `OBS>GMON DONE: CamStatus=…` 응답을 정상적으로 받는다.

→ **"지금 GMON이 어디 있지?"를 물을 수 있어야 가능한 일**이므로, XIS는 반드시 **노드ID → 주소** 방향 테이블을 갖고 매 수신마다 갱신한다. 이 방향은 확실하다. 주소→노드ID 만으로는 `dest=GMON` 을 어디로 보낼지 알 수 없다.

**(b) 그러나 동시에 같은 (IP,포트)를 쓴 노드는 48GB 어디에도 없다.** 같은 호스트에 있는 노드들도 전부 포트를 달리 쓴다 — `K.IC`:6600/`K.CB`:10601, `ICG`:6600/`TC`:6606. `ABC`/`GMON` 이 같은 포트 번호로 잡히는 사례가 다수 있지만 그건 **시간차 재사용**이지 동시 점유가 아니다.

> 레거시에서 `K.IC`~`N.IC` 가 전부 6600을 쓸 수 있었던 것은 **각자 다른 호스트**에 있었기 때문이다(.102/.103/.104/.105). 시뮬은 한 호스트라 같은 방식을 쓸 수 없다.

#### (4) XIS 등록 로그 — 테이블은 노드 ID로 키잉된다 (2026-08-04 추가 확인)

XIS는 클라이언트를 등록할 때 로그를 남긴다. 이걸 놓치고 있었다:

```
2025-04-02T23:30:56.783833 [192.168.14.102:10601] K.CB>XIS PONG
2025-04-02T23:30:56.783850 Added UDP Client K.CB on host 192.168.14.102:10601
```

CTIO 60일치에서 `Added UDP Client` 99건을 분석한 결과:

| 노드 | 등록 횟수 | 등록에 쓰인 주소 개수 |
|---|---:|---:|
| `K.IC`·`M.IC`·`T.IC`·`N.IC`·`*.CB`·`ICG`·`G.IC`·`TC`·`OBS` (고정 포트) | 각 6 | 각 **1** |
| `ABC`·`GMON` (ephemeral 포트) | 각 7 | 각 **7** |

**결정적 관찰**: `ABC`/`GMON` 은 하루에 수천 개 주소를 쓰는데 `Added` 는 **7번뿐**이고, 그 횟수가 XIS 재시작 횟수와 같다.

→ **XIS는 이미 아는 ID면 주소만 조용히 갱신하고, 처음 보는 ID일 때만 `Added` 를 남긴다.** 테이블이 **주소**로 키잉돼 있었다면 `ABC`/`GMON` 이 포트를 바꿀 때마다(하루 수천 번) `Added` 가 떴어야 한다. 그러지 않는다는 것은 **테이블이 노드 ID로 키잉된다**는 강력한 증거다.

또한 `Added UDP Client` 99건 중 **같은 (IP,port)에 서로 다른 ID가 등록된 사례는 0건**이다 — (3)절 관찰의 재확인.

**부수 관찰**
- **`ICS` 는 `Added UDP Client` 목록에 없다.** 시리얼이라 UDP 클라이언트가 아니기 때문이다. 우리 시뮬은 `ICS` 를 **UDP로** 등록하는데, 실제 XIS가 한 번도 겪어본 적 없는 구성이다.
- 등록 직후 `XIS>GMON ERROR: No Route to Destination Host OBS` 가 뜬다 — 재시작 후 `OBS` 가 아직 재등록 전이라 GMON 폴링이 실패한 것이다. `OBS` 는 XIS에 PING을 하루 2회밖에 안 보내므로 **실제 운영에 이 공백이 존재한다.**
- `Added` 를 유발한 직전 메시지는 PONG이 대부분이지만 `gmon>obs sysstatus`, `abc>tc fttgoto` 같은 **평범한 명령도 등록을 유발**한다. 등록에 특별한 메시지가 필요하지 않다는 뜻이다.

#### (5) 남은 불확실성

(4)로 위험도는 상당히 낮아졌지만 **완전한 증명은 아니다.**

- "테이블이 ID로 키잉된다"와 "같은 주소를 여러 ID가 공유해도 된다"는 **별개 명제**다. 등록 시 같은 주소의 기존 항목을 정리하는 로직이 따로 있을 가능성을 배제할 수 없다.
- **XIS 서버 소스가 저장소에 없다.** 있는 건 클라이언트 라이브러리(`ISISclient`)뿐이다.
- **실제 배치에서 한 번도 시험된 적 없는 구성**이라는 사실은 그대로다.

> 에러 문구의 `host is unknown/**unlisted**` 를 보고 "XIS에 정적 호스트 목록이 있을지 모른다"고 우려했으나, (4)의 `Added UDP Client` 로그가 **동적 등록**임을 보여준다. "unlisted" 는 그 동적 목록에 없다는 뜻으로 읽는 것이 자연스럽다. 정적 설정 파일 우려는 낮춰도 될 것 같다 — 다만 소스로 최종 확인한다.

#### (6) 1안 / 2안

| | **1안 — 단일 소켓** | **2안 — 노드별 소켓** |
|---|---|---|
| UDP 소켓 | 1개 (`bind_port`) | 9개 (노드마다 포트 하나) |
| 등록 | 9개 ID로 PING을 **같은 포트에서** 발신 | 각 노드가 **자기 포트에서** 자기 이름으로 PING |
| XIS 호환성 | **미검증** — 같은 (IP,port)에 9개 ID | **보장** — 레거시 배치와 동일 구조 |
| 구현 비용 | 낮음 (현재 구조 그대로) | 중간 (`UdpEndpoint` 9개, 발신 시 소켓 선택) |
| 설정 부담 | 포트 1개 | 포트 9개 배정 필요 |

2안의 포트 배정안(레거시 관례를 한 호스트에 맞춰 편 것):

```
ICS   6600
K.IC  6601   M.IC  6602   T.IC  6603   N.IC  6604
K.CB 10601   M.CB 10602   T.CB 10603   N.CB 10604
```

#### (7) 결정 — 일단 1안, XIS 소스 확보 후 재검토

**사용자 결정 (2026-08-04)**: ISIS/XIS 소스를 찾아 공유하기로 했고, 그때까지는 **1안으로 완성해 커밋**한다.

구현:
- `Emitter.register_ping(node_id)` — src를 그대로 지정한다. **`emit_node_mode` 를 따르지 않는다** — merged는 *발신 이름*만 통일하는 옵션이고 수신은 언제나 9개여야 하기 때문이다.
- `IcsSim.register()` — `router.registered_ids` 9개 전부로 PING.
- `[transport] register_all_nodes` (기본 `true`) — 끄면 `ICS` 만 등록하고 경고를 낸다. XIS가 다중 등록을 거부하는 것으로 밝혀졌을 때의 임시 탈출구이지만, **그 상태로는 개별 IC 명령을 받을 수 없다.**

검증: `test_startup_registers_all_nine_nodes` · `test_registration_ignores_emit_node_mode`(legacy/merged 양쪽) · `test_register_all_nodes_false_only_registers_ics`.

#### (8) 2안으로 전환해야 하는 조건

아래 중 하나라도 확인되면 2안으로 간다.

1. **XIS 소스 확인 결과** 클라이언트 테이블이 주소로 인덱싱되거나, 등록 시 같은 주소의 기존 항목을 제거한다.
2. **실물 시험에서** 9개 PING 후 `OBS>K.IC STATUS` 가 도달하지 않는다. 가장 빠른 확인법 — XIS를 띄우고 시뮬을 `--xis-host` 로 붙인 뒤 `kstatus` 를 쳐 본다.
3. XIS 로그에 등록 교체/거부를 시사하는 메시지가 남는다.

**XIS 소스를 받으면 확인할 것** (우선순위 순)

1. **노드 목록이 정적 설정인가 동적 등록인가** — 에러 문구의 `host is unknown/**unlisted**` 가 목록의 존재를 시사한다(아래 (9)절). 설정 파일 기반이라면 시뮬을 **그 목록에 추가**해야 하고 PING만으로는 부족하다. **1안/2안보다 근본적인 문제이므로 이것부터 본다.**
2. **클라이언트 테이블의 인덱스 키** — 노드ID인지, (IP,port)인지, 둘 다인지
3. **같은 주소로 다른 ID가 등록될 때의 처리** — 추가인가, 교체인가, 거부인가
4. **재시작 시 등록 요청의 정확한 형태** — (9)절에서 "PING을 뿌린 뒤 로그를 연다"는 순서까지는 확인됐다. 남은 것은 그것이 `AL` 브로드캐스트 한 방인지 알려진 노드들에 개별 PING인지, 그리고 재시작 직후 XIS의 테이블이 비어 있을 텐데 **누구에게** 보내는지다(= 어딘가에 노드 목록이 있다는 뜻일 수 있다)
5. **테이블 최대 크기** — 9개를 더 얹을 여유가 있는지
6. **`AL`/`ALL` 브로드캐스트가 같은 주소의 여러 ID에게 어떻게 나가는지** — 우리 소켓이 하나뿐이라 같은 메시지를 9번 받을 수 있다

마지막 항목은 1안 고유의 부작용이라 실물 시험 때 반드시 같이 볼 것. 지금 코드는 브로드캐스트를 `ICS` 가 대표로 처리하므로(`NodeRouter.resolve`) 중복 수신이 와도 9번 응답하지는 않지만, 수신 트래픽은 9배가 된다.

#### (9) XIS 재시작 시의 재등록 — 실측 (2026-08-04)

*"XIS가 재실행될 때 아마도 `>AL ping` 할 것 같은데"* 라는 가설을 로그로 확인했다. **맞다.**

샘플 로그에서 **하루 중간에 XIS가 재시작한 사례 16건**을 찾았고, 16건 전부 같은 패턴이다:

```
XIS runtime log (re)started at UTC 2024-09-02T06:18:00.059046
  TC>XIS PONG     M.CB>XIS PONG   G.CB>XIS PONG   K.CB>XIS PONG
  N.CB>XIS PONG   T.CB>XIS PONG   ICG>XIS PONG    N.IC>XIS PONG
  K.IC>XIS PONG   T.IC>XIS PONG   M.IC>XIS PONG   G.IC>XIS PONG
```

**재시작 직후 12개 노드가 전부 `>XIS PONG` 을 보낸다.** PONG은 PING에 대한 응답이므로 XIS가 재시작하면서 등록 요청을 뿌렸다는 뜻이다.

**PING은 로그를 열기 전에 나간다 (확인됨).** 로그에 `XIS>AL PING` 이 찍혀 있지 않다 — 샘플 전체에서 **XIS 발신 PING이 로그에 남은 횟수 0**이다. XIS의 다른 발신은 잘 남는데(`XIS>K.IC PONG` 28,457건) 그 PING만 없다.

로그 재시작을 **첫 로그 항목** 기준으로 분류하면 성격이 갈린다:

| 첫 로그 항목 | 건수 | 정체 |
|---|---:|---|
| `K.CB>K.IC REQ INITDISK` | 48 | 시스템 전체 콜드 스타트 — 디스크 초기화가 먼저 |
| `TC>AL ping` | 33 | 시스템 전체 기동 — TC의 브로드캐스트가 첫 트래픽 |
| `OBS>TC TSTAT` 등 (PONG 0건) | 17 | **정오 정각 로그 로테이션** — XIS는 계속 실행 중 |
| **`*.CB>XIS PONG` · `TC>XIS PONG`** | **약 12** | **XIS 단독 재시작** |

마지막 부류가 결정적이다. XIS 단독 재시작에서는 **로그의 맨 첫 줄이 노드의 PONG**이고, 재시작 타임스탬프로부터 **1~1.5 ms** 후다:

```
XIS runtime log (re)started at UTC 2025-04-02T23:30:56.782917
2025-04-02T23:30:56.783833  K.CB>XIS PONG      ← 0.9 ms 후, 로그의 첫 항목
2025-04-02T23:30:56.783850  Added UDP Client K.CB on host 192.168.14.102:10601
```

PING이 로그에 없는데 PONG이 1 ms 안에 도착하는 것으로 보아 PING이 확실히 나갔다. **왜 로그에 없는지는 (12)④에서 소스로 확인했다** — `handShake()` 가 `write()`/`sendto()` 를 직접 호출하고 `logMessage()` 를 거치지 않기 때문이다. **XIS는 자신이 보내는 handshake PING을 로깅하지 않는다.**

> **정정**: 처음에는 "로그 파일을 열기 전에 보냈을 것"으로 추론했으나 **틀렸다.** `main.c` 의 실제 순서는
> `loadConfig() → openSocket() → initLog() → 메인 루프 진입 → doStartup=COLD_START → handShake()`
> 로, **로그가 먼저 열린다.** 12.9절 참고.

**여기서 따라나온 질문 — 테이블이 비었는데 누구에게 보내나?**

재시작 직후 XIS의 클라이언트 테이블은 비어 있다((4)절의 `Added UDP Client` 가 그 뒤에 찍히는 것이 근거다). 그런데도 PING이 모든 노드에 닿는다. 당시 두 가설을 세웠다 — (a) IP 서브넷 브로드캐스트, (b) 어딘가에 노드 목록이 있다.

**(b)가 맞았다.** `isis.ini` 의 preset UDP 목록(`UDPPort <ip> <port>`)에 개별 `sendto` 한다((12)④⑦). IP 브로드캐스트가 아니므로 `bind_host` 가 `127.0.0.1` 이어도 **그 자체로 PING을 놓치지는 않는다** — 다만 외부 장비와 통신하려면 어차피 `0.0.0.0` 이 필요하다.

**평시 재등록 경로도 두 가지 더 있다:**

| 경로 | 빈도 (CTIO 하루) | 성격 |
|---|---|---|
| `TC>AL ping` → 전 노드가 `>TC PONG` | 138회 (전체 샘플) | TC 기동 시. 브로드캐스트 한 번에 11개 노드가 각자 이름으로 응답 |
| `*.IC>XIS PING` → `XIS>*.IC PONG` | 노출당 1회 (K.IC 191, M/T/N.IC 각 189) | 원래 목적은 디스크 쓰기 완료 타이밍 신호(4.1절)지만, **부수 효과로 매 노출마다 등록이 갱신된다** |

즉 레거시는 **노출을 한 번만 해도 스스로 복구**됐다. 우리 시뮬은 통합 구조라 그 PING/PONG 편법이 불필요해 뺐고, 그러면서 **자동 복구 효과도 같이 잃었다.**

**우리 시뮬의 현재 동작 (실측)**

| 받은 메시지 | 시뮬 응답 |
|---|---|
| `XIS>AL PING` | `ICS>XIS PONG` — **1개뿐** |
| `TC>AL ping` | `ICS>TC PONG` — **1개뿐** |

브로드캐스트를 `ICS` 가 대표로 처리하도록 만들어서(`NodeRouter.resolve` 가 `AL` → `ICS`) **XIS 재시작 후 `ICS` 하나만 재등록되고 나머지 8개는 영영 돌아오지 않는다.** 레거시는 노드마다 프로세스가 따로라 각자 PONG을 보냈기에 문제가 없었다.

**→ 고쳐야 할 사항 (미착수)**
1. **브로드캐스트 PING에는 9개 노드 전부로 PONG** — 레거시와 동일한 동작.
2. **주기적 재등록** (`register_interval_sec`) — XIS가 조용히 재시작하고 아무도 브로드캐스트를 안 쏘는 경우(주간 대기 시간 등)를 위한 안전망. 레거시는 노출당 PING이 이 역할을 했다.

#### (10) 라우팅 실패는 에러로 통보된다 — 실물 시험의 판정 기준

```
XIS>OBS  ERROR: No Route to Destination Host K.IC - host is unknown/unlisted
XIS>GMON ERROR: No Route to Destination Host OBS  - host is unknown/unlisted
XIS>ICG  ERROR: No Route to Destination Host G.IC - host is unknown/unlisted
```

등록되지 않은 노드로 메시지를 보내면 **발신자에게** 이 에러가 돌아온다. 실물 시험의 판정이 명확해진다 — 9개 PING 후 `kstatus` 를 쳤을 때 `No Route to Destination Host K.IC` 가 오면 등록 실패다.

> **"unknown/`unlisted`" 라는 단어에 주의.** "unlisted"는 XIS가 **호스트 목록을 갖고 있다**는 뉘앙스다. 순수 동적 등록이 아니라 **설정 파일에 노드 목록이 있을 가능성**이 있고, 그렇다면 시뮬을 그 목록에 **등록해 주어야** 하며 PING만으로는 부족할 수 있다. **1안/2안보다 더 근본적인 문제**이므로 소스 확인 시 최우선으로 볼 것.

> 부수 관찰: 목적지가 깨진 사례도 있다 — `No Route to Destination Host 0<0xef><0xbf><0xbd>ICG`, `Host <0xef><0xbf><0xbd>ZY´ZY<0xef><0xbf><0xbd>`. 5.6.3절의 전송 손상이 라우팅 실패로 드러난 것이다.

#### (12) **XIS 서버 소스 확인 — 결론** (2026-08-04)

사용자가 `ics_legacy/__dts_legacy/` 에 **ICS 컴퓨터(icsci 서버)의 `dts` 폴더 백업**을 3개 사이트분 올려 주었다. `EXEC_ISIS/server/` 에 **XIS 서버 소스 전체**가 들어 있다 — `clients.c` · `messages.c` · `interfaces.c` · `main.c` · `loadconfig.c` · `xisisserver.h`. (클라이언트 라이브러리는 `TCSAgent/__reference/ISISclient` 와 `OBSAgent/OBSAgent.latest/ISISclient` 에도 있다.)

**(8)절의 6개 질문에 전부 답이 나왔다.**

##### ① 정적 목록인가 동적 등록인가 → **둘 다, 역할이 다르다**

- **클라이언트 테이블은 완전 동적**이다. `updateHosts()` 가 메시지를 받을 때마다 호출되어 등록/갱신한다. 정적 화이트리스트는 없다.
- **다만 재시작 시 PING을 뿌릴 대상은 `isis.ini` 의 preset 목록**(`UDPPort <ip> <port>`)이다. 이 목록에 없으면 XIS 재시작 시 PING을 받지 못한다.

→ (10)절의 `host is unknown/**unlisted**` 는 **동적 목록에 없다**는 뜻이 맞다. 정적 설정 파일 우려는 해소됐다.

##### ② 테이블 인덱스 키 → **노드 ID만. 주소는 비교에 쓰이지 않는다**

```c
// clients.c  updateHosts()
strcpy(testStr, hostID);
upperCase(testStr);                              // ID는 대문자로 정규화해 저장

if (isis.numClients > 0) {
  for (i=0; i<MAXCLIENTS; i++) {
    if (strcmp(testStr, clientTab[i].ID)==0) {   // ← ID로만 비교
      clientTab[i].method = method;
      clientTab[i].fd     = fd;
      clientTab[i].addr   = addr;                // ← 주소는 그냥 갱신
      clientTab[i].port   = port;
      clientTab[i].tstamp = timeStamp;
      return (i);
    }
  }
}
// 없으면 method==UNASSIGNED 인 첫 빈 슬롯에 새로 추가
```

(4)절에서 로그로 추론한 "ID로 키잉된다"가 소스로 확정됐다.

##### ③ 같은 주소에 여러 ID → **문제없다. 설계상 예상된 상황이다**

- 주소 충돌 검사 로직이 **아예 없다.** 각 ID가 자기 슬롯을 갖는다.
- 더 결정적인 것은 `messages.c` 의 클라이언트 브로드캐스트 주석이다:
  > *"it must pass along the message to all known hosts EXCEPT the sending host **and all clients that share the same port as the sending host**"*

  **여러 클라이언트가 한 포트를 공유하는 상황을 코드가 명시적으로 다룬다.** 예상 밖의 구성이 아니다.

→ **1안(단일 소켓 + 9개 ID PING)은 안전하다. 확정.** 2안으로 전환할 이유가 없어졌다.

##### ④ 재시작 시 등록 요청 → **`XIS>AL PING` 을 시리얼 + preset UDP 포트에 개별 전송**

```c
// interfaces.c  handShake()
//   "Sends a '>AL PING' message to all open serial ports and all preset
//    UDP ports. This is a blind broadcast that should lead to 'PONG's back
//    from any ISIS clients..."
sprintf(message,"%s>AL PING\r", isis.serverID);      // → "XIS>AL PING\r"
for (iPort=0; iPort<isis.numSerial; iPort++)  write(ttyTab[iPort].fd, message, ...);
for (iPort=0; iPort<isis.numPreset; iPort++)  sendto(..., udpTab[iPort], ...);
```

**사용자 가설이 소스로 확정됐다.** IP 서브넷 브로드캐스트가 아니라 **preset 목록에 개별 `sendto`** 다.

##### ⑤ 테이블 최대 크기 → **`MAXCLIENTS 64`**

현재 운용은 13개 안팎이다. 9개를 더 얹어도 여유가 충분하다. 초과 시 `ERR_HOSTS_FULL(-3)`.

##### ⑥ `AL` 브로드캐스트 중복 수신 → **9개 ID면 9번 받는다**

```c
// messages.c  broadcastMessage(), sendHost == ISIS_SERVER 인 경우
for (i=0; i<MAXCLIENTS; i++) {
  if (clientTab[i].method == SOCKET) {
    client.sin_addr.s_addr = htonl(clientTab[i].addr);
    client.sin_port        = htons(clientTab[i].port);
    sendto(isis.sockFD, message, ...);            // ← 슬롯마다 한 번씩
  }
}
```

슬롯 전수 순회이므로 우리 9개 ID가 같은 주소를 가리키면 **같은 데이터그램을 9번 받는다.** 기능상 문제는 없다 — 현재 코드는 브로드캐스트를 `ICS` 가 대표로 처리하므로(`NodeRouter.resolve`) 9번 응답하지 않는다. 다만 **수신 트래픽이 9배**이고, `XIS>AL PING` 에 대해서도 PONG을 한 번만 보내게 되어 있어 **재등록이 `ICS` 하나만 갱신된다**((9)절의 미착수 항목과 같은 문제).

##### ⑦ 함께 확정된 운영 설정 (CTIO `Config/isis.ini`)

```
ServerID   XIS
ServerPort 6660
ServerLog  /lhome/data/Logs/ISIS/isis
TTYPort /dev/ttyS0 115200          ← ICS↔XIS 시리얼 링크, 115200 baud

# Ping the isisrelays on all the IC machines
UDPPort 192.168.14.102 6600  …  .103 .104 .105 .106 .107 .108   (IC 계열 7줄)
# Ping the caliban data-transfer agents only as needed
UDPPort 192.168.14.102 10601 …  .103 .104 .105 .106            (CB 계열 5줄)
# Ping the PC-TCS Agent
UDPPort 192.168.14.108 6606                                     (TC 1줄)

Instrument KMTC
```

- **`.109`(OBS)가 preset 목록에 없다** → (10)절에서 본 `XIS>GMON ERROR: No Route to Destination Host OBS` 가 완전히 설명된다. OBS는 XIS 재시작 후 **자기가 먼저 메시지를 보내기 전까지** 등록되지 않는다. `OBS>XIS PING` 이 하루 2회뿐인 것과 맞물려 실제 공백이 생긴다.
- ICS의 시리얼 링크가 설정으로 확인된다 — `/dev/ttyS0` 115200 baud.

##### ⑧ 미해결로 남은 것 — `MAXPRESET` 불일치

`xisisserver.h` 와 `old_isisserver.h` 모두 `#define MAXPRESET 8` 인데 **CTIO `isis.ini` 에는 `UDPPort` 가 13줄**이고, `loadconfig.c` 는 초과분을 명시적으로 버린다:

```c
if (isis.numPreset == MAXPRESET) {
  printf("ERROR: Cannot define more than %d preset UDP socket ports\n", MAXPRESET);
  printf("       extra port ignored.\n");
}
```

8개만 반영된다면 9번째 이후(`M/T/N/G.CB`, `TC`)는 PING을 못 받아야 하는데, **재시작 로그에는 그들도 전부 PONG을 보낸다.** 즉 **배포된 `xisis` 바이너리는 이 백업 소스와 다른 `MAXPRESET` 으로 빌드됐을 가능성이 크다** — `isis.ini` 주석도 "max 32"라고 적혀 있다(헤더는 8).

→ 실물 연동 전에 XIS 콘솔에서 `info` 를 쳐 `NumPreset=? MaxPreset=?` 를 직접 확인할 것(`commands.c` 가 그 값을 출력한다). **우리 시뮬을 preset 목록에 추가할 여유가 있는지가 여기 달렸다.**

##### ⑨ 그래서 시뮬은 무엇을 해야 하나

| 항목 | 조치 | 상태 |
|---|---|---|
| 1안 유지 | 소스로 안전 확정. 2안 불필요 | **확정** |
| `bind_host = 0.0.0.0` | IP 브로드캐스트가 아니므로 필수는 아니지만, 외부 연동에는 여전히 필요 | 설정만 바꾸면 됨 |
| **`XIS>AL PING` 에 9개 PONG** | 브로드캐스트 PING 에 9개 노드 ID 전부로 PONG 응답 | **구현 완료 (2026-08-04)** |
| **XIS `isis.ini` 에 시뮬 등록** | `UDPPort <sim_ip> <sim_port>` 한 줄 추가. **1안이라 한 줄이면 된다**(2안이면 9줄 필요) | 운영 측 작업 |
| 주기적 재등록 | preset에 등록되면 필수는 아니나 안전망으로 유효 | 선택 |

구현: `commands.py` `cmd_ping()` 이 `msg.is_broadcast` 면 `router.registered_ids` 전부로 PONG 을 보낸다. 지목된 PING(`OBS>K.IC PING`)에는 그 노드로만 답한다.
검증: `test_broadcast_ping_answered_by_all_nine_nodes` · `test_directed_ping_answered_by_that_node_only`.

#### (13) 레거시 실제 배치 구조 — VDOS IC + 리눅스 relay (2026-08-04)

같은 백업의 설정 파일들로 **로그만으로는 보이지 않던 물리 구조**가 드러났다. 상세는 [`../ics_legacy/ics_legacy_report.md`](../ics_legacy/ics_legacy_report.md) 1.3.1절이고, 신규 설계에 걸리는 부분만 옮긴다.

- **IC/ICS 는 VDOS(DOS 계열) 프로그램**이고, **리눅스 호스트 위의 KVM 게스트**에서 돈다(`IC2.img`, `/var/lib/libvirt/images`). 리눅스 `isisrelay` 가 UDP 6600 ↔ 가상 시리얼 9600 으로 중계한다. 로그의 `[192.168.14.102:6600] K.IC>XIS PONG` 은 **relay 가 게스트의 응답을 올려준 것**이다.
- **`TRANSFER DISK<n>` 의 디스크는 게스트에 붙인 가상 디스크**다. 1998년 SCSI 이중버퍼 패턴이 가상화 환경에 그대로 이식돼 살아남았다. 신규는 단일 PC 통합이라 이 계층 자체가 사라진다(6.2절).
- **`ICS` 는 IC 와 같은 소프트웨어다.** `INSTRUMENT=ICS` 로 설정만 다르고, 프로그램 디렉토리가 `\KMTX`(vs 과학 IC `\KMTS`, 가이드 `\KMTG`)일 뿐이다.
  → **5장 메시지 오염 버그가 `ICS` 와 `K.IC` 양쪽에 똑같이 나타나는 이유가 이것이다** — 같은 코드베이스의 단일 결함이다.
- **BUILD 접두어 = 프로그램 디렉토리**: `ICSBUILD=KX…`(\KMTX) · `KBUILD=KS…`(\KMTS) · `GBUILD=KG…`(\KMTG). 4.3절 텔레메트리 꼬리의 정체가 풀렸다.
- **`SP` 노드**(`INSTRUMENT=KMTNsp`, `\KMTS`)가 설정에 존재한다 — 과학 계열 **예비 IC** 로 보이며, XIS preset 의 `192.168.14.107 6600`(로그에 트래픽 0) 자리로 판단된다.

> **신규 설계 함의**: 신규 `ics` 는 이 3계층(VDOS IC + relay + 통합 제어)을 **한 프로그램으로 대체**한다. relay 계층과 시리얼 구간이 통째로 사라지므로 5.3절의 전송 손상도 함께 사라진다. **XIS 입장에서는 relay 가 있던 자리에 신규 `ics` 가 들어오는 것으로 보여야 한다** — 그래서 (12)의 등록 규약이 중요하다.
>
> **IC(VDOS) 본체 소스는 이 백업에 없다.** 백업이 리눅스 측(icsci 서버)이라 XIS 서버·relay·Caliban 소스는 있으나 `\KMTS`/`\KMTX`/`\KMTG` 프로그램은 빠져 있다. 5장 오염 버그의 **코드 위치는 여전히 미확인**이며 분석은 로그 실측 기반이다.
>
> **다만 디스크 이미지 자체는 확보됐다 (2026-08-04)** — `__localonly_osc_legacy/IC2_KX20160323.1381_ICSci_{CTIO,SAAO}/IC2.img`, 각 8 GB. 마운트해서 `\KMTX`(ICS) 디렉토리를 꺼내면 실행파일의 문자열·`printf` 포맷에서 오염 메커니즘을 직접 볼 수 있다. **16비트 DOS 바이너리 역어셈블은 실용적이지 않으므로 문자열/포맷 추출까지가 현실적인 선**이고, 그것만으로도 (a) 로그에 안 나온 메시지까지 포함한 완전한 카탈로그와 (b) 커맨드워드 슬롯이 어떻게 채워지는지를 얻을 수 있다. 두 사이트분이 있어 빌드 차이 비교도 가능하다.

> **1안의 부수 이점이 드러났다**: preset 목록은 (IP, port) 단위라 **단일 소켓이면 한 줄만 추가하면 되고**, 9개 ID가 모두 그 PING을 받아 PONG할 수 있다. 2안이었다면 `MAXPRESET` 을 9줄이나 잡아먹었을 것이고, ⑧의 제약을 감안하면 들어갈 자리가 없었을 수도 있다.

#### (11) 함께 확인된 포트 설정

| 키 | 현재 값 | 비고 |
|---|---|---|
| `bind_host` | `127.0.0.1` | **로컬 전용.** 외부 XIS/OBSAgent와 붙이려면 `0.0.0.0` 으로. XIS가 재시작 시 IP 서브넷 브로드캐스트로 PING을 뿌린다면((9)절) `0.0.0.0` 이 **필수**다 — 아니면 재등록 기회를 놓친다 |
| `bind_port` | `6600` | 레거시 IC 계열 관례 포트. 실제 배치의 ICS는 시리얼이라 정해진 UDP 포트가 없어 임의로 고른 값이다. **같은 호스트에 실제 `K.IC` 가 떠 있으면 충돌** |
| `xis_host` | (빈 값) | 비어 있어 **direct-reply 모드가 기본**. 이 모드에서는 (1)의 등록 문제가 드러나지 않는다 |
| `xis_port` | `6660` | CTIO 기준 (OBSAgent `ISISPort 6660`) |

### 3.2 CamStatus 상태머신 (commands.c 757~864)

**발신 노드 필터** (757~759행): 발신자가 `ICS` / `{K,M,T,N}.IC` / `{K,M,T,N}.CB` 중 하나(대소문자 무관)여야 처리한다. `ICG`/`G.IC`/`G.CB` 는 v0.3.2 부터 명시적으로 무시된다 — 가이드 계통이 같은 문자열을 뿌려도 과학 상태머신이 오염되지 않는 이유다.

**`strstr` if/else-if 체인 — 순서가 곧 우선순위**:

```
if  (EXPSTATUS=IDLE)          → IDLE_3, count_fitssaving=0, count_ready=0   [독립 if]
if  (Wrote)                   → ++count_wrote; 4회↑면 FitsSaved=1, FitsNum 파싱
elif(Acquisition Complete.)   → IDLE_1; ++count_acqcomp; 4회↑면 IDLE_2
elif(PCTREAD=)                → READ_1→READ_2→READ_3; count_acqcomp=0, count_wrote=0, FitsSaved=0
                                 ※ READ_1일 때 OBSAgent가 ICS로 'ExpNum'을 자동 발신 (3.4)
elif(EXPSTATUS=READOUT)       → READ_1; count_wrote=0, FitsSaved=0
elif(Shutter=Closed)          → CLOSING
elif(Remaining=)              → INT_3
elif(Shutter=Open)            → INT_2 (노출 시작 시각 기록, strCurNum←strNextNum)
elif(EXPSTATUS=INTEGRATING)   → INT_1
elif(EXPSTATUS=ERASE)         → PREP_E
elif(EXPSTATUS=INITIALIZING)  → PREP_I
```

**개수 규약**: `Acquisition Complete.`(**마침표 포함**) 4회 → `IDLE_2`, `Wrote` 4회 → `FitsSaved=1`. `PCTREAD=` 가 두 카운터를 리셋하므로 사이클 순서도 지켜야 한다.

**`FitsNum` 파싱** (776~784행): `Wrote` 본문에서 `"KMTN"` 위치 **+6 부터 15자**를 잘라 쓴다.

```
LASTFILE=/mnt/ICSData/KMTNk.20250902.057288.fits
                      ^KMTN     └──── 15자 ────┘
```
→ 파일명 `KMTN<ccd 1글자>.<8자리 날짜>.<6자리 번호>.fits` 형식이 **고정**이다. `"KMTN"` 이 없으면 `FitsNum=00000000.000000`, `FitsOsc=CHECK`.

구현: [`ics_sim/obsagent_model.py`](ics_sim/obsagent_model.py) 가 이 체인을 그대로 재현한다. 시뮬 검증과 로그 재생에 **같은 코드**를 쓴다.

#### 3.2.1 상태 전이는 선형이 아니다 (실측)

이 체인을 샘플 로그(3사이트 9개월, 노출 약 28,200회)에 재생해 전이를 집계했다. **OBSAgent 는 자기 앞으로 온 메시지만 보므로 `dest ∈ {OBS, AL, ALL}` 로 거른 결과다.**

| 전이 | 트리거 | 횟수 |
|---|---|---:|
| `PREP_I → PREP_E → INT_1` | `EXPSTATUS=ERASE` / `=INTEGRATING` | 28,217 |
| `INT_1 → INT_2` | `Shutter=Open` | 26,701 |
| `INT_2 → INT_3` | `Remaining=` | 26,706 |
| `INT_3 → CLOSING` | `Shutter=Closed` | 27,073 |
| `CLOSING → READ_1` | `EXPSTATUS=READOUT` | 28,194 |
| **`INT_1 → CLOSING`** (INT_2·INT_3 건너뜀) | `Shutter=Closed` | **1,252** |
| **`INT_1 → INT_3`** (INT_2 건너뜀) | `Remaining=` | **262** |
| **`INT_2 → CLOSING`** (INT_3 건너뜀) | `Shutter=Closed` | **91** |
| `INT_3 → INT_1` / `INT_2 → INT_1` (역행) | — | **0** |

**세 가지 결론**

1. **`Shutter=Closed Integration Remaining=0 sec.` 은 `Remaining=` 을 품고 있어도 체인 순서상 항상 `CLOSING` 이 된다.** 다만 그 앞의 순수 `Remaining=` 카운트다운이 이미 `INT_3` 을 만들어 두므로, `INT_2 → CLOSING` 직행은 26,797건 중 **91건(0.34%)** 에 그친다. 셔터를 열었지만 카운트다운이 한 번도 못 나간 초단시간 노출에 한한다.

2. **실제로 흔한 건너뜀은 `INT_1 → CLOSING`(1,252건)이다.** DARK/BIAS 는 셔터를 열지 않아 `Shutter=Open` 이 없고, 노출이 짧아 중간 카운트다운도 없어 `INT_2`·`INT_3` 을 통째로 건너뛴다. **DARK/BIAS 에서도 ICS 가 `Shutter=Closed Integration Remaining=0 sec.` 을 보내 주기 때문에** `CLOSING` 은 정상적으로 밟히고, 곧이어 `EXPSTATUS=READOUT`/`PCTREAD=` 가 `READ_1` 로 넘겨준다. 셔터를 연 적 없는데 "닫혔다"고 보고하는 셈이지만, **이 관례는 신규에서도 그대로 유지한다** — 없애면 `CLOSING` 을 못 밟는다.

3. **역행 전이는 0건이다.**

> **여기서 신규 설계 제약이 나온다.** 레거시가 `EXPSTATUS=` 를 담은 텔레메트리 중계를 마구 뿌려도 안전했던 이유는 **그것이 `OBS` 가 아니라 `*.IC` 앞으로 갔기 때문**이다. 신규 통합 `ics` 는 IC 들이 내부 객체가 되어 그 중계가 사라지는데, 편의상 그런 메시지를 **브로드캐스트(`AL`)하거나 `OBS` 로도 보내면 `CamStatus` 가 `INT_1` 으로 역행해 스크립트 관측이 깨진다.**
>
> → `EXPSTATUS=` 를 포함한 메시지는 **노출 상태가 실제로 전이한 시점에 정확히 1회씩만, `OBS` 로만** 보낸다.
>
> 검증: `test_obsagent_contract.py::test_no_backward_transitions`, `test_emitter_hygiene.py::test_expstatus_only_goes_to_obs`.

#### 3.2.2 셔터가 닫힌 뒤의 `EXPSTATUS=INTEGRATING` 반복 — 제거 대상

실측(`samples_for_bug.txt`)에서 노출마다 아래가 반복된다:

```
10:39:46  ICS>OBS STATUS:  STATUS: EXPSTATUS=INTEGRATING
10:39:52  ICS>OBS STATUS:   Shutter=Closed Integration Remaining=0 sec. EXPSTATUS=INTEGRATING
10:40:43  ICS>OBS STATUS:  STATUS: EXPSTATUS=INTEGRATING
10:40:49  ICS>OBS STATUS:   Shutter=Closed Integration Remaining=0 sec. EXPSTATUS=INTEGRATING
```

`STATUS:  STATUS:` 는 5.1 의 커맨드워드 오염이고, 노출 종료(셔터 닫힘) 국면인데도 `EXPSTATUS=INTEGRATING` 이 계속 실려 나간다. **신규는 이렇게 하지 않는다:**

- `EXPSTATUS=<상태>` 알림은 **상태가 실제로 바뀌는 시점에 1회**만 발신한다.
- 셔터가 닫힌 뒤에는 `EXPSTATUS=INTEGRATING` 을 **일절 보내지 않는다.** 종료 알림은 `Shutter=Closed …` 1회이고, 다음 상태 알림은 `EXPSTATUS=READOUT` 이다.
- 커맨드워드는 비동기 알림이므로 **빈 값**으로 명시한다.

검증: `test_emitter_hygiene.py::test_expstatus_not_repeated_after_shutter_closes`.

### 3.3 하드 타임아웃 4종 (main.c 650~708, 1카운트 ≈ 0.045초)

| 조건 | 상수 | 시간 | 초과 시 |
|---|---|---|---|
| 1번째 `Acquisition Complete.`<br>→ 4번째 | `force_idle=40` | ≈1.8초 | `IDLE_3` 강제 +<br>**`opause`(스크립트 정지)** +<br>`ERROR: Acquisition is not fully completed !!` |
| 4번째 `Acquisition Complete.`<br>→ `EXPSTATUS=IDLE` | `force_idle/2=20` | ≈0.9초 | `IDLE_3` 강제 +<br>`WARNING: No 'EXPSTATUS=IDLE' message from ICS` |
| `IDLE_3` 진입<br>→ 4번째 `Wrote` | `force_fitssaved=560` | ≈25초 | `FitsSaved=1` 강제 +<br>`WARNING: Writing FITS data is not fully completed !!` +<br>`ExpStatus=ERROR` |
| `IDLE_3` → `READY` | `force_ready=270` | ≈12.2초 | (정상 전이 — 메시지로 앞당길 수 없음) |

실측 레거시는 4개 `Acquisition Complete.` 가 ~3ms 안에, `EXPSTATUS=IDLE` 이 0.38초 뒤에 도착한다.

**네 값 모두 `ics_sim.ini` 의 `[obsagent]` 에서 편집 가능하다.** 시뮬이 직접 쓰진 않고, 기동 시 `[timing]` 값이 이 창을 침범하는지 **자가검증**하는 데 쓴다(`config.validate()`). 여유를 좁혀 경보 경로를 시험하는 것도 정당한 사용이라 경고만 내고 기동은 막지 않는다.

검증: `test_obsagent_contract.py::test_timeout_windows_not_violated`, `::test_config_self_check_flags_bad_timing`.

### 3.4 `ExpNum` 자동 질의 — 반드시 응답해야 하는 항목

`commands.c` 797~803행: 첫 `PCTREAD=` 를 받아 `READ_1` 일 때 OBSAgent 가 **스스로** `OBS>ICS ExpNum` 을 보낸다.

```
OBS>ICS ExpNum
ICS>OBS DONE: EXPNUM  Filename=20250902.057288 EXPSTATUS=READOUT
```

**목적과 내력** (소스 서두 개정이력 주석 218~229행):

- **v1.0.1 (2024-07-01)** — *"Add ExpNum query to ICS and ExpNum(strNextNum/strCurNum) update"*. **카메라 제어용이 아니라 상태 표시용**으로 추가된 비교적 최근 기능이다.
- 응답의 `Filename=` 값(**정확히 15자**, `strncpy(expinfo.strNextNum, pstr+9, 15)`)이 `expinfo.strNextNum` 이 되고, 다음 노출의 `Shutter=Open`(또는 `EXPSTATUS=INTEGRATING`) 시점에 `strCurNum` 으로 승격된다.
- 흘러가는 곳: **v1.0.0(2024-06-29)에 추가된 `expinfo`/`ee` 명령**의 반환 문자열과, **v1.0.3~1.0.4(2024-07-05)에 추가된 `/data/Logs/ObsStatus.txt`** 의 `EXP.INFO:` 줄(포맷은 `OBSAgent.latest/Ref.ObsStatus.txt`). **관측자 화면과 상태파일의 `ExpNum` 필드를 채우는 유일한 경로다.**
- 후속 디버깅 이력: **v1.0.6** `expinfo.dStartTime` 누락(ExpProg) · **v1.0.7~1.0.8** SSO 에서의 ExpNum 오류 · **v1.0.9** `strPreNum`/`FitsOsc` 추가 · **v1.1.3(2024-07-18)** *"Debug momentary unmatch of ExpNum and ExpStatus, Debug missing ExpNum/ExpStart update in dark/bias mode"*.
- **응답이 없으면**: 카메라 동작 자체는 정상이지만 `ExpNum` 이 갱신되지 않아 `expinfo`·`ObsStatus.txt`·`GMON` 표시가 이전 값이나 `00000000.000000` 에 머문다.

CTIO 아카이브에서 **125,451회** 확인. **2024-03 로그에는 없고 2025 로그에만 있는 것이 v1.0.1 도입 시점(2024-07)과 정확히 일치한다.**

> **기존 8.0.1절·`obsagent_report.md` 6절 어디에도 없던 항목이다.**

`DONE:` 파싱 순서(947~960행, else-if): `ExpTime=` → `atof(+8)` · `EXP=` → `atof(+4)` · `Filename=` → 15자 복사.

검증: `test_obsagent_contract.py::test_expnum_query_answered`, `::test_expnum_advances_between_exposures`.

### 3.5 스크립트 관측 응답 체크 (885~1015행)

`.osc` 스크립트 실행 중에는 명령마다 응답을 확인한다.

- **`GO`**: 본문이 아니라 **`CamStatus` 가 `PREP_I`~`INT_3` 범위에 들어오면** OK (885행). → `go` 접수 후 지체 없이 `EXPSTATUS=INITIALIZING` 을 보내야 한다.
- **그 외**: `DONE:` 본문에 명령어 문자열이 포함돼야 한다 — `PROJID` / `STANDARD` / `DOMEFLAT` / `SKY` / `FLAT` / `OBJECT` / `DARK` / `BIAS` / `EXP` / `OBSERVER` / `LEDFLASH` / `DATASOURCE` / `DMAWAIT` / `FILENAME` / `ACQSTATUS` / **`" STATUS"`(앞 공백 필요, 987행)**.

레거시 응답이 `DONE: <커맨드워드> <본문>` 형식이므로 자연히 만족하지만, 커맨드워드를 생략하면 깨진다.

검증: `test_obsagent_contract.py::test_script_response_check_strings`.

### 3.6 명령별 응답 문자열 (실측)

```
ICS>OBS DONE: PROJID  ProjID=OBS
ICS>OBS DONE: OBSERVER  Observer=(jeonghyun)                    ← 괄호로 감쌈
ICS>OBS DONE: EXP  ExpTime=30 seconds.
ICS>OBS DONE: DARK  ImageType=DARK ObjectName='begin' EXP=30    ← EXP=는 변경 전 현재값
ICS>OBS DONE: BIAS  ImageType=BIAS ObjectName='bias' EXP=0
ICS>OBS DONE: OBJECT  ImageType=OBJECT ObjectName='BLG11' EXP=60
ICS>OBS DONE: FLAT / SKY / DOMEFLAT / STANDARD   (동일 형식)
ICS>OBS DONE: EXPNUM  Filename=20250902.057288 EXPSTATUS=READOUT
ICS>OBS DONE: ACQSTATUS  ACQSTATUS=READY K.IC=READY M.IC=READY T.IC=READY N.IC=READY MASTER=K.IC
ICS>OBS DONE: STATUS  Inst=ICS ExpTime=60 GuideExp=0 ImageType=OBJECT ObjectName='N7793-1' Mode=Acquiring ComTest=F
ICS>OBS DONE: FILENAME  Filename=ICS.20171228T013347.058164
ICS>OBS ERROR: EXP  Cannot change EXPTIME for ImgType=BIAS
ICS>OBS ERROR: GO  Data acquisition already in progress! EXPSTATUS=READOUT
ICS>OBS ERROR:   Failed to initialize one or more ICs            ← OBSAgent가 flag_icscheck를 세움
ICS>OBS ERROR:   Failed to Start acquisition on one or more ICs  ← 〃 (1030~1035행)
K.IC>OBS DONE: STATUS  Inst=KMTNk  DetectorID=K Driving=1 +FIBERS +SYNCH Build=KS2016-01-13:1370
K.IC>OBS DONE: DATASOURCE   DataSource=CT_CORRECTION CTCSource=FIRMWARE
K.IC>OBS ERROR: DATASOURCE  Invalid selection for DataSource. ADC, CTC, and SIM are valid. DataSource=ADC
K.IC>OBS DONE: DMAWAIT  DMAWaitTime=500
K.IC>OBS DONE: LEDFLASH  LEDFlashTime=1
K.IC>ICS DONE: FLASHNOW  LED Flash Done.
K.IC>OBS DONE: FILENAME  Filename=KMTNk.20171228.058164
K.IC>OBS DONE: SHCLOSE  Shutter=Closed Shutter was not open
*.IC>ICS ERROR: <cmd>  Didn't understand <cmd> <args> ?          ← 미상 명령 거부 형식
```

**노출 진행 중이면 모든 `DONE:` 끝에 ` EXPSTATUS=<현재상태>` 가 붙는다.** 레거시는 노출 중에도 설정 변경을 잠그지 않고 현재 국면을 덧붙였다. OBSAgent v0.2.7 이 `Wrote` 카운트 버그를 고친 원인이 바로 이 접미사다.

`SYNCHRONIZE` — **`STATUS:` 와 `DONE:` 두 타입 모두 실측됨** (CTIO 기준 `DONE:` 2,230회 / `STATUS:` 1,284회):

```
K.IC>ICS SYNCHRONIZE
ICS>K.IC STATUS: SYNCHRONIZE   IMGTYPE=OBJECT OBJNAME=BLG33 EXP=60 OBSERVER=smc PROJID=BLG
ICS>N.IC DONE:   SYNCHRONIZE   IMGTYPE=… (동일 본문)
```

---

## 4. 레거시 노출 사이클

`t` 는 `OBS>ICS go` 기준 상대시각(XIS 로그 실측 중앙값). 타이밍 수치는 전부 7장의 설정 항목이다.

### 4.1 DARK/BIAS (셔터 안 염)

```
t+0.00  OBS>ICS go
t+0.70  ICS>TC AUXSTATUS                     → TC>ICS DONE: AUXSTATUS <역순 필드>
t+0.81  ICS>OBS STATUS: EXPSTATUS=INITIALIZING
t+0.81  ICS>G.IC INITIALIZE <yyyymmdd>T<HHMMSS>       ← 가이드에도 발신
t+0.82  ICS>K.IC INITIALIZE <yyyymmdd>.<nnnnnn>       ← K→M→T→N, ~3ms 간격
t+1.22    {K,M,T,N}.IC>ICS DONE: INITIALIZE  Initialization Complete.
t+1.30  ICS>OBS STATUS: EXPSTATUS=ERASE
t+1.30  ICS>K.IC ERASE                                ← K master에만
t+1.36  ICS>N.IC STATUS: AUXSTATUS  <필드…> EXPSTATUS=ERASE   ← N→T→M→K, ~58ms 간격
t+1.54  ICS>TC TCSSTATUS                    → TC>ICS DONE: TCSSTATUS <역순>  (중계는 보류)
t+8.55    K.IC>ICS DONE: Erase Cycle Complete.        ← ERASE ~7.24초
t+8.57  ICS>OBS STATUS: EXPSTATUS=INTEGRATING         ← 노출 개시 시각 확정
t+8.60  ICS>N.IC STATUS: TCSSTATUS  DATE-OBS=<개시시각> … EXPSTATUS=INTEGRATING
t+14.6  ICS>OBS STATUS: Remaining=24 sec. of 30 sec.  EXPSTATUS=INTEGRATING   ← 5초 간격
        … 19, 14, 9
t+38.6  ICS>OBS STATUS: Shutter=Closed Integration Remaining=0 sec. EXPSTATUS=INTEGRATING
t+38.6  ICS>M.IC GO OBS / ICS>T.IC GO OBS / ICS>N.IC GO OBS
t+38.66   {M,T,N}.IC>ICS STATUS: GO                   ← 본문 없음
t+38.69 ICS>OBS STATUS: EXPSTATUS=READOUT
t+38.70 ICS>K.IC GO OBS                               ← K master는 항상 마지막
t+38.75   K.IC>ICS STATUS: GO
t+41.4    K.IC>OBS STATUS: GO  PCTREAD=6              ← K만, sourceID에게만. 3.37초 간격
          … 17, 28, 39, 50, 61, 72, 83, 94 (9틱, +11씩)
          ← 이 첫 PCTREAD 시점에 OBSAgent가 'ExpNum'을 되쏜다 (3.4)
t+70.1    {K,M,T,N}.IC>OBS STATUS: GO  PCTREAD=100 Acquisition Complete. Disk Transfer Starting.
t+70.14   {T,N,M,K}.IC>ICS STATUS: GO  Acquisition Complete      ← ICS 방향은 마침표 없음
t+70.5  ICS>OBS DONE: EXPSTATUS=IDLE
t+78.9    N.IC>N.CB TRANSFER DISK<d> 1 ICS            ← CCD별 시차(N→T→M→K)
t+78.9    N.IC>XIS PING  →  XIS>N.IC PONG
t+79.0    N.IC>ICS STATUS: GO  Disk Write Complete    ← PONG 수신 후
t+82.3    N.CB>ICS DONE: Wrote LASTFILE=/mnt/ICSData/KMTNn.<…>.fits RATE=1056543 KB/sec
t+82.3  ICS>OBS STATUS: Wrote LASTFILE=… RATE=… KB/sec           ← ICS가 OBS로 중계
t+83.3    N.CB>N.IC DONE DISK<d> 1 / N.CB>N.IC REQ SWAP
t+83.4    N.IC>N.CB ACK SWAP
```

> **핵심**: `Wrote` 가 OBSAgent 에 닿는 경로는 `CB>ICS` 직송이 아니라 **`ICS>OBS STATUS: Wrote …` 중계**다. 3.2 의 "`Wrote` 4회" 는 이 중계 메시지 4개를 뜻한다.
>
> CTIO 는 `CB>ICS DONE: Wrote`, SSO 는 `CB>ICS STATUS: Wrote` 로 타입이 다르지만, `case DONE:` 에는 `Wrote` 핸들러가 없으므로 어느 쪽이든 OBSAgent 는 **중계분만** 센다.

### 4.2 OBJECT/FLAT/… (셔터 염) 차이점만

```
ICS>OBS STATUS: EXPSTATUS=INTEGRATING
ICS>K.IC SHOPEN 60 OBS USESTATUS                       ← DARK엔 없는 단계. K master만
  K.IC>OBS STATUS: SHOPEN  Shutter=Open                (+0.15초)
  K.IC>OBS STATUS: SHOPEN  Integration Remaining=54 sec.
ICS>K.IC STATUS: TCSSTATUS  DATE-OBS=<셔터 개방 시각> …   ← Shutter=Open 직후
  K.IC>OBS STATUS: Integration Remaining=49 sec.       ← ~5.217초 간격
  …  43, 38, 33, 28, 22, 17, 12, 7, 1
  K.IC>OBS STATUS: Shutter=Closed Integration Remaining=0 sec.
(+6.0초) ICS>OBS STATUS: EXPSTATUS=READOUT             ← 이후는 4.1과 동일
```

카운트다운 문구가 경로별로 다르다 — DARK 는 ICS 의 `Remaining=N sec. of M sec.`, OBJECT 는 K.IC 의 `Integration Remaining=N sec.`. 둘 다 `Remaining=` 을 포함하므로 `INT_3` 전이는 동일하다.

**`Shutter=Open` 메시지가 아예 누락되는 경우가 실측된다**(`samples_for_bug.txt`). 그 경우 `INT_2` 를 못 밟으며, OBSAgent v1.1.3 이 `expinfo.flagStart` 로 이를 보정한다(831행).

### 4.3 텔레메트리 중계 — 필드 순서가 뒤집힌다

`TC>ICS DONE: AUXSTATUS` 의 필드 순서와 `ICS>*.IC STATUS: AUXSTATUS` 의 순서가 **정확히 역순**이다. 스택에 쌓았다 빼는 구현으로 보인다.

```
TC→ICS : AUXQDATE=.. TIMESYS=.. TELID=.. AUXLINK=.. ... ENS2=.. ENS1=..
ICS→IC : ENS7=.. ENS6=.. ... AUXLINK=.. TELID=.. TIMESYS=.. AUXQDATE=..
         + KBUILD=.. MBUILD=.. TBUILD=.. NBUILD=.. GBUILD=.. ICSBUILD=.. EXPSTATUS=..
```

**필드 집합은 사이트마다 다르다.** SSO 는 `DSSTAT` 앞에 돔 필드 `DSTEL DSALT DSAUTO DSSAF DSLW DSUP` 가 더 있고 `GBUILD` 가 채워져 있는 반면, CTIO 는 그 필드들이 없고 `GBUILD=` 가 빈 값이다.

**그래서 사이트별 필드 테이블을 두지 않는다.** 받은 `key=value` 를 순서 그대로 보존해 역순으로 되돌려 보낸다(pass-through). ICS 가 알아야 할 것은 "어디까지가 TC 필드이고 어디부터 내가 붙이는 꼬리인지"뿐이다. FITS 헤더 생성에 특정 필드가 필요한데 없으면 **없다는 것이 드러나는 sentinel**(수치 `0`, 문자열 `NC`)로 채운다 — 레거시의 `GBUILD=`(빈 값)·`DSSTAT=NC` 관례와 같은 방식이다.

**타이밍** (`ics_legacy_report.md` 5.3절):
- **AUXSTATUS 는 질의 즉시 중계**한다. 환경·필터 정보는 시간에 덜 민감하다. 메시지에 `EXPSTATUS=ERASE` 태그가 붙어 "플러싱 중 스냅샷"임을 알 수 있다.
- **TCSSTATUS 는 셔터가 실제로 열린 시각을 `DATE-OBS` 로 확정한 뒤에야 중계**한다. FITS 헤더의 `DATE-OBS`/좌표가 노출 시작 순간을 정확히 반영하도록 하기 위한 설계다. DARK/BIAS 는 `ERASE` 완료 시점을 "논리적 노출 시작"으로 삼는다.

구현: [`ics_sim/telemetry.py`](ics_sim/telemetry.py).

---

## 5. 메시지 오염 버그 — 원인 분석과 신규 설계 대응

> **이 장이 이번 조사에서 가장 실질적인 신규 발견이다.**
>
> **2026-08-04 — 원인 코드를 확정했다.** 5.1~5.3 은 로그 실측만으로 세운 추론이었고, 이제 `IC2.img` 에서 확보한 ICS 소스로 검증됐다. **추론은 전부 맞았고**, 한 가지는 예상보다 더 나쁜 형태였다(`EXPSTATUS=` 가 상태 통보가 아니라 일괄 접미사였다는 것). 확정 내용은 **5.5절**이다. 앞 절들은 현상 기록으로 그대로 둔다.

48GB 전량 + 사용자 제공 `samples_for_bug.txt` 를 **커맨드워드 슬롯 단위로 분류**해 확인했다. 세 가지 별개 현상이다.

### 5.1 현상 A — 스테일 커맨드워드 (결정론적, 대량)

IMPv2 메시지는 `src>dest <TYPE> <커맨드워드> <본문>` 구조인데, **레거시 ICS/IC 는 이 슬롯을 "가장 최근에 처리한 메시지"의 것으로 채운 채 비우지 않는다.** 명령에 대한 직접 응답이 아닌 **비동기 상태 메시지**(카운트다운, EXPSTATUS 전이 등)에서 잔재가 그대로 드러난다.

**실측 잔재 목록** (CTIO 634일 기준):

| 오염된 발신 | 건수 |
|---|---:|
| `ICS>OBS STATUS:  STATUS: EXPSTATUS=INTEGRATING` | 173,635 |
| `K.IC>OBS STATUS: REQ  Integration Remaining=54 sec.` | 148,430 |
| `K.IC>OBS STATUS: SHOPEN  Integration Remaining=14 sec.` | 93,724 |
| `K.IC>OBS STATUS: DATASOURCE  Integration Remaining=5 sec.` | 39,614 |
| `K.IC>ICS DONE: REQ  Erase Cycle Complete.` | 31,604 |
| `K.IC>OBS STATUS: FLASHNOW  Integration Remaining=… sec.` | 4,522 |
| `K.IC>ICS DONE: DONE  Erase Cycle Complete.` | 276 |
| `ICS>OBS ERROR: SYNCHRONIZE  Failed to Start acquisition on one or more ICs` | 122 |
| `K.IC>OBS STATUS: SHCLOSE  Integration Remaining=165 sec.` | 113 |
| `K.IC>ICS DONE: DATASOURCE  Erase Cycle Complete.` | 101 |
| `K.IC>{OBS,ICS} STATUS: FOUND  Integration Remaining=…` | 103 |
| `K.IC>OBS STATUS: {DONE,PROJID,OBJECT,PING,PONG,STATUS,EXP}  Integration Remaining=…` | 각 1~154 |
| `ICS>OBS STATUS: PING  Remaining=24 sec. of 30 sec.` | 5 |
| `ICS>OBS ERROR: EXPNUM  Failed to Start acquisition on one or more ICs` | 1 |

**올바른 형태**는 같은 본문이 빈 커맨드워드로 나가는 것이다: `K.IC>OBS STATUS: Integration Remaining=9 sec.`(152,847회), `K.IC>ICS DONE: Erase Cycle Complete.`(141,435회).

**증거의 핵심 세 가지:**

1. **같은 본문이 제각각인 커맨드워드를 달고 나간다.** `Integration Remaining=` 하나만 놓고 봐도 빈 값 / `REQ` / `SHOPEN` / `DATASOURCE` / `FLASHNOW` / `DONE` / `PROJID` / `OBJECT` / `PING` / `PONG` / `FOUND` / `STATUS` / `EXP` 가 모두 관측된다.
2. **`REQ`·`DONE`·`PONG`·`FOUND` 같은 프로토콜 키워드가 커맨드워드 자리에 나타난다.** 검증된 명령 테이블이 아니라 **직전 파싱 토큰**에서 슬롯이 채워졌다는 뜻이다. `REQ` 가 1위인 것은 IMPv2 에서 타입 생략 시 암묵 기본값이 `REQ` 이기 때문으로 보인다.
3. **인과가 로그에서 직접 보인다.** SSO `isis.20240111.log` 등에서 `OBS>*.IC datasource ctc` → `*.IC>OBS DONE: DATASOURCE  DataSource=…` 직후, 같은 노출의 다음 비동기 카운트다운이 `K.IC>OBS STATUS: DATASOURCE  Integration Remaining=5 sec.` 로 나간다. 명령을 받은 적 없는 `PING`/`PONG` 까지 슬롯에 남는 것도 같은 경로다.

`SHOPEN`·`FLASHNOW` 는 그 카운트다운을 시작시킨 명령이라 첫 메시지에는 타당해 보이지만, 같은 위치에 다른 값이 뒤섞인다는 점에서 슬롯이 관리되지 않는다는 결론은 같다.

### 5.2 현상 B — 누적(2단계 이상) 오염

잔재가 하나로 끝나지 않고 **겹쳐 쌓이며 본문을 밀어내 소실**시킨다:

| 실측 | 사이트/건수 | 해석 |
|---|---|---|
| `ICS>OBS STATUS: SYNCHRONIZE STATUS:` | CTIO 14 | 커맨드워드 `SYNCHRONIZE` + 잔재 `STATUS:` + **본문 완전 소실** |
| `ICS>OBS STATUS: PING STATUS: EXPSTATUS=INTEGRATING` | SSO 1 | 잔재 2개(`PING`,`STATUS:`)가 연달아 |
| `K.IC>ICS DONE: EXP  FLAT  ImageType=FLAT ObjectName='flat' EXP=30` | CTIO 각 IC 2 | 커맨드워드 **2개**(`EXP`,`FLAT`) 적층 |
| `ICS>OBS DONE: PROJID  ProjID=ALL BIAS BIAS` | SAAO 5 | 이전 메시지 잔재가 **꼬리에 2회 반복** |
| `ICS>OBS STATUS: EXPNUM` | CTIO 1 | 슬롯만 남고 본문 전부 소실 |
| `ICS>OBS STATUS: : EXPSTATUS=INTEGRATING` | CTIO 1 | 슬롯이 콜론 한 글자로 잘림 |

### 5.3 현상 C — 버퍼 겹침·전송 절단 (비결정론적, 희소하지만 데이터 손실)

문자열이 **중간부터 겹쳐 쓰여** 토큰이 깨진다. 발신·수신 양쪽에서 관측된다:

```
K.IC>ICS DONE: INITIALIZitialization Complete.     ← "INITIALIZE"+"Initialization Complete." 겹침
ICS>T.IC STATUS: TCSSTATUS  DATE5-04-03T06:26:41   ← "DATE-OBS=2025"가 "DATE5"로 (7자 소실)
ICS>T.IC STATUS: AUXTATUS  ENS7=…                  ← "AUXSTATUS" → "AUXTATUS"
M.IC>ICS ERROR: OBCT  Didn't understand OBCT BLG37 ?           ← 수신측: "OBJECT"가 "OBCT"로
K.IC>ICS ERROR: N  Didn't understand N 60 OBS USESTATUS ?      ← "SHOPEN 60 …"이 "N 60 …"로
K.IC>ICS ERROR: EN  Didn't understand EN 60 OBS USESTATUS ?    ← 〃 (SSO)
M.IC>ICS ERROR: STATUSTUS  Didn't understand STATUSTUS  DATE-OBS= ?   ← 두 메시지 접합 (SAAO)
K.IC>0 STATUS: EXP  Integration Remaining=145 sec.             ← 수신 노드명이 "0"으로 파괴
```

**운영 영향이 실재한다**: `SHOPEN 60 OBS USESTATUS` 가 `N 60 …` 으로 깨져 K.IC 가 거부한 건은 **셔터가 열리지 않은 노출**을 뜻한다.

원인 추정: ICS↔XIS 링크만 시리얼(`/dev/ttyS0`)이고 나머지 노드는 전부 UDP 인데, 이 계열 손상이 그 구간에 집중된다(15장). **신규 시스템이 UDP 로 가면 이 계열 손상은 구조적으로 사라진다.**

### 5.4 신규 설계 대응

1. **커맨드워드는 매 메시지마다 명시적 인자.** `emitter.py` 의 모든 메서드가 `cmdword` 를 파라미터로 받고, 비동기 상태 메시지는 `cmdword=''` 를 **명시적으로** 넘긴다. 전역/멤버 상태에서 물려받는 경로를 아예 만들지 않는다.
2. **메시지 조립은 불변 값 → 새 `bytes` 반환.** 재사용 버퍼도, `bytearray` 누적도 없다.
3. **`EXPSTATUS=` 알림은 상태 전이 시점에 1회씩만, `OBS` 로만**(3.2.1·3.2.2). 셔터 닫힘 후 `INTEGRATING` 재발신 금지.
4. **송신 직전 자체 검증** `emitter.validate()`:
   | 항목 | 잡아내는 것 |
   |---|---|
   | `header` | `src>dest TYPE:` 형태가 아님 |
   | `type_in_body` | 본문/커맨드워드에 메시지 타입 키워드 재등장 (`STATUS:  STATUS:`) |
   | `unknown_cmdword` | 커맨드워드가 허용 집합 밖 (`REQ`/`DONE`/`FOUND`/`PONG`) |
   | `stale_cmdword` | 본문에 맞지 않는 커맨드워드 (`DATASOURCE  Integration Remaining=`) |
   | `stacked_cmdword` | 본문 첫 토큰이 또 다른 커맨드워드 (`EXP  FLAT  ImageType=`) |
   | `repeated_tail` | 끝에 같은 커맨드워드가 반복 (`ProjID=ALL BIAS BIAS`) |

   `stale_cmdword` 는 **본문 접두사 → 허용 커맨드워드 표**로 판정한다. 같은 본문이 제각각인 커맨드워드를 달고 나가는 것이 오염의 정의였으므로, 본문마다 커맨드워드를 하나로 못박는 것이 그 역이다.
5. **수신은 관대하게**: 깨진 명령은 크래시 없이 레거시와 동일한 `ERROR: <cmd>  Didn't understand <cmd> <args> ?` 로 거부한다.
6. **레거시 재현 모드**: `[behavior] bug_compat = true` 면 5.1 의 오염을 의도적으로 재현한다(**기본 꺼짐**). 골든 대조에서 레거시와 맞추는 용도이며, **두 모드 모두 OBSAgent 규약 테스트를 통과해야 한다** — 즉 "이 버그는 OBSAgent 동작에 영향이 없다"가 검증 대상이다. 그래서 레거시가 수년간 이 상태로 운용될 수 있었다.

검증: `test_emitter_hygiene.py` 전체. 특히 **역방향 검증** — `tests/fixtures/bug_patterns.txt` 의 레거시 오염 샘플 18종이 전부 위반으로 잡히는지 확인한다. 이게 없으면 검증기가 껍데기여도 정방향 테스트는 통과한다.

### 5.5 원인 코드 확정 (2026-08-04)

`IC2.img` 에서 ICS 본체 소스를 확보했다. 자료의 성격은 2.1 표와 `ics_legacy_report.md` 1.3.1⑤ 에 적었고, 여기서는 **버그와 직접 관련된 코드**만 본다. 상세 인용은 `ics_legacy_report.md` 5.6.6절에 있으니 중복하지 않는다.

#### 5.5.1 세 줄 요약

| 현상 | 원인 코드 | 5.1~5.3 의 추론은 |
|---|---|---|
| A. 스테일 커맨드워드 | `SHARE\PAP7COM.INC:797-802` 의 `SUB Prt` 가 `COMS(OutPort).CommandEcho` 를 **무조건** 끼워 넣는다. 삽입 조건이 "응답인가"가 아니라 **"첫 낱말이 콜론으로 끝나는가"** 뿐 | **맞았다.** 다만 슬롯의 출처가 "직전 파싱 토큰"이 아니라 **"직전에 도착한 정식 명령"** 이었다 |
| B. 누적 오염 | 같은 `SUB Prt` 가 인자를 **BYREF 로 덮어쓴다**. `CALL PRT(Buffer, OutBuffer(Buffer))` 로 부르면 버퍼 자체가 오염된 문자열로 바뀐다 | **맞았다.** "재사용 버퍼" 라고 본 것이 정확히 이 형태 |
| C. 버퍼 겹침·절단 | 이 코드가 아니다. 수신부(`PAP7COM.INC:735-756`)는 1024자 폭주만 막고 손상 자체는 다루지 않는다 | **맞았다.** 시리얼 구간 원인 추정 유지 |

#### 5.5.2 예상 밖이었던 것 — `EXPSTATUS=` 는 접미사다

이건 추론에 없던 내용이라 따로 적는다. `PAP7COM.INC:809-814`:

```basic
'-- If we are in an acquisition loop, add the EXPSTATUS= info
IF GoFlag > 0 OR ShutterOpenFlag > 0 THEN
   OutgoingMessage = OutgoingMessage + " EXPSTATUS="+TRIM(ExpStatus)
END IF
```

그리고 노출 시퀀스에서 상태를 알리는 자리(`KMTX\PAP7KX.CCD:122, 151, 289`)는 **본문이 비어 있고 `EXPSTATUS=` 문자열은 주석 처리돼 있다**:

```basic
'OutBuffer(Buffer) = ICHost + ">" + AcquisitionInitiator + " STATUS: EXPSTATUS=ERASE"
OutBuffer(Buffer) = ICHost + ">" + AcquisitionInitiator + " STATUS: "
```

**즉 레거시의 `EXPSTATUS=` 는 상태 전이를 알리는 메시지가 아니라, 노출 중 모든 콜론 메시지에 붙는 스냅샷 접미사다.**

이게 왜 중요하냐면 — 3.2.2 에서 "셔터 닫힌 뒤에도 `EXPSTATUS=INTEGRATING` 이 반복된다"를 **레거시의 버그성 습관**으로 보고 재현하지 않기로 했는데, 실제로는 **버그라기보다 설계가 그런 것**이었다. `ExpStatus` 변수는 `PAP7KX.CCD:284` 에서야 `"READOUT"` 이 되고 셔터 닫힘 알림은 `:276` 에서 나가니, 그 시점 스냅샷이 `INTEGRATING` 인 게 당연하다.

**결론은 바뀌지 않는다.** OBSAgent 의 `CamStatus` 는 이 접미사를 *전이 트리거*로 쓰므로(3.2), 스냅샷을 그대로 흉내내면 역행이 생긴다. 5.4-3 규칙("전이 시점 1회, `OBS` 로만")은 **레거시 모방이 아니라 레거시보다 엄격한 선택**이라는 점만 분명해졌다. 3.2.1 실측에서 역행이 0건이었던 것은 레거시가 그 접미사를 주로 `*.IC` 앞으로 보냈기 때문이지, 레거시가 규율이 있어서가 아니다.

#### 5.5.3 왜 `REQ`·`PING`·`PONG`·`FOUND` 가 슬롯에 들어가나

5.1 에서 "검증된 명령 테이블이 아니라 직전 파싱 토큰에서 채워진 증거"라고 썼는데, **절반만 맞았다.** `PAP7KX.CMD` 의 `CASE` 100개를 뽑아 보니 `REQ`·`PING`·`PONG`·`FOUND` 가 **전부 정식 명령**이다. 슬롯은 정상적인 명령 테이블에서 채워진다 — 문제는 **비워지지 않는 것**뿐이다.

슬롯 대입부(`PAP7KX.CMD:1496-1504`)에 두 번째 누출 경로도 있다:

```basic
IF RIGHT(Words(1),1) <> ":" THEN
   IF LEN(Words(1)) < 16 THEN          ' ← 16자 이상이면 갱신 자체를 건너뛴다
      COMS(Buffer).CommandEcho = Words(1) + SPACE(16-LEN(Words(1)))
   END IF
ELSE
   Coms(Buffer).CommandEcho = SPACE(16)
END IF
```

16자 이상 낱말이 오면 **더 오래된 잔재가 그대로 살아남는다.** 정상 운용 중 슬롯을 비우는 유일한 경로는 콜론으로 끝나는 낱말이 도착하는 경우와 종료 브로드캐스트(`PAP7.INC:3935`)뿐이다.

#### 5.5.4 우리 구현에 대한 확인

`emitter.py` 는 (a) 커맨드워드를 메서드 인자로 매번 받고, (b) 새 `bytes` 를 반환하며, (c) `validate()` 로 적층·재등장을 잡는다. 5.5.1 의 세 경로를 **구조적으로** 갖지 않는다 — 즉 5.4 의 대응은 원인을 모르는 상태에서 세웠는데도 정확히 그 자리를 막고 있었다. 코드 변경은 필요 없었다.

다만 `validate()` 의 `unknown_cmdword` 항목 설명(5.4-4 표)에서 `REQ`/`DONE`/`FOUND`/`PONG` 을 "허용 집합 밖"이라고 적은 것은 **표현이 부정확했다.** 레거시 기준으로 이들은 정식 명령이고, 우리가 잡으려는 것은 "정식 명령어가 **비동기 알림의 커맨드워드 자리에** 나타나는 것"이다. 검사 자체는 원래부터 그렇게 동작한다(`cmdword` 를 명시적으로 넘긴 경우에만 판정).

---

## 6. 전량 스캔에서 새로 나온 시퀀스·메시지

`__sample_isislog/`(9개월)에는 없고 전체 아카이브(48GB)에만 있는 것들.

### 6.1 `GO n` 다중 노출 — 샘플에 전혀 없던 전체 시퀀스

`GO 5` 의 실측 전개 (CTIO `isis.20240102.log`, ICS→OBS 만 추림):

```
ICS>OBS STATUS: Image 1 of 5 complete. EXPSTATUS=IDLE     ← 프레임 1 종료 (DONE:이 아니라 STATUS:)
ICS>OBS STATUS: EXPSTATUS=INITIALIZING                    ← 프레임 2 시작 (GO 재발행 없이 ICS가 자동)
ICS>OBS STATUS: EXPSTATUS=ERASE
ICS>OBS STATUS: Wrote LASTFILE=…KMTNm.20240103.023885.fits …   ← 프레임 1의 저장 완료가
ICS>OBS STATUS: Wrote LASTFILE=…KMTNk…                          ← 프레임 2 준비 중에 도착
ICS>OBS STATUS: Wrote LASTFILE=…KMTNn…                          ← (파이프라인)
ICS>OBS STATUS: Wrote LASTFILE=…KMTNt…
ICS>OBS STATUS: EXPSTATUS=INTEGRATING
ICS>OBS STATUS: Shutter=Closed Integration Remaining=0 sec. EXPSTATUS=INTEGRATING
ICS>OBS STATUS: EXPSTATUS=READOUT
ICS>OBS STATUS: Image 2 of 5 complete. EXPSTATUS=IDLE
…
ICS>OBS DONE: EXPSTATUS=IDLE                              ← 마지막 프레임만 DONE:
```

- **건수 근거**: CTIO 에서 `Image 1 of 5`(1,254) · `2 of 5`(1,250) · `3 of 5`(1,246) · `4 of 5`(1,244) 가 있고 **`5 of 5` 는 0건**이다 → 마지막 프레임은 `DONE: EXPSTATUS=IDLE` 로 끝난다. `of 4`(13) · `of 3`(8) · `of 2`(23) 도 같은 패턴.
- **OBSAgent 소스가 뒷받침한다** — `commands.c` 765행 주석: *"msg type of 'EXPSTATUS=IDLE' is STATUS in the case of 'go n' command, added here at v0.3.0"*. v0.3.0 이 이 경로 때문에 `STATUS:` 에도 `EXPSTATUS=IDLE` 핸들러를 넣었다.
- **타이밍 제약**: 프레임 N 의 `Wrote` 4개가 프레임 N+1 의 `INITIALIZING`/`ERASE` **이후**에 도착하지만, 프레임 N+1 의 `EXPSTATUS=READOUT`/`PCTREAD=` 가 `count_wrote` 를 리셋하기 **전**에는 다 들어와야 한다. 어기면 `FitsSaved` 가 영영 1이 되지 않는다.

검증: `test_obsagent_contract.py::test_go_n_emits_image_progress`, `::test_go_n_wrote_counts_survive_pipelining`.

### 6.2 디스크는 최대 4중화 — 그러나 신규에서는 폐지한다

샘플에서는 `DISK0`/`DISK1` 만 보여 "이중버퍼"로 정리했으나 실제로는:

| 사이트 | K master | M/T/N |
|---|---|---|
| CTIO | `DISK0`(85,940) · `DISK2`(258) | 주로 `DISK0` |
| SSO | `DISK1`(20,470) · `DISK2`(14,823) · **`DISK3`(177)** | `DISK0`/`DISK1` |
| SAAO | `DISK0`/`DISK1` | `DISK0`/`DISK1` |

→ `ics_legacy_report.md` 의 "이중화" 서술은 **정정 대상**이다.

**다만 신규 `ics` 에는 가져가지 않는다.** 레거시가 여러 디스크를 돌린 이유는 (1) 1998년 SCSI 시절의 성능 최적화이고, (2) NFS 로 Science server 에 옮기는 데 걸리는 시간을 운영상 감당하기 위해서다. 신규 `ics` 는 **관측자료 취합 서버 역할과 기기제어·자료획득 역할(`x.IC`)을 단일 PC 에 통합**하므로 그 전제가 사라진다.

→ 설정파일에는 **저장 경로만** 둔다(`[paths] data_dir`). 디스크 링·`TRANSFER DISK<n>`/`REQ SWAP`/`ACK SWAP` 핸드셰이크는 내부 구현에서 제거했다.

### 6.3 새로 확인된 노드와 sourceID

- **`CHA` 노드** — `ICS>CHA DONE: EXPNUM  Filename=20240628.021488`, `M.IC>CHA DONE: EXPNUM  Filename=KMTNm.20240628.5956`, `M.IC>CHA DONE: INITIALIZE  Initialization Complete.` (SSO, 2024-06-28 전후, 2,441회). ICS 와 개별 IC 양쪽에 `EXPNUM`·`INITIALIZE` 를 보내는 **엔지니어링/운영자 콘솔 클라이언트**로 보인다. 성격 미확정.
- **`C1` sourceID** — `T.IC>T.CB TRANSFER DISK0 <n> C1` (CTIO 3~6회). `ICS`/`OBS`/`ABC` 외의 전송 요청 주체.
- **`0`** — `K.IC>0 STATUS: …` (1회). 5.3 의 노드명 파괴 사례이지 실재 노드가 아니다.

→ **신규 `ics` 는 발신 노드를 특정하지 않는다.** 프로토콜에 맞는 메시지면 누가 보냈든 처리하고 요청자에게 응답한다. 검증: `test_impv2.py::test_unknown_node_still_served`.

### 6.4 새로 확인된 에러·경고 메시지

```
ICS>OBS ERROR: GO  Data acquisition already in progress! EXPSTATUS=<st>
    → GO 중복 거부.  OBSAgent 도 CamStatus 가 IDLE_3/READY 가 아니면 GO 를 막지만,
      ICS 자체 방어선이 따로 있다.
*.IC>OBS ERROR: DATASOURCE  Invalid selection for DataSource. ADC, CTC, and SIM are valid. DataSource=<cur>
    → 문서에 없던 제3의 값 SIM 이 존재한다.  시뮬 백엔드를 DATASOURCE SIM 으로
      노출하면 프로토콜상 자연스럽게 맞물린다 (9장).
K.CB>ICS ERROR: No SIMPLE card in FITS file #2, skipping...        (SSO)
    → CB 가 쓰다 만/손상된 FITS 를 만났을 때.  디스크 슬롯 번호가 함께 나온다.
*.CB>{ICS,OBS} WARNING: FITS file '<path>' already exists, writing as '/mnt/ICSData/<yymmdd>.<nnn>.fits' instead
    → ICS 와 OBS **양쪽으로** 발신된다 (기존 보고서는 OBS 방향만 기록).
```

파일명 fail-safe 는 1999년 Prospero 시절부터 이어진 데이터 유실 방지 장치다. 신규에서도 그대로 유지한다.

### 6.5 텔레메트리 중계 실패 형태

```
ICS>N.IC STATUS: AUXSTATUS  KBUILD=… MBUILD=… TBUILD=… NBUILD=… GBUILD= ICSBUILD=… EXPSTATUS=ERASE
```

TC 질의가 실패하면 **TC 필드 전체가 비고 ICS 가 덧붙이는 꼬리만** 남은 채 그대로 중계된다(CTIO 4회, SSO 144회). **노출은 중단되지 않고 진행되며**, 그 노출의 FITS 헤더는 망원경 정보가 빈 채로 저장된다.

시뮬 기본값(`tc_timeout_mode = passthrough`)은 이 형태를 재현한다. `canned` 로 바꾸면 내장 텔레메트리로 채운다.

### 6.6 기타 형식 변형

- `K.IC>ICS DONE: STATUS  Inst=KMTNk … -FIBERS +SYNCH …` — **`-FIBERS`**(광케이블 미연결) 플래그. 샘플엔 `+FIBERS` 만 있었다. `Driving=0`/`1` 도 함께 변한다.
- **`FLASHNOW` 실사용 확인** — `K.IC>ICS DONE: FLASHNOW  LED Flash Done.` (CTIO 4,700+회). LED 프로젝터 점검 시퀀스가 실제 운용에서 정기적으로 돈다.
- `ICS>OBS DONE: DARK  ImageType=DARK ObjectName='end' EXP=0` — `EXP=0` 인 DARK(관측 종료 시 관례적으로 찍는 이름 `end`).
- `SYNCHRONIZE` 가 `DONE:`(CTIO 2,230회)와 `STATUS:`(1,284회) 두 타입 모두로 발신.
- `K.CB>ICS STATUS: Wrote …`(SSO) vs `DONE: Wrote …`(CTIO) — ~~사이트/빌드별 타입 차이~~ → **SSO 고유 결함이었다. 6.9절.**
- `ICS>OBS STATUS: GO  EXPSTATUS=INITIALIZING`(SSO 7회) 형태.

### 6.7 전량에서도 "없음"이 확인된 것

- **`FATAL:` 메시지 0건.** 샘플 기준 관찰이 48GB 전량에서도 유지된다.
- **`STOP`/`ABORT`/`BIN`/`ROI`/`DISPL`/`MOVIE` 송수신 0건.** ~~문서상 "미구현"이 운용에서도 한 번도 쓰이지 않았음이 확인된다.~~ → **0건인 것은 맞지만 이유가 달랐다. 6.8절.**

### 6.8 명령 테이블 실측 — "미구현" 서술의 정정 (2026-08-04)

`IC2.img` 의 ICS 소스에서 디스패치 테이블을 그대로 뽑았다. 전제가 틀렸다.

**ICS 는 공용 명령 세트를 포함하지 않는다.** `KMTX\PAP7KX.BAS` 는 명령 파서로 `KMTX\PAP7KX.CMD`(`CASE` 100개) **하나만** `#INCLUDE` 한다. 소스 주석이 명시한다 — *"This is the only IC that doesn't use the shared command set code"*. 과학 IC(`KMTS\PAP7KS.BAS`)는 `SHARE\PAP7.CMD`(202개)를 넣는다.

그래서 6개 명령은 **두 가지 다른 상황**이 뭉뚱그려져 있었다:

| 명령 | ICS | 공용 | 실제 |
|---|:---:|:---:|---|
| `BIN` `STOP` `ABORT` | ✅ | ✅ | **레거시 ICS 에 구현되어 있다.** 로그 0건은 "안 썼다"는 뜻 |
| `ROI` `DISPL` `MOVIE` | ❌ | ✅ | **ICS 에 아예 없다.** 레거시 ICS 는 `ERROR: … Didn't understand … ?` 로 거부 |

`STOP`/`ABORT` 의 레거시 동작도 소스에 그대로 있다(`PAP7KX.CMD:279-302`) — 진행 중이면 플래그를 내리고 `AbortHost` 를 기록, 아니면 `ERROR: No integration in progress. Nothing to stop.` / `ERROR: No acquisition in progress. Nothing to abort.`

**코드 반영 (`commands.py`)**

- `UNIMPLEMENTED` 상수를 **`NOT_YET_IMPLEMENTED = ('BIN','STOP','ABORT')`** 로 좁혔다. "레거시가 미구현" 이 아니라 "**우리가** 아직 안 만들었다" 이므로 이름도 바꿨다.
- **`cmd_roi` / `cmd_displ` / `cmd_movie` 핸들러를 삭제했다.** 핸들러가 없으면 디스패처가 기본 경로로 `ERROR: … Didn't understand …` 를 내는데, 그게 바로 레거시 ICS 의 동작이다. **핸들러를 두는 것이 오히려 레거시와 어긋났다.**
- `cmd_stop`/`cmd_abort` 의 docstring 에 레거시 분기와 거부 문자열을 그대로 적어 두었다. 구현할 때 그대로 옮기면 된다.
- 참고용 `IC_ONLY` 상수를 추가했다 — ICS 범위 밖 명령 목록(`ROI` `DISPL` `MOVIE` `SNAP` `DMAWAIT` `FLASHNOW`). 핸들러를 실수로 추가하지 않도록 하는 표지다.

> **13장 백로그 조정**: `STOP`/`ABORT` 는 "레거시에 없던 기능을 새로 넣는 일"이 아니라 **"레거시에 있는 기능을 아직 안 옮긴 것"** 이다. 우선순위를 올린다.

### 6.9 SSO 의 `Wrote` 중계 단절 — 사이트 고유 결함 (2026-08-04)

6.6 에서 `CB>ICS` 의 `Wrote` 타입이 CTIO(`DONE:`)와 SSO(`STATUS:`)가 다른 것을 "빌드 차이"로 적고 넘어갔다. **영향이 없다고 본 것이 틀렸다.**

ICS 의 중계 코드(`KMTX\PAP7KX.CMD:1327-1335`)는 `DONE:` 을 `STATUS:` 로 바꿔 노출 개시자에게 되돌리는데, 분기 조건이 `Words(1) = "DONE:"` 이다. CB 가 `STATUS: Wrote` 로 보내면 **중계가 아예 일어나지 않는다.** 로그 실측이 정확히 그렇다:

| 사이트 | ICS 빌드 | `CB>ICS DONE:` | `CB>ICS STATUS:` | `ICS>OBS` 중계 |
|---|---|---:|---:|---:|
| CTIO | `KX2016-03-23:1381` | 1,176 / 908 | 0 | **1,176 / 908** |
| SAAO | 〃 | 1,058 / 1,007 | 0 | **1,058 / 1,007** |
| SSO | 〃 | 0 | 546 / 872 | **0** |

세 사이트 ICS 빌드는 같다. 원인은 **Caliban 쪽**이고, 커밋해둔 사이트별 소스에 그대로 있다 — `__dts_legacy/dts.icsci.20190326.<site>/dts.icsci/Agents/Caliban/src/GetFITS.c:532` 가 CTIO·SAAO 는 `"DONE: Wrote …"`, SSO 만 `"STATUS: Wrote …"` 다.

**운영상의 의미 — 처음에 과장했다가 바로잡은 부분**

`FitsSaved` 는 `Wrote` 4회로 서므로(3.2) SSO 에서는 `force_fitssaved=560`(≈25초) 타임아웃으로만 세워진다. 여기까지 확인하고 **"SSO 는 매 노출 `WARNING` 과 `ExpStatus=ERROR` 가 뜬다"고 적었는데, 틀렸다.** OBSAgent `main.c:692-708` 에 **SSO 전용 분기가 이미 있다**:

```c
if( sys.force_fitssaved < sys.count_fitssaving ) {
  sys.status_fitssaved = 1;
  if( strcasecmp(client.isisHost,"192.168.15.109") ) {   // SSO 가 아니면
    … "WARNING: Writing FITS data is not fully completed !!"
    expinfo.nStatus = EXPSTATUS_ERROR;
  }
  else {                       // SSO 면 조용히 통과
    strcpy(expinfo.strFitsNum, expinfo.strPreNum);
  }  // added in v1.0.6 for SSO
}
```

`obsagent_report.md` §6.1 에 이 분기를 이미 적어 두었는데도 놓쳤다 — **내가 쓴 문서를 확인하지 않고 새 발견의 파급을 추정한 것**이다. 12.11 에 기록한다.

**실제로 남는 영향**은 둘이다:

1. **노출 후 `FitsSaved` 까지 항상 ≈25초.** 메시지로 앞당길 수 없어 SSO 의 노출 간격에 하한이 생긴다(CTIO·SAAO 는 마지막 `Wrote` 도착 즉시, 통상 16초).
2. **`FitsNum` 이 `strPreNum`(직전 번호) 추정값**이다. 실제 저장 파일명이 아니다.

**그리고 진짜 문제는 원인 진단이 틀려 있다는 것이다.** 소스 주석은 원인을 *"no 'Wrote' message anymore due to IC upgrade at v0.2.9 at SSO"* — **IC 버전 문제**로 적었다. 실제 원인은 **Caliban 의 메시지 타입 한 단어**이고 IC 와 무관하다. 그래서 주석의 *"should be removed after SSO IC version is upgraded"* 는 영영 충족되지 않고, 우회는 **IP 주소 하드코딩**에 매달려 있다. 고칠 곳은 SSO Caliban `GetFITS.c:532` 의 `STATUS:` → `DONE:` 한 단어다.

**설계 결정**: `ics_sim` 은 **CB 측 타입과 무관하게 항상 `ICS>OBS STATUS: Wrote …` 를 4회 방출한다.** 사이트별 분기를 두지 않는다 — 이 결함은 재현 대상이 아니라 회피 대상이다. `[node] site` 값이 `sso` 여도 마찬가지다. 현재 구현이 이미 그렇게 동작하므로 코드 변경은 없다.

---

## 7. 설정파일 레퍼런스 (`ics_sim.ini`)

**모든 동작 파라미터는 여기서 편집한다.** 주석 문자는 `#` 하나이고 **줄 어디에나 올 수 있으며, `#` 앞의 내용은 유효하다**. CLI 인자가 같은 키를 덮어쓴다.

### `[node]` — 노드 정체성

| 키 | 기본값 | 설명 |
|---|---|---|
| `site` | `ctio` | `ctio` / `saao` / `sso` / `testbed` |
| `telid` | `KMTC` | AUXSTATUS 의 TELID. ctio=KMTC, saao=KMTS, sso=KMTA |
| `ics_id` | `ICS` | 통합 노드 이름 |
| `ic_ids` | `K.IC, M.IC, T.IC, N.IC` | 수신할 IC 노드 ID (3.1) |
| `cb_ids` | `K.CB, M.CB, T.CB, N.CB` | 수신할 CB 노드 ID |
| `master` | `K` | readout 진행률(PCTREAD)을 보고하는 master CCD |
| `guide_ic_id` | `G.IC` | INITIALIZE 만 보낸다. ICG 자체는 범위 밖 |
| `emit_node_mode` | `legacy` | `legacy`=노드별 발신 / `merged`=전부 ICS 이름. **둘 다 규약을 통과해야 한다** |

### `[transport]` — UDP

| 키 | 기본값 | 설명 |
|---|---|---|
| `bind_host` / `bind_port` | `127.0.0.1` / `6600` | 수신 소켓 |
| `xis_host` / `xis_port` | (빈 값) / `6660` | 비우면 direct-reply 모드 |
| `send_gap_ms` | `2` | rate-limited 발신 큐 간격. 레거시 `dispatcher.cpp` 패턴 |
| `peer_ttl_sec` | `3600` | 학습한 피어 주소 유효시간 |
| `register_all_nodes` | `true` | 기동 시 **9개 노드 ID 전부로 PING** 을 보내 XIS에 등록(3.1.1). `false` 면 `ICS` 만 등록되고 `kstatus`/`dmawait`/`datasource` 가 도달하지 않는다 |

> `bind_host` 기본값이 `127.0.0.1` 이라 **로컬에서만 받는다.** 외부 XIS·OBSAgent와 붙이려면 `0.0.0.0` 으로 바꿀 것. `bind_port=6600` 은 레거시 IC 계열 관례 포트라 **같은 호스트에 실제 `K.IC` 가 있으면 충돌**한다(3.1.1 (11)).

### `[paths]` — 저장

| 키 | 기본값 | 설명 |
|---|---|---|
| `data_dir` | `./icsdata` | **단일 저장 경로.** 레거시 DISK0~3 링은 폐지(6.2) |
| `write_fits` | `false` | true 면 astropy 로 더미 FITS 생성 |
| `fits_shape` | `256, 256` | 더미 이미지 크기 |

### `[timing]` — 노출 타이밍 (초, 전부 실측 중앙값)

| 키 | 기본값 | 근거 |
|---|---|---|
| `time_scale` | `1.0` | 전체 축척. `[obsagent]` 창은 축척 제외 |
| `go_to_initializing` | `0.81` | 4.1 t+0.81 |
| `initialize_ack` | `0.40` | 4.1 t+1.22 - t+0.82 |
| `erase_sec` | `7.24` | 4.1 t+8.55 - t+1.30 |
| `aux_relay_gap` | `0.058` | 4개 IC 중계 간격 |
| `tcs_relay_gap` | `0.029` | 〃 |
| `shutter_open_delay` | `0.15` | 4.2 SHOPEN → Shutter=Open |
| `countdown_tick_dark` | `5.00` | DARK/BIAS 의 `Remaining=N sec. of M sec.` |
| `countdown_tick_shop` | `5.217` | OBJECT 의 `Integration Remaining=N sec.` |
| `shutter_to_readout` | `6.00` | 4.2 Shutter=Closed → EXPSTATUS=READOUT |
| `acq_to_idle` | `0.40` | 4번째 Acquisition Complete. → EXPSTATUS=IDLE. **3.3 의 0.9초 창 안** |
| `write_delay` | `3.40` | 획득 완료 → Wrote |
| `ccd_skew` / `ccd_skew_order` | `0.0, 0.6, 0.7, 1.6` / `N, T, M, K` | CCD 별 저장 시차 |
| `tc_query_timeout` | `0.50` | TC 응답 대기 |
| `tc_timeout_mode` | `passthrough` | `passthrough`=빈 필드 중계(6.5) / `canned`=내장값 |

### `[readout]` — PCTREAD 진행률 모델

| 키 | 기본값 | 설명 |
|---|---|---|
| `pctread_start` | `6` | 실측: 6 → 17 → … → 94 → 100 |
| `pctread_step` | `11` | |
| `pctread_tick` | `3.37` | 틱 간격(초) |
| `pctread_final` | `100` | 도달 시 `Acquisition Complete. Disk Transfer Starting.` |

> **이 모델은 근사가 아니라 정확한 재현이다.** `samples_for_bug_pctread.txt`(노출 294회분)에서 `6·17·28·39·50·61·72·83·94·100` 이 **각각 정확히 294회**씩 나온다 — 편차가 0이다. 레거시 IC 는 진행률을 실제 픽셀 카운트가 아니라 고정 스텝으로 보고했다는 뜻이다.
>
> 실기(`archon` 백엔드)에서는 컨트롤러의 실제 진행률을 그대로 흘려보내면 되고, 값이 촘촘해져도 OBSAgent 는 문제없다 — `PCTREAD=` 는 2회 이상이면 `READ_3` 에 도달한다(3.2).

### `[obsagent]` — OBSAgent 쪽 상수 (자가검증용, 3.3)

| 키 | 기본값 | 의미 |
|---|---|---|
| `tick_sec` | `0.045` | 주기 루프 1카운트 |
| `force_idle` | `40` | ~1.8초 |
| `force_ready` | `270` | ~12.2초 |
| `force_fitssaved` | `560` | ~25초 |

### `[behavior]` — 동작 스위치

| 키 | 기본값 | 설명 |
|---|---|---|
| `strict_legacy` | `true` | 미구현 명령을 레거시처럼 무응답 처리 |
| `bug_compat` | `false` | 레거시 커맨드워드 오염 재현 (5.4-6) |
| `send_guide_init` | `true` | `ICS>G.IC INITIALIZE` 발신 여부 |
| `console` | `true` | stdin 키보드 인터페이스 |
| `inject` | (빈 값) | 결함 주입: `init_fail`, `acq_short`, `wrote_drop`, `dma_timeout`, `shopen_corrupt`, `tc_timeout` |

### `[hardware]` / `[logging]`

| 키 | 기본값 | 설명 |
|---|---|---|
| `backend` | `sim` | `sim` / `archon`. 실기 전환은 이 한 줄(9장) |
| `level` | `info` | `debug`/`info`/`warning`/`error` |
| `wire` | `true` | 송수신 메시지를 콘솔에 출력 |
| `file` | (빈 값) | 파일 로깅 경로 |

---

## 8. 코드 구조

```
ics_sim/
├── README.md · DevNote.md · SMC_CLAUDE.md · ics_sim.ini
├── ics_sim/
│   ├── config.py          ini 로드 → SimConfig, 값 검증(3.3 창 침범 포함)
│   ├── impv2.py           Message 파싱/조립, 노드명 검증, key=value
│   ├── transport.py       UdpEndpoint — XIS 경유/직접회신 + rate-limited 발신 큐
│   ├── nodes.py           9개 노드 ID 등록·수신 라우팅 (3.1)
│   ├── state.py           IcsState + ChannelState(K/M/T/N) + 파일명
│   ├── telemetry.py       TC 질의, pass-through 역순 직렬화, sentinel (4.3)
│   ├── emitter.py         메시지 방출 전담 + 오염 검증기 (5.4)
│   ├── sequencer.py       노출 상태머신(asyncio), GO n 포함
│   ├── commands.py        명령 디스패치 + 미구현 스텁 (9.2)
│   ├── obsagent_model.py  OBSAgent CamStatus 재현 — 검증과 로그 재생에 공용
│   ├── app.py             배선
│   ├── console.py         로컬 키보드 인터페이스
│   ├── fitsout.py         FITS 생성
│   ├── __main__.py        CLI
│   └── hardware/
│       ├── base.py        DetectorBackend 계약 (9.1)
│       ├── sim.py         시뮬 백엔드
│       └── archon.py      **실기 구동 코드가 들어갈 자리** (스텁)
├── tools/
│   ├── scan_legacy_logs.py    5·6장 스캐너 (재검증용)
│   └── extract_golden.py      골든 픽스처 생성
└── tests/
    ├── conftest.py            헤드리스 실행 헬퍼
    ├── fixtures/golden_*.txt  레거시 시퀀스 발췌 (커밋)
    ├── fixtures/bug_patterns.txt  오염 샘플 (커밋)
    ├── test_impv2.py
    ├── test_emitter_hygiene.py
    ├── test_obsagent_contract.py
    └── test_sequence_golden.py
```

**저장소 관례를 따른다**: `pyproject.toml` 없음, 평범한 패키지 디렉토리 + `__init__.py`, `#!/usr/bin/env python3` + `# -*- coding: utf-8 -*-` 헤더, `from __future__ import annotations`, pytest. **표준 라이브러리만 필수**이고 astropy/numpy 는 FITS 옵션에서만 lazy import 한다.

### 8.1 `samples_for_bug.txt` 의 위치 — 복사하지 않고 파생본을 둔다

사용자가 제공한 `ics_legacy/__sample_isislog/samples_for_bug.txt`(2,755행)는 **원본 위치에 그대로 두고 git 에 커밋**한다. 이 파일은 `.gitignore` 에 걸리지 않는다(`__sample_isislog/` 에서 무시되는 것은 `*.log` 뿐).

`ics_sim/` 에는 **복사본 대신 파생 픽스처** `tests/fixtures/bug_patterns.txt` 를 둔다. `tools/scan_legacy_logs.py patterns` 가 중복을 제거한 오염 패턴 목록(패턴별 대표 1행 + 관측 건수, 18종)을 뽑아 만든다.

- 원본은 **레거시 조사 증거물**이라 `ics_legacy/` 에 속한다. 같은 파일을 두 곳에 두면 나중에 갈라진다.
- 위생 테스트에 필요한 건 2,755행 전체가 아니라 **서로 다른 오염 패턴**뿐이다.
- 파생 픽스처가 커밋되므로 원본이 없는 환경에서도 테스트가 돈다.

---

## 9. 하드웨어 확장점 — 다음 단계로 가는 통로

이번 산출물은 시뮬이지만 **다음 단계에서 실제 CCD 를 구동해 영상을 얻고 FITS 로 저장**한다. 그래서 처음부터 아래 구조로 짰다.

### 9.1 `DetectorBackend` 계약 (`hardware/base.py`)

시퀀서는 하드웨어를 직접 만지지 않고 이 인터페이스만 호출한다. `sim.py` 는 `asyncio.sleep` 과 난수 이미지로, `archon.py` 는 실제 컨트롤러로 같은 계약을 구현한다.

```python
class DetectorBackend(Protocol):
    async def initialize(self, ccd: str, suffix: str) -> None: ...
    async def erase(self, ccd: str) -> None: ...
    async def open_shutter(self, seconds: float) -> None: ...
    async def close_shutter(self) -> None: ...
    async def flash_led(self, milliseconds: int) -> None: ...
    def readout(self, ccd: str) -> AsyncIterator[int]: ...        # 진행률 yield
    async def fetch_image(self, ccd: str): ...
    async def write_fits(self, ccd: str, path: str, header: dict) -> int:  # → KB/sec
    def status(self, ccd: str) -> dict: ...
```

**`readout()` 이 진행률을 `yield` 하도록 만든 것이 핵심이다.** 시뮬에서는 `[readout]` 설정대로 6→17→…→100 을, 실기에서는 컨트롤러가 보고하는 실제 진행률을 그대로 흘려보낸다. PCTREAD 메시지를 만드는 쪽은 어느 쪽이 오는지 알 필요가 없다 — **시퀀서 코드를 고치지 않는다.**

전환은 `[hardware] backend = archon` 한 줄.

**이미 있는 자산**:

| 파일 | 쓸모 |
|---|---|
| `cam_char/archon/archon_kmtnet_labtest_v2.py` | Archon 텍스트/바이너리 프로토콜로 노출·FETCH 까지 하는 실동작 스크립트. 명령 시퀀스(POWERON, LOADPARAM, FASTPREPPARAM/RELEASETIMING, STATUS/FRAME 폴링, 1 KiB 블록 FETCH)를 그대로 옮기면 된다 |
| `cam_char/archon/archon_simulator.py` | 하드웨어 없이 위 스크립트를 시험하는 프로토콜 시뮬레이터. 이 백엔드 개발 시 상대역 |
| `mef_converter/` · `mef_fits_spec/` | Archon raw → L0 64-amp MEF 규격. `write_fits()` 가 최종적으로 맞출 산출물 형식 |

**구현 시 유의할 점** (전부 3.3 의 시간 창에서 나온다):
- 4개 CCD 를 병렬로 읽되 **4개의 획득 완료가 1.8초 안에** 모여야 한다. 넘으면 OBSAgent 가 스크립트 관측을 멈춘다.
- 4번째 획득 완료 후 **0.9초 안에** `EXPSTATUS=IDLE` 을 내야 한다.
- `write_fits()` 는 4개 파일을 **25초 안에** 다 써야 한다.
- `config.validate()` 가 기동 시 이 창을 검사하므로, 실측 타이밍을 `[timing]` 에 넣으면 자동으로 경고가 뜬다.

### 9.2 명령 처리부는 전부 "구현 자리"를 갖는다

`commands.py` 는 명령마다 핸들러 함수를 **하나씩 실제로 만들어 뒀다.** 아직 동작하지 않는 것도 docstring 과 레거시 근거 주석을 갖춘 스텁으로 존재한다:

```python
def cmd_abort(self, msg, target) -> Reply:
    """ABORT -- 전체 중지, readout/저장 안 함.

    레거시 상태: **구현되어 있다** (PAP7KX.CMD:291-302).
        IF GoFlag = 1 THEN PauseFlag=0 : ExpLoopFlag=0 : GoFlag=0
                            AbortHost = 발신자
        ELSE  ERROR: No acquisition in progress. Nothing to abort.
    구현 시: self.app.seq.cancel(save=False) 후 EXPSTATUS=IDLE 을 발신한다.
             진행 중이던 저장 태스크도 정리해야 한다.
    """
    return self._unimplemented(msg, target)
```

**대상은 `BIN` · `STOP` · `ABORT` 세 개다** (2026-08-04 정정, 6.8절). 전에는 `ROI`/`DISPL`/`MOVIE` 도 같은 묶음이었는데, 소스를 보니 이 셋은 **ICS 명령 테이블에 아예 없어서** 레거시가 `ERROR: … Didn't understand … ?` 로 거부한다. 그래서 **핸들러를 삭제했다** — 없는 편이 레거시와 같다. 참고용 `IC_ONLY` 상수에 목록만 남겼다.

`strict_legacy=true` 면 세 스텁은 **무응답**이다. 레거시가 이들을 어떤 형식으로 응답하는지 48GB 로그에 한 건도 없어 재현할 근거가 없기 때문이지, "레거시가 미구현이라서"가 아니다. `false` 면 `ERROR:` 를 돌려주는 현대화 모드가 되고, 실제 구현을 넣을 때는 스텁 본문만 채우면 된다 — 레거시 분기와 거부 문자열이 docstring 에 이미 적혀 있다.

### 9.3 FITS 경로

`fitsout.py` 는 지금은 더미 배열을 쓰지만, **헤더 생성(AUX/TCS 텔레메트리 → FITS 키워드)은 처음부터 실제와 같은 경로**로 만들었다. 다음 단계에서 `fetch_image()` 가 실제 픽셀을 돌려주면 그대로 저장된다.

`mef_fits_spec/` 의 KMT-CEU 키워드 규격과의 정합은 실기 단계에서 붙인다. 지금은 레거시 헤더 재현까지가 목표다.

---

## 10. 테스트 전략

```bash
cd ics_sim
python -m pytest tests -q
```

현재 **113개 전부 통과**.

| 파일 | 지키는 것 |
|---|---|
| `test_obsagent_contract.py` | **최우선.** 3장 규약 전체 — 상태 전이, 개수 규약, 타임아웃 창, `ExpNum` 왕복, 응답 체크 문자열, 수신 9노드, `GO n` |
| `test_emitter_hygiene.py` | 5장 오염 방지 — 정방향(시뮬 출력이 깨끗한가) + **역방향**(레거시 샘플을 잡아내는가) |
| `test_sequence_golden.py` | 4·6장 — 레거시 실측 시퀀스와 메시지 종류·순서·개수 일치 |
| `test_impv2.py` | 프로토콜 파싱 — malformed 무응답, 대소문자 무관, 다중 단어 값, 깨진 명령 거부 |

**음성 테스트**(일부러 깨뜨려 검출을 확인하는 것)를 여러 곳에 뒀다. 없으면 검증기가 껍데기여도 통과하기 때문이다:

- `test_config_self_check_flags_bad_timing` — 창을 좁히면 실제로 경고가 나오는가
- `test_short_acquisition_trips_opause_path` — `Acquisition Complete.` 3회면 위반으로 잡히는가
- `test_missing_wrote_is_detected` — `Wrote` 3회면 `FitsSaved` 가 안 서는가
- `test_legacy_contamination_is_detected` — `bug_patterns.txt` 18종이 전부 위반인가
- `test_bug_compat_reproduces_contamination` — `bug_compat` 을 켜면 실제로 더러워지는가

**`obsagent_model.py` 를 검증과 로그 재생에 공용으로 쓰는 것이 중요하다.** 실측에서 나온 전이 패턴과 시뮬이 만드는 전이 패턴을 같은 자로 재야 비교가 성립한다.

---

## 11. 설계 결정 기록

각 항목은 *배경 → 대안 → 선택 → 이유* 순.

### 11.1 디스크 다중화 폐지

- **배경**: 레거시는 `DISK0`~`DISK3` 를 돌리며 `TRANSFER`/`REQ SWAP`/`ACK SWAP` 핸드셰이크를 했다(6.2).
- **대안**: (a) 그대로 재현 (b) 2중만 유지 (c) 폐지하고 단일 경로.
- **선택**: (c).
- **이유**: 다중화의 두 근거가 모두 사라진다. 1998년 SCSI 성능 최적화는 현대 스토리지에서 의미가 없고, NFS 전송시간 확보는 **취합 서버와 기기제어를 단일 PC 에 통합**하면 불필요하다. 설정파일에 저장 경로 하나만 둔다.

### 11.2 텔레메트리 필드 pass-through

- **배경**: AUXSTATUS 필드 집합이 사이트마다 다르다(4.3).
- **대안**: (a) 사이트별 테이블 유지 (b) 받은 대로 넘기기.
- **선택**: (b). 없는 필드는 sentinel(`0`/`NC`).
- **이유**: 테이블을 유지하면 사이트가 늘거나 AUX 펌웨어가 바뀔 때마다 코드를 고쳐야 한다. ICS 가 알아야 할 것은 "어디까지가 TC 필드인가"뿐이고, 그건 자기가 붙이는 꼬리를 아는 것으로 충분하다.

### 11.3 DARK/BIAS 의 `Shutter=Closed` 관례 유지

- **배경**: 셔터를 연 적 없는데 "닫혔다"고 보고한다(3.2.1).
- **대안**: (a) 없애고 다른 종료 알림 (b) 유지.
- **선택**: (b).
- **이유**: OBSAgent 가 이걸로 `CLOSING` 을 밟고 곧바로 `PCTREAD=` 로 `READ_1` 이 된다. 없애면 `CLOSING` 을 건너뛰고, 그 경로가 검증된 적이 없다. 의미상 어색해도 동작이 확실한 쪽을 택했다.

### 11.4 `EXPSTATUS=` 알림은 전이 시 1회, `OBS` 로만

- **배경**: 레거시는 셔터 닫힘 후에도 `INTEGRATING` 을 반복했고, IC 앞 텔레메트리 중계에도 `EXPSTATUS=` 를 실었다.
- **선택**: 상태가 실제로 바뀌는 시점에 1회, `OBS` 로만.
- **이유**: 후자가 `OBS` 로도 가면 CamStatus 가 `INT_1` 으로 역행한다(3.2.1). 레거시가 안전했던 것은 그 메시지가 `*.IC` 앞으로 갔기 때문이지 내용이 무해해서가 아니다. 통합 구조에서 그 경계가 사라지므로 명시적 규칙이 필요하다.

### 11.5 `bug_compat` 플래그를 둔 이유

- **배경**: 골든 대조는 레거시 로그와 맞춰야 하는데, 레거시 로그에는 오염이 들어 있다.
- **대안**: (a) 골든 대조에서 오염분을 정규화 (b) 재현 모드를 둔다.
- **선택**: 둘 다. 기본은 꺼짐.
- **이유**: 재현 모드가 있으면 **"오염이 있어도 OBSAgent 규약은 만족한다"** 를 실행으로 보일 수 있다. 그게 레거시가 수년간 이 상태로 운용된 이유를 설명한다. 동시에 꺼진 상태의 청결성도 검증된다.

### 11.6 수신 9노드 / 발신 자유의 비대칭

- **배경**: 3.1.
- **선택**: 수신은 9개 ID 전부, 발신은 `emit_node_mode` 로 선택.
- **이유**: OBSAgent 의 필터는 발신자만 보지만, 명령은 노드별 주소로 온다. 비대칭이 실재하므로 코드도 비대칭이어야 한다.

### 11.7 미상 노드도 프로토콜대로 처리

- **배경**: `CHA`/`C1` 같은 문서에 없는 클라이언트가 명령을 보낸다(6.3).
- **선택**: 발신자 화이트리스트를 두지 않는다.
- **이유**: IMPv2 에 노드 인증 개념이 없고 레거시도 그랬다. 화이트리스트를 두면 운영자가 임시 도구를 붙일 때마다 코드를 고쳐야 한다.

### 11.8 명령 처리부를 전부 스텁으로라도 만든다

- **배경**: `STOP`/`ABORT` 등 6개가 레거시에서 미구현이고 로그에도 0건(6.7).
- **대안**: (a) 아예 없애기 (b) 스텁 + 구현 지침.
- **선택**: (b).
- **이유**: 다음 단계에서 본문만 채우면 된다. 특히 `STOP`/`ABORT` 는 운영 편의상 실제 구현 가치가 높다(13장).

### 11.9 INI 주석은 `#`, 인라인 허용

- **이유**: 값 옆에 실측 근거를 적을 수 있어야 설정파일 자체가 문서 역할을 한다. `configparser` 를 `comment_prefixes=('#',)`, `inline_comment_prefixes=('#',)` 로 만든다.

### 11.10 XIS 등록 — 단일 소켓(1안) 채택, 잠정

- **배경**: 통합 `ics` 는 9개 노드 ID로 메시지를 받아야 하는데(3.1), IMPv2에는 등록 API가 없어 "그 이름으로 메시지를 한 번 보내기"가 곧 등록이다.
- **대안**: (a) 단일 소켓에서 9개 ID로 PING (b) 노드마다 소켓/포트를 따로 열기.
- **선택**: (a). 단 `register_all_nodes` 스위치를 남기고, XIS 소스 확보 시 재검토하기로 했다.
- **이유**: 로그 실측으로 XIS가 **노드ID→주소** 방향 테이블을 갖는다는 것은 확인됐다(`ABC`/`GMON` 이 ephemeral 포트로 매번 바꿔 보내는데도 응답을 받는다). 다만 **같은 (IP,port)에 여러 ID를 올린 사례가 48GB 전체에 없고** XIS 서버 소스도 없어 안전을 확신할 수 없다. 구현 비용이 낮은 쪽을 먼저 하고, 실물 시험이나 소스 확인에서 문제가 드러나면 (b)로 간다.
- **보강 (2026-08-04)**: XIS의 `Added UDP Client` 로그 분석에서 **테이블이 노드 ID로 키잉된다**는 강력한 증거가 나왔다(3.1.1 (4)) — `ABC`/`GMON` 이 하루 수천 번 주소를 바꿔도 `Added` 는 XIS 재시작당 1회뿐이다. 1안의 위험도가 크게 낮아졌지만 "ID로 키잉된다"와 "같은 주소를 여러 ID가 공유해도 된다"는 별개 명제라 소스 확인은 그대로 유지한다.
- **전환 조건과 확인 항목**: 3.1.1 (8)절.

---

## 12. 정정 이력

조사 중 **틀렸다가 바로잡은 것**을 남긴다. 재조사 비용을 줄이고, 같은 함정을 다시 밟지 않기 위해서다.

### 12.1 "`INT_3 ↔ INT_1` 역행이 26,583건" → **실제 0건**

가장 값진 정정이다.

처음 CamStatus 재생 스크립트를 돌렸을 때 `INT_3 → INT_1` 역행이 26,583건 나왔고, "K.IC 의 카운트다운과 ICS 의 `EXPSTATUS=INTEGRATING` 이 노출 중 번갈아 도착하기 때문"이라고 해석했다. **틀렸다.**

원인은 재생 스크립트에 **`dest` 필터가 빠진 것**이었다. OBSAgent 는 자기 앞으로 온 메시지만 보는데, 스크립트는 XIS 로그의 모든 메시지를 먹였다. 그래서 `ICS>N.IC STATUS: TCSSTATUS … EXPSTATUS=INTEGRATING` 같은 **IC 행 중계**까지 상태머신에 들어갔다. `dest ∈ {OBS, AL, ALL}` 로 거르자 역행은 **0건**이 됐다.

> **이 정정에서 오히려 신규 설계 제약이 도출됐다**(3.2.1). 레거시가 `EXPSTATUS=` 를 마구 뿌려도 안전했던 것은 수신 주소 덕이었고, 통합 구조에서 그 경계가 사라지므로 명시적 규칙이 필요하다. **틀린 측정이 없었으면 이 제약을 놓쳤을 것이다.**

교훈: OBSAgent 동작을 재현할 때는 **발신 노드 필터(commands.c 757)만이 아니라 수신 주소도** 함께 봐야 한다. `obsagent_model.py` 에 두 필터를 모두 못박고 docstring 에 이 사연을 적어 뒀다.

### 12.2 "디스크는 이중화" → **최대 4중**, 그리고 신규에서는 폐지

샘플 로그에 `DISK0`/`DISK1` 만 나와 "이중버퍼"로 정리했으나, 전량 스캔에서 `DISK2`·`DISK3` 가 나왔다(6.2). 그리고 신규 구조에서는 다중화 자체가 불필요하다는 결론에 이르렀다(11.1).

### 12.3 "상태 전이는 선형" → **건너뜀이 일상적**

`NC→PREP_I→…→READY` 를 순서대로 밟는다고 서술했으나, 실측에서 `INT_1 → CLOSING`(1,252건) 등 건너뜀이 흔하다(3.2.1). DARK/BIAS 가 `Shutter=Open` 을 안 보내기 때문이다.

### 12.4 "`Wrote` 는 CB 가 OBS 로 직접" → **ICS 중계**

`K.CB>ICS DONE: Wrote …` 를 보고 CB 가 직접 보고한다고 생각했으나, OBSAgent 가 실제로 세는 것은 `ICS>OBS STATUS: Wrote …` **중계**다. `case DONE:` 에 `Wrote` 핸들러가 없다는 점이 결정적 근거다(4.1).

**2026-08-04 — ICS 소스로 중계 코드를 직접 확인했다**(`PAP7KX.CMD:1327-1335`). 동시에 **후속 오류 하나가 드러났다**: 6.6 에서 CTIO(`DONE:`)/SSO(`STATUS:`) 타입 차이를 "빌드 차이, 영향 없음"으로 적었는데, 중계 분기가 `Words(1)="DONE:"` 조건이라 **SSO 에서는 중계가 통째로 안 일어난다**(6.9). "영향 없음"이 틀렸다.

### 12.5 "공백 개수가 규약" → **의미 없음**

로그의 `STATUS:` 뒤 2칸/3칸/4칸을 규약으로 오해했으나, 수신측이 공백을 토큰 구분자로만 쓰고 개수는 무시한다. 실제 제약은 `Acquisition Complete.` 의 마침표, `" STATUS"` 의 앞 공백, `Filename=`/`KMTN…` 의 문자 위치뿐이다(3장 서두).

### 12.6 "`ExpNum` 은 정체 불명" → **`expinfo`/`ObsStatus.txt` 갱신용**

처음에는 2025 로그에만 있는 이유를 몰랐다. OBSAgent 소스 서두의 개정이력 주석에서 **v1.0.1(2024-07-01)에 상태 표시용으로 추가**된 것임을 확인했고, 로그의 등장 시점과 정확히 일치했다(3.4).

### 12.7 "9개 ID가 같은 주소를 가리켜도 문제없다" → **근거 부족, 미해결**

XIS 등록 결함(3.1.1)을 발견하고 해법을 제시하면서 *"XIS는 노드ID→주소 매핑이라 9개가 같은 주소를 가리켜도 문제없다"* 고 단언했다. **근거가 부족했다.**

사용자가 *"동일 IP/port의 노드는 ID가 덮어씌워지는 것은 아닐까?"* 라고 물어 다시 확인한 결과:

- **방향은 맞았다** — `ABC`/`GMON` 이 ephemeral 포트로 매 메시지 주소를 바꾸는데도 응답을 받는다는 사실이, XIS가 노드ID로 주소를 찾는다는 것을 증명한다.
- **그러나 "문제없다"는 근거가 없었다** — 같은 (IP,port)에 여러 ID가 동시에 올라간 사례가 48GB 전체에 **한 건도 없고**, XIS 서버 소스도 저장소에 없다.

지금은 1안으로 두되 **미해결로 명시**하고, XIS 소스를 받으면 확인하기로 했다(3.1.1 (7)(8)).

**후속 (2026-08-04)**: XIS의 `Added UDP Client` 로그를 찾아 분석한 결과 테이블이 노드 ID로 키잉된다는 강력한 증거가 나왔다(3.1.1 (4)). 처음의 단언이 결과적으로는 맞는 방향이었던 셈이지만, **단언한 시점에 그 근거를 갖고 있지 않았다**는 사실은 달라지지 않는다. 결론이 맞았는지가 아니라 근거의 범위를 지켰는지가 문제다.

교훈: **"동작 원리를 안다"와 "그 구성이 검증됐다"는 다르다.** 방향을 확인한 것만으로 미시험 구성을 안전하다고 말하면 안 됐다. 12.1의 `dest` 필터 누락과 같은 계열의 실수다 — 근거의 범위를 넘어서 결론을 내렸다.

### 12.8 "XIS가 PING을 로그 열기 전에 보낸다" → **순서가 반대. 이유가 달랐다**

`XIS>AL PING` 이 로그에 없는데 PONG이 1 ms 안에 도착하는 것을 보고 "PING을 먼저 보내고 그 다음 로그를 연 것"으로 추론했다. **순서는 틀렸다.**

`main.c` 의 실제 기동 순서는 `loadConfig() → openSocket() → initLog() → 메인 루프 → COLD_START → handShake()` 로 **로그가 먼저 열린다.**

PING이 로그에 없는 진짜 이유는 `handShake()` 가 `write()`/`sendto()` 를 직접 호출하고 `logMessage()` 를 거치지 않기 때문이다 — **XIS는 자기가 보내는 handshake PING을 로깅하지 않는다.** 관측(PING 없음 + PONG 1 ms)은 두 설명 모두와 양립했고, 소스를 봐야 갈렸다.

교훈: **관측이 가설과 일치한다고 해서 그 가설만 참인 것은 아니다.** 같은 관측을 낳는 다른 메커니즘이 있는지 먼저 세어봤어야 했다.

### 12.9 XIS 서버 소스로 확정된 것 — 이전 추론들의 최종 판정

`ics_legacy/__dts_legacy/` 의 XIS 서버 소스로 3.1.1 (8)절의 질문에 전부 답이 나왔다((12)절). 이전 단계의 추론이 어떻게 판정됐는지 정리한다:

| 추론 | 근거 단계 | 최종 판정 |
|---|---|---|
| XIS 테이블은 노드ID→주소 방향 | `ABC`/`GMON` ephemeral 포트 | **맞음** (`updateHosts()`) |
| 테이블이 ID로 키잉된다 | `Added UDP Client` 빈도 | **맞음** — 주소는 비교에 아예 안 쓰인다 |
| 같은 주소에 9개 ID를 올려도 안전 | (근거 없이 단언 → 보류) | **맞음.** 충돌 검사가 없고, 브로드캐스트 코드가 "같은 포트를 공유하는 클라이언트"를 명시적으로 다룬다 |
| XIS 재시작 시 `>AL PING` 을 뿌린다 | 재시작 16건의 PONG 패턴 | **맞음** (`handShake()`) |
| PING을 로그 열기 전에 보낸다 | 타임스탬프 1 ms | **틀림** — 12.8 참고 |
| `unlisted` 가 정적 목록을 시사한다 | 에러 문구 | **틀림** — 클라이언트 테이블은 완전 동적. 다만 **preset PING 목록**은 정적이라, 우려의 방향 자체는 유효했다 |
| IP 서브넷 브로드캐스트일 수 있다 | 빈 테이블 문제 | **틀림** — preset 목록에 개별 `sendto` |

12.7의 "결론이 맞았는지가 아니라 근거의 범위를 지켰는지가 문제"라는 지적이 여기서도 유효하다. **맞은 추론과 틀린 추론이 섞여 있고, 어느 쪽인지는 소스를 보기 전까지 알 수 없었다.**

### 12.10 구현 중 발견한 경합 — 파일 일련번호

`GO 5` 테스트에서 일련번호가 5개가 아니라 4개만 나왔다. 저장 태스크가 나중에 `ChannelState.suffix` 를 읽는데, 그때는 이미 다음 프레임이 덮어쓴 뒤였다. **파일명을 프레임 시작 시점에 확정해 넘기도록** 고쳤다(`sequencer._store(… , wanted)`).

레거시가 IC/CB 를 별도 프로세스로 두어 우연히 피했던 문제가, 통합 구조에서는 명시적으로 다뤄야 하는 문제로 바뀐 사례다.

### 12.11 ICS 소스로 확정된 것 — 로그 추론들의 최종 판정 (2026-08-04)

12.9 가 XIS 서버 소스로 등록 관련 추론을 판정했다면, 이번은 **ICS 본체 소스**로 5·6장을 판정한 것이다. 12.9 와 같은 형식으로 정리한다.

| 로그로 세웠던 추론 | 판정 | 근거 |
|---|---|---|
| 커맨드워드 슬롯이 비워지지 않는다 | **맞음** | `PAP7COM.INC:797-802` + `PAP7KX.CMD:1496-1504` (5.5.1) |
| 슬롯이 "검증된 명령 테이블이 아니라 직전 파싱 토큰"에서 온다 | **절반 틀림** | `REQ`·`PING`·`PONG`·`FOUND` 는 **정식 `CASE` 레이블**이다. 출처는 정상이고 **비워지지 않는 것**만 문제였다 (5.5.3) |
| 누적 오염은 "재사용 버퍼" 때문 | **맞음** | `SUB Prt` 가 인자를 BYREF 로 덮어쓴다 (5.5.1 B) |
| 현상 C 는 시리얼 구간 손상 | **맞음(유지)** | 소스에 대응 코드가 없다. 수신부는 폭주만 막는다 (5.5.1 C) |
| `EXPSTATUS=` 반복은 레거시의 나쁜 습관 | **성격이 달랐음** | 습관이 아니라 **일괄 접미사 설계**였다. 결론(전이 시 1회)은 그대로 (5.5.2) |
| `BIN`/`ROI`/`DISPL`/`STOP`/`ABORT`/`MOVIE` 는 레거시 미구현 | **틀림** | `BIN`/`STOP`/`ABORT` 는 구현되어 있고, `ROI`/`DISPL`/`MOVIE` 는 ICS 에 아예 없다 (6.8). **코드도 고쳤다** |
| `Wrote` 타입의 사이트 차이는 영향 없음 | **틀림** | SSO 는 중계가 0건이고 매 노출 25초 타임아웃을 탄다 (6.9) |
| `GO n` 마지막 프레임만 `DONE:` | **맞음** | `PAP7KX.CMD:1355-1376` 의 `ImageCount=0` 분기 (6.1) |

**패턴이 12.9 와 같다.** 로그에서 *무엇이 일어나는가*는 잘 읽혔고, *왜*를 추정한 대목에서 절반이 어긋났다. 특히 **"영향 없음"이라고 단정한 두 건**(12.4 의 `Wrote` 타입 차이, 그리고 5.4 끝의 "이 버그는 OBSAgent 에 영향 없음")이 위험했다 — 뒤엣것은 다행히 맞았지만 앞엣것은 틀렸고, **둘 다 같은 수준의 근거로 적혀 있었다.** 근거의 강도를 문장에 드러내야 한다는 12.7 의 교훈이 반복된다.

**그리고 같은 실수를 반대 방향으로 한 번 더 했다.** 6.9 를 처음 쓸 때 "SSO 는 매 노출 `WARNING` + `ExpStatus=ERROR` 가 뜬다"고 단정했는데, OBSAgent `main.c:694` 에 **SSO 전용 우회 분기가 이미 있어서** 실제로는 조용히 통과한다. 더 나쁜 것은 **그 분기를 내가 `obsagent_report.md` §6.1 에 이미 적어 두었다는 점**이다 — 새 발견의 파급을 추정하면서 **내가 쓴 문서를 확인하지 않았다.**

교훈을 갱신한다: 근거의 강도를 표시하는 것만으로 부족하고, **새 발견이 기존 결론과 만나는 지점에서는 기존 문서를 되짚어야 한다.** 특히 "이 발견 때문에 X 가 깨진다"는 형태의 주장은, X 를 다루는 절을 열어 보기 전에는 쓰지 않는다.

---

## 13. 개선 제안 · 백로그

| 항목 | 내용 | 우선도 |
|---|---|---|
| ~~XIS 등록 방식 확정 (1안 vs 2안)~~ | **해결됨 (2026-08-04).** XIS 서버 소스로 테이블이 노드ID로만 키잉되고 주소 충돌 검사가 없음을 확인 → **1안 확정, 2안 불필요**(3.1.1 (12)) | 완료 |
| ~~`XIS>AL PING` 에 9개 PONG 응답~~ | **구현 완료 (2026-08-04)** — `cmd_ping()` 이 브로드캐스트면 9개 ID 전부로 PONG(3.1.1 (12)⑨) | 완료 |
| **XIS `isis.ini` 에 시뮬 등록** | `UDPPort <sim_ip> <sim_port>` 한 줄 추가(운영 측 작업). 단 `MAXPRESET` 여유 확인 필요 — 백업 소스는 8인데 CTIO 설정엔 13줄이라 배포 바이너리가 다를 수 있다(3.1.1 (12)⑧) | **최우선** |
| **XIS 콘솔 `info` 로 `MaxPreset` 실측** | 위 항목의 선행 조건. `commands.c` 가 `NumPreset=? MaxPreset=?` 를 출력한다 | **최우선** |
| 주기적 재등록 | preset 목록에 등록되면 필수는 아니나 안전망으로 유효 | 중간 |
| Caliban(`*.CB`) 소스 검토 | `__dts_legacy/.../Agents_V1/Caliban/src/` 에 CB 노드 소스가 있다(`TransferDisk.c` 등). 신규는 CB 계층을 내부화하므로 우선순위는 낮지만, 디스크 핸드셰이크·파일명 fail-safe 의 실제 구현이다 | 낮음 |
| ~~**`IC2.img` 에서 `\KMTX` 추출**~~ | **완료 (2026-08-04).** 예상과 달리 바이너리가 아니라 **FreeBASIC 소스**가 통째로 들어 있어 역어셈블이 불필요했다. 결과: 5.5(오염 원인 코드) · 6.8(명령 테이블) · 6.9(SSO `Wrote` 단절) | 완료 |
| **`\KMTS`·`\KMTG` 소스 정독** | 위 작업의 후속. ICS(`\KMTX`)만 읽었고 과학/가이드 IC 는 미검토다. **IC 쪽 고유 동작**(`SHOPEN` 카운트다운 주기, `DATASOURCE` 처리, `TRANSFER`/`REQ SWAP` 핸드셰이크)을 확정하려면 필요. SAAO 이미지와의 빌드 차이 비교도 함께 | 중간 |
| **실물 XIS 연동 시험** | `transport.feed()` 로는 검증할 수 없는 라우팅 경로 전체를 처음으로 실증하는 일 | **최우선** |
| **`STOP`/`ABORT` 실제 구현** | ~~레거시 미구현.~~ **레거시에 구현되어 있다**(6.8). 즉 "새 기능 추가"가 아니라 **"있는 기능을 아직 안 옮긴 것"** 이다. 분기 로직과 거부 문자열이 `commands.py` docstring 에 그대로 적혀 있어 옮기기만 하면 된다 | **높음** |
| **SSO `Wrote` 결함 운영측 보고** | 6.9 — SSO Caliban 의 `GetFITS.c:532` 가 `STATUS:` 로 고쳐져 있어 ICS 중계가 끊겼고, 그 결과 **매 노출 `FitsSaved` 가 25초 타임아웃으로만 서고 있다.** 레거시를 계속 쓰는 동안은 한 단어(`STATUS:`→`DONE:`) 수정으로 고쳐진다. 신규 `ics` 에는 해당 없음 | 중간 |
| **`EXPNUM` 자릿수 통일** | 레거시는 ICS 6자리 / IC 4자리라 `INITIALIZE` 로 우회했다. 신규는 이미 6자리로 통일했으니, 외부 문서도 갱신 필요 | 완료(신규) |
| **구조화 로깅(JSON) 병행** | 이번 48GB 스캔 같은 사후 분석 비용을 크게 낮춘다. 사람이 읽는 로그와 병행 출력 | 높음 |
| **상태 조회 API(HTTP/JSON)** | `GMON` 이 UDP 로 초당 폴링하는 방식의 현대적 대안. IMPv2 채널은 그대로 두고 추가 | 중간 |
| **`DataSource=SIM` 정식 승격** | 레거시에 이미 정의된 값(6.4). 시뮬 백엔드를 이 이름으로 노출하면 프로토콜상 자연스럽다 | 완료 |
| **`SYNCHRONIZE` 모델 결정** | 레거시는 "누가 보냈든 반영"하는 수동 리스너였다. 발신자 검증형으로 바꿀지 결정 필요 | 중간 |
| **파일명 fail-safe 유지** | 1999년 Prospero 시절부터 검증된 데이터 유실 방지 장치. 그대로 가져간다 | 완료 |
| **`force_ready=270`(12.2초) 대기** | 신규 시스템에서 병목이면 OBSAgent 개정이 필요하다. **현재는 개정하지 않기로 확정**된 상태이므로 기록만 | 보류 |
| **`CHA` 노드 성격 확인** | 운영자에게 물어보면 바로 풀릴 사안(6.3) | 낮음 |
| **ICG 오염 여부 확인** | 5장의 버그가 `ICG`/`G.IC`/`G.CB` 발신에도 있는지. OBSAgent 가 가이드를 무시하므로 영향은 없지만 `icg` 구현 시 참고 | 낮음 |

---

## 14. 기존 문서 갱신 내역

이번 작업에서 아래 문서를 갱신했다. 각 항목의 상세 근거는 이 문서의 해당 절.

### `ics_legacy/ics_legacy_report.md`
- **5.6절 신설** — "ICS 메시지 오염 버그" (이 문서 5장 전체)
- **8.0.1절 보강** — `ExpNum` 자동 질의(3.4) · 수신 9노드 필요(3.1) · 타임아웃 4종(3.3) · `Wrote` 는 ICS 중계(4.1) · 텔레메트리 역순 중계(4.3) · 상태 전이 실측과 역행 제약(3.2.1) · `GO n` 경로(6.1)
- **정정** — 디스크 최대 4중화 + 신규 폐지 방침(6.2)
- **보강** — `CHA`/`C1` 노드(6.3) · 새 에러·경고(6.4) · 텔레메트리 실패 형태(6.5) · 형식 변형(6.6) · 전량 0건 확인(6.7)
- **자료 색인** — 48GB 전량 스캔 사실과 스크립트 위치

### `ics_legacy/icg_legacy_report.md`
- 신규 `icg` 구현 명세에 오염 버그 대응 규칙과 **가이드 계통의 비대칭**(OBSAgent 가 무시하므로 `bug_compat` 불필요) 추가
- 디스크 링 폐지 방침 반영
- ICS 와의 비교표에 상태 전이·`GO n` 항목 추가

### `OBSAgent/obsagent_report.md`
- **6절 보강** — `ExpNum` 왕복의 전모와 목적(3.4) · `force_fitssaved=560` 과 `IDLE_1` 초과 시 `opause`(3.3) · 상태 전이 실측표와 "건너뜀이 일상적, 역행은 없음" 정정(3.2.1) · `GO n` 의 `STATUS: EXPSTATUS=IDLE` 경로(6.1)
- **7절 보강** — `EXP.INFO:` 의 `ExpNum` 이 3.4 의 질의로 채워진다는 연결고리

### 그 외
- 최상위 `README.md` "저장소 구성" 표에 `ics_sim/` 추가
- `ics_legacy/SMC_CLAUDE.md` "다음에 이어서 할 만한 일" 갱신
- `ics_legacy/__sample_isislog/samples_for_bug.txt` git 추가(8.1)

---

## 15. 범위 밖과 그 이유

| 항목 | 왜 뺐나 |
|---|---|
| **XIS 허브** | 별도 프로그램이고 이미 운용 중이다. 시뮬은 `xis_host` 설정으로 붙거나, 비워 두면 direct-reply 로 혼자 돈다 |
| **TC 스텁** | TC 는 `TCSAgent` 라는 완성된 프로그램이 있다. 시뮬은 질의를 보내되 응답이 없으면 레거시와 같이 빈 필드로 진행한다(6.5) |
| **OBS 드라이버** | OBSAgent 가 실물로 존재한다. 손으로 돌려볼 수단은 `console.py`(레거시 관례상 ICS 자체 기능) |
| **ICG/ABC 가이드 계통** | 별도 프로그램(`icg`)으로 갈 것이 확정돼 있다. OBSAgent 가 가이드 발신을 무시하므로 하위호환 부담도 비대칭이다 |
| **시리얼 트랜스포트** | 아래 참고 |

### 시리얼에 관하여

실측 로그상 **ICS↔XIS 링크만 시리얼(`/dev/ttyS0`)** 이고 나머지 노드(IC/CB/TC/OBS)는 전부 UDP 다. 5.3 의 바이트 손상·메시지 접합이 이 구간에 집중되는 것과 정합적이다.

시뮬은 UDP 만 쓴다. **신규 시스템이 UDP 로 가면 5.3 계열 손상은 구조적으로 사라진다** — 셔터가 열리지 않은 노출 같은 실제 데이터 손실이 없어진다는 뜻이다. 이것만으로도 전환의 근거가 된다.

`transport.py` 는 필요하면 pyserial 백엔드를 추가할 수 있는 구조지만, 지금은 넣지 않았다.
