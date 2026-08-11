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
| [`xis/xis.md`](xis/xis.md) | **레거시 허브(XIS) 원본 보관본** — 소스·운영 설정·기동 방식·재빌드. **부록 A 에 XIS 노드 등록 논의 전 과정**(3.1.1 에서 이관) |
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
| **4. XIS 폐지** | 허브 없는 구성 | 미정 — 아래 참고 | 로드맵에 있음 (2026-08-11 확인) |

2단계에서 시퀀서를 고칠 일이 없도록 처음부터 **하드웨어 추상화 계층**을 뒀다(9장). `[hardware] backend = sim | archon` 한 줄로 전환한다.

> **4단계에 관하여 (2026-08-11, 운영자 확인).** 신규 계통도(`KMTNet Cam Architecture R2.0.pdf`)에 XIS 박스가 없는 것은 그림 단순화이면서 동시에 **XIS 자체를 나중에 없앨 로드맵이 있기 때문**이다. 이 문서의 다른 판단에는 지금 영향이 없다 — 3단계까지는 허브가 그대로 있고, 15장의 "XIS 는 범위 밖" 도 유효하다. 다만 두 가지를 미리 적어 둔다.
>
> 1. **9개 노드 ID 등록(3.1.1)은 폐지될 때까지 필수이고, 폐지되면 문제 자체가 사라진다.** 9개가 필요한 유일한 이유가 XIS 의 클라이언트 테이블 라우팅이기 때문이다. 즉 그 작업은 버려지는 것이 아니라 **XIS 가 사는 동안의 필수 조건**이고, 폐지 후에는 수신 주소가 하나로 합쳐진다.
> 2. **OBSAgent 무개정 확정과 충돌하는 지점이 있다.** OBSAgent·TCSAgent 는 ISIS 클라이언트라 모든 발신을 `ISISHost`/`ISISPort` 한 곳으로 보낸다(`obstool.ini` 의 `ISISID XIS`). 허브를 그냥 없애면 두 에이전트를 고쳐야 하는데 그건 확정 사항과 어긋난다. → **유력한 경로는 `ics` 가 허브 역할을 흡수하는 것**이다: `ics` 가 XIS 포트를 열어 자기가 소유한 9개 노드는 내부에서 처리하고 `TC`/`OBS` 로만 중계하면, 두 에이전트는 `ISISHost` 를 `ics` 쪽으로 돌리는 **설정 한 줄**로 끝난다. 신규 배치에서 OBSAgent 와 `ics` 가 같은 머신(`Inst. Ctrl.`, 9.1)이라 `127.0.0.1` 이 되고, TCSAgent 만 다른 머신에서 붙는다. 보관해 둔 [`xis/`](xis/) 소스가 그때 **모방 대상**이 된다 — 지금은 "상대를 알기 위한" 자료지만 4단계에서는 "흡수할 동작의 명세" 로 성격이 바뀐다.
>
> 어느 쪽이든 4단계는 **2·3단계가 끝난 뒤의 별개 과제**이고, 지금 설계를 바꿀 이유는 없다.

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
| `ics_legacy/__dts_legacy/dts.icsci.*/` | 2,800 파일 / 24.7 MB | **커밋됨** | icsci 서버 `dts` 백업에서 소스·설정만 선별. **XIS 허브 소스**가 12.9 의 등록 방식 확정 근거. 단 **운영본은 `ISIS/server/`(v2.9.1)이지 `EXEC_ISIS/server/`(v2.7.3)가 아니다** — 12.12 |
| `ics_sim/xis/` | 162 파일 / 1.5 MB | **커밋됨** | 위 백업에서 **XIS 관련 자산만 뽑아 정리한 보관본**. 소스·사이트별 운영 설정·기동 스크립트·은퇴 분기 실행파일. 체크섬 포함. 시작 문서 [`xis/xis.md`](xis/xis.md) |
| `__localonly_osu_legacy/` | 원본 백업 + **VM 이미지 5개** | `__localonly_*` 비커밋 | `IC2.img` × 5, 각 8 GB. **IC/ICS 의 FreeBASIC 소스 전량**이 실행파일과 함께 들어 있다 — 5장·6.8·6.10 의 근거 |

확보된 VM 이미지 5개 (전부 CTIO, SAAO 는 ICSci 하나):

| 이미지 | 빌드 | 실행 | 무엇을 확정했나 |
|---|---|---|---|
| `IC2_KX20160323.1381_ICSci_CTIO` | `KX2016-03-23:1381` | `\KMTX` | 5.5 오염 버그 원인 코드, 6.8 명령 테이블 |
| `IC2_KX20160323.1381_ICSci_SAAO` | 〃 | 〃 | CTIO 판과 프로그램 동일(2.2 말미) |
| `IC2_KX20160323.1381_ICGui_CTIO` | 〃 | `\KMTX` | **ICG 가 ICS 와 같은 바이너리** (6.11) |
| `IC2_KS20160113.1370_K.IC_CTIO` | `KS2016-01-13:1370` | `\KMTS` | 6.10 IC 쪽 동작 전부 |
| `IC2_KG20160602.1407_G.IC_CTIO` | `KG2016-06-02:1407` | `\KMTG` | 가이드 검출기, 2017 개발 스냅샷 |

**역할은 부팅 설정 `0ICCFG\IC.INI` 가 정한다.** 모든 이미지가 세 프로그램(`PAP7KX`/`KS`/`KG`)을 전부 담고 있고, 그 파일의 `ICHOST`/`INSTRUMENT` 와 `CD \KMTx` 한 줄로 무엇이 되는지 갈린다. 상세는 `ics_legacy_report.md` 1.3.1⑧.

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
7z l "__localonly_osu_legacy/IC2_KX20160323.1381_ICSci_CTIO/IC2.img"

# 소스 트리만 꺼낸다 -- 8GB 이미지지만 0.3초, 31MB
7z x "…/IC2.img" -o<대상> -y -r \
   'FREEBASI\KMTX\*' 'FREEBASI\SHARE\*' 'FREEBASI\KMTS\*' 'FREEBASI\KMTG\*'
```

읽어야 할 것은 `KMTX\PAP7KX.{BAS,CMD,CCD}` 와 `SHARE\PAP7{.INC,COM.INC,.CMD,.DEC}` 다. `PAP3`~`PAP7` 세대가 모두 남아 있으니 **버전 간 diff 로 개정 의도**도 볼 수 있다. 배포 빌드는 `PAP7` — `PAP7KX.EXE` 타임스탬프(2016-03-23 18:59)가 이미지 이름·로그의 `ICSBUILD=KX2016-03-23:1381` 과 일치하는 것으로 확인했다.

> **주의**: 소스는 `__localonly_*` 안에 있으므로 **커밋 대상이 아니다.** 문서에는 인용과 행 번호만 남긴다. 다른 컴퓨터에서 확인하려면 위 절차로 다시 꺼내면 된다.

**CTIO 이미지와 SAAO 이미지는 어느 쪽을 써도 된다.** 두 이미지를 전수 대조한 결과 SHA256 은 다르지만 **프로그램과 소스는 완전히 동일**하다 — `\FREEBASI\` 600개 항목이 크기·타임스탬프까지 같고, 양쪽 로그의 실행파일 스탬프도 `Compile Date: 03-23-2016 / Compile Time: 18:59:51` 로 같다. 차이는 로그와 `.INI` 마지막 세션 상태뿐이다(공통 경로 22,254개 중 89개, 그중 82개가 로그). 상세는 `ics_legacy_report.md` 1.3.1⑥.

**그리고 이미지에는 사이트 정체성이 없다** — 소스 어디에도 `CTIO`/`SAAO`/`SSO`/`TELID` 가 하드코딩돼 있지 않고, 네 사이트 FITS 템플릿이 모든 이미지에 함께 들어 있다. 사이트 정보는 전부 TC 텔레메트리에서 런타임에 온다. **4.3 의 pass-through 판단이 레거시 구조와 같은 방향이었음이 확인된 셈이다**(1.3.1⑦).

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

### 3.1.1 XIS 노드 등록 — 결론과 규약

> **해결됨.** 1안(**단일 소켓 + 9개 ID PING**) 확정, 2안 불필요. 근거는 XIS 서버 소스다.
>
> **그리고 2026-08-11 에 실물로 확인됐다.** SSO AIC 리눅스에서 재빌드한 XIS(v2.9.1)에 시뮬을 붙이자 `HOSTS` 가 **`NumClients=9`** 를 찍었고, 9개 ID 가 `Host0`~`Host8` 로 **각자 슬롯을 하나씩** 차지한 채 전부 `127.0.0.1:6600` 을 가리켰다. 덮어쓰기는 없었다. 소스로만 판정하고 48GB 로그 어디에도 사례가 없던 **마지막 미실증 항목이 닫혔다.** 절차와 전체 결과는 [`xis/xis.md` 8절](xis/xis.md).
>
> **논의 전 과정 449줄은 [`xis/xis.md` 부록 A](xis/xis.md) 로 옮겼다 (2026-08-06).** 근거 없는 단언 → 사용자 지적 → 로그 실측 → 소스 확인으로 이어진 기록이라 지우지 않았다. 되짚을 일이 있으면 거기를 본다. **이 절은 결론과 지켜야 할 것만 남긴다.**

**문제**: IMPv2 에는 등록 API 가 없다. 노드가 **자기 이름으로** 아무 메시지나 보내면 XIS 가 "노드ID → 그 데이터그램의 (IP,port)" 를 기억하는 것이 전부다. 그래서 `ICS` 이름으로만 보내면 XIS 는 `ICS` 하나만 알고, `OBS>K.IC STATUS`(kstatus) · `DMAWAIT` · `DATASOURCE` 가 **라우팅 단계에서 사라진다**(3.1).

**채택**: 소켓 하나에서 9개 ID 로 각각 PING 을 보내 전부 등록한다. 노드마다 소켓/포트를 따로 여는 2안은 불필요하다.

#### XIS 서버 소스로 확정된 것

| 항목 | 확정 내용 | 근거 |
|---|---|---|
| 클라이언트 테이블 키 | **노드 ID 만.** 주소는 비교에 안 쓰이고 갱신만 된다 | `clients.c` `updateHosts()` |
| 같은 주소에 여러 ID | **주소 충돌 검사 로직이 없다** → 1안 안전 | 〃 |
| 테이블 크기 | `MAXCLIENTS 64` (현재 운용 13개 안팎) | `isisserver.h` |
| preset 목록 크기 | **`MAXPRESET 32`** (사용: CTIO 13 · SAAO 14 · SSO 13) | 〃 |
| 재시작 시 재등록 | `XIS>AL PING` 을 **시리얼 + preset UDP 에 개별 `sendto`**. IP 브로드캐스트가 아니다 | `interfaces.c` `handShake()` |
| 브로드캐스트 relay | 송신 **슬롯 하나만** 제외 → 우리 `AL` 발신이 **8부 에코**된다 | `messages.c` |
| 라우팅 실패 통보 | `XIS>OBS ERROR: No Route to Destination Host K.IC - host is unknown/unlisted` — **실물 시험의 판정 기준** | `interfaces.c` |

> ⚠️ 위 근거는 `ISIS/server/`(**stock ISIS v2.9.1, 운영본**)의 코드다. 백업에는 이름이 비슷한 은퇴 분기 `EXEC_ISIS/`(XISIS v2.7.3)가 함께 있고, **처음에는 그쪽을 읽었다**(정정 경위 12.12). 인용한 파일들이 두 분기에서 `#include` 한 줄 빼고 바이트 동일이라 결론은 그대로다. 트리 판정 근거와 신규 설계 함의 전체는 [`xis/xis.md` 3·6절](xis/xis.md).

#### 구현과 남은 일

- `Emitter.register_ping(node_id)` — src 를 그대로 지정한다. **`emit_node_mode` 를 따르지 않는다** (merged 는 *발신 이름*만 통일하는 옵션이고 수신은 언제나 9개여야 한다).
- `IcsSim.register()` — `router.registered_ids` 9개 전부로 PING.
- `cmd_ping()` — **`XIS>AL PING` 에는 9개 ID 전부로 PONG.** XIS 재시작 후 재등록의 **유일한 경로**다. 지목된 PING(`OBS>K.IC PING`)에는 그 노드로만 답한다.
- `[transport] register_all_nodes` (기본 `true`) — 끄면 `ICS` 만 등록하고 경고를 낸다. **그 상태로는 개별 IC 명령을 받을 수 없다.**

검증: `test_startup_registers_all_nine_nodes` · `test_registration_ignores_emit_node_mode` · `test_register_all_nodes_false_only_registers_ics` · `test_broadcast_ping_answered_by_all_nine_nodes` · `test_directed_ping_answered_by_that_node_only`.

| 남은 일 | 내용 |
|---|---|
| **운영 측** | XIS `isis.ini` 에 `UDPPort <sim_ip> <sim_port>` **한 줄** 추가. `MAXPRESET 32` 라 여유는 충분하다. 넣기 전에 XIS 콘솔 `UDPPING <ip> <port>` 로 선시험할 수 있다 |
| ~~**우리 쪽**~~ | ~~자기 발신 브로드캐스트 에코 무시~~ — **구현 완료 (2026-08-08, 3.1.2).** 점검에서 브로드캐스트보다 심각한 **유니캐스트 루프백**이 드러나 수신 초입 필터로 확대했다 |
| 설정 | `bind_host` 기본값이 `127.0.0.1` 이라 로컬 전용이다. 외부 XIS·OBSAgent 와 붙이려면 `0.0.0.0` 으로 |

> **이 결함은 `transport.feed()` 테스트로 드러나지 않는다.** 테스트는 XIS 라우팅 단계를 통째로 건너뛰고, direct-reply 모드(기본)에서도 상대가 우리 주소로 직접 쏜다. **XIS 경유 모드로 바꾸는 순간에만 드러나는 종류**다 — 에코 문제(3.1.2)도 같은 이유로 숨어 있었고, 지금은 `test_xis_echo.py` 가 XIS 의 에코 동작 자체를 feed 로 흉내 내 검증한다.

### 3.1.2 자기 발신 에코와 브로드캐스트 중복 (2026-08-08)

XIS 경유 모드에서만 나타나는 두 가지 되돌림을 수신 초입에서 거른다. 실물 연동 시험(11.11) 전 점검에서 확정했다.

**① 유니캐스트 루프백 — 자기 발신은 버린다.** 시퀀서는 레거시 통신규약대로 `K.IC` 등 자기 노드 앞으로 `INITIALIZE`/`ERASE`/`SHOPEN`/`GO` 를 와이어에 내보내는데, 실행은 발신 전에 내부에서 이미 끝난다. XIS 는 클라이언트 테이블대로 `K.IC` 의 등록 주소(=우리 자신)로 그 메시지를 배달하므로, 걸러내지 않으면 **에코가 새 명령으로 재실행된다** — `ERASE` 이중 실행, `SHOPEN` 재구동 + `Shutter=Open` 중복 발신(CamStatus 역행), `GO` busy ERROR 잉여 발신. 원래 백로그에는 "cmd_ping 에서 브로드캐스트 에코만 거르기"로 적혀 있었으나 그 범위로는 이 경로가 안 막힌다(정정 12.13).

**② 브로드캐스트 슬롯별 복사 — 첫 부만 처리한다.** v2.9.1 의 `AL` relay 는 송신 슬롯 하나만 제외하므로(`messages.c`), 9개 ID 로 등록한 우리에게 같은 데이터그램이 최대 9부 도착한다. 억제하지 않으면 외부 브로드캐스트 PING 1건에 PONG 81발(9부 × 9 ID)이 나가고, 브로드캐스트 명령은 9회 중복 실행된다.

**구현** (`app.py _on_message` 초입):
1. `router.owns(msg.src)` 면 버린다. 정당한 외부 발신자(`OBS`/`TC`/`XIS`/`CHA`/`C1`/`ICG`…)는 우리 9개 ID 와 겹치지 않으므로 안전하다. `G.IC` 는 owns 가 아니라서(범위 밖 무응답 규칙, 1.3) 필터와 무관하게 기존 동작 유지.
2. `AL` 브로드캐스트는 같은 원문이 `[transport] broadcast_dedup_sec`(기본 2.0초) 안에 다시 오면 슬롯별 복사본으로 보고 버린다. 0 이하로 두면 끈다(진단용).

덧붙여 `config.validate()` 가 노드 ID 를 검증한다 — IMPv2 이름 규칙(2~8자, `A-Z 0-9 . _`), 예약어(`AL`/`ALL`/브로드캐스트, `XIS`/허브 ServerID), 중복, guide 충돌. **v2.9.1 허브에는 ServerID 사칭 방어도 주소 충돌 검사도 없으므로**(xis/xis.md 6.3) 거르는 책임이 전적으로 우리에게 있다.

검증: [`tests/test_xis_echo.py`](tests/test_xis_echo.py) 15개 — 에코 재실행 차단(대조군 포함), 전체 사이클 발신 전량 되먹임에도 신규 발신 0건, 브로드캐스트 3부 → PONG 9발 한 세트, dedup off 시 구동작 재현, 노드 ID 검증 6종.

**실물 확인 (2026-08-11)** — 자기 발신 에코가 **정확히 36개**(`0+1+…+8`, 등록이 진행될수록 슬롯이 늘어 삼각수) 돌아왔고 시뮬의 **발신은 0건**이었다. 필터가 없었으면 324발이 나갔을 자리다. 이 개수가 운영본 트리 판정(v2.9.1 은 송신 슬롯 하나만 제외 — 은퇴 분기였다면 0개)까지 동작으로 뒷받침한다 → 3.7 · [`xis/xis.md` 10절](xis/xis.md).

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

> **논리 이름 vs 물리 파일 (D-011/D-010; D-009는 2026-08-10 D-011로 대체)** — 위 형식이 고정인 것은 **`Wrote` 메시지에 싣는 논리 이름**이다. 실기(ics_archon)의 디스크 실물은 **컨트롤러당 1개, 노출당 2개** `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits` 로 저장하고 (`<SITE>` 는 `[node] site`/`telid` 에서 유도한 `KMTC`/`KMTS`/`KMTA`/`KMTT` — config.validate() 가 site↔telid 정합을 검사한다), 통보만 CCD 단위 4회를 논리 이름으로 낸다 ([`../raw_fits_spec/`](../raw_fits_spec/README.md) 2.3/2.5절). 시뮬은 레거시 재현이 목적이라 CCD당 1파일을 그대로 쓴다 — 전환 계약은 9.3.

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

### 3.4 `ExpNum` 자동 질의 — 응답해야 하고, **값도 규약이다**

`commands.c` 797~803행: 첫 `PCTREAD=` 를 받아 `READ_1` 일 때 OBSAgent 가 **스스로** `OBS>ICS ExpNum` 을 보낸다.

```
OBS>ICS ExpNum
ICS>OBS DONE: EXPNUM  Filename=20250902.057288 EXPSTATUS=READOUT
```

> #### ⚠️ 답할 값 — 노출 N 의 readout 중에는 **N+1** 이다
>
> OBSAgent 는 받은 값을 `strNextNum` 에 담아 두었다가 **다음 노출이 시작될 때** `strCurNum` 으로 승격해 화면의 `ExpNum` 으로 쓴다(아래 항목). 따라서 readout 중 답할 값은 **다음 노출이 쓸 번호**다.
>
> 레거시 실측 (CTIO `isis.20250401.log`, 연속 3 사이클 — 응답이 한 칸 앞선다):
>
> | readout 중 응답 | 그 노출이 저장한 파일 |
> |---|---|
> | `Filename=20250401.010459` | `KMTNt.20250401.010458.fits` |
> | `Filename=20250401.010460` | `KMTNk.20250401.010459.fits` |
>
> 구현은 `state.peek_suffix()`. **이 값 규약이 오래 빠져 있었고 실물 연동에서야 드러났다 → 12.14.**

**목적과 내력** (소스 서두 개정이력 주석 218~229행):

- **v1.0.1 (2024-07-01)** — *"Add ExpNum query to ICS and ExpNum(strNextNum/strCurNum) update"*. **카메라 제어용이 아니라 상태 표시용**으로 추가된 비교적 최근 기능이다.
- 응답의 `Filename=` 값(**정확히 15자**, `strncpy(expinfo.strNextNum, pstr+9, 15)`)이 `expinfo.strNextNum` 이 되고, 다음 노출의 `Shutter=Open`(또는 `EXPSTATUS=INTEGRATING`) 시점에 `strCurNum` 으로 승격된다.
- 흘러가는 곳: **v1.0.0(2024-06-29)에 추가된 `expinfo`/`ee` 명령**의 반환 문자열과, **v1.0.3~1.0.4(2024-07-05)에 추가된 `/data/Logs/ObsStatus.txt`** 의 `EXP.INFO:` 줄(포맷은 `OBSAgent.latest/Ref.ObsStatus.txt`). **관측자 화면과 상태파일의 `ExpNum` 필드를 채우는 유일한 경로다.**
- 후속 디버깅 이력: **v1.0.6** `expinfo.dStartTime` 누락(ExpProg) · **v1.0.7~1.0.8** SSO 에서의 ExpNum 오류 · **v1.0.9** `strPreNum`/`FitsOsc` 추가 · **v1.1.3(2024-07-18)** *"Debug momentary unmatch of ExpNum and ExpStatus, Debug missing ExpNum/ExpStart update in dark/bias mode"*.
- **응답이 없으면**: 카메라 동작 자체는 정상이지만 `ExpNum` 이 갱신되지 않아 `expinfo`·`ObsStatus.txt`·`GMON` 표시가 이전 값이나 `00000000.000000` 에 머문다.

CTIO 아카이브에서 **125,451회** 확인. **2024-03 로그에는 없고 2025 로그에만 있는 것이 v1.0.1 도입 시점(2024-07)과 정확히 일치한다.**

> **기존 8.0.1절·`obsagent_report.md` 6절 어디에도 없던 항목이다.**

`DONE:` 파싱 순서(947~960행, else-if): `ExpTime=` → `atof(+8)` · `EXP=` → `atof(+4)` · `Filename=` → 15자 복사.

검증: `test_obsagent_contract.py::test_expnum_query_answered`(형식 15자) · `::test_expnum_answers_next_frame_number`(**값이 N+1**) · `::test_expnum_outside_exposure_does_not_skip`(노출 밖에서는 두 칸 밀지 않기) · `::test_expnum_advances_between_exposures`(프레임 간 연속).

> 앞의 두 기존 테스트가 이 결함을 못 잡은 이유가 분명하다 — 하나는 **형식**(15자)만, 하나는 **파일명 연속성**만 봤다. **질의에 답한다는 사실과 옳은 값을 답한다는 사실이 별개**라는 것을 규약이 구분하지 않았던 탓이다.

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

### 3.7 실물 연동 시험 (2026-08-11) — 이 장 전체의 첫 실행 검증

이 장의 규약은 **OBSAgent 소스를 정독해 세운 것**이고, 지금까지의 검증은 `transport.feed()` 로 메시지를 주입하고 `obsagent_model.py` 재현본으로 상태를 재생하는 방식이었다. 둘 다 **XIS 라우팅 단계를 건너뛰고, 받은 값이 관측자 화면에서 어떻게 쓰이는지를 다루지 않는다.** SSO AIC 리눅스에서 실물 넷을 한 허브에 물려 그 공백을 메웠다.

**구성** — XIS(v2.9.1 재빌드) · `ics_sim` · **실물 TCSAgent**(`pctcs` v1.7.2) · **실물 OBSAgent**(`obstool` v1.2.0). 프로그램 넷이 각자 노드로 등록돼 서로 라우팅된 것은 처음이다. 벤치 기동 명령은 [`xis/xis.md` 8절](xis/xis.md), 두 에이전트의 재빌드는 [`../TCSAgent/tcsagent_report.md`](../TCSAgent/tcsagent_report.md) 12절 · [`../OBSAgent/obsagent_report.md`](../OBSAgent/obsagent_report.md) 12절.

| 판정 | 결과 | 근거 절 |
|---|---|---|
| 9개 노드 ID 등록 | `NumClients=9`, `Host0`~`Host8` 각자 슬롯, 전부 `127.0.0.1:6600` | 3.1.1 |
| 자기 발신 에코 필터 | 에코 **36개**(`0+1+…+8`) 수신, 발신 **0건** | 3.1.2 |
| `XIS>AL PING` 재등록 | `UDPPING` 한 방에 9개 ID 전부 PONG | 3.1.1 |
| 개별 IC 라우팅 | `kstatus`·`dmawait`·`datasource` 전부 도달, 해당 노드 이름으로 응답. 허브 왕복 **2~4 ms** | 3.1 |
| 브로드캐스트 dedup | `OBS>AL PING` → PONG **9발 한 세트**(81발 아님) | 3.1.2 |
| CamStatus 전 구간 | DARK 사이클에서 경고·에러 **0건**, `READY` 복귀, `FitsSaved=1` | 3.2 |
| `FitsNum` 파싱 | `Wrote` 의 `KMTN`+6 부터 15자가 그대로 `20260811.000001` | 3.2 |
| `ExpNum` 왕복 | 첫 `PCTREAD=6` **3 ms 뒤** OBSAgent 가 스스로 질의 | 3.4 |

**타임아웃 창 실측** (DARK 5초, 시간축척 1.0). 3.3 의 네 상수가 실물에서 처음 측정됐다:

| 창 | 실측 | 한계 | 여유 |
|---|---|---|---|
| `Acquisition Complete.` 1번째 → 4번째 | **8 ms** | 1.8 초 (`force_idle=40`) | 225× |
| 4번째 → `EXPSTATUS=IDLE` | **0.394 초** | 0.9 초 (`force_idle/2`) | 2.3× |
| `IDLE` 진입 → 4번째 `Wrote` | **4.63 초** | 25 초 (`force_fitssaved=560`) | 5.4× |

가장 빠듯한 것이 두 번째 창(2.3배)인데, `[timing] acq_to_idle = 0.40` 을 그대로 반영한 값이라 예상 범위다. 레거시 실측은 0.38초였다(3.3).

**잡은 결함 하나** — `ExpNum` 응답 값이 한 칸 밀려 있었다. 규약은 3.4, 경위와 교훈은 12.14. **이 장의 규약 중 유일하게 "값"을 명시하지 않았던 항목에서 나왔다.**

**부수로 드러난 XIS 동작 두 가지**

- **빈 노드 ID 도 등록된다.** 발신 ID 가 빈 메시지(`>` 로 시작하는 줄)를 보냈더니 `Host12: ID= …:6650` 이 테이블에 올랐고, 그 슬롯은 **XIS 재시작 전까지 회수되지 않는다.** `updateHosts()` 에 ID 검증이 없다는 3.1.1 표의 실물 확인이고, 우리가 `config.validate()` 로 노드 ID 를 스스로 거르는 이유이기도 하다(3.1.2 말미).
- **한 주소에 세 ID.** `127.0.0.1:6650` 을 `OBS`·`CHA`·(빈 ID) 가 동시에 점유했다 — 9개 ID 실험과 별개 경로에서 같은 성질이 재현됐다.

~~**다음 시험 초반에 먼저 할 것** — **`ExpNum` 교정의 실물 재확인.**~~ → **완료. 3.7.2.**

**그 밖에 아직 안 해 본 것**: `STOP`/`ABORT`(9.2.1 의 `DONE:` 본문은 실측 근거 없이 정한 것이라 실물 확인이 필요하다) · `GO n` 다중 노출(6.1) · `.osc` 스크립트 관측(3.5 의 명령별 응답 판정) · 결함 주입 6종(7장). 벤치가 그대로 남아 있어 이어서 하면 된다.

#### 3.7.1 레거시 에이전트 재빌드 — 현대 툴체인 이식 목록

시험의 전제가 **TCSAgent·OBSAgent 를 실제로 빌드하는 것**이었다. 원 배포본은 2014~2018년 CentOS 계열에서 g++ 로 빌드된 것이라 12년치 차이가 그대로 드러났다. **OBSAgent 는 개정하지 않기로 확정돼 있으므로 신규 `ics` 전환 뒤에도 두 에이전트는 어딘가에서 계속 빌드돼야 한다** — 그때 필요한 체크리스트다.

절차는 [`../TCSAgent/build-local.sh`](../TCSAgent/build-local.sh) · [`../OBSAgent/build-local.sh`](../OBSAgent/build-local.sh) 가 정본이고, 운용 관점 요약은 두 보고서 12절. 여기에는 **근거**를 남긴다.

| # | 문제 | 위치 | 계기 | 증상 |
|---|---|---|---|---|
| 1 | `.c.o:` 서픽스 규칙에 전제조건 | 세 Makefile 전부 | GNU make | `ignoring prerequisites on suffix rule definition`. 여기서는 `CC`/`CFLAGS` 가 Makefile 에 있어 빌드는 진행된다(XIS 는 `VFLAGS` 가 날아가 `VERSION 0.0` 이 됐다 — `xis/xis.md` 4.2 ③) |
| 2 | **포인터를 정수 0 과 순서비교** | TCS `commands.c:1105` · OBS `commands.c:1477` · **ISISclient `isismessage.c:134`** | C++ Core Issue 1512 | `ordered comparison of pointer with integer zero`. `-w` 로도 `-std=gnu++98` 로도 안 넘어간다 → `!= NULL` |
| 3 | **`pow10()`** | TCS `commands.c:4924` · OBS `calculation.c:243` | glibc 2.27(2018) 삭제 | BSD 확장이었다 → `pow(10.0,(double)n)` |
| 4 | 커밋된 `libisis.a` 가 non-PIC | `ISISclient/libisis.a`(2014 빌드) | PIE 기본화 | `relocation R_X86_64_32 … PIE object` → 소스에서 재빌드(그러면 2번이 나온다) |
| 5 | **`rl_refresh_line()` 을 readline 초기화 전 호출** | TCS·OBS 의 `_msgout()`, TCS `testcode()` | readline 8.x | **빌드는 되고 실행이 즉사한다** — 아래 |
| 6 | 리터럴 → `char*` | 곳곳 | C++11 | `-std=gnu++98` |
| 7 | **vendored hiredis 의 `all:` 이 `.so` 만 만든다** | OBS 전용 | — | `-lhiredis` 가 `.so` 를 우선 잡아 **실행이 안 되는 바이너리**가 나온다 → `make static` + `.a` 경로 직접 링크 |

**2·3 은 두 에이전트에 같은 줄로 존재한다** — OBSAgent 가 TCSAgent 코드베이스를 복사해 출발했다는 계보가 결함까지 물려받은 형태로 남아 있다.

**5 가 가장 고약하다.** 정적 분석으로는 안 나오고 실행해야 드러난다:

```
#0 __strrchr_evex()  #1 rl_redraw_prompt_last_line() [libreadline.so.8]
#2 _rl_refresh_line()  #3 rl_refresh_line()  #4 testcode()  #5 main()
```

`rl_callback_handler_install()` 은 이벤트 루프 직전에야 도는데 **배너·설정 로딩 메시지가 전부 그 전에 `_msgout()` 을 타고**, 그 안에 `if(!KeyCmdFlag) rl_refresh_line(0,0);` 이 있다. readline 8.x 의 `rl_redraw_prompt_last_line()` 이 NULL 인 `rl_prompt` 에 `strrchr` 을 건다. **구버전(5/6번대)에는 이 경로가 없어 운영 머신에서는 지금도 멀쩡히 돈다.** 교정은 호출 제거가 아니라 `if(rl_prompt)` 가드다 — readline 이 뜬 뒤에는 원래 동작(비동기 출력 후 프롬프트 재그리기)이 필요하다.

**로그 경로는 ini 로 못 고친다.** 설정을 읽기 **전에** 하드코딩 경로(`/data/Logs/…`)로 임시 로그를 열고, 설정을 읽은 뒤 `mv` 로 옮겨 이어 쓰는 구조라서다. 배너처럼 설정 이전에 나오는 메시지를 놓치지 않으려는 설계이고, 그래서 그 첫 경로만은 설정 항목이 없다. 실패하면 **이벤트 로그가 통째로 안 남는다.**

**실행으로 드러난 레거시 결함 둘**

- **`ISISclient/isisutils.c:428` `ISODate()`** — `static char str[11]` 에 `CCYY-MM-DDThh:mm:ss` 19자+NUL. **최소 출력이 이미 버퍼를 넘는다.** 같은 파일의 다른 날짜 함수는 전부 정확하고 이것만 어긋난다 — 2004년에 `UTCDate()`(날짜 전용이라 11 로 정확)를 복사해 시각을 덧붙이며 버퍼를 안 키운 것이다. `static`(.bss) · 기동 시 1회 호출 · 최적화 없는 빌드가 겹쳐 20년 넘게 조용했다.
- **TCSAgent `main.c` 의 `sprintf` 6곳** — 1024바이트 버퍼에 최대 2059바이트(IMPv2 최대 2048자). 전부 `_vmsgout` 경로라 **`VERBOSE on` 일 때만** 발현한다. 운영 ini 는 `off` 이므로, **디버깅하려고 켜는 순간이 가장 위험하다.** 미교정.

**소스 정독에서 나온 것 하나 (2026-08-11)** — 위 둘과 달리 실행으로 드러난 것이 아니라 설정 로더를 읽다 나왔다. 근거의 성격이 다르므로 따로 적는다.

- **TCSAgent `loadconfig.c` 의 액추에이터 키 오류 메시지가 복붙이다** — `AUX_FA_ActNum_East`(:708)와 `_West`(:723) 의 범위 오류 메시지가 둘 다 `"AUX_FA_ACTNUM_SOUTH is %d unrecognized"` 로 찍힌다. 세 키 중 어느 것이 틀렸는지 메시지로 알 수 없다. **값 자체는 `1..3` 범위 검사와 중복 검사(:772)를 정상적으로 통과/거부하므로 동작 결함은 아니고, 진단만 못 쓰게 되는 종류다.** 미교정 — **TCSAgent 코드를 손볼 일이 생기면 같이 고칠 항목**(운영자 합의, 2026-08-11). 배치·번호 대응의 의미는 [`../TCSAgent/tcsagent_report.md`](../TCSAgent/tcsagent_report.md) 6.4절.

> **이 목록의 성격.** 앞의 여섯 중 넷(2·3·4·6)은 **빌드가 안 되는 것**이고, 5·7 은 **빌드는 되는데 실행이 안 되는 것**이다. 후자는 실제로 띄워 봐야만 나오므로, 이식 작업에서 "컴파일 통과 = 끝" 으로 보면 안 된다. XIS 재빌드에서 걸림돌 넷 중 하나가 실제 컴파일에서만 드러났던 것(`xis/xis.md` 4.2 ④)의 확대판이다.

#### 3.7.2 2차 시험 — `ExpNum` 값 규약의 실물 확정 (2026-08-11, 같은 날 후속)

3.7 이 남긴 최우선 항목(`ExpNum` 교정의 실물 재확인)을 같은 벤치에서 닫았다. **12.14 의 수정이 시뮬 단위 테스트를 넘어 실물 OBSAgent 화면에서 확인된 것은 이번이 처음이다.**

노출 두 번(`000002`·`000003`)을 돌리며 `ee` 로 관측자 화면을 직접 읽었다.

| 판정 | 프레임 `000002` | 프레임 `000003` | 결과 |
|---|---|---|---|
| readout 중 `ExpNum` == 그 프레임이 저장할 번호 | `ExpNum=20260811.000002` → `KMTNn.20260811.000002.fits` | `ExpNum=20260811.000003` → `…000003.fits` | **일치** |
| 종료 후 `ExpNum` == `FitsNum` | 둘 다 `20260811.000002` | 둘 다 `20260811.000003` | **일치** |
| `EXPNUM` 응답이 N+1 (3.4) | `Filename=20260811.000003` | `Filename=20260811.000004` | **레거시 실측과 동일** |
| `FitsOsc` | `CHECK` → **`NO`** | `NO` | `KMTN` 파싱 성공의 지표 |

**타임아웃 창 3종이 두 프레임에서 밀리초까지 같았다** — `Acquisition Complete.` 1→4번째 **8 ms**(한계 1.8초) · 4번째→`EXPSTATUS=IDLE` **0.394초**(0.9초) · `IDLE`→4번째 `Wrote` **4.63초**(25초). 3.7 의 1차 측정치와도 같다. 시퀀서가 결정론적으로 도는 것이 재현으로 확인된 셈이다.

**전제였던 결함 하나를 먼저 고쳐야 했다.** 2차 시험 첫 시도에서 `FitsNum=00000000.000000` · `FitsOsc=CHECK` 가 나왔는데, 원인은 파서가 아니라 **EXPNUM 카운터가 매 실행 1 로 되돌아가는 것**이었다 — 번호가 겹쳐 파일명 fail-safe 가 `KMTN` 없는 이름(`260811.004.fits`)을 쓰자 3.2 의 `KMTN`+6 슬라이스가 통째로 실패했다. 지속 카운터로 고쳤다(11.12). **판정 ②가 성립한 직접 조건이 "fail-safe 가 침묵하는 것"** 이라는 점이 이 시험에서 드러났다.

> **로그를 읽을 때의 함정 하나 (기록해 둘 값이 있다).** 이번 로그를 터미널 스크롤백에서 받았더니 `.fits`→`.its`, `INTEGRATING`→`INTEGRATNG`, `UNKNOWN`→`UNNOWN` 처럼 **한 글자씩 빠진 자리가 여럿** 나왔다. 5.3 의 "현상 C — 버퍼 겹침·절단" 과 겉모습이 똑같아 와이어 손상으로 오인할 수 있는데, **캡처 아티팩트였다.**
>
> 판정 근거 둘: (1) 누락 위치가 **col 105·210·314·420 — 약 105 컬럼 주기**로, 페인 폭에서 줄이 접히는 경계마다 한 글자가 먹혔다. (2) 같은 손상이 `Move=UNKNOWN`·`SHUTSTAT` 처럼 **OBSAgent 가 자기 콘솔에 찍는 문자열**(와이어를 타지 않는다)에도 나타났다 — ics_sim 발신과 OBSAgent 로컬 출력에 공통으로 걸리는 것은 터미널/캡처 경로뿐이다.
>
> → **연동 시험 로그는 터미널을 거치지 말고 `[logging] file` 로 파일에 직접 남긴다.** 폭 무관이고 `grep` 도 된다. 레거시 로그로 5.3 을 판정할 때 같은 함정을 밟지 않은 것은 그쪽에 "시리얼 구간 집중" 이라는 별개 근거가 있었기 때문이지, 형태만으로 가릴 수 있었던 것이 아니다.

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

- **`CHA` 노드** — `ICS>CHA DONE: EXPNUM  Filename=20240628.021488`, `M.IC>CHA DONE: EXPNUM  Filename=KMTNm.20240628.5956`, `M.IC>CHA DONE: INITIALIZE  Initialization Complete.` (SSO, 2024-06-28 전후, 2,441회). **정체 확정 (2026-08-11, 운영자 확인): 시험할 때 쓰는 임시 노드 ID.** 추정했던 "엔지니어링/운영자 콘솔 클라이언트" 가 맞았고, 2024-06-28 전후의 2,441 건은 운영 트래픽이 아니라 **그날의 시험 세션**이다. `EXPNUM`·`INITIALIZE` 를 ICS 와 개별 IC 양쪽에 찔러보는 패턴도 시험 그대로다.
  - **이 확정이 아래 결론을 사후에 뒷받침한다.** 미상 발신자의 정체가 곧 **운영자의 시험 콘솔**이라면, 발신 노드 화이트리스트를 뒀을 때 제일 먼저 막히는 것이 운영자 자신이다. "레거시가 그러니까" 가 아니라 **그래야 하는 이유**가 생겼다.
  - 실물 연동 시험(2026-08-11)에서 우리가 붙인 프로브도 XIS 테이블에 같은 자리를 차지했다 — 같은 `127.0.0.1:6650` 에 `OBS`·`CHA`·(빈 ID) 셋이 공존했다.
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

### 6.10 IC 쪽 동작 확정 — `\KMTS` 소스 (2026-08-05)

`K.IC` 이미지의 `PAP7KS.{BAS,CCD}` 를 읽었다. **공용 소스는 ICS 이미지의 것과 바이트 단위로 같으므로** 5.5 의 오염 분석이 IC 에도 그대로 적용된다. 전문 인용은 `ics_legacy_report.md` 4.6절에 두고, 여기서는 **시뮬레이터 값과의 대조**만 적는다.

| 항목 | 소스가 말하는 것 | 실측 | `ics_sim.ini` | 판정 |
|---|---|---|---|---|
| `Acquisition Complete.` 마침표 | **의도된 비대칭** — OBS 에는 마침표 있는 문자열, ICS 에는 없는 문자열을 **각각 따로** 보낸다(`PAP7KS.CCD:172-176`) | 동일 | `emitter.ic_acq_complete_obs/_ics` 로 분리 | **맞음** |
| `PCTREAD` 발신자 | master 만 (`I_Am_Driving > 0`) | `K.IC` 만 | `[node] master` | **맞음** |
| `PCTREAD` 간격 | 5% 누적 임계 **AND** ≥2초. 검사는 **256라인 DMA 블록마다** | +11 / 3.37초 | `pctread_step=11`, `pctread_tick=3.37` | **실측 유지** (아래 주) |
| 셔터 카운트다운(IC) | `TimesUp(LastUpdate, 4.9)` | 5.217초 | `countdown_tick_shop=5.217` | **맞음** |
| 카운트다운(DARK, ICS) | `TimesUp(LastIntegrationUpdate, 5)` | 5.00초 | `countdown_tick_dark=5.00` | **맞음** |
| `USESTATUS` | 셔터 닫힘 알림 타입을 `DONE:`→`STATUS:` 로 바꾸는 스위치 | — | 항상 붙여 보냄 | **맞음** |

> **`PCTREAD` 간격에 대한 정직한 기록**: 과학 CCD 는 `DetY=9232`, 블록은 256라인이므로 **블록당 2.773%**, 실측 +11% 는 **정확히 4블록**이다. 계단이 블록 양자화라는 것까지는 확정됐다. 그런데 **왜 3블록(2.53초, 이미 2초 하한을 넘김)이 아니라 4블록인지는 이 코드만으로 설명되지 않는다.** `YLinesIn` 갱신 지점과 preheat 라인(`NUMPHLINES=32`) 처리를 더 봐야 한다. 억지로 이야기를 맞추지 않고, **시뮬레이터는 실측값을 쓴다** — OBSAgent 가 실제로 본 것이 그 값이기 때문이다.

**디스크 전송 핸드셰이크**도 확정됐다(`PAP7KS.CCD:1290-1292`, `PAP7.CMD:2252-2270`). IC → CB `TRANSFER <디스크> <장수> <완료보고 대상>`, CB → IC `REQ SWAP` → IC 는 남은 이미지가 있으면 `TRANSFER` 를 한 번 더, 없으면 `ACK SWAP`. 세 번째 인자가 `ConfirmHost`(관측자 UI)에서 `AcquisitionInitiator`(GO 발신자)로 **의도적으로 바뀐 흔적**이 주석에 남아 있고, 6.3 의 `C1` 같은 sourceID 변주가 그것으로 설명된다. **신규 설계에서는 CB 계층이 내부화되므로 이 핸드셰이크 자체가 사라진다**(6.2와 같은 이유).

### 6.11 ICG 는 ICS 와 같은 바이너리다 (2026-08-05)

`ICGui` 이미지의 `0ICCFG\IC.INI` 가 `INSTRUMENT=ICG / ICHOST=ICG` 이고 **`CD \KMTX`** 로 들어간다 — ICS 와 **같은 `PAP7KX.EXE`** 다. 분기는 런타임 `ICHost` 값으로 다섯 군데뿐이고, 그중 하나가 계통의 성격을 가른다:

```basic
IF ICHOST = "ICS" THEN
   IF AcquisitionCompleteCounter > 3 THEN      ' CCD 4개
ELSEIF ICHOST = "ICG" AND AcquisitionCompleteCounter > 0 THEN   ' CCD 1개
```

**3장의 "4회 누적" 규약이 과학 계통에만 있는 구조적 이유가 이것이다.** 상세는 `icg_legacy_report.md` 8.1절.

→ **13장 백로그의 "ICG 오염 여부 확인" 항목이 이것으로 해소된다.** ICG 는 같은 바이너리이므로 5.5 의 오염이 **그대로 있다.** 다만 OBSAgent 가 가이드 발신을 무시하므로 관측에는 영향이 없고, 신규 `icg` 는 하위호환 부담 없이 5.4 규칙만 지키면 된다.

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
| `broadcast_dedup_sec` | `2.0` | 같은 `AL` 브로드캐스트 원문이 이 시간 안에 다시 오면 XIS 슬롯별 복사본으로 보고 버린다(3.1.2). 0 이하면 끔 |

> `bind_host` 기본값이 `127.0.0.1` 이라 **로컬에서만 받는다.** 외부 XIS·OBSAgent와 붙이려면 `0.0.0.0` 으로 바꿀 것. `bind_port=6600` 은 레거시 IC 계열 관례 포트라 **같은 호스트에 실제 `K.IC` 가 있으면 충돌**한다([`xis/xis.md` 부록 A](xis/xis.md) (11)).

### `[paths]` — 저장

| 키 | 기본값 | 설명 |
|---|---|---|
| `data_dir` | `./icsdata` | **단일 저장 경로.** 레거시 DISK0~3 링은 폐지(6.2) |
| `write_fits` | `false` | true 면 astropy 로 더미 FITS 생성 |
| `fits_shape` | `256, 256` | 더미 이미지 크기 |
| `expnum_file` | (빈 값) | **마지막으로 쓴 EXPNUM 기록 파일.** 비우면 **이 설정파일 옆**에 같은 이름 `.expnum` 으로 자동 결정된다 — 벤치에서는 `~/AICS/Config/ics_sim.expnum`. 재실행하면 그 **+1** 부터 쓴다. `data_dir` 를 비워도 번호는 되돌아가지 않는다(11.12) |

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
| `strict_legacy` | `true` | 남은 스텁(`BIN` 하나, 9.2)을 무응답 처리. 응답 형식의 실측 근거가 없어서다 — `ROI`/`DISPL`/`MOVIE` 는 이 스위치와 무관하게 항상 `Didn't understand` 거부(6.8) |
| `bug_compat` | `false` | 레거시 커맨드워드 오염 재현 (5.4-6) |
| `send_guide_init` | `true` | `ICS>G.IC INITIALIZE` 발신 여부 |
| `console` | `true` | stdin 키보드 인터페이스 |
| `inject` | (빈 값) | 결함 주입: `init_fail`, `acq_short`, `wrote_drop`, `dma_timeout`, `shopen_corrupt`, `tc_timeout` |

### `[auxcontrol]` — AUX control 서버 (9.2.2)

키 이름은 TCSAgent 의 `pctcs.kmtn*.ini` 와 같다. 값 뒤의 `(KMTNC)` 같은 괄호 설명은 무시된다.

| 키 | 기본값 | 설명 |
|---|---|---|
| `enabled` | `false` | 켜야 접속을 시도한다 |
| `AUX_Host` | `127.0.0.1` | 사이트 실제값: KMTNC `192.168.14.60` · KMTNS `192.168.13.60` · KMTNA `192.168.15.60` |
| `AUX_Port` | `5752` | |
| `AUX_TelID` | `KMTNET` | **틀리면 서버가 응답 자체를 안 한다**(규격 2-4) |
| `AUX_SysID` | `AUX` | 규격상 고정 |
| `packet_prefix` | `ICS` | 패킷 ID 접두어 → `ICS1`, `ICS2`, … |
| `packet_id` | (빈 값) | 채우면 고정 사용(예: `00`). 응답 대조가 느슨해진다 |
| `verbose` | `false` | `true` 면 성공(`OK`)도 콘솔에 표시 |
| `ack_timeout` | `1.0` | 응답 대기. 넘으면 경고만 남기고 노출은 진행 |
| `connect_timeout` | `3.0` | |
| `reconnect_sec` / `reconnect_max_sec` | `2.0` / `30.0` | 재접속 간격(실패할수록 2배씩) |
| `hello_cmd` | (빈 값) | 접속 직후 1회. 예: `ALL ECHO ics_sim` |
| `shopen_cmd` | `FILTERS SET_SH OPEN` | 셔터 개방 시 |
| `shclose_cmd` | `FILTERS SET_SH CLOSE` | 셔터 폐쇄 시 |

### `[hardware]` / `[logging]`

| 키 | 기본값 | 설명 |
|---|---|---|
| `backend` | `sim` | `sim` / `archon`. 실기 전환은 이 한 줄(9장). **`archon` + `auxcontrol.enabled=true` 조합은 검증이 경고한다**(9.2.2) |
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
│   ├── auxcontrol.py      AUX control 서버 TCP 연동 (9.2.2)
│   ├── __main__.py        CLI
│   └── hardware/
│       ├── base.py        DetectorBackend 계약 (9.1)
│       ├── sim.py         시뮬 백엔드
│       └── archon.py      **실기 구동 코드가 들어갈 자리** (스텁)
├── tools/
│   ├── scan_legacy_logs.py    5·6장 스캐너 (재검증용)
│   ├── extract_golden.py      골든 픽스처 생성
│   └── xis_probe.py           **실물 연동 시험용 IMPv2 프로브** (3.7)
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

> **⚠️ 상대할 하드웨어의 규모 — Archon 은 2대가 아니라 3 unit 이고, 그중 하나가 가이드다 (2026-08-11 확인).**
>
> 근거는 `__localonly_tcs_simulator/KMTNet Cam Architecture R2.0.pdf` (Rev.2.0 / 2026-06-10, 작성 SMC) 다. 최상위 [`../README.md`](../README.md) 의 *"STA Archon controller 2대"* 는 **과학 계통만 센 값**이다.
>
> | Unit | 담당 | 모듈 구성 |
> |---|---|---|
> | Unit 1 | Sci. **K/M** | ADM ×2 · CLK ×2 · BIAS ×2 · Core · FPGA · DC/DC · 1G Ethernet |
> | Unit 2 | Sci. **N/T** | 〃 |
> | **Unit 3** | **Guide** (CCD N/E/S/W 4대) | **ADC ×2 · Clk · Bias · Utility** — 과학 unit 과 구성이 다르다 |
>
> (계통도에는 과학 unit 두 박스가 둘 다 `Unit 1 (Sci. K/M)` 으로 적혀 있으나 **두 번째는 `Unit 2 (Sci. N/T)` 의 라벨 오타**다 — 운영자 확인. raw pair 의 `MK`/`NT` 분할과도 일치한다.)
>
> **설계 함의 둘**
>
> 1. **`hardware/base.py` 계약을 `ics` 전용으로 좁게 짜면 `icg` 에서 다시 만들어야 한다.** 가이드도 같은 컨트롤러 계열이므로, 아래 D-011/D-010 상기 블록의 시그니처 개정을 할 때 **"컨트롤러 = unit" 단위로 잡고 채널 수·모듈 구성은 설정으로 빼는** 편이 낫다. Unit 3 이 ADC 계열이라 모듈 구성이 다르다는 점이 그 근거다.
> 2. **컴퓨터가 2대로 통합된다.** `Inst. Ctrl.` = `/data` + **OBSAgent** + Obs. utilities + Image viewer + **CCD/Archon Control SW**(= 신규 `ics`), `Inst. Bakup` = `/data` + PSF monitoring & Auto focus + Image viewer + Obs. utilities + **TCSAgent**. 레거시의 Science/Guider server + IC K/M/T/N/G 머신 7대가 둘로 줄고, **`ics` 와 OBSAgent 가 같은 머신·`TCSAgent` 가 다른 머신**이 된다(레거시와 정반대 배치 — [`../OBSAgent/obsagent_report.md`](../OBSAgent/obsagent_report.md) 3절의 운영 규칙이 갱신 대상). 지금 벤치가 한 머신에 다 올라간 구성이라 오히려 신규 배치에 가깝다.

**이미 있는 자산**:

| 파일 | 쓸모 |
|---|---|
| `cam_char/archon/archon_kmtnet_labtest_v2.py` | Archon 텍스트/바이너리 프로토콜로 노출·FETCH 까지 하는 실동작 스크립트. 명령 시퀀스(POWERON, LOADPARAM, FASTPREPPARAM/RELEASETIMING, STATUS/FRAME 폴링, 1 KiB 블록 FETCH)를 그대로 옮기면 된다 |
| `cam_char/archon/archon_simulator.py` | 하드웨어 없이 위 스크립트를 시험하는 프로토콜 시뮬레이터. 이 백엔드 개발 시 상대역 |
| [`raw_fits_spec/`](../raw_fits_spec/README.md) | **`write_fits()` 가 맞출 1차 산출 규격** — Archon raw FITS pair (컨트롤러당 1개, `MK`/`NT`). 2.3 파일명 · 2.5 저장/통보 분리 · 5장 헤더 · 변경점 C-8 이 구현 지시다 |
| `mef_converter/` · `mef_fits_spec/` | raw pair → L0 64-amp MEF **변환기와 그 출력물** 규격. `write_fits()` 의 산출물이 아니라 **다음 단계의 입력↔출력 관계**다 |

**구현 시 유의할 점** (전부 3.3 의 시간 창에서 나온다):
- 4개 CCD 를 병렬로 읽되 **4개의 획득 완료가 1.8초 안에** 모여야 한다. 넘으면 OBSAgent 가 스크립트 관측을 멈춘다.
- 4번째 획득 완료 후 **0.9초 안에** `EXPSTATUS=IDLE` 을 내야 한다.
- `write_fits()` 는 raw pair 저장을 **25초 안에**(정확한 마감은 다음 프레임의 `EXPSTATUS=READOUT` 발신 전, 6.1) 끝내고 `Wrote` 4회를 내보내야 한다.
- `config.validate()` 가 기동 시 이 창을 검사하므로, 실측 타이밍을 `[timing]` 에 넣으면 자동으로 경고가 뜬다.

> **⚠️ ics_archon 착수 시 상기 — 저장 단위와 통보 단위가 갈라진다 (D-009/D-010, 2026-08-07 확정).**
> 시뮬은 레거시 재현이라 "CCD당 파일 1개 = 노출당 4개 + `Wrote` 4회"지만, 실기는 **파일은 컨트롤러당 1개(노출당 `MK`/`NT` 2개), `Wrote` 통보만 CCD 단위 4회를 레거시 형식의 논리 이름으로** 낸다 ([`raw_fits_spec/`](../raw_fits_spec/README.md) 2.5절, 변경점 C-8·C-16). 이때 바뀌는 곳:
> - `hardware/base.py` — `write_fits(ccd, …)` Protocol 이 CCD 단위라 **컨트롤러 단위 저장을 표현할 수 없다.** 시그니처 개정 필요 (2단계 "무개정 전환" 약속은 시퀀서·명령부·메시지 규약에 대한 것이고, 하드웨어 계약 자체는 이 확장의 대상이다).
> - `sequencer._store()` / `state.filename()` — 저장 경로와 `Wrote` 논리 이름의 분리 (C-16). `LASTFILE` 은 실재 경로가 아니게 된다.
> - `telemetry.py` 의 결측 `'0'` 채움 — raw_fits_spec 5.0절 sentinel 규약(`0` 금지)과 정렬 필요 (OI-6/C-9, 11.2 참조).

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

**남은 스텁은 `BIN` 하나다** (2026-08-05 기준). 경과는 이렇다:

- 2026-08-04 — `ROI`/`DISPL`/`MOVIE` 는 **ICS 명령 테이블에 아예 없어서** 레거시가 `ERROR: … Didn't understand … ?` 로 거부한다는 것이 확인돼(6.8) **핸들러를 삭제했다.** 없는 편이 레거시와 같다. 참고용 `IC_ONLY` 상수에 목록만 남겼다.
- 2026-08-05 — **`STOP`/`ABORT` 를 실제로 구현했다** (9.2.1).

`strict_legacy=true` 면 `BIN` 스텁은 **무응답**이다. 레거시가 이를 어떤 형식으로 응답하는지 48GB 로그에 한 건도 없어 재현할 근거가 없기 때문이지, "레거시가 미구현이라서"가 아니다.

### 9.2.1 `STOP` / `ABORT` 구현 (2026-08-05)

레거시(`KMTX\PAP7KX.CMD:279-302`)의 두 분기를 그대로 옮겼다:

| | 레거시 조건 | 우리 조건 | 수락 시 | 거부 문자열(레거시 그대로) |
|---|---|---|---|---|
| `STOP` | `ExpLoopFlag = 1` | `seq.integrating` | 적분만 끊고 readout·저장은 정상 | `No integration in progress. Nothing to stop.` |
| `ABORT` | `GoFlag = 1` | `seq.busy` | 전부 중지, readout·저장 안 함 | `No acquisition in progress. Nothing to abort.` |

**STOP 은 "중단"이 아니라 "조기 종료"다.** 레거시도 `SoftStop = 1` 만 세우고 사이클은 그대로 흘려보낸다. 구현도 같게 했다 — `_countdown` 이 `asyncio.Event` 를 보고 남은 시간을 건너뛸 뿐, 셔터 닫힘 알림부터 `Wrote` 까지 **전부 정상 경로**를 탄다. 바깥에서 보면 그냥 짧은 노출이다. 테스트가 이걸 확인한다(`Acquisition Complete.` 4회, `Wrote` 4회가 그대로 나오는지).

**ABORT 에는 레거시에 없던 일이 하나 더 있다.** 레거시는 CB 가 별도 프로세스라 저장을 따로 신경 쓸 필요가 없었지만, 통합 구조에서는 **이미 떠 있는 저장 태스크를 직접 취소**해야 한다(12.10 과 같은 부류의 차이).

그리고 **중지 후 반드시 `DONE: EXPSTATUS=IDLE` 을 보낸다.** 안 보내면 OBSAgent 의 `CamStatus` 가 `READ_*` 에 갇혀 `force_idle` 타임아웃을 타고 **`opause` 로 스크립트 관측이 멈춘다**(3.3). 레거시가 이 경로를 어떻게 처리했는지는 로그에 한 건도 없어 알 수 없으므로, **3장 규약에서 역산해 정했다.**

> **응답 형식은 근거가 없다.** 두 명령 모두 48GB 전량에서 송수신 0건이라 `DONE:` 본문을 실측할 수 없었다. `Integration stopped by <요청자>` / `Acquisition aborted by <요청자>` 는 **우리가 정한 것**이다(레거시의 `AbortHost` 기록에 대응). 거부 문자열만 레거시 그대로다. 실물 연동에서 관측자 UI 가 이 본문을 파싱한다면 조정이 필요할 수 있다.

### 9.2.2 AUX control 연동 — HW 트리거의 시뮬레이션용 대체물 (2026-08-05)

**레거시에는 없는 경로다.** IC(`\KMTS`)·ICS(`\KMTX`) 소스 어디에도 외부 TCP 발신이 없다 — CEU 에서 새로 붙는다.

규격: `TCSAgent/__reference/KMTNet AUX control remote commands(v20140908).pdf` (Rev.20140908, Sang-Mok Cha, KASI)

```
요청  <TelID> <SysID> <PacketID> <SUBSYSTEM> <COMMAND>[LF]
응답  <TelID> <SysID> <PacketID> <RESPONSE>[LF]
```

#### 이 경로의 성격 — 먼저 짚어야 할 것

**실제 시스템에는 카메라 셔터를 여닫는 SW 명령이 없다.** HE 박스에서 나오는 **TTL 트리거 신호**가 셔터를 구동하고, AUX 는 `FILTERS LIMIT_SHUT` 으로 블레이드 리밋을 **읽기만** 한다(규격 4-2 주석). 여기서 쓰는 `FILTERS SET_SH OPEN|CLOSE` 는 **하드웨어 없이 시험하려고 AUX 쪽에 새로 넣은 명령**이고, 그래서 v20140908 문서에 없다.

→ **실기(`[hardware] backend = archon`)로 넘어가면 `[auxcontrol] enabled = false` 로 꺼야 한다.** 켜 둔 채로 돌리면 셔터에 구동원이 둘 생긴다. `config.validate()` 가 이 조합을 경고한다.

#### 설정 — `pctcs.kmtn*.ini` 와 키 이름을 맞췄다

TCSAgent 가 붙는 AUX 서버와 **대상이 같으므로**, 두 설정을 나란히 놓고 비교할 수 있어야 한다:

```ini
[auxcontrol]
enabled     = false
AUX_Host    = 127.0.0.1 (Local)     # 괄호 설명은 무시된다 (첫 토큰만 읽는다)
AUX_Port    = 5752
AUX_TelID   = KMTNET
AUX_SysID   = AUX
shopen_cmd  = FILTERS SET_SH OPEN
shclose_cmd = FILTERS SET_SH CLOSE
```

`pctcs` 쪽이 값 뒤에 `192.168.14.60 (KMTNC)` 처럼 설명을 붙여 두므로, **그 형식을 그대로 복사해 넣어도 되게** `_head()` 가 첫 토큰만 취한다. 사이트 실제값은 KMTNC `192.168.14.60` · KMTNS `192.168.13.60` · KMTNA `192.168.15.60` 이고, 규격 문서의 `192.168.24.10` 은 작성 시점 값이라 현행과 다르다. 기본값은 로컬 시험을 전제로 `127.0.0.1`.

#### 동작

| 시점 | 보내는 것 |
|---|---|
| 셔터 개방 직후 | `KMTNET AUX ICS1 FILTERS SET_SH OPEN` |
| 셔터 폐쇄 직후 | `KMTNET AUX ICS2 FILTERS SET_SH CLOSE` |

**DARK/BIAS 는 아무것도 보내지 않는다.** 셔터를 열지 않기 때문이고, 레거시의 `SHOPEN`/`SHCLOSE` 도 셔터 경로에만 있으므로 범위가 같다.

응답 등급(사용자 지정):

| 응답 | 처리 | 콘솔 |
|---|---|---|
| `OK` `SUCCESS` | 통과 | 조용히 (`verbose=true` 면 흐리게) |
| `BAD` `FAILURE` `ERROR` | 경고 | **빨강** |
| `WAIT` | 경고 | **청록** — 거부가 아니라 "아직 못 한다" |
| **무응답** | 경고 | **빨강** + 설정 확인 안내 |

#### 무응답을 별도 등급으로 둔 이유

규격 2-4: *"If `<Telescope ID>` or `<System>` is incorrect, or the arguments number is insufficient, the server does NOT return any response."*

**오타가 나도 에러가 아니라 침묵이다.** 가장 헷갈리는 실패 형태이므로 타임아웃을 정상적인 실패 경로로 다루고, 경고에 `AUX_TelID`/`AUX_SysID` 를 확인하라는 안내를 붙였다. 테스트도 이 경우를 따로 잡는다(`test_wrong_telescope_id_times_out_rather_than_hanging`).

#### 실패해도 노출은 계속한다

사용자 결정(2026-08-05): ack 를 기다리되 `ack_timeout` 초과 시 경고만 남기고 진행, 접속이 끊겨 있어도 노출은 진행, 재접속은 백그라운드에서 계속. `AuxControlClient` 는 **예외를 밖으로 내보내지 않는다** — 실패는 전부 반환값과 로그로 표현한다. 테스트가 `OK`/`BAD`/`WAIT`/`ERROR`/무응답/서버부재/TelID오타 전부에서 `Acquisition Complete.` 4회와 `Wrote` 4회가 그대로 나오는지 확인한다.

#### 시험 수단

`tests/test_auxcontrol.py` 에 규격대로 대꾸하는 **가짜 AUX 서버**(`FakeAux`)가 있다. 응답을 바꾸거나 `silent=True` 로 규격 2-4 침묵을 흉내낼 수 있고, **실제 TCP 로** 전 경로를 돈다. AUX 실물 없이 연동을 확인할 때 떼어 쓸 수 있다.

#### 9.2.3 KASI TCS 시뮬레이터의 AUX 서버와 대조 (2026-08-11)

`FakeAux` 는 우리가 규격을 읽고 만든 것이라 **상대의 상태머신을 갖고 있지 않다**. KASI 가 별도로 만든 TCS 통신 시뮬레이터(`__localonly_tcs_simulator/TCS_simulation.zip`, 5750 Telcom + 5752 AUX)에는 그 상태머신이 있고, **`FILTERS SET_SH OPEN|CLOFE` 를 그쪽도 신설 verb 로 구현해 두었다** — 우리 `shopen_cmd`/`shclose_cmd` 기본값과 문자 단위로 일치한다(양쪽 모두 같은 담당자 합의에서 나왔으므로 당연한 결과지만, 실제로 맞물리는 것은 별개 사실이다).

**개발 PC(Windows, Python 3.12)에서 시뮬레이터를 직접 띄워 와이어로 확인했다.** 벤치가 아니라 로컬 대조이므로 근거의 범위는 "프로토콜과 시간 예산" 까지다 — pctcs 를 경유한 `SHUTOP` 관측은 벤치 몫이다.

| 시각 | 보낸 것 | 응답 | `FILTERS LIMIT_SHUT` |
|---|---|---|---|
| t+0.00 | `KMTNET AUX ICS1 FILTERS SET_SH OPEN` | `OK` | `0 1` (Full 이동 중) |
| t+1.00 | `KMTNET AUX ICS2 FILTERS SET_SH CLOSE` | `OK` | — (노출 1초 → 규격 CASE B "이동 슬릿") |
| t+1.00 | `KMTNET AUX ICS3 FILTERS SET_SH OPEN` | **`WAIT`** | — (재장전 중) |
| t+6.00 | | | `1 2` (dwell) |
| t+11.0 | | | `0 0` (재장전 이동) |
| t+14.0 | | | `2 1` (**standby 복귀**) |
| t+14.0 | `KMTNET AUX ICS4 FILTERS SET_SH OPEN` | `OK` | |
| — | 틀린 `AUX_TelID` / `AUX_SysID` | **무응답** | 규격 2-4 그대로 |

**여기서 나오는 운용 제약 하나 — `[auxcontrol] enabled = true` 인 시험은 `[timing] time_scale = 1.0` 이어야 한다.**

셔터 한 사이클이 **와이어 기준 약 14초**(개방 5 + 폐쇄 5 + dwell 0.5 + 재장전 5, 스큐 포함)인데, **상대 시뮬의 시간은 우리 `time_scale` 을 따라오지 않는다.** 축척을 낮춰 돌리면 다음 노출의 `SET_SH OPEN` 이 재장전 구간에 걸려 `WAIT` 를 받고, 9.2.2 의 응답 등급대로 청록 경고가 뜬다 — 우리 결함이 아니라 축척 불일치다. 따라서 AUX 를 물린 시험은 `time_scale = 1.0` · `exp >= 5` · 노출 간격 >= 15초 로 돌리고, 빠른 회귀는 `enabled = false` 로 따로 돈다.

> 참고로 상대 시뮬의 `AuxConfig` 주석은 **TCSAgent 가 `OPENING`/`CLOSING`/`RELOADING` 이 `FS_ShutOpTime + SOP_TIMEOUT = 6.2초` 를 넘으면 `SHUTOP=ERROR` 로 표시**한다고 적어 두었고, 재장전 구간(5.7초)이 그 예산에 0.5초만 남긴다고 명시한다. 실기 셔터도 같은 예산이므로, **`archon` 백엔드로 갈 때 이 창이 그대로 살아 있다** — `[auxcontrol] enabled = false` 로 꺼도 HE 박스 TTL 이 같은 시퀀스를 구동한다는 뜻이다(9.2.2 서두).

### 9.3 FITS 경로

`fitsout.py` 는 지금은 더미 배열을 쓰지만, **헤더 생성(AUX/TCS 텔레메트리 → FITS 키워드)은 처음부터 실제와 같은 경로**로 만들었다. 다음 단계에서 `fetch_image()` 가 실제 픽셀을 돌려주면 그대로 저장된다.

실기 단계의 헤더·파일 규격은 [`raw_fits_spec/`](../raw_fits_spec/README.md) 다 (5장 헤더 키워드, 2.3 파일명, 2.5 저장/통보 분리 — 위 9.1 의 상기 블록). `mef_fits_spec/` 정합은 raw pair 를 받는 converter 쪽 일이다. 지금은 레거시 헤더 재현까지가 목표다.

---

## 10. 테스트 전략

```bash
cd ics_sim
python -m pytest tests -q
```

현재 **177개 전부 통과** (2026-08-11).

> **테스트가 잡지 못한 것도 기록해 둔다.** `ExpNum` 값 결함(12.14)은 `transport.feed()` 테스트 156개를 전부 통과한 채로 살아남았다 — 형식(15자)과 파일명 연속성은 검사했지만 **값의 의미**를 검사하지 않았기 때문이다. 이 계층의 테스트가 다루지 못하는 것이 무엇인지는 3.7 참고.

| 파일 | 지키는 것 |
|---|---|
| `test_obsagent_contract.py` | **최우선.** 3장 규약 전체 — 상태 전이, 개수 규약, 타임아웃 창, `ExpNum` 왕복, 응답 체크 문자열, 수신 9노드, `GO n` |
| `test_emitter_hygiene.py` | 5장 오염 방지 — 정방향(시뮬 출력이 깨끗한가) + **역방향**(레거시 샘플을 잡아내는가) |
| `test_sequence_golden.py` | 4·6장 — 레거시 실측 시퀀스와 메시지 종류·순서·개수 일치 |
| `test_impv2.py` | 프로토콜 파싱 — malformed 무응답, 대소문자 무관, 다중 단어 값, 깨진 명령 거부 |
| `test_stop_abort.py` | 9.2.1 — STOP/ABORT 의 레거시 분기 재현과 중지 후 IDLE 복귀 |
| `test_auxcontrol.py` | 9.2.2 — AUX control 연동, 응답별 처리, 무응답에도 노출 완주 |
| `test_xis_echo.py` | 3.1.2 — 자기 발신 에코·브로드캐스트 중복·노드 ID 검증 |

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
- **주의 (2026-08-08)**: 결측 수치를 `'0'` 으로 채우는 이 sentinel 은 **레거시 메시지 계층**의 관례다. `raw_fits_spec/` 5.0절은 FITS 헤더에서 `0` 을 값-없음으로 쓰는 것을 금지한다(`-999.0`/`-1`/`'NC'`) — **ics_archon 의 헤더 생성 경로는 규격 쪽을 따라야 한다** (OI-6/C-9, 9.1 상기 블록·13장).

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
- **보강 (2026-08-04)**: XIS의 `Added UDP Client` 로그 분석에서 **테이블이 노드 ID로 키잉된다**는 강력한 증거가 나왔다([`xis/xis.md` 부록 A](xis/xis.md) (4)) — `ABC`/`GMON` 이 하루 수천 번 주소를 바꿔도 `Added` 는 XIS 재시작당 1회뿐이다. 1안의 위험도가 크게 낮아졌지만 "ID로 키잉된다"와 "같은 주소를 여러 ID가 공유해도 된다"는 별개 명제라 소스 확인은 그대로 유지한다.
- **확정 (2026-08-04)**: XIS 서버 소스로 **1안 안전 확정, 2안 불필요**(3.1.1). "잠정"은 해제됐다. `register_all_nodes` 스위치는 남긴다.
- **근거 트리 정정 (2026-08-05)**: 위 확정의 근거가 은퇴 분기(`EXEC_ISIS/`)였고 **운영본은 `ISIS/` v2.9.1** 이다(3.1.1, 12.12). 인용한 코드가 두 분기에서 바이트 동일하므로 **결정 자체는 바뀌지 않는다.** 1안의 이점도 그대로다 — preset 한 줄, `MAXPRESET 32` 중 19줄 여유.
- **전환 조건과 확인 항목**: [`xis/xis.md` 부록 A](xis/xis.md) (8).

### 11.11 실물 연동 시험의 XIS 빌드·기동 환경 — 원격 리눅스 채택 (2026-08-07)

- **배경**: 실물 연동 시험([`xis/xis.md` 7~8절](xis/xis.md))은 XIS(ISIS v2.9.1)를 소스에서 재빌드해 띄우는 것이 선행 조건인데, 운영 바이너리가 백업에 없고 소스는 리눅스용(g++ · readline · ncurses)이다. 개발 PC(Windows 11)에는 WSL · Docker · gcc 가 전부 없다.
- **대안**:
  - (a) **WSL2 + Ubuntu 설치** — 실제 운영 환경(리눅스)과 가장 가깝고 이후 OBSAgent(obstool) 빌드에도 재사용 가능. 단 관리자 권한과 재부팅이 필요할 수 있다.
  - (b) **원격 리눅스 머신** — 이미 있는 리눅스 서버(KASI 내부 서버, KMTNet TestBed 등)에 SSH 로 접속해 빌드·기동. 운영과 같은 실제 리눅스라 판정 신뢰도가 가장 높다. 접속 정보·네트워크 경로(시뮬 ↔ XIS 간 UDP 왕복)가 전제.
  - (c) **MSYS2** — POSIX 호환 레이어로 Windows 에서 빌드. 관리자 권한이 필요 없지만 소켓/시리얼 동작이 실제 리눅스와 다를 수 있어 판정 신뢰도가 떨어진다.
- **선택**: (b) 원격 리눅스 머신. (2026-08-07, 사용자 결정)
- **이유**: 추가 설치 없이 실제 리눅스에서 판정할 수 있어 신뢰도와 착수 비용이 모두 낫다. ics_sim 은 Python 이라 원격 머신에서 함께 돌리거나, UDP 가 통하면 이 PC 에서 `--xis-host` 로 원격 XIS 를 가리켜도 된다. (a)/(c) 는 원격 머신이 여의치 않을 때의 대비책으로 남긴다.
- **후속 (2026-08-11)**: 그 리눅스에서 칠 명령을 [`xis/build-local.sh`](xis/build-local.sh) 로 굳혔다. **2026-08-11 에 그 머신에서 실제로 빌드해 `isis`·`isisd` 를 얻었다.** 걸림돌은 넷이었고(정적 분석 3 + 실측 1) 전부 스크립트가 처리한다. 배경은 [`xis/xis.md` 4절](xis/xis.md).

### 11.12 EXPNUM 을 파일에 지속시킨다 — `data_dir` 스캔은 채택하지 않았다 (2026-08-11)

- **배경**: 벤치 연동 시험에서 `FitsNum=00000000.000000` · `FitsOsc=CHECK` 가 나왔다. 추적해 보니 `state.py` 의 `expnum` 이 **매 실행 1 부터 시작**해서(초기값이 곧 유일한 출처였고 ini 키도 없었다) 두 번째 실행부터 기존 파일과 충돌했고, 파일명 fail-safe(6.4)가 `KMTN` 없는 이름(`260811.000.fits`)으로 바꿔 쓰는 바람에 OBSAgent 의 `FitsNum` 파싱(`KMTN`+6 부터 15자, 3.2)이 통째로 실패한 것이었다. **fail-safe 자체는 정상 동작이다** — 문제는 매 실행 그것을 부르게 만든 카운터 초기화다.
- **요구사항 (운영자 확정)**: *"ics 를 재실행해도, `data_dir` 내부 파일 유무와 상관없이, EXPNUM 은 무조건 1 씩 증가해야 한다."* 그리고 *"마지막에 썼던 EXPNUM 을 어딘가에 기록해 두고, 재실행 시 그 번호에서 1 증가해 사용한다."*
- **대안**: (a) 기동 시 `data_dir` 를 훑어 `KMTN?.<날짜>.<번호>.fits` 최대값+1 (b) 마지막으로 쓴 번호를 파일에 기록 (c) 그대로 두고 시험 전에 `data_dir` 를 비우는 운용 규칙.
- **선택**: **(b).**
- **이유**: (a) 는 요구사항을 정면으로 깬다 — 저장 파일을 지우거나 다른 곳으로 옮기면 번호가 되돌아가고, 그러면 지난 야간의 파일과 번호가 겹칠 수 있다. (c) 는 사람이 매번 기억해야 하는 규칙이고, 잊으면 증상이 `FitsNum` 실패라는 **엉뚱한 곳**에서 나타난다(실제로 그렇게 나타났다). (b) 는 레거시 ICS 의 지속 카운터 의미와도 같다 — 레거시가 ICS 6자리 / IC 4자리 불일치를 `INITIALIZE` 로 동기 맞춰야 했던 이유 자체가 그 번호가 지속되는 값이었기 때문이다.
- **기록 위치**: `[paths] expnum_file`. **비워 두면 설정파일 옆에 같은 이름 `.expnum` 으로 자동 결정**된다(`config.resolve_expnum_file`) — 벤치 배치에서 `-c ~/AICS/Config/ics_sim.ini` 로 띄우면 `~/AICS/Config/ics_sim.expnum` 이 된다. `~/AICS` 의 네 폴더 중 `Config/` 를 고른 것은 `Logs/` 는 비워지고 `data/` 는 요구사항상 배제되기 때문이다(저장 파일과 무관해야 한다). 설정파일 이름을 따르므로 `-c` 로 여러 구성을 나란히 돌려도 카운터가 섞이지 않는다.
- **기록 시점은 `advance()` 가 아니라 `next_suffix()` 다.** 즉 번호를 **쓰는 순간** 기록한다. `advance()`(=`EXPSTATUS=IDLE` 직후)까지 미루면 노출 도중에 죽었을 때 그 번호가 기록되지 않아 재실행이 같은 번호를 다시 쓰고, 방금 저장한 파일과 충돌해 결국 위와 같은 fail-safe 경로를 탄다. 임시 파일 + `os.replace` 로 바꿔 넣어 기록이 반쯤 쓰인 상태로 남지 않게 했다.
- **실패해도 기동·노출을 막지 않는다.** 기록이 없으면 1 부터, 깨져 있으면 경고를 내고 1 부터, 쓸 수 없으면 경고만 내고 진행한다. 번호가 겹치면 fail-safe 가 받아 주고 **그 경고가 곧 "카운터가 안 읽혔다" 는 신호**가 되므로, 조용히 틀리는 경로가 없다.
- **단위 테스트는 지속을 끈다.** `conftest.make_config()` 가 `expnum_file = ''` 로 덮는다 — 저장소 ini 를 읽으므로 그대로 두면 `<repo>/ics_sim.expnum` 이 생기고, 실행마다 번호가 올라가 프레임 번호를 기대값으로 박아 둔 테스트가 **실행 순서에 좌우된다.** 지속 자체는 `tests/test_expnum_persist.py` 가 `tmp_path` 로 따로 검증한다(12개).

> **`ics_archon` 으로 넘어갈 때 같이 볼 것** — fail-safe 이름 `<yymmdd>.<nnn>.fits` 에는 **CCD 식별이 없다.** 이번 벤치 로그에서 4개 CCD 가 `260811.000`~`003` 으로 흩어져 어느 파일이 어느 검출기인지 알 수 없게 됐다. 레거시는 최후수단이라 감수했지만, raw pair 는 컨트롤러당 1파일이므로 **fail-safe 이름에도 `MK`/`NT` 태그를 유지하는 쪽**이 맞다. `raw_fits_spec` 의 open item 에 없는 항목이다 → 13장.

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

지금은 1안으로 두되 **미해결로 명시**하고, XIS 소스를 받으면 확인하기로 했다([`xis/xis.md` 부록 A](xis/xis.md) (7)(8)).

**후속 (2026-08-04)**: XIS의 `Added UDP Client` 로그를 찾아 분석한 결과 테이블이 노드 ID로 키잉된다는 강력한 증거가 나왔다([`xis/xis.md` 부록 A](xis/xis.md) (4)). 처음의 단언이 결과적으로는 맞는 방향이었던 셈이지만, **단언한 시점에 그 근거를 갖고 있지 않았다**는 사실은 달라지지 않는다. 결론이 맞았는지가 아니라 근거의 범위를 지켰는지가 문제다.

교훈: **"동작 원리를 안다"와 "그 구성이 검증됐다"는 다르다.** 방향을 확인한 것만으로 미시험 구성을 안전하다고 말하면 안 됐다. 12.1의 `dest` 필터 누락과 같은 계열의 실수다 — 근거의 범위를 넘어서 결론을 내렸다.

### 12.8 "XIS가 PING을 로그 열기 전에 보낸다" → **순서가 반대. 이유가 달랐다**

`XIS>AL PING` 이 로그에 없는데 PONG이 1 ms 안에 도착하는 것을 보고 "PING을 먼저 보내고 그 다음 로그를 연 것"으로 추론했다. **순서는 틀렸다.**

`main.c` 의 실제 기동 순서는 `loadConfig() → openSocket() → initLog() → 메인 루프 → COLD_START → handShake()` 로 **로그가 먼저 열린다.**

PING이 로그에 없는 진짜 이유는 `handShake()` 가 `write()`/`sendto()` 를 직접 호출하고 `logMessage()` 를 거치지 않기 때문이다 — **XIS는 자기가 보내는 handshake PING을 로깅하지 않는다.** 관측(PING 없음 + PONG 1 ms)은 두 설명 모두와 양립했고, 소스를 봐야 갈렸다.

교훈: **관측이 가설과 일치한다고 해서 그 가설만 참인 것은 아니다.** 같은 관측을 낳는 다른 메커니즘이 있는지 먼저 세어봤어야 했다.

### 12.9 XIS 서버 소스로 확정된 것 — 이전 추론들의 최종 판정

`ics_legacy/__dts_legacy/` 의 XIS 서버 소스로 [`xis/xis.md` 부록 A](xis/xis.md) (8)의 질문에 전부 답이 나왔다(같은 부록 (12)). 이전 단계의 추론이 어떻게 판정됐는지 정리한다:

| 추론 | 근거 단계 | 최종 판정 |
|---|---|---|
| XIS 테이블은 노드ID→주소 방향 | `ABC`/`GMON` ephemeral 포트 | **맞음** (`updateHosts()`) |
| 테이블이 ID로 키잉된다 | `Added UDP Client` 빈도 | **맞음** — 주소는 비교에 아예 안 쓰인다 |
| 같은 주소에 9개 ID를 올려도 안전 | (근거 없이 단언 → 보류) | **맞음.** 충돌 검사가 아예 없다. ~~브로드캐스트 코드가 "같은 포트를 공유하는 클라이언트"를 명시적으로 다룬다~~ → **그건 코드가 아니라 주석이었다. 12.12 참고.** 결론은 앞 근거 하나로 성립 |
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

### 12.12 "XIS 서버 소스는 `EXEC_ISIS/server/`" → **운영본은 `ISIS/server/` 였다** (2026-08-05)

XIS 자산을 [`xis/`](xis/) 로 따로 정리하는 작업에서 나왔다. **12.9 의 판정표 전체가 은퇴한 트리를 읽고 만들어진 것이었다.**

**무엇을 착각했나.** 백업 `dts.icsci/` 에는 허브로 보이는 트리가 셋 있다 — `ISIS/`(v2.9.1) · `EXEC_ISIS/`(XISIS v2.7.3) · `ISIS_V1/`(v2.7.3). 로그의 노드 이름이 `XIS` 이고 그중 하나가 `EXEC_ISIS` 안에서 스스로를 `XISIS` 라 부르니(`xisisserver.h`, `xisis.ini`, `xisis.last`) **이름이 맞는 것을 운영본으로 집어 들었다.** 다른 두 트리는 열어 보지도 않았다.

실제로는 `XIS` 가 **프로그램 이름이 아니라 `Config/isis.ini` 의 `ServerID` 값**이다. stock ISIS 를 `ServerID XIS` 로 띄우면 로그가 똑같이 `XIS>…` 로 찍힌다.

**어떻게 드러났나.** 보관본을 만들며 세 트리를 나란히 놓고 나서다. 결정적이었던 것은 **운영 설정 자체가 v2.9.1 을 요구한다**는 점이었다 — `TTYPort /dev/ttyS0 115200` 의 속도 인자를 파싱하는 코드가 v2.9.1 에만 있고, v2.7.3 은 `B9600` 하드코딩이다. `isis.ini` 주석의 *"max 16 / max 32"* 도 v2.9.1 헤더와만 맞는다. 3개 사이트 기동 스크립트가 전부 `/home/dts/ISIS/server/isis` 를 띄우고, `stopisis`/`chkisis` 가 `ps -C isis` 로 찾는 것(v2.7.3 산출물 이름은 `xisis`)까지 한 방향을 가리켰다. 전체는 [`xis/xis.md` 3절](xis/xis.md).

**판정 — 결론 대부분은 살아남았다.** `clients.c` · `messages.c` · `commands.c` · `serverlog.c` · `utils.c` 가 두 분기에서 **`#include` 한 줄 빼고 바이트 동일**이다. 등록 방식(② ID 키잉 · ③ 충돌 검사 없음 · ⑤ `MAXCLIENTS 64` · ⑥ 브로드캐스트 9회) 과 `handShake()`(④) 는 그대로다. **1안 확정도 유지된다.**

| 12.9 의 항목 | 트리 교체 후 |
|---|---|
| 노드ID→주소 방향 · ID 키잉 · `handShake()` · `unlisted` 해석 · preset 개별 `sendto` | **영향 없음** (동일 코드) |
| "브로드캐스트 코드가 같은 포트 공유를 명시적으로 다룬다" | **틀림 — 코드가 아니라 주석이었다.** 운영본은 `i != sendHost` |
| ⑧ `MAXPRESET` 미해결 | **해결.** 운영본은 32 |

**교훈 세 가지.**

1. **12.11 의 패턴이 한 단계 위에서 반복됐다.** 거기서는 *무엇*은 맞고 *왜*가 어긋났는데, 여기서는 **읽은 코드가 맞는지를 확인하지 않았다.** 코드를 인용하면 근거가 단단해진 느낌이 들지만, **어느 코드인지가 틀리면 인용은 아무것도 보장하지 않는다.**
2. **이름의 일치를 검증으로 착각했다.** `XIS` ↔ `XISIS` 는 그럴듯했고, 그럴듯함이 확인을 대신했다. **"이 소스가 정말 운영본인가"는 별도의 질문이고, 별도의 근거가 필요하다** — 기동 스크립트·설정 경로·빌드 산출물 이름처럼.
3. **틀린 근거로도 맞는 결론에 닿을 수 있다.** 결론이 살아남은 것은 두 분기가 거의 같았던 **운** 이지 판단의 질이 아니다. 12.7 의 *"결론이 맞았는지가 아니라 근거의 범위를 지켰는지가 문제"* 가 세 번째로 반복된다.

> **파급 점검 (12.11 의 교훈 적용).** 이 정정이 닿는 절을 전부 열어 확인했다 — 3.1.1 · 11.10 · 12.9 · 13장 백로그 · 2.1 자료표 · `README.md` · `SMC_CLAUDE.md`. **깨진 결론은 없고, `MAXPRESET` 하나가 해결되고 브로드캐스트 에코 항목이 하나 늘었다.**

### 12.13 "에코 문제는 브로드캐스트 PING 뿐" → **유니캐스트 루프백이 본체였다** (2026-08-08)

실물 연동 시험 전 전 문서·코드 일제 점검에서 나왔다. 백로그와 xis.md 는 에코 대응을 *"`cmd_ping()` 이 `msg.src ∈ registered_ids` 면 무응답"* 으로만 적어 두었는데, **그 범위로 고쳤다면 진짜 문제가 그대로 살아남았다.**

**무엇을 놓쳤나.** 시퀀서가 레거시 규약대로 `K.IC` 앞으로 내보내는 `INITIALIZE`/`ERASE`/`SHOPEN`/`GO` 는 **유니캐스트**다. XIS 경유 모드에서 이 메시지들은 클라이언트 테이블의 `K.IC` 주소(=우리 자신)로 배달되고, `_on_message` 에 src 검사가 없어 **새 명령으로 재실행된다** — `ERASE` 이중 실행, `SHOPEN` 셔터 재구동 + `Shutter=Open` 중복 발신(CamStatus 역행), `GO` busy ERROR. PONG 버스트는 이 옆의 소음일 뿐이었다.

**왜 놓쳤나.** 에코를 처음 인지한 맥락이 "XIS 재시작 브로드캐스트에 9개 PONG" 이라서, 대응도 그 사례 안에서만 설계했다. **"XIS 는 우리가 보낸 모든 것을 자기 테이블대로 되돌려줄 수 있다"** 로 일반화하지 않았다. 12.11 의 교훈("새 발견이 기존 결론과 만나는 지점에서 기존 문서를 되짚어라")의 변형이다 — 이번엔 새 발견이 아니라 **알고 있던 결함의 적용 범위**를 되짚지 않았다.

수정: 수신 초입 자기 발신 필터 + 브로드캐스트 중복 억제 (3.1.2). `nodes.py` 의 `owns()` 가 정의만 되고 호출처가 없던 것이 이 구멍의 흔적이다.

### 12.14 "`ExpNum` 은 응답하기만 하면 된다" → **값도 규약이었다** (2026-08-11)

3.4 는 `ExpNum` 자동 질의를 발견하고 *"응답하지 않으면 표시가 갱신되지 않는다"* 까지 적었다. **무슨 값을 답해야 하는지는 적지 않았다.** 그래서 구현은 현재 카운터를 그대로 답했고, 테스트 둘(`test_expnum_query_answered` = 15자 형식 / `test_expnum_advances_between_exposures` = 파일명 연속성)은 **둘 다 통과했다.**

실물 OBSAgent 를 붙이자마자 드러났다 — 노출 2 가 도는 내내 관측자 화면이 `ExpNum=...000001` 이었고, 그 노출이 저장한 파일은 `...000002` 였다. 종료 후에도 `ExpNum`/`FitsNum` 이 한 칸 어긋난 채 남았다.

**어느 쪽 잘못인지는 아카이브가 갈랐다.** 두 가능성이 있었다 — (a) 우리가 틀렸다 (b) 레거시도 N 을 답했고 OBSAgent 의 오래된 표시 버그다. CTIO `isis.20250401.log` 에서 `EXPNUM` 응답과 같은 노출의 `Wrote` 파일명을 대조하니 세 사이클 연속으로 응답이 한 칸 앞섰다(3.4 표). **(a) 였다.**

**왜 놓쳤나.** 이 규약을 로그에서 발견할 때 본 것이 *"질의가 있고 응답이 있다"* 는 왕복 자체였다. 응답의 **값**이 무엇인지는 그때 물어보지 않았고, 물어봤더라도 같은 로그로 답할 수 있었다 — 필요한 것은 이번에 한 대조 한 번뿐이었다. 3.2 의 `Wrote`·`Acquisition Complete.` 는 개수와 문자열이 곧 규약이라 자연히 값까지 봤는데, `ExpNum` 은 "응답하면 되는 것"으로 분류해 버린 것이 갈림길이었다.

**교훈.** 상대가 보낸 값을 **어디에 쓰는지**까지 따라가야 규약이 완성된다. `strNextNum` → `strCurNum` 승격이라는 이름이 소스에 이미 있었고, 그 이름만 제대로 읽었어도 "다음 노출 번호"가 나왔다. 12.6 에서 `ExpNum` 의 **목적**을 밝혀낸 것으로 만족하고 **값**까지 가지 않은 것이 이 결함의 자리다.

수정: `state.peek_suffix()` 가 프레임이 번호를 점유 중일 때(`exposing and suffix_taken`) 하나 더한다. `suffix_taken` 은 `next_suffix()` 가 세우고 `advance()` 가 내리며, ABORT 로 `advance()` 를 건너뛰어도 `exposing` 이 `_run()` 의 finally 에서 내려가 자가 복구된다.

> **이것이 실물 연동 시험의 값을 가장 잘 보여주는 사례다.** `transport.feed()` 테스트도, `obsagent_model.py` 재현본도 이 결함을 잡을 수 없었다 — 재현본은 CamStatus 체인만 흉내 내고 `strNextNum` 승격은 다루지 않기 때문이다. **받은 값이 관측자 화면에서 어떻게 쓰이는지는 실물 OBSAgent 만 보여줄 수 있었다.**

**실물 재확인 완료 (2026-08-11 2차, 3.7.2).** 이 수정은 그때까지 시뮬 단위 테스트까지만 검증돼 있었다. 벤치에서 노출 두 번을 돌려 관측자 화면을 직접 읽은 결과 **readout 중 `ExpNum` 이 그 프레임의 파일 번호와 같고, 종료 후 `ExpNum`==`FitsNum`** 이었다(두 프레임 모두). `EXPNUM` 응답도 `000003`/`000004` 로 N+1 이었다.

> **그리고 재확인 자체가 한 번 막혔다.** 첫 시도는 `FitsNum=00000000.000000` 으로 판정이 아예 불가능했는데, 원인은 이 수정이 아니라 **EXPNUM 카운터가 재실행마다 1 로 되돌아가는 별개 결함**이었다(11.12). 번호가 겹쳐 파일명 fail-safe 가 `KMTN` 없는 이름을 쓰자 3.2 의 슬라이스가 실패한 것이다.
>
> 여기서 얻은 것 — **`ExpNum` 규약의 실물 판정은 파일명 fail-safe 가 침묵할 때만 성립한다.** 두 항목이 독립이라고 보고 있었는데 실제로는 후자가 전자의 전제였다. 12.11 의 교훈("새 발견이 기존 결론과 만나는 지점을 되짚어라")이 **판정 절차 자체에도 적용된다**는 사례다.

---

## 13. 개선 제안 · 백로그

| 항목 | 내용 | 우선도 |
|---|---|---|
| ~~XIS 등록 방식 확정 (1안 vs 2안)~~ | **해결됨 (2026-08-04).** XIS 서버 소스로 테이블이 노드ID로만 키잉되고 주소 충돌 검사가 없음을 확인 → **1안 확정, 2안 불필요**(3.1.1) | 완료 |
| ~~`XIS>AL PING` 에 9개 PONG 응답~~ | **구현 완료 (2026-08-04)** — `cmd_ping()` 이 브로드캐스트면 9개 ID 전부로 PONG(3.1.1) | 완료 |
| **XIS `isis.ini` 에 시뮬 등록** | `UDPPort <sim_ip> <sim_port>` 한 줄 추가. ~~`MAXPRESET` 여유 확인 필요~~ → **선행 조건 해소 (2026-08-05).** 시험 벤치에서는 `127.0.0.1 6600` 한 줄로 **적용·검증 완료 (2026-08-11)**. **운영 허브 반영은 남아 있다** — 다만 xis.md 7절 경고대로 레거시 정지 또는 분리 인스턴스가 전제다 | 운영 측 |
| ~~**XIS 콘솔 `info` 로 `MaxPreset` 실측**~~ | **선행 조건에서 확인 절차로 격하 (2026-08-05).** 소스로 32 확정. 실물에서는 `VERSION`(2.9.1 인지) · `INFO`(`… of 32 max`) 로 판정만 재확인한다 | 중간 |
| ~~**`UDPPING` 으로 등록 선시험**~~ | **완료 (2026-08-11).** XIS 콘솔 `UDPPING 127.0.0.1 6600` 한 방에 9개 ID 전부가 PONG 했다 — XIS 재시작 후 재등록의 유일한 경로가 실물에서 확인됐다 | 완료 |
| ~~**자기 발신 에코 무시**~~ | **구현 완료 (2026-08-08, 3.1.2).** 점검에서 브로드캐스트 에코보다 심각한 **유니캐스트 루프백**(ERASE/SHOPEN 이중 실행)이 드러나(12.13) `_on_message` 초입 필터로 확대. 브로드캐스트 중복 억제·노드 ID 검증 포함, 테스트 15개 | 완료 |
| **`write_fits()` raw pair 구현 (C-8)** | ics_archon 에서 `raw_fits_spec/` 2.3·2.5·5장대로 **컨트롤러당 1파일**(`MK`/`NT`) 저장. `hardware/base.py` 의 CCD 단위 Protocol 시그니처 개정 포함 (9.1 상기 블록) | ics_archon |
| **저장/통보 단위 분리 (C-16)** | `sequencer._store()`·`state.filename()` 을 물리 저장 경로와 `Wrote` 논리 이름으로 분리 (D-010). 물리 경로 prefix 는 `[node]` 의 사이트 코드 (D-011). `LASTFILE` 은 실재 경로가 아니게 된다 | ics_archon |
| **sentinel 정렬 (C-9)** | ics_archon 헤더 생성 경로의 결측값을 raw_fits_spec 5.0절 규약(`-999.0`/`-1`/`'NC'`, `0` 금지)으로 — 메시지 계층의 `'0'` 채움(11.2)과 구분 | ics_archon |
| ~~**EXPNUM 이 재실행마다 1 로 되돌아간다**~~ | **해결 (2026-08-11, 11.12).** 벤치에서 `FitsNum=00000000.000000` 으로 드러났다 — 번호가 겹쳐 파일명 fail-safe 가 `KMTN` 없는 이름을 쓰자 OBSAgent 파싱이 실패했다. 마지막으로 쓴 번호를 `[paths] expnum_file`(기본: 설정파일 옆)에 기록하고 기동 시 +1 부터 쓴다. 테스트 12개(`test_expnum_persist.py`) | 완료 |
| **fail-safe 가 나면 검출기 식별이 복구 불가다** | 대체 이름 `<yymmdd>.<nnn>.fits` 에 검출기 식별이 없는데, **헤더에도 없다** — `telemetry.header_dict()` 는 AUX/TCS 필드 + sentinel + `TELID` + `DATE-OBS` 뿐이고 `DETECTOR`/`INSTRUME`/`CCDNAME`/`FILENAME`/`EXPID`/`CTRLTAG` 가 하나도 없다. 게다가 4개 CCD 가 `dict(header)` 로 **같은 헤더**를 받는다(`sequencer.py:285,289`). 즉 CCD 식별이 **파일명에만** 있었고, 이름이 바뀌면 파일만 보고는 되찾을 수 없다. 벤치에서 실제로 4개가 `260811.000`~`004` 로 흩어졌다(11.12 말미). **고치는 방향은 이미 규격에 있다** — `raw_fits_spec` README 가 *"아카이브·DTS 도구는 `LASTFILE` 대신 raw 헤더의 `FILENAME`/`EXPID`/`CTRLTAG` 를 근거로 삼아야 한다"* 고 정했다(D-010 의 부작용 절). 그 세 키워드가 헤더에 들어가면 대체 이름이 무엇이든 식별이 살아남고, raw pair 는 컨트롤러당 1파일이므로 `MK`/`NT` 태그도 함께 유지한다 | ics_archon |
| **발신 길이 검사** | 2048자 제한이 수신에서만 강제된다(`impv2.py`). 텔레메트리 pass-through 가 TC 응답에 꼬리를 붙이는 구조라 발신 초과를 스스로 진단할 수단이 필요 | 낮음 |
| **XIS 재빌드 검증** | 운영 바이너리(`isis` v2.9.1)가 백업에 없다. **빌드 스크립트 `xis/build-local.sh` 를 만들어 뒀다(2026-08-11)** — 보관본을 건드리지 않고 작업 사본에서 빌드·설치하고, 현대 툴체인 걸림돌 3가지(CRLF · `logMessage` 리터럴/`register` · `.c.o` 서픽스 규칙)를 처리한다(`xis/xis.md` 4.2). **2026-08-11 SSO AIC 리눅스에서 빌드 성공** — 걸림돌은 넷이었고 그중 하나(포인터/정수0 순서비교)는 실제 컴파일에서만 드러나 스크립트에 반영했다. **재빌드 가능성이 실측으로 확인됐다** | 완료 |
| 주기적 재등록 | preset 목록에 등록되면 필수는 아니나 안전망으로 유효 | 중간 |
| Caliban(`*.CB`) 소스 검토 | `__dts_legacy/.../Agents_V1/Caliban/src/` 에 CB 노드 소스가 있다(`TransferDisk.c` 등). 신규는 CB 계층을 내부화하므로 우선순위는 낮지만, 디스크 핸드셰이크·파일명 fail-safe 의 실제 구현이다 | 낮음 |
| ~~**`IC2.img` 에서 `\KMTX` 추출**~~ | **완료 (2026-08-04).** 예상과 달리 바이너리가 아니라 **FreeBASIC 소스**가 통째로 들어 있어 역어셈블이 불필요했다. 결과: 5.5(오염 원인 코드) · 6.8(명령 테이블) · 6.9(SSO `Wrote` 단절) | 완료 |
| ~~**`\KMTS`·`\KMTG` 소스 정독**~~ | **완료 (2026-08-05).** `K.IC`·`G.IC`·`ICGui` 이미지를 추가로 확보해 읽었다. 결과: 6.10(IC 동작 전부) · 6.11(ICG = ICS 같은 바이너리) · `ics_legacy_report.md` 4.6 | 완료 |
| **`PCTREAD` 4블록 간격의 이유** | 6.10 주석 — 블록 양자화까지는 확정했으나 왜 3블록이 아니라 4블록인지 미해결. `YLinesIn` 갱신 지점과 `NUMPHLINES=32` preheat 처리를 봐야 한다. 시뮬은 실측값을 쓰므로 **동작에는 영향 없음** | 낮음 |
| ~~**실물 XIS 연동 시험**~~ | **완료 (2026-08-11).** 9개 ID 등록 · 에코 필터 · 브로드캐스트 재등록 · 개별 IC 라우팅 · 실물 TCSAgent/OBSAgent 연동 · 노출 사이클 전 구간. **`ExpNum` 값 결함 하나를 잡았다**(12.14). 결과는 [`xis/xis.md` 8절](xis/xis.md) | 완료 |
| **`STOP`/`ABORT` 실물 재확인** | 9.2.1 의 `DONE:` 본문은 실측 근거 없이 우리가 정한 것이라 실물 OBSAgent 로 확인하려 했으나 **이번 시험에서 다루지 못했다.** 벤치가 그대로 있으므로 `go` 중 `stop`/`abort` 를 쳐 보면 된다 | 중간 |
| **`GO n` · `.osc` 스크립트 관측 실물 확인** | `Image k of n complete. EXPSTATUS=IDLE` 경로(6.1)와 명령별 응답 판정(3.5)은 실물에서 미확인. `.osc` 자산이 `OBSAgent.latest/KMTObs/osc/` 에 있어 회귀 시험으로 쓸 수 있다 | 중간 |
| ~~**`STOP`/`ABORT` 실제 구현**~~ | **완료 (2026-08-05).** 레거시 분기(`PAP7KX.CMD:279-302`)를 그대로 옮겼다(9.2.1). 테스트 12개 추가. 단 **`DONE:` 본문 형식은 실측 근거가 없어 우리가 정한 것**이므로 실물 연동에서 재확인 필요 | 완료 |
| **SSO `Wrote` 결함 운영측 보고** | 6.9 — SSO Caliban 의 `GetFITS.c:532` 가 `STATUS:` 로 고쳐져 있어 ICS 중계가 끊겼고, 그 결과 **매 노출 `FitsSaved` 가 25초 타임아웃으로만 서고 있다.** 레거시를 계속 쓰는 동안은 한 단어(`STATUS:`→`DONE:`) 수정으로 고쳐진다. 신규 `ics` 에는 해당 없음 | 중간 |
| **`EXPNUM` 자릿수 통일** | 레거시는 ICS 6자리 / IC 4자리라 `INITIALIZE` 로 우회했다. 신규는 이미 6자리로 통일했으니, 외부 문서도 갱신 필요 | 완료(신규) |
| **구조화 로깅(JSON) 병행** | 이번 48GB 스캔 같은 사후 분석 비용을 크게 낮춘다. 사람이 읽는 로그와 병행 출력 | 높음 |
| **상태 조회 API(HTTP/JSON)** | `GMON` 이 UDP 로 초당 폴링하는 방식의 현대적 대안. IMPv2 채널은 그대로 두고 추가 | 중간 |
| **`DataSource=SIM` 정식 승격** | 레거시에 이미 정의된 값(6.4). 시뮬 백엔드를 이 이름으로 노출하면 프로토콜상 자연스럽다 | 완료 |
| **`SYNCHRONIZE` 모델 결정** | 레거시는 "누가 보냈든 반영"하는 수동 리스너였다. 발신자 검증형으로 바꿀지 결정 필요 | 중간 |
| **파일명 fail-safe 유지** | 1999년 Prospero 시절부터 검증된 데이터 유실 방지 장치. 그대로 가져간다 | 완료 |
| **`force_ready=270`(12.2초) 대기** | 신규 시스템에서 병목이면 OBSAgent 개정이 필요하다. **현재는 개정하지 않기로 확정**된 상태이므로 기록만 | 보류 |
| ~~**`CHA` 노드 성격 확인**~~ | **해결됨 (2026-08-11).** 운영자 확인 — **시험용 임시 노드 ID** 다. 6.3 갱신 | 완료 |
| ~~**ICG 오염 여부 확인**~~ | **해결됨 (2026-08-05).** ICG 는 ICS 와 **같은 바이너리**라 5.5 의 오염이 그대로 있다(6.11). OBSAgent 가 가이드를 무시하므로 관측 영향은 없다 | 완료 |

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

### `ics_sim/xis/` — 신설 (2026-08-05)
- **XIS 원본 보관본을 만들었다.** `__dts_legacy` 3사이트 백업에서 허브 관련 자산 **162 파일 / 1.5 MB** 를 뽑아 정리 — 운영본 소스(`src/`) · 사이트별 운영 설정(`install/config/`) · 기동 스크립트(`install/scripts/`) · 연동 시험 도구(`tools/isisPerl/`) · 은퇴 분기와 실행파일(`branches/xisis-2.7.3/`)
- `xis/xis.md` — 중심 문서. 트리 판정 근거(3절) · 확보 범위와 재빌드(4절) · 사이트별 설정(5절) · **신규 `ics` 에 걸리는 것(6절)** · 실물 확인 절차(7절)
- `xis/MANIFEST.md` — 파일별 출처와 사이트 간 동일성 / `xis/SHA256SUMS.txt` — 162 파일 체크섬
- `xis/.gitignore` — 루트의 `*.log`·`test.*` 규칙이 원본 파일명을 거르지 않도록 무력화
- 원본은 `ics_legacy/__dts_legacy/` 에 그대로 둔다. 보관본은 **사본**이지 이동이 아니다

### `ics_sim/` 자체 문서
- `SMC_CLAUDE.md` — 문서표에 `xis/xis.md` 추가, "XIS 노드 등록" 절에 **근거 트리 정정 + `MAXPRESET` 해결** 블록, `xis/` 신설 안내
- `README.md` — "XIS 허브에 붙이기" 절에서 브로드캐스트 근거 문장을 정확히 고치고 **자기 발신 8부 에코** 주의 추가

### 그 외
- 최상위 `README.md` "저장소 구성" 표에 `ics_sim/` 추가
- `ics_legacy/SMC_CLAUDE.md` "다음에 이어서 할 만한 일" 갱신
- `ics_legacy/__sample_isislog/samples_for_bug.txt` git 추가(8.1)

> ~~**미반영 (2026-08-05)**: `ics_legacy/ics_legacy_report.md` 도 `EXEC_ISIS/server/` 를 "XIS 서버 소스 전체"로 적고(자료 색인) **8.0.1 (13) 에 같은 `MAXPRESET` 미해결 항목**을 두고 있다.~~ → **반영 완료 (2026-08-08).** 아래 일제 점검에서 처리.

### 전 문서 정합성 일제 점검 (2026-08-08)

실물 연동 시험 전에 작업 산출물 전체(레거시 보고서 3부작 · TCSAgent/OBSAgent 보고서 · ics_sim · xis · raw_fits_spec)를 교차 점검했다. 지적 47건 중 확정 15건 + 추가 검증 통과분을 반영:

- `ics_legacy/ics_legacy_report.md` — §8.0.1(13) 근거 트리 `ISIS/server/` 정정 + `MAXPRESET` 해결 처리, **§8.0.1(14) 신설**(스크립트 응답 체크, 3.5 의 역이식), §8.1 STOP/ABORT 모순 제거, §1.1 `TELID=KMTS`→SAAO 오기, §4.2/§8.1 디스크 서술, 내부 절 참조 3건
- `ics_legacy/icg_legacy_report.md` — "ICS 는 셔터 OPEN 시 질의" 4곳 정정(실제는 ERASE 전후 질의, 셔터 후는 TCSSTATUS 중계만), 서두의 "소스 없음" 낡은 서술, 디스크 3개→최대 4중, 죽은 4.7절 참조
- `OBSAgent/obsagent_report.md` — **`EXPSTATUS=READOUT` 도 `count_wrote`/`FitsSaved` 리셋** 반영(마감시한이 문서보다 ~2.7초 빠름), §6.1(e) 응답 체크 신설, if/else-if 체인 구조, `force_idle/2` 수치, 마침표 비대칭, GMON 절 번호
- `TCSAgent/tcsagent_report.md` — catalog 경로 모순(`pctcs.h:112` 로 확정), §9.1 필드명 배포 주체 매듭
- `raw_fits_spec/` — 2.5절 `Wrote` 마감시한을 READOUT 기준으로 정정 + ics_archon 발신 순서 규칙 명시, 5.5절 트래커 서술 완화 / `DECISION_LOG.md` D-009 영향절 조건부화
- `ics_sim/xis/xis.md` — **7절에 운영 허브 라우팅 가로채기 경고**(레거시 정지 후 시험), 체크리스트 정리, 파일 수 162 통일, 부록 A 참조 3건 / `MANIFEST.md` `.gitattributes` 등재
- 이 문서 — 3.1.2 신설(에코 필터), 12.13, 9.1/9.3 raw_fits_spec 연결, 3.2 논리/물리 파일명 구분, 7장/10장/13장 갱신

### 실물 연동 시험 반영 (2026-08-11)

- **이 문서** — 3.7 신설(시험 결과) · 12.14 신설(`ExpNum` 결함) · 3.4 에 값 규약 · 3.1.1/3.1.2 실물 검증 · 6.3 `CHA` 확정 · 10·13장
- **코드** — `state.py` 의 `suffix_taken`, 테스트 2개 추가(165개 통과)
- **`TCSAgent`·`OBSAgent` 보고서 12절 신설** — 현대 툴체인 재빌드(걸림돌 6종 + 실행으로 드러난 레거시 결함 2종)와 `~/AICS` 벤치 배치. **`build-local.sh` 두 개로 자동화**했다
- 두 `SMC_CLAUDE.md` — "아직 git 에 커밋되지 않았다"(2026-07-29) 낡은 서술 정정

---

## 15. 범위 밖과 그 이유

| 항목 | 왜 뺐나 |
|---|---|
| **XIS 허브** | 별도 프로그램이고 이미 운용 중이다. 시뮬은 `xis_host` 설정으로 붙거나, 비워 두면 direct-reply 로 혼자 돈다. **만들지는 않지만 상대는 알아야 하므로 소스·설정을 [`xis/`](xis/) 에 보관해 두었다**(3.1.1). **단 XIS 폐지가 로드맵에 있으므로 이 "범위 밖" 은 3단계까지의 것이다** — 4단계에서는 `ics` 가 허브를 흡수하는 것이 유력한 경로이고, 그때 보관본은 모방 대상이 된다(1.2 의 4단계 블록) |
| **TC 스텁** | TC 는 `TCSAgent` 라는 완성된 프로그램이 있다. 시뮬은 질의를 보내되 응답이 없으면 레거시와 같이 빈 필드로 진행한다(6.5) |
| **OBS 드라이버** | OBSAgent 가 실물로 존재한다. 손으로 돌려볼 수단은 `console.py`(레거시 관례상 ICS 자체 기능) |
| **ICG/ABC 가이드 계통** | 별도 프로그램(`icg`)으로 갈 것이 확정돼 있다. OBSAgent 가 가이드 발신을 무시하므로 하위호환 부담도 비대칭이다 |
| **시리얼 트랜스포트** | 아래 참고 |

### 시리얼에 관하여

실측 로그상 **ICS↔XIS 링크만 시리얼(`/dev/ttyS0`)** 이고 나머지 노드(IC/CB/TC/OBS)는 전부 UDP 다. 5.3 의 바이트 손상·메시지 접합이 이 구간에 집중되는 것과 정합적이다.

시뮬은 UDP 만 쓴다. **신규 시스템이 UDP 로 가면 5.3 계열 손상은 구조적으로 사라진다** — 셔터가 열리지 않은 노출 같은 실제 데이터 손실이 없어진다는 뜻이다. 이것만으로도 전환의 근거가 된다.

`transport.py` 는 필요하면 pyserial 백엔드를 추가할 수 있는 구조지만, 지금은 넣지 않았다.
