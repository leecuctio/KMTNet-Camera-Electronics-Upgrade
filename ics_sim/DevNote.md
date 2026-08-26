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

> **논리 이름 vs 물리 파일 (D-011/D-010; D-009는 2026-08-10 D-011로 대체)** — 위 형식이 고정인 것은 **`Wrote` 메시지에 싣는 논리 이름**이다. 실기(ics_archon)의 디스크 실물은 **컨트롤러당 1개, 노출당 2개** `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits` 로 저장하고 (`<SITE>` 는 `[node] site`/`telid` 에서 유도한 `KMTC`/`KMTS`/`KMTA`/`KMTT` — config.validate() 가 site↔telid 정합을 검사한다), 통보만 CCD 단위 4회를 논리 이름으로 낸다 ([`../raw_fits_spec/`](../raw_fits_spec/README.md) 2.3/2.5절). **시뮬도 2026-08-11 부터 이 물리 구성으로 저장한다** — 하드웨어 없이 D-010/D-011 을 실물 OBSAgent 로 검증하려고 앞당겼다(11.13, D-012). 종전에는 레거시 재현으로 CCD당 1파일을 썼다. 전환 계약은 9.1·9.3.

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
- **TCSSTATUS 는 `DATE-OBS` 를 확정한 뒤에야 중계**한다. FITS 헤더의 `DATE-OBS`/좌표가 노출 시작 순간을 반영하도록 하기 위한 설계다. DARK/BIAS 는 `ERASE` 완료 시점을 "논리적 노출 시작"으로 삼는다.
  - **`DATE-OBS` 는 `SHOPEN` 을 지시한 시각이다 (2026-08-12 확정).** 레거시는 `Shutter=Open` 응답을 받은 뒤(+0.15초) 확정했으나, **실기에는 셔터 개방 완료를 알려 주는 경로가 없다** — TTL 이 구동하고 AUX 는 리밋을 읽기만 한다(9.2.2). ICS 가 아는 시각은 지시를 낸 순간뿐이므로 그것을 정의로 삼는다. 근거와 파급은 [`../raw_fits_spec/`](../raw_fits_spec/README.md) 5.7절 블록.

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
| `expnum_file` | (빈 값) | **마지막으로 쓴 EXPNUM 기록 파일.** 비우면 **이 설정파일 옆**에 같은 이름 `.expnum` 으로 자동 결정된다 — 벤치에서는 `~/AIC/Config/ics_sim.expnum`. 재실행하면 그 **+1** 부터 쓴다. `data_dir` 를 비워도 번호는 되돌아가지 않는다(11.12) |

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
> **→ 이 세 가지는 2026-08-11 에 시뮬에서 먼저 처리했다 (11.13, D-012).** 하드웨어 없이 검증되는 부분이라 앞당겼다:
> - `hardware/base.py` — `write_fits(ccd, …)` → **`write_frame(controller, chips, path, header)`** 로 개정 완료. (2단계 "무개정 전환" 약속은 시퀀서·명령부·메시지 규약에 대한 것이고, 하드웨어 계약 자체는 이 확장의 대상이었다.)
> - `sequencer._store()` / `state.filename()` — 분리 완료 (C-16). 물리/논리 이름 생성은 신설 [`rawpair.py`](ics_sim/rawpair.py), `state.filename()` 은 논리 이름 생성기로 남았다. `LASTFILE` 은 실재 경로가 아니게 됐다.
> - `telemetry.py` 의 결측 `'0'` 채움 — `fits_header_dict()` 분리로 해결 (C-9/OI-6). 메시지 계층은 `'0'` 유지.
>
> **`archon.py` 에 남은 것은 실제 픽셀·실물 크기·`BITPIX=16`+`BZERO=32768`·4장 픽셀 배치다** — 파일 구성과 이름·헤더 규약은 시뮬이 이미 지키고 있다.

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

현재 **197개 전부 통과** (2026-08-11).

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
- **기록 위치**: `[paths] expnum_file`. **비워 두면 설정파일 옆에 같은 이름 `.expnum` 으로 자동 결정**된다(`config.resolve_expnum_file`) — 벤치 배치에서 `-c ~/AIC/Config/ics_sim.ini` 로 띄우면 `~/AIC/Config/ics_sim.expnum` 이 된다. `~/AIC` 의 네 폴더 중 `Config/` 를 고른 것은 `Logs/` 는 비워지고 `data/` 는 요구사항상 배제되기 때문이다(저장 파일과 무관해야 한다). 설정파일 이름을 따르므로 `-c` 로 여러 구성을 나란히 돌려도 카운터가 섞이지 않는다.
- **기록 시점은 `advance()` 가 아니라 `next_suffix()` 다.** 즉 번호를 **쓰는 순간** 기록한다. `advance()`(=`EXPSTATUS=IDLE` 직후)까지 미루면 노출 도중에 죽었을 때 그 번호가 기록되지 않아 재실행이 같은 번호를 다시 쓰고, 방금 저장한 파일과 충돌해 결국 위와 같은 fail-safe 경로를 탄다. 임시 파일 + `os.replace` 로 바꿔 넣어 기록이 반쯤 쓰인 상태로 남지 않게 했다.
- **실패해도 기동·노출을 막지 않는다.** 기록이 없으면 1 부터, 깨져 있으면 경고를 내고 1 부터, 쓸 수 없으면 경고만 내고 진행한다. 번호가 겹치면 fail-safe 가 받아 주고 **그 경고가 곧 "카운터가 안 읽혔다" 는 신호**가 되므로, 조용히 틀리는 경로가 없다.
- **단위 테스트는 지속을 끈다.** `conftest.make_config()` 가 `expnum_file = ''` 로 덮는다 — 저장소 ini 를 읽으므로 그대로 두면 `<repo>/ics_sim.expnum` 이 생기고, 실행마다 번호가 올라가 프레임 번호를 기대값으로 박아 둔 테스트가 **실행 순서에 좌우된다.** 지속 자체는 `tests/test_expnum_persist.py` 가 `tmp_path` 로 따로 검증한다(12개).

> **`ics_archon` 으로 넘어갈 때 같이 볼 것** — fail-safe 이름 `<yymmdd>.<nnn>.fits` 에는 **CCD 식별이 없다.** 이번 벤치 로그에서 4개 CCD 가 `260811.000`~`003` 으로 흩어져 어느 파일이 어느 검출기인지 알 수 없게 됐다. → **11.13 에서 해결됐다** (헤더에 식별 카드를 실어 개명과 무관하게 살아남게 했다).

### 11.13 raw pair 규격을 시뮬에 적용 — 저장/통보 분리 (2026-08-11)

- **배경**: `raw_fits_spec` 은 실기(`ics_archon`)가 지킬 규격으로 쓰였고, 시뮬은 레거시 재현이라 CCD당 1파일을 그대로 썼다. 그래서 D-010(저장/통보 분리)·D-011(사이트 코드)·C-8·C-16 이 **한 번도 실행된 적이 없었다** — 규약이 문서에만 있었다.
- **대안**: (a) 실기 단계까지 미룬다 (b) 시뮬을 규격대로 바꾼다 (c) 헤더·sentinel 만 맞추고 저장 단위는 그대로 둔다.
- **선택**: **(b).**
- **이유**: **하드웨어가 없어도 검증되는 부분이다.** 실물 OBSAgent 로 `Wrote` 4회·논리 이름·`FitsNum` 파싱을 확인할 수 있으므로, 규약 리스크를 Archon 도착 전에 소진한다. `ExpNum` 값 결함이 실물 연동에서야 드러난 경위(12.14)가 이 순서를 택한 직접적인 이유다 — **규약은 실물에 붙여야 값이 틀린 걸 안다.** (a)/(c) 는 그 확인을 하드웨어 도착 뒤로 미룬다.
- **하드웨어 계약을 먼저 개정했다 (D-012).** `write_fits(ccd, …)` → `write_frame(controller, chips, path, header)`. 종전 시그니처로는 컨트롤러 단위 저장을 **표현할 수 없었다**(9.1 의 상기 블록이 적어 둔 그 문제다). 가이드도 Archon 이므로(9.1) 컨트롤러 단위로 잡아 두면 `icg` 가 같은 계약을 재사용한다 — CCD 단위로 좁게 두면 두 번 만들어야 했다.
- **분리의 책임 위치**: 저장/통보 분리와 파일명 fail-safe 는 **시퀀서**가 하고 백엔드는 관여하지 않는다. 백엔드에는 이미 확정된 경로가 내려온다. 물리/논리 이름 생성과 정체성 카드는 신설 [`rawpair.py`](ics_sim/rawpair.py) 한 곳에 모았다.
- **`state.ChannelState.filename()` 은 논리 이름 생성기로 남았다** (C-16 의 지시 그대로). 물리 경로는 `rawpair.physical_path()` 다.

**결과 — 한 노출이 만드는 것**

```
물리 파일 2개   <SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits   (chip M, K)
                <SITE>.<YYYYMMDD>.<NNNNNN>.NT.fits   (chip N, T)
Wrote 통보 4회  KMTN{m,k,n,t}.<YYYYMMDD>.<NNNNNN>.fits   (논리 이름, KMTN 불변)
```

**OBSAgent 는 변경이 없다.** 기존 규약 테스트 177개가 **한 개도 손대지 않고 전부 통과**한 것이 그 증거다 — 통보가 논리 이름 그대로이므로 `count_wrote`·`FitsNum`·타임아웃 창이 모두 같다. D-010 이 설계한 대로다.

#### 11.13.1 이 과정에서 잡은 것 둘

**① 헤더에 검출기 식별이 하나도 없었다.** `telemetry.header_dict()` 는 AUX/TCS 텔레메트리만 담고 `DETECTOR`/`INSTRUME`/`FILENAME`/`EXPID`/`CTRLTAG` 가 전무했으며, 4개 CCD 가 `dict(header)` 로 **같은 헤더**를 받았다. 즉 검출기 식별이 **파일명에만** 있었고, fail-safe 가 이름을 바꾸면 되찾을 방법이 없었다. 규격 5.1·5.2절 카드를 실어 해결했고, **개명 후에도 `EXPID`+`CTRLTAG` 가 남는다**는 규칙을 규격 2.3.1절에 명시했다.

**② `EXPID` 가 실수 카드로 저장됐다.** `fitsout._apply_header` 는 텔레메트리를 와이어 문자열로 받아 숫자로 바꾼다 — `EQUINOX='2000.000'` 이 실수로 들어가야 하므로 그 동작이 맞다. 그런데 `EXPID='20260811.000001'` 이 그 규칙에 걸려 float 이 됐다. 규격 5.2절은 `EXPID` 를 **문자열**로 정의한다.

> **파급이 형 문제로 끝나지 않는다 — 자릿수가 날아간다.** 실수 카드는 뒤쪽 0 을 버리므로 `'20260811.000010'` → `20260811.00001` 이 되어 **규격 2.3절이 필수로 정한 6자리 zero-padding 이 파괴된다**(`000100`→`0001`, `010000`→`01`). `EXPID` 는 파일명 `<NNNNNN>` 과 같은 값이고 pair 동일성 검사와 `Wrote` 논리 이름의 근거라, 어긋나면 규격 6.2절의 "조용히 틀린 값" 부류가 된다. 규칙을 규격 **5.0절**에 적어 뒀다.
>
> **그리고 내 첫 테스트가 이걸 놓칠 수 있었다.** 시험값을 `000001` 로 잡았는데 그 값은 실수 왕복이 우연히 성립한다 — `000010` 이었으면 바로 드러났다. 지금은 형 검사(값 무관)와 **끝자리 0 네 가지 값의 왕복 검사**를 함께 둔다(`test_expid_keeps_its_zero_padding`).

> 교정은 `fitsout.FitsStr` — "문자열로 강제" 를 값 자체가 들고 다니게 하는 타입이다. 호출측 시그니처를 늘리지 않고, 정체성 카드만 그 타입으로 싣는다. `test_identifier_cards_stay_strings` 가 회귀를 막는다.
>
> **이 결함은 테스트를 쓰면서 잡혔다.** 헤더 카드가 "있는지" 만 봤다면 통과했을 것이다 — `EXPID` 는 값도 형도 규약이라는 점에서 `ExpNum`(12.14)과 **같은 부류**다. 그때의 교훈("상대가 그 값을 어디에 쓰는지까지 따라가야 규약이 완성된다")이 이번엔 converter 쪽에 적용된다.

#### 11.13.2 레거시 헤더 실측본으로 식별 keyword 를 재정의 (2026-08-12)

운영자가 레거시 raw/MEF 헤더 실물을 `../raw_fits_spec/__reference/Legacy raw fits header samples/` 에 넣어 줬다 — **raw 1건**(`KMTNk.20170209`, SSO)과 같은 노출의 MEF 33건, 그리고 `KMTNc.20210503` 1건이다.

> **근거의 크기를 정확히 적어 둔다.** `KMTNc` 가 2021년 자료라서 "raw 2건이 4년간 불변" 으로 읽고 싶어지지만 **그건 raw 가 아니다** — ROI 조각을 모자이크로 재구성한 combination 산출물이다(운영자 확인). 두 파일의 keyword 집합은 `INPUTFMT` 하나만 다른데, 그게 뒷받침하는 사실은 *"raw 헤더가 4년간 안 바뀌었다"* 가 아니라 **"같은 헤더 틀을 raw 와 조합 산출물에 함께 썼다"** 다. 틀이 정착돼 있었다는 근거는 되지만 시간에 따른 안정성의 근거는 아니다. 처음에 전자로 적었다가 고쳤다.

여기서 우리 설계의 중복이 드러났다. 레거시는 이렇게 나눴다:

```
FILENAME = 'KMTNk.20170209.044131'   / Filename assigned by the data-taking system
UNIQNAME = '170209.000'              / Unique filename; if filename is invalid
```

**`FILENAME` 하나가 날짜+연번을 다 담고 있었다.** 우리가 새로 만든 `EXPID`(`'20260811.000001'`)와 `EXPNUM`(정수 연번)은 그 상위집합의 부분집합이었던 셈이다.

그래서 **새 keyword 를 만드는 대신 레거시의 두 낱말을 이어받기로 했다**(운영자 확정):

- **`FILENAME` 을 그대로 이어받는다** — `EXPID`·`EXPNUM` 은 삭제한다. 같은 정보를 담은 카드가 넷이면 서로 어긋날 수 있고, 어긋났을 때 무엇이 정본인지 규격이 답해야 하는데 그 답을 만들 이유가 없다. 20년 가까이 쓰인 이름을 쓰면 기존 아카이브·도구·운영자의 지식이 이어지는 이점도 있다. `EXPID` 는 이 저장소가 새로 만든 낱말이고 MEF 규격·converter·레거시 어디에도 없었다.
- **`UNIQNAME` 은 보완해서 계속 쓴다** — 이름 충돌 대비라는 취지는 살리되, 형식과 역할을 아래처럼 바꿨다. MEF keyword 정의서가 `UNIQNAME` 을 *"unique filename or exposure ID"* 로 받으므로 전달할 자리도 이미 있다.

| | 결정 |
|---|---|
| `EXPID` · `EXPNUM` | **삭제.** `UNIQNAME` 이 날짜·연번·컨트롤러를 다 담는다 |
| `UNIQNAME` | **정본 식별자로 승격.** 필수 · 불변 · `<SITE>.<8자리>.<6자리>.<MK\|NT>` |
| `FILENAME` | **실제로 쓴 이름.** 평소엔 `UNIQNAME` 과 같다 |
| 둘 다 | **확장자를 빼고** 기록 — 레거시 관례 |
| `NAMECLSH` | 신설. 이름이 겹쳤을 때**만** |

**레거시와 방향이 반대인 지점이 하나 있다.** 레거시는 `UNIQNAME` 을 *대체* 이름으로 썼는데, 우리는 *정본* 으로 뒀다. 이유는 **파싱 규칙을 하나로 만들기 위해서**다 — 레거시 방식에서는 상황에 따라 `FILENAME` 이나 `UNIQNAME` 을 골라 읽어야 했지만, 정본을 불변으로 두면 언제나 `UNIQNAME` 하나만 보면 된다.

**이름 충돌 처리도 바꿨다** — 개명 대신 **격리**가 먼저다:

```
정상   <data_dir>/KMTA.20260811.000001.MK.fits
충돌   <data_dir>/clash/KMTA.20260811.000001.MK.clash20260812T031545Z.fits
       + NAMECLSH = T
```

개명하는 목적은 "덮어쓰지 않기" 하나뿐인데 디렉토리를 옮기면 그 목적이 달성되면서 **이름을 훼손하지 않는다.** 접미를 번호가 아니라 시각으로 한 것은 소진되지 않고 **언제 생긴 중복인지가 남기** 때문이다. `clash` 라는 낱말은 겹친 것이 **이름**이고 자료는 멀쩡하다는 뜻이다 — `dup` 은 자료가 중복이라는 오해를 부른다. 디렉토리·접미·카드가 같은 낱말을 쓴다.

부수로 `state.unique_path()` 는 삭제했다 — 레거시 `<yymmdd>.<nnn>` 을 만들던 함수이고 이제 `rawpair.resolve_write_path()` 가 대신한다.

> **`KMTNc.20210503.030331` 샘플은 raw pair 가 아니다** — `DETID='C'`, 1616×1616 인데, **raw 영상의 ROI 조각들을 모자이크로 재구성한 combination 산출물**이다(운영자 확인). 검출기가 아니므로 이 규격 범위 밖이다. 다음 사람이 또 파지 않도록 적어 둔다.

**아직 안 한 것**: 픽셀은 더미이고 크기도 실물(19200×9400, 파일당 344 MiB)이 아니다. 4장 픽셀 배치도 실기 몫이다 — **구조와 규약만 맞췄다.** chip 2개를 X 방향으로 이어 붙이는 것까지는 흉내 낸다(`sim._join_x`). `BITPIX=16`+`BZERO=32768`(규격 3장)은 **11.14 에서 맞췄다** — 그러지 않으면 산출물이 converter 에 한 번도 들어가 볼 수 없다.

---

### 11.14 레거시 헤더 123개를 하나씩 판정하고 규격 5장을 실제로 구현 (2026-08-13)

운영자 요청은 *"기존 raw fits의 헤더를 참고하여 남겨둘 것은 남겨두고 없앨것은 없애고, 새로 추가할 건 추가해서 새로운 archon 용 raw fits pair의 헤더를 정의하고, ics_sim에 반영"* 이었다. 11.13.2 가 **식별 keyword** 만 다뤘으니 이번엔 나머지 전부다.

#### 방법 — 세 방향으로 맞댔다

한 방향만 보면 반드시 놓친다. 그래서 셋을 각각 돌렸다.

| 방향 | 질문 | 결과 |
|---|---|---|
| 레거시 → 규격 | 레거시에 있는데 규격에 없는 것 | 123개 중 **22개** |
| converter → 규격 | converter 가 읽는데 규격이 정의하지 않은 것 | **7개** |
| 규격 → 구현 | 규격이 요구하는데 `ics_sim` 이 안 쓰는 것 | **~130개** |

세 번째가 가장 컸다. `ics_sim` 은 68장(정체성 17 + 텔레메트리 중계)만 쓰고 있었고, geometry(5.3) · detector(5.4) · controller(5.5) · 전압(5.6) · 노출(5.7) · 관측(5.8) · 측지값(5.9) · 온도(5.10)가 **통째로 없었다.**

#### 판정 22개 — 계승 5 · 개칭 1 · 폐지 16

표는 규격 5.13절에 있다. 계승 판단의 기준을 하나로 정했다 — **뜻이 같을 때만 이름을 물려받는다.**

계승 넷은 "이 카드가 없으면 자료를 오인하게 되는 것" 들이다:

- **`DATASRC`** — 픽셀이 실물인지 시뮬인지 알려주는 유일한 카드다. 값을 `ARCHON`/`SIM` 으로 재정의했다. 레거시도 `SIM` 을 유효값으로 뒀다(6.4).
- **`HEMODE`** — Archon 3대 중 1대가 guide 전용이라 `SCIENCE`/`GUIDE` 구분이 살아 있다.
- **`LEDFLASH`** — 램프로 만든 실험실 flat 을 하늘 자료로 오인하지 않게 한다.
- **`ICSBUILD`** — 헤더 이상을 소스 상태로 되짚는 근거다.

다섯째 `NPHLINES` 는 Archon timing script 에도 있는 개념이라 값의 출처만 바뀐다.

#### 이번 재검토에서 나온 것 셋

**(가) `OVERSCNY` 는 이름 계승이 위험할 수 있음을 보여준다.** 레거시의 Y overscan 은 **가장자리**를, 신규는 **영상 중앙**을 뜻한다(규격 4.2절). 이름을 물려주면 `OVERSCNY=168` 을 본 도구가 "위쪽 168행 자르기" 를 해서 **아무 오류 없이** active 픽셀을 지운다. 계승을 기본값으로 두면 안 된다는 것을 이 하나가 보여준다.

**(나) 규격 안에 불일치가 있었다 — 컨트롤러 정체가 조용히 사라진다.**

```
규격 5.5절     : raw 가 CTRLNAME/CTRLSN/CTRLFW(단수형)를 싣고
                 converter 가 CTRL1ID/CTRL1SN/... 으로 옮긴다
규격 6.3절     : raw 가 CTRL1ID/CTRL1SN/CTRL1FW/CTRL2* 를 실어야 한다
converter 실물 : v("CTRL1ID","UNKNOWN")  <- 색인 이름을 raw 에서 직접 읽는다
```

**converter 는 그 변환을 하지 않는다.** `primary_cards()` 는 `mk_hdr` 하나만 받고(`v2_1.py:758`), 색인 이름이 없으면 `'UNKNOWN'` 을 넣는다. 즉 종전 규격대로 구현하면 MEF 의 컨트롤러 정체가 **전부 `UNKNOWN`** 이 되고, **오류 없이** 그렇게 된다.

이걸 계기로 레거시 설계를 다시 봤더니 같은 구조였다 — raw 파일마다 `KBUILD`/`MBUILD`/`TBUILD`/`NBUILD`/`GBUILD` 를 **다 실어서** 한 장만 열어도 카메라 전체 전자부 상태를 알 수 있게 했다. **내가 11.13.2 에서 이 다섯을 "중복이니 폐지" 로 기울었던 것이 틀렸다** — 취지가 있었고, 색인형이 그 계승이다(규격 5.5.0절, D-013).

**정체와 런타임 상태를 갈랐다.** 노출 1회 안에서 컨트롤러의 *정체*는 달라질 수 없으므로 양쪽에 실어도 어긋날 수 없다. 반면 보드 온도·독출 시간·오류 플래그는 실제로 다르므로, MK 헤더에 두 대분 실으면 NT 자신의 헤더와 어긋날 수 있는 값이 생긴다. 그래서 런타임 상태는 단수형으로 두고, MEF `TELEMETRY` 표의 2행을 채우는 것은 converter 가 NT 헤더도 읽는 일로 남겼다(C-17).

**(다) `DSTEL` 은 개칭이 강제된다.** AUX 실선이 보내는 이름은 `DSTEL`(`pctcs/commands.c:2023`)인데 Archon converter 는 `v("DSTELALT","")` 로 **`DSTELALT` 만** 읽는다(`v2_1.py:485`). 레거시32 converter 에는 `sv(ph,"DSTELALT", sv(ph,"DSTEL"))` 로 fallback 이 있지만 Archon 쪽에는 없다. 그래서 `telemetry.py` 에 `_FITS_RENAME` 을 두고 옮겨 싣는다 — **원래 이름도 함께 남긴다**(레거시 도구와의 연속성이고, 옮겨 실은 것이 대조 가능해야 한다).

#### 구현

| 파일 | 한 일 |
|---|---|
| `rawhdr.py` (신설) | 규격 5.3~5.10 카드 생성. geometry 상수 + **import 시 불변식 검사**, detector, controller(색인형 포함), amp 배선, 전압, 노출, 관측, 측지값, 온도 |
| `hardware/base.py` | 계약 확장 — `controller_info()` · `sensors()` · `voltages()` · `amp_map()` |
| `hardware/sim.py` | 위 넷 구현. 값은 레거시 실측 범위 |
| `hardware/archon.py` | 위 넷 스텁. **예외를 던지지 않고 빈 값을 돌려준다** — 헤더 생성은 저장 경로이므로 여기서 던지면 다른 이유로 실기를 돌려 보는 사람이 저장 단계에서 막힌다 |
| `sequencer.py` | `_store()` 가 세 덩어리를 겹쳐 헤더를 만든다. `_backend_fact()` 로 백엔드 실패를 sentinel 로 흡수. `_darktime()` 분리. `st.exp_end` 기록(`TSHSHUT`) |
| `telemetry.py` | `_FITS_RENAME` (`DSTEL`→`DSTELALT`), `TCSQDATE`/`TCSUDATE`/`AUXQDATE`/`AUXUDATE` 를 문자열 sentinel 로 |
| `fitsout.py` | 더미를 `uint16` 으로 저장 → `BITPIX=16`+`BZERO=32768`. `checksum=True` |
| `config.py` | `[site]` 섹션(`SiteCfg`) |
| `state.py` | `exp_end` |

결과: 헤더가 68장 → **221장**. 시험 199 → **258개**(`test_raw_header.py` 59개 신설).

**`BITPIX` 를 맞춘 이유가 따로 있다.** converter 는 `BITPIX != 16` 이면 그 자리에서 `ValueError: Only BITPIX=16 is supported` 로 멈춘다(규격 6.1절). 시뮬이 float32 로 쓰면 산출물이 **변환 경로에 한 번도 들어가 볼 수 없어서** 크기 말고는 아무것도 시험할 수 없다. 픽셀값이 더미라도 저장형을 맞춰 두면 끝까지 돌려 볼 수 있다.

#### 측지값은 추측하지 않았다

레거시 실측본으로 확인된 것은 **SSO 뿐**이다(`LATITUDE='-31:16:24'` `LONGITUD='210:56:08'` `ELEVATIO=1150`). CTIO·SAAO 값은 이 저장소 어디에도 없다. 추측한 좌표는 규격 6.2절이 경계하는 "조용히 틀린 값" 그 자체다 — **겉보기엔 유효한 좌표라 아무도 의심하지 않는다.** 그래서 `[site]` 설정으로 받고 없으면 sentinel 을 싣는다. 미확인 상태는 규격 **OI-11** 로 남겼다.

> `LONGITUD` 는 레거시 관례대로 **서경**(`[deg W]`)이다 — SSO 의 `210:56:08` 이 동경 `149:03:52` 의 보수다. 동경으로 적으면 부호가 뒤집힌 좌표가 아카이브에 박힌다. 다음 사람이 "왜 210도?" 하고 고치지 않도록 적어 둔다.

#### 아직 안 한 것

- **`EXPMEAS`** — 컨트롤러 트리거 타임스탬프 실측이라 실기 몫이다.
- **`DARKTIME` 정밀화** — 엄밀한 정의는 ERASE 완료~readout 끝이고 그러려면 ERASE 완료 시각이 필요하다. 지금은 노출 구간만 재므로 readout 중 전하가 빠진다. 레거시는 이 칸을 아예 채우지 않았고(실측본이 `EXPTIME=30` 인데 `DARKTIME=0`) converter 는 없으면 `0.0` 으로 떨어뜨려 **BIAS 와 구분되지 않게** 만들므로(규격 6.2절), 근사값이라도 싣는 편이 낫다고 판단했다.
- **`AMPMAP`** — 실제 배선을 모르므로 `'DEFAULT'` 로 **선언한다.** 그럴듯한 매핑을 만들어 `EXPLICIT` 로 실으면 실기에서 배선을 넣는 일이 이미 끝난 것처럼 보인다(C-11).
- **MEF extension 헤더 35건** — amp 단위 좌표·WCS 관례는 converter 소관이고 raw 가 실을 값이 아니다(규격 5.12절). 다만 실측본을 읽어 두었고 `DETSEC`/`AMPSEC` 계산에 필요한 mosaic 상수는 5.4절이 이미 싣는다.

---

### 11.15 파일명 날짜부를 사이트별 관측일로 (2026-08-13, D-014)

> ⚠️ **갱신 (2026-08-25, D-017)** — 아래 본문의 `TESTBED`/`KMTT` 는 당시 표기다. 현행은 **`KASI`/`KMTK`** 이고 보정 `0` 과 세 관측소 경계는 그대로다. 이력 기록이라 본문은 고치지 않는다 — 현행 규칙은 raw spec 2.2절과 `rawpair.OBSDATE_SHIFT_MIN` 이 정본이다.

이충욱과 협의한 뒤 운영자가 확정했다. **종전 잠정안(UT 날짜)에 조용한 결함이 있었고, 새 규약이 그것을 구조적으로 없앤다.**

#### 결함이 무엇이었나

취득 SW 는 두 값을 **다른 시점에** 만든다:

```
next_suffix()           파일명 날짜부      EXPSTATUS=INITIALIZING   (sequencer ~203행)
   +0.40s  initialize_ack
   +7.24s  erase_sec
st.exp_start = utcnow()  DATE-OBS          셔터 개방 지시           (~232/336행)
```

UT 날짜의 경계는 UT 자정이고, **그게 관측 시간대 안에 있는 사이트가 둘이다**:

| 사이트 | UT 자정 = 현지 | |
|---|---:|---|
| CTIO (UT−4) | **20시** | 관측 시작 무렵 |
| SAAO (UT+2) | **22시** | 관측 중 |
| SSO (UT+11) | 11시 | 낮 — 안전 |

그래서 그 7.6초 창이 UT 자정을 걸치면 **파일명은 어제 · `DATE-OBS` 는 오늘**이 된다. 두 사이트에서 매 야간 한 번씩 프레임 경계가 그 부근을 지난다.

**오류는 나지 않는다.** 파일명으로 야간을 묶는 도구가 그 프레임 하나를 엉뚱한 날짜에 넣고, C-4 의 pair 일관성 검사도 MK·NT 가 **똑같이** 어긋나므로 잡지 못한다.

> **처음에 나는 이걸 "SAAO 만의 문제" 로 적었다.** 야간이 UT 날짜 둘로 갈리는 것만 봤기 때문이다. 실제 문제인 7.6초 창은 **자정이 관측 시간대 안에 있으면** 생기므로 CTIO 도 해당한다. 규격 OI-10 의 종전 서술도 같은 오류를 담고 있었고 함께 고쳤다.

#### 새 규약

| 사이트 | 경계 UT | 보정 | 현지 |
|---|---:|---:|---:|
| CTIO `KMTC` | 16:30 | `+7:30` | 12:30 |
| SAAO `KMTS` | 10:30 | `−10:30` | 12:30 |
| SSO `KMTA` | 01:30 | `−1:30` | 12:30 |
| TESTBED `KMTT` | — | `0` | — |

근거는 **동지 때 관측 종료와 관측 시작 사이의 중간 시각**. **세 경계가 모두 현지 12:30 인 것이 검산 불변식**이고, 시험이 그걸 직접 지킨다 -- 숫자를 고칠 일이 생겼을 때 손으로 확인할 근거가 있어야 한다.

**경계가 현지 12:30 이라 관측 중에는 지나가지 않는다.** 그래서 걸침 자체가 사라진다.

#### 구현에서 신경 쓴 것 둘

**(가) `if` 로 경계를 나열하지 않았다.** 보정을 더한 뒤 날짜만 취하는 한 줄이다:

```python
return (ut + timedelta(minutes=shift)).strftime('%Y%m%d')
```

경계를 `if` 로 쓰면 `<`/`<=` 를 잘못 잡는 off-by-one 이 생기는데, 그건 **1년에 몇 번만 드러나는** 부류다. 보정 방식은 경계에서 정확히 `00:00` 이 되므로 그 실수가 성립하지 않는다.

**(나) 사이트 코드를 상태에 뒀다** (`IcsState.site_code`). `next_suffix()` 와 `peek_suffix()` 가 **같은 규칙**을 써야 하는데 호출측이 매번 넘기게 하면 한쪽을 빠뜨린다 -- 그러면 `EXPNUM` 응답과 실제 파일명의 날짜가 갈리고, 그것도 야간 경계에서만 드러난다.

#### `UT` 카드 폐지 · `DATE-OBS` 밀리초

`DATE-OBS` 가 날짜·시각을 밀리초까지 담게 되니 `UT` 는 완전한 중복이 됐다. 레거시가 둘 다 실은 것은 `UT` 에 `TSHOPEN`(백분초)을 붙여 정밀도를 보태려던 것이었다.

**폐지가 안전한 근거를 먼저 확인했다:**

- MEF 의 `UT` 는 raw 의 `UT` 가 아니라 **`DATE-OBS` 날짜부 + raw `TSHOPEN`** 으로 조립된다 (`v2_1.py:440,583`). 둘 다 그대로 싣고 있다.
- OBSAgent 는 `DATE-OBS` 를 파싱하지 않는다 -- `OBSAgent.latest/KMTObs/commands.c` 전량에 주석 한 줄(`:187`)뿐이다. 그래서 TCS 중계 본문의 형식을 밀리초로 바꿔도 안전하다.

#### `<SITE>` 정규화

`KMTC`/`KMTS`/`KMTA` 밖은 모두 `KMTT` 로 떨어뜨린다. TC 가 보내는 `TELID` 에 사이트가 아닌 `KMTN`(pctcs 기본값, `pctcs.h:115`)이 올 수 있어서 필요하다.

**다만 떨어뜨리는 것이 곧 안전은 아니다** -- 실제 관측 자료가 `KMTT` 이름으로 저장되면 사이트 정체를 잃는다. 그래서 정규화가 실제로 일어나면 `app.py` 가 경고를 남긴다.

#### 남는 잔여 위험

**현지 12:30 무렵의 주간 교정 프레임.** bias/dome flat 을 그 시각에 찍으면 프레임 개시와 셔터 개방 사이 7.6초가 경계를 걸칠 수 있다. 교정 프레임에 한정되고 오류로 이어지지 않으므로 지금은 다루지 않고 기록만 해 둔다 (규격 OI-12 의 해소 항목).

#### 곁가지로 잡은 내 버그

`config.py` 에 `_int_or()` 를 넣을 때 `log.warning()` 을 썼는데 **그 파일에 `logging` import 도 `log` 도 없었다.** `elevatio` 에 숫자 아닌 값이 들어가면 sentinel 로 떨어지는 대신 `NameError` 로 기동 중에 죽는다 -- OI-11 을 닫으려고 `[site]` 를 손으로 편집하는 바로 그 순간에 터지는 자리였다. 미결 항목 전수 훑기가 찾아냈다.

---

### 11.16 사이트를 호스트 IP 로 판정한다 (2026-08-13, D-015)

> ⚠️ **이 절의 결정(D-015)은 폐지됐다 (2026-08-24, 11.27).** 사이트는 이제 `[node] observatory` 한 줄이 정하고 `siteid.py` 는 지웠다 — **IP 판정을 되살리지 말 것.** 아래 본문의 `KMTT`(벤치)도 당시 표기이고 현행 코드는 **`KMTK`(KASI)** 다 (D-017, 11.28). 이력 기록이라 본문은 고치지 않는다 — 코드 정본은 `rawpair.KASI_SITE` 와 `rawpair.site_of_observatory()` 다.
>
> (`main` 은 구판 `ics_sim` 을 들고 있어 이 포인터를 "판정 규칙은 그대로" 라고 적었다. 이 브랜치에서는 아니다 — 머지하면서 바로잡았다.)

운영자 질문에서 시작했다 — *"ics_sim 에서 자체적으로 어떤 사이트인지 판단할 수 있는 방안이 있을까? 예를 들면 TCS 의 정보를 받아서."*

#### 처음 답은 "TC 로는 안 된다" 였고, 그게 맞았다

TC 의 `AUXSTATUS TELID=` 는 사이트 코드를 그대로 보낸다(`commands.c:2092` 주석: *"TELID : Telescope Identifier - KMTN/KMTC/KMTS/KMTA"*). 그런데 출처를 따라가면:

```c
commands.c:1999   sprintf(reply, "AUXSTATUS … TELID=%s …", aux.FitsTelID, …)
loadconfig.c:512  else if (strcasecmp(keyword, "FITS_TELID")==0)   // pctcs.ini 설정
pctcs.h:115       #define DEFAULT_FITS_TELID "KMTN"                // 사이트가 아닌 기본값
loadconfig.c:177  // "Temporary, … this info will be get from AUX"  // 원래 의도
```

**하드웨어가 아니라 `pctcs.ini` 의 또 다른 수동 설정이다.** 레거시 자신도 "나중엔 AUX 에서 받아올 것" 이라 적어 뒀는데 아직 안 됐다. 즉 같은 사람이 같은 실수를 할 수 있으니 정본이 못 된다. 상류 개선은 ACT-008 로 남겼다.

#### 진짜 독립 신호는 호스트 IP 였다

```
ics_legacy/icg_legacy_report.md:47
192.168.14.x=CTIO(KMTC) · 192.168.13.x=SAAO(KMTS) · 192.168.15.x=SSO(KMTA)
```

**사이트마다 /24 대역이 따로이고, 자기 인터페이스 주소는 우리가 배포하는 어떤 ini 에도 없다.** 설정 묶음을 통째로 복사해도 IP 는 따라오지 않는다 — TC 의 `TELID` 가 못 가진 성질이 이것이다.

대역 매핑은 네 갈래로 확인했다: 각 사이트 자기 `isis.ini` 의 `Instrument` 키워드 · `pctcs.kmtn{c,s,a}.ini` 의 `ISISHost`+`FITS_TelID` · OBSAgent `test.debug.ini:35-37` 범례 · 위 보고서.

**다만 신규 CEU 망이 이 대역을 재사용한다는 것은 구두 확인뿐이고 저장소에 CEU 망 문서가 없다.** 코드 주석에 *inferred* 로 명시하고 ACT-009 로 등재했다 — 대역이 바뀌면 실사이트가 벤치로 판정돼 **실자료가 `KMTT` 이름으로** 저장된다.

#### 레거시가 같은 일을 했고, 그 실패까지 우리가 기록해 뒀다

```c
// ics_legacy_report.md:763
if( strcasecmp(client.isisHost,"192.168.15.109") ) {  // SSO 가 아니면
```

그리고 `:784` 가 이미 비판해 뒀다 — **호스트 IP 를 통째로 박아서** SSO 의 XIS 주소가 바뀌면 갑자기 매 노출 경고가 떴다. 그래서 **`/24` 대역만** 보고 마지막 옥텟은 안 본다. 신규는 머신 7대가 2대로 통합돼(9.1) 레거시의 역할-옥텟 지도가 **아예 무효**이기도 하다.

**인터페이스가 보고하는 netmask 도 쓰지 않는다** — 13/14/15 가 인접해서 누군가 `/22` 로 잡으면 세 사이트가 한 망으로 합쳐진다. literal `/24` 로만 비교한다.

#### 판정이 설정을 이긴다

벤치 요구사항이 이걸 강제했다 — 벤치는 사이트 이름을 `kmtnet-sso`/`kmtnet-ctio`/`kmtnet-kasi`/`kmtnet-helab` 무엇으로 두더라도 **파일명이 `KMTT.…`** 여야 한다(운영자 확정). 설정이 이기면 성립하지 않는다.

`[node] site_from_ip = false` 로 끌 수 있고 **시험이 그 경로를 쓴다** — 켜 두면 판정이 시험을 돌리는 머신 IP 에 좌우돼 기대 파일명이 흔들린다.

부수로 설정 구조를 고쳤다. 실효 사이트가 **기동 시점에** 정해지므로 설정 읽기 단계에서 `[site.<이름>]` 하나를 고를 수 없다 → `site_table` 에 전부 읽어 두고 `site_for(code)` 로 꺼낸다.

#### 오탐을 막는 것이 설계의 절반이었다

운영자가 먼저 지적한 것이기도 하다 — **오탐이 잦은 검사는 사람이 무시하는 것을 학습시켜서 검사가 없는 것보다 나쁘다.** 그래서:

| 상황 | 처리 |
|---|---|
| `TELID` 가 계속 다름 | **서로 다른 값마다 한 번씩** 경고 — "바뀔 때마다" 가 아니다. `KMTS`→`KMTC`→`KMTS` 로 오가도 두 번째 `KMTS` 는 조용하다. AUXSTATUS 는 노출마다 오므로 매번이면 하룻밤 1000줄 |
| `TELID` 없음 · TC 무응답 | **조용.** 정보가 없는 것과 틀린 것은 다르다 |
| canned 텔레메트리 | **교차검증 입력으로 인정하지 않는다.** `_apply_timeout()` 이 `vals['TELID'] = cfg.node.telid` 로 **우리 설정을 복사**하므로(`telemetry.py:203`), 그걸 C 로 쓰면 한 출처를 두 번 읽고 "두 출처가 합의했다" 고 보고하는 꼴이 된다 — **거짓 일치가 불일치보다 위험하다** |
| 오프라인 노트북 · 벤치 | 조용 |
| `TELID=KMTN` | 사이트 불일치가 아니라 **"pctcs 미설정"** 이라고 말한다. 다르게 말하면 엉뚱한 곳을 보게 된다 |

시험 26개 중 절반이 **"경고가 안 뜬다"** 를 지킨다.

#### 근거 조사가 내 시험 하나를 무효로 만들었다

`test_canned_telemetry_does_not_carry_a_telid` 는 `CANNED_AUX_VALUES` 상수에 `TELID` 가 없는지만 봤다. **통과하지만 아무것도 증명하지 못했다** — 값이 상수가 아니라 `_apply_timeout()` 에서 동적으로 주입되기 때문이다. 지켜야 할 속성은 "canned 경로가 `check_telid()` 를 건드리지 않는다" 이고, 그걸 직접 검증하도록 바꿨다.

#### 하나 더 막은 구멍

**판정이 `KMTT` 인데 백엔드가 실물 `archon` 인 경우.** 보통 `KMTT` 는 정말 벤치이고 시뮬 프레임이라 문제가 없다. 그런데 실물이면 **실화소가 `KMTT.…` 로 아카이브에 들어간다.** `config.validate()` 는 `testbed`+`KMTT` 를 정합으로 보고 통과시키고(내부적으로 일관되므로 맞다), `_resolve_site()` 의 경고는 판정과 ini 가 **다를 때만** 뜬다 — 둘이 같으면서 둘 다 벤치인 경우가 남는다. 그 조합만 따로 경고한다.

#### 기동 배너

가장 값싼 방어였다. 오배포가 **자료 한 장 찍기 전에** 눈에 띈다:

```
 사이트         KMTC   (OBSERVAT=CTIO)
 판정 근거      192.168.14.109 in 192.168.14.0/24
 TELESCOP       KMTNet 1.6m #1
 위치           lat -30:10:01.84   lon +70:48:14.39 (서경)   elev 2140 m
 관측일 경계    UT 16:30   -- 파일명 <YYYYMMDD> 가 이 경계로 갈린다
 파일명 예시    KMTC.20260813.001234.MK.fits
 backend        archon   ->  DATASRC=ARCHON
```

**파일명 예시를 넣은 이유**: 운영자가 실제로 확인해야 하는 것은 "이 이름으로 아카이브에 들어가도 되나" 이고, 설정값 나열보다 완성된 이름 한 줄이 오배포를 빨리 드러낸다. **`DATASRC` 를 넣은 이유**: 시뮬 산출물이 실제 아카이브로 흘러드는 것을 막는 유일한 카드다.

절차는 `../project_management/operations/ICS_DEPLOYMENT_CHECKLIST.md` 로 신설했다.

#### 곁가지로 정정한 것

`README.md:63` 의 `--xis-host 192.168.14.101` 은 **저장소 어디에도 없는 주소**였다(우리 README 에만 있었다). 실물 XIS 는 `192.168.14.109` 다(`pctcs.kmtnc.ini:34`, OBSAgent `test.debug.ini:35`). 그 예시를 따라 하면 아무 데도 붙지 않는다.

#### 미확인

- 신규 CEU 망 대역 문서 (ACT-009).
- `Inst. Ctrl.` PC 의 실제 주소/옥텟 — 판정에 쓰지 않으므로 막힘은 아니다.
- 리눅스에서 경로 없는 대역 탐침의 `errno`(윈도우는 확인). `except OSError` 로 덮이므로 최악이 "정보 없음" 이다 — 벤치에서 한 번 확인하면 좋다.

### 11.17 raw ↔ MEF 키워드 전수 대응표 (2026-08-13, ACT-011)

11.14 에서 레거시 방향(레거시 → 신규)은 판정했다. 남은 방향이 **신규 raw → MEF** 다. `rawhdr.py` 가 만드는 카드 이름을 취득 SW 쪽에서 정해 두었을 뿐, converter 와 맞대어 본 적이 없었다. 그래서 양쪽 전량을 한 표에 놓고 대조했다 (289행).

**대조 결과의 정본은 판정 원장 [`../raw_fits_spec/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.14.md`](../raw_fits_spec/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.14.md) 다** (2026-08-23 정리). 대응 관계는 각 장의 `Use in MEF` 열로, 판정 준거는 그 문서 **0장**으로, MEF/converter 쪽 미결 4건은 [`../raw_fits_spec/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md`](../raw_fits_spec/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md) §6 으로 들어갔다. 별도 검토 문서로 두었던 대응표는 흡수 완료로 폐기했다(운영자 재가).

> ⚠️ **`ics_sim` 의 현재 헤더 출력은 raw 쪽 사실의 근거가 아니다 — 근거가 순환한다.** 판정 원장 0장이 이것을 순위표에서 명시적으로 제외한다. raw 쪽 기준선은 **레거시 raw 실측 헤더**(`__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt`, keyword **123개**)이고, `rawhdr.py`·`rawcards.py`·`telemetry.py` 는 그 기준선과 규격을 따라가는 **구현**이다.
>
> **`ics_archon` 합본 때 특히 걸린다.** 구현이 이미 돌아가고 있으므로 "코드가 이렇게 하니 이게 맞겠지" 로 규격을 되짚는 길이 열려 있다. 그 방향은 순환이다 — 판단은 판정 원장과 규격에서 내려온다

**코드 주석에서 원장의 판 번호를 고정하지 않는다 (2026-08-23 정리).** 원장은 사흘 만에 v1.7 → v1.14 로 올랐다. 주석에 판을 박으면 그 즉시 낡고, 심하면 `archive/` 로 내려간 판을 가리킨다 — 실제로 `config.py`·`ics_sim.ini`·`test_raw_header.py` 다섯 곳이 v1.12/v1.13 을 가리키고 있었다. **절 번호만 쓴다**(예 "Header_and_Refs 3.3절") — 절 구성은 안정적이고, 결정의 확정 근거는 어차피 **D-번호**다. 판 번호를 적는 것은 "언제 확정됐나" 를 기록할 때뿐이다(`rawpair.py` 의 "확정 2026-08-21, Header_and_Refs v1.7" 같은 이력 인용, `rawhdr.py` 의 "원장 v1.9").

같은 정리에서 **`hardware/archon.py` 스텁이 없는 파일을 가리키고 있던 것**도 고쳤다 — `ics_archon/archon_kmtnet_labtest_v1.0.bigbuf.py` 는 루트에 없다(현행은 `v1.1.bigbuf.py`, v1.0 원본은 `__ref_archon_control/`). **v0.0 합본에서 제일 먼저 읽을 것이 그 스텁의 주석**이라 낡은 경로 하나가 비싸다. 함께 미검증 3자리 경고와 `README_labtest.md` 포인터도 그 자리에 넣었다.

#### 문서가 아니라 코드에서 뽑았다

MEF 쪽 키워드는 `mef_fits_spec/` 문서가 아니라 **converter 소스에서 기계 추출**했다. 이유는 하나다 — **실제로 도는 것이 코드**이고, 문서와 코드가 어긋나면 자료에 남는 것은 코드 쪽이다. 문서 정의는 차이를 표시하는 용도로만 썼다.

추출은 `card(...)` 호출을 **괄호 균형으로 파싱**해 줄번호로 HDU 에 귀속시킨다. 처음에는 함수별로 소스를 잘라 파싱했는데, 그 방식이 `extra_cards=[…]` 안의 5장(`GEOMVER` `TELSTAT` `NAMP` `NXTALK` `EXTTYPE`)을 통째로 놓쳤다. **함수 경계로 자르면 인자 안에 들어앉은 카드가 사라진다.**

| | 개수 |
| --- | ---: |
| MEF 키워드 (코드가 만드는 것) | 236 |
| raw 키워드 (`ics_sim` 이 쓰는 것) | 188 |
| 양쪽에 있는 것 | 135 |
| MEF 에만 | 101 |
| raw 에만 | 53 |

#### 대조 결과 — 이름은 안 어긋난다, 값이 어긋난다

**코드가 만드는 236개 전부가 문서에 정의돼 있었다.** converter 가 문서 밖 이름을 발명한 사례도, 문서에만 있고 코드가 안 만드는 이름도 없다. 예상과 달랐던 부분이고, 덕분에 남은 문제가 좁혀졌다 — 차이는 **값과 동작**에 있다.

문서는 실측을 요구하는데 코드는 고정값을 넣는 자리가 여럿이다. `telemetry_rows()` 와 `volt_rows()` 는 **헤더 인자를 아예 받지 않아서**(C-18) 컨트롤러 실측이 들어갈 통로가 없고, amp 의 `MODULE`/`CHANNEL` 은 소스가 스스로 *"placeholder"* 라 적어 둔 추정식이다(C-11). 이것이 틀리면 `XTALKGROUP` 이 틀리고 **crosstalk 계수 측정 자체가 무의미해진다.** `convert()` 가 `mk_hdr` 하나만 넘기는 것(C-17)도 같은 자리에서 드러났다 — 11.14 에서 `CTRL<n>ID` 로 잡은 문제와 뿌리가 같다.

전부 converter 쪽 작업이라 취득 SW 가 손댈 수 없다. 그래서 규격이 아니라 **검토 문서**로 남겼다.

#### 규격 대비 구현 구멍 16개

converter 가 raw 에서 읽으려 하는데 `ics_sim` 이 그 카드를 만들지 않는 것이 16개다 — 돔 10개(`DSUP`…`DAZERR`), FSA 환경 4개(`FSATEMP`…`FSAALRM`), 영상 점검 2개(`CHKIMG`·`CHKIMG_C`). **전부 우리 규격 5.10절이 "반드시 있어야 한다" 로 적어 둔 것들이다.**

왜 이렇게 됐는지는 추적됐다. 이 필드들은 AUX 중계값이고 `CANNED_AUX` 는 **CTIO 실측 기반**인데, 레거시 CTIO AUX 는 돔 필드를 보내지 않았고(SSO 만 보냈다) FSA·영상점검 필드는 레거시 raw 실측본에 아예 없다. 그래서 sentinel 목록에도 안 들어갔다.

고쳐야 하는 이유는 5.0·5.9절이 **"값이 없었다"를 sentinel 로 헤더에 남기라**고 정해 두었기 때문이다. 지금은 카드가 없어서 converter 가 `""` 를 채우고 **MEF 에 빈 문자열이 조용히 들어간다** — `TC 가 안 보냈다` 와 `이 규격을 모르는 취득 SW` 가 구분되지 않는다. 11.14 의 `CTRL<n>ID`, 11.16 의 사이트 오배포와 **같은 부류의 결함**이다: 오류 없이 틀린 값이 남는다.

#### 왜 지금 해야 하나

핵심은 **Archon setup·구성·유닛 텔레메트리 카드의 이름과 구성**이다. `__reference/` 는 MEF 목적지(표 컬럼)를 전부 정의하지만 raw 쪽 카드 이름은 하나도 정의하지 않는다 — raw 쪽을 정하는 것이 `raw_fits_spec/` 이므로 당연한 상태다. 문제는 **목적지는 합의됐는데 출발지 이름은 합의되지 않았다**는 것이다.

미루면 비싸진다. 실기가 이 이름으로 자료를 쌓기 시작한 뒤 converter 쪽에서 다른 이름을 고르면 **그때까지의 아카이브는 영구히 읽히지 않는다.** 파일명·`OBSERVAT` 처럼 되돌릴 수 없는 부류다(11.16).

결정이 필요한 10항목은 문서 5장에 모았다.

---

### 11.18 HK 블록 재구성 -- CCDTEMP 실측 전환 · DEWPRES 문자열 sentinel (2026-08-21)

**무엇을.** 운영자 v1.7_revision.docx 와 확정 초안 v0.3.5(`raw_fits_spec/__review/KMTA.20260818.012345.MK.fits.header.txt`)가 HK(열·듀어) 블록을 재구성했다. `rawhdr.thermal_header()` 를 그에 맞췄다.

- **`CCDTEMP` 는 실측 대표 센서 1개의 값이다** -- 종전 "두 chip 온도의 평균"(11.14, 2026-08-13)을 폐기했다. 온도센서 구성이 바뀐 결과다. 대표는 백엔드 `ccdtemp1`(초안 comment "CCD temperature M")이고, 대표가 죽으면 이웃 값으로 **대체하지 않고** sentinel `-999.0` + 경고다 -- 대표가 아닌 값을 대표라고 적으면 조용히 틀린 값이 된다. `CCDTEMP1`/`CCDTEMP2` 카드는 도입 후보에서 제외 확정.
- **`DEWPRES` 는 문자열 카드** `x.xxe-x` [torr], 측정불가는 전부 `'9.99e-9'` -- 값 없음 · 0(게이지의 `0.00e-0` 포함) · 음수 · 비수치 · 유한하지 않음 · 인정 범위 [1e-8, 1e+3] 밖. 문자열인 이유: astropy 가 실수 카드의 표기를 크기 보고 정하므로 지수 표기를 규격으로 고정하려면 문자열이어야 한다. ⚠️ sentinel 이 정상값과 안 겹치는 성질은 **인정 하한(1e-8) > sentinel(9.99e-9)** 에 걸려 있다 -- 게이지 실측 하한이 이보다 낮으면 sentinel 을 바꿔야 한다(`DEWPRES_MIN` docstring).
- **신설 3장** `DMPTEMP` / `WALLBRD` / `HEBOX` -- `DEWAR_CARDS` 와 sim 백엔드에 추가. `WALLBRD` 는 wallboard 의 모음 탈락 축약(8자 절단형 `WALLBOAR` 를 대체 -- 절단형은 "wall boar" 로 읽히고 확장 여유가 없다).
- 공급 계통이 셋으로 갈렸다 -- ICG RTD(Archon 쪽) / standalone RTD readout unit(AIR·GLYC) / Tapaculo sensor(HEBOX). 시뮬에서는 전부 `sensors()` 한 창구로 온다.

**남은 일 (13장 백로그).** 초안 v0.3.5 의 노출·컨트롤러 블록 재편은 아직 코드에 안 갔다 -- `DARKTIME`/`TSHOPEN`/`TSHSHUT`/`NPHLINES`/`HEMODE`/`READMODE`/`CTR_CFG` 제거, `CTRL1CFG`/`CTRL2CFG`/`TCSTIME` 신설, `DATASRC` 값 체계(`ARCHON_SCIENCE`/`ARCHON_GUIDE`/`SIM`). 카드 comment 지원(`fitsout._apply_header()`)이 선행돼야 초안의 comment 까지 재현된다. 근거 문서: `raw_fits_spec/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.8.md` (확인 요망 9건 포함). **→ 11.19 에서 전량 완료 (2026-08-22).**

### 11.19 raw spec v1.3 전면 정렬 -- 템플릿 주도 헤더 · D-016 충돌 처리 (2026-08-22)

**무엇을.** raw spec v1.3 발행(2026-08-22)에 맞춰 헤더 층을 전면 재편했다. 인수인계 목록(`raw_fits_spec/SMC_CLAUDE.md` "ics_sim 구현 일감" ①~⑤)의 전량이고, 11.18 의 "남은 일"도 여기서 닫혔다. 버전 v0.1.0 → **v0.2.0**.

**핵심 판단 -- 헤더는 템플릿이 조립한다 (신설 `rawcards.py`).** 견본 초안 v1.0 pair 가 "카드 순서·comment·패딩까지 바이트 단위 기준"이 됐으므로(5장 머리말), 카드 집합을 코드 여기저기서 dict 로 겹치는 구판 방식을 버리고 **견본의 기계 사본(템플릿)이 값 풀에서 카드를 꺼내 조립**하게 했다. 세 가지가 한꺼번에 풀린다 -- ① 카드 순서·comment·문자열 패딩이 견본과 **바이트 단위로 같다**(`tests/test_raw_draft.py` 가 견본 값을 역산해 넣으면 견본 136카드가 그대로 재현됨을 대사한다 -- 불일치 0) ② 템플릿에 없는 와이어 키는 카드로 **샐 수 없다**(구판 `SHUTTER` 겹침 사고 부류의 구조적 차단 -- `_store()` 의 런타임 겹침 검사도 함께 은퇴) ③ 견본이 개정되면 템플릿 대사 시험이 어긋난 자리를 가리킨다.

- **카드 수 221 → 값 135 + COMMENT 8.** 폐지: geometry 선언 27장(`RAWNAX*`/`OSCNPATT`/`ROWORDR`/`RDDIRT/B`…), detector 잉여(`DETSIZE`/`NCCD`/`NAMPS`/`HEMODE`…), 컨트롤러 런타임·버전(`CTRLVER`/`TIMVER`/`BIASVER`/`CLKVER`/`BCKTEMP`/`ACFFILE`/`NPHLINES`/`CTRLnFW`…), 전압 색인 계열, `AMPMAP`/`AMOD*`/`ACHN*`, 파생 시각(`MJD-OBS`/`UT`/`TSHOPEN`/`TSHSHUT`/`DARKTIME`), 정체성 잉여(`UNIQNAME`/`NAMECLSH`/`PAIRFILE`/`CTRLTAG`/`CHIP*`/`RAWVER`/`RAWPROD`/`NUMFILES`/`DATE`/`CREATOR`). 신설: `FPAID`/`DETID`(pair 재정의)/`CHMAP_*` 4장/`ORIGNAME`/`CTRLnCFG` 상시/`RDMODE`/`Cn_TEMP·VOLT·CURR` 6장/`TCSTIME`/돔 신설 5장(`DSUP`~`DSTELAZ`)/`DALTERR`·`DAZERR`(ICS 계산)/`FSATEMP`·`FSAHUM`. **geometry 배치의 정본은 카드가 아니라 4.3 포장 규범 조항**이 됐다 -- 선언-하드코딩 갈림의 방어는 `test_geometry_vs_converter.py`(코드-대-코드)가 그대로 맡고, `XOSC_PATTERN='RRRRLLLL'` 은 카드 아닌 내부 상수로 남겼다(OI-15 상충 증거 주의도 함께).
- **D-016 충돌 처리.** `clash/` 격리 + `NAMECLSH` + WARNING 메시지 세 겹을 **선검사 + 번호 증가** 하나로 교체했다 -- `rawpair.resolve_pair_number()`(MK·NT 두 경로 pair 동시 선검사, 099999→000000 되감음, 한 바퀴 초과 시 `NumberSpaceExhausted` = 유일한 저장 실패), `state.sync_expnum()`(확정 번호 동기화 + 평소 영속화 경로), `advance()`/`load_expnum()` 의 번호 공간 순환. 이름 결정은 `_frame` 이 하고 `_store` 는 수령만 한다(통합 문서 Part 2 §3). `emitter.name_clash()` 폐지 -- 통보 대신 WARNING 로그다(2.5절). ⚠️ **알려진 잔여**: 번호가 점프한 프레임의 readout 중 `ExpNum` 응답은 점프 전 값이라 관측자 화면이 한 프레임 동안 낡을 수 있다 -- 충돌 자체가 비정상 상황(재저장·수동 개입)에서만 나므로 감수했고, 다음 프레임에서 자가 교정된다.
- **백엔드 계약 개정 (D-012 후속).** `voltages()`/`amp_map()` 폐지(대응 카드 소멸), **`controller_telemetry()` 신설** -- 두 컨트롤러의 `{'temp','volt','curr'}` 목록(5.9절 "반드시 동일"이라 컨트롤러 인자가 없다). 실기 원천은 Archon STATUS(`BACKPLANE_TEMP`+`MODm/TEMP`, 전원 레일 `_V`/`_I` -- 매뉴얼 p.47-49), 자리 순서는 `VOLT_RAILS`. `controller_info()` 는 `units` 의 `fw` 를 `cfg` 로 바꿨다(버전 문자열의 `CTRLnCFG` 귀속). `sensors()` 에 Tapaculo 2장(`fsatemp`/`fsahum`) 추가.
- **TC 중계 카드 전부 문자열.** 5.7절 "TCS 중계값은 문자열로 싣는다"에 따라 FITS 쪽 수치 sentinel(`-1`/`-999.0`)을 문자열 공통 `'NC'` 로 접었다(메시지 계층 `'0'` 과의 분리는 유지, C-9). `TCSTIME` 은 TCS 응답의 `TIMESYS` 를 **이관**해 만들고 ICS 자신의 `TIMESYS` 카드와 분리했다. `DALTERR`/`DAZERR` 는 돔-망원경 지향차의 ICS 계산(`±.1f` 문자열, 피연산 결측이면 `'NC'`). **판단 2건 (목 확인 대상)**: ① `RADECSYS` 는 TC 가 안 보내면 기본 `'ICRS'` 로 채웠다 -- 규격 값 칸이 `'ICRS'` 고정이고 좌표계 선언은 RA/DEC 가 sentinel 일 때 무해해서다 ② ENS1~7 결측 sentinel 은 `'NC'` 로 뒀다 -- 5.0절의 `'-999.99'` 는 "HK 온도·습도 카드"(5.6절 + FSA 2장) 규약으로 읽었고, ENS 는 AUX 중계 pass-through(5.8절 "중계 그대로")라서다. FSA 2장은 `'-999.99'` + ENS식 소수 1자리(`format_ens`, OI-16 잠정).
- **`fitsout`**: 순서 있는 카드 목록 + COMMENT 구분 카드 + comment 기록(`apply_cards`), `EXTEND` 제거(견본에 없음), **`CHECKSUM`/`DATASUM` 중단**(OI-7 미도입 -- 구판이 astropy 로 넣고 있었다). BZERO/BSCALE comment 는 카드를 미리 만들어 보존.
- **시뮬 이미지의 spec 기하** -- `fits_shape = spec`(ini) 이면 chip 당 9400×9600, 파일 19200×9400(344.3 MiB)을 **4장 배치 그대로** 만든다: strip 8개×TOP/BOT amp 별 bias offset, X overscan 좌우(`RRRRLLLL`), 중앙 Y overscan 168행(84/84, OI-4 가정), active 에만 신호(+150, BIAS 는 0). **converter end-to-end 실검증**: 이 pair 를 `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` 에 넣어 69-HDU L0 MEF 생성 확인 -- `DATE-OBS`/`CTRL1ID`/`CCDTEMP` 실값 pass-through, amp `DATASEC` 평균(신호) vs `BIASSEC` 평균(바이어스)이 값으로 갈라진다. MEF `UNIQNAME` 만 빈 문자열 -- 알려진 C-항목(LEECU 몫, 통합 문서 Part 1 §1)이라 우리 쪽 결함이 아니다.
- **자잘한 정렬**: KMTT 의 `TELESCOP='Sim'`(5.3절 -- 종전 `'NC'`), `INSTRUME` 유도 `'<SITE> 18k CCD'`, `[camera] fpaid`·`[controllers] rdmode` ini 키 신설(ICS INI 카드 전량 ini 편집 가능 -- 운영자 지시), `DATASRC` 값 체계 3분(`datasrc_of`: archon→`ARCHON_SCIENCE`, 미상→`SIM`).
- **테스트 재편 -- 305개 전부 통과.** 신설 `test_raw_draft.py`(견본 대사 3겹: 템플릿 구조 / 바이트 재현 MK·NT / pair 상이 7장), `test_raw_header.py`·`test_raw_pair.py` 전면 개정(필수 목록을 손 목록 대신 템플릿에서 유도, 폐지 카드 부활 감시 RETIRED ~100장, D-016 충돌·되감음·상한·카운터 동기화), `test_geometry_vs_converter.py` 상수 개명 대응. OBSAgent 규약 시험(177개 부류)은 **한 줄도 안 고치고 통과** -- 메시지 계층은 이번 개정의 범위 밖이라는 확인이다.

**시사점.** ① 바이트 정본이 생기면 "규격 문서 → 코드" 번역을 사람이 반복할 이유가 없다 -- 기계 사본(템플릿) 하나를 두고 양쪽(ics_sim `rawcards.py` · ics_archon v1.1 스크립트 내장본)이 공유하는 구조가 markdown 표 대조보다 강하다. ② 견본 자체가 충돌 사례(`FILENAME≠ORIGNAME`)와 comment 오타("Telesope"·"Acutator")까지 담고 있다 -- 오타도 정본의 일부이므로 고치지 않고 재현했다(고치려면 견본 개정이 먼저다).

### 11.20 v1.3 정렬분 적대적 검토 -- 확정 14건 중 12건 수정 (2026-08-22)

**무엇을.** 11.19 를 끝낸 뒤 관점 4개(규격 준수 · 동시성/경계조건 · archon 스크립트 · OBSAgent 규약)로 코드를 다시 훑고, 나온 주장마다 **반박을 시도하는 검증**을 붙였다. 확정 14건 중 12건을 고쳤고(회귀 시험 동반), 2건은 아래 "남긴 것"이다. 시험 305 → **317개**.

**오늘 들어온 결함 (내가 만든 것)**

- ⚠️ **critical -- D-016 선검사가 노출 태스크를 죽였다.** `_frame` 이 저장 직전에 `st.channel(ccds[0]).suffix` 를 **다시 읽어** 번호를 파싱했는데, 그 필드는 `INITIALIZE <suffix>` 로 **외부 노드가 임의 문자열을 넣을 수 있는 자리**다(레거시 관례상 형식 검증이 없고, 레거시 IC 는 점 없는 4자리를 실었다). 그 값이 프레임 중간에 들어오면 `int(num_str)` 이 `ValueError` 를 내고, fire-and-forget 태스크라 아무도 회수하지 않아 **`EXPSTATUS=IDLE` 0회 · `Wrote` 0회 · `advance()` 미실행**이 된다 -- 규약 3장 6항 중 3개가 한 번에 깨지고 OBSAgent 는 창 초과로 `opause` 에 빠진다. 재현·측정으로 확인됐다. **고침**: 프레임 개시 때 확정한 **지역 변수**를 그대로 쓴다(재읽기 제거 -- 프레임의 이름은 프레임이 정한다) + 번호 파싱 앞에 `isdigit()` 가드. 시험 `test_external_initialize_cannot_break_the_frame`(3 케이스).
- **pair 동일성이 구조적으로 보장되지 않았다** (5.9절). `_store` 가 `sensors`/`controller_telemetry`/`controller_info` 를 **컨트롤러별로 따로** 질의했고 두 호출은 `write_delay + skew` 만큼(기본 1.0초) 벌어진다 -- 시뮬은 고정값을 돌려주므로 **시험이 통과하는 채로 실기에서만 갈리는** 부류였다. 시간 가변 백엔드로 바꿔 보면 `CCDTEMP`·`Cn_VOLT`·`Cn_CURR` 가 실제로 갈렸다. **고침**: 노출당 한 번 `_frame` 이 스냅샷을 떠 두 `_store` 에 같은 값으로 넘긴다(이미 `telem` 이 쓰던 패턴 -- 백엔드 사실 3개만 그 스냅샷에서 빠져 있었다). 질의 **횟수**를 세는 시험으로 못박았다.
- **노출 메타데이터도 같은 경합이었다.** `IMAGETYP`/`OBJECT`/`EXPTIME`/`PROJID`/`OBSERVER`/`LEDFLASH` 를 저장 시점 live state 에서 읽어, `IDLE` 이후 다음 관측의 `object`/`exp` 가 들어오면 **프레임 N 헤더에 프레임 N+1 의 값**이 실렸다(5.4절이 sentinel 조차 금지한 카드들의 조용한 오염). 두 writer 의 skew 차 때문에 MK·NT 가 서로 다른 `IMAGETYP` 를 갖는 것도 재현됐다. 같은 스냅샷으로 고쳤다.
- **`fits_shape = spec` 이 이벤트 루프를 막았다.** 344 MiB 프레임의 생성(numpy)과 쓰기(astropy)가 둘 다 블로킹이라 그 몇 초 동안 UDP 수신·다른 CCD 발신이 멈춘다 -- 3장의 시간 창이 허용하지 않는다. `asyncio.to_thread` 로 내보냈다. 실기 백엔드의 FETCH 도 같은 성질이라 이 구조가 그쪽 선례가 된다.
- **번호 점프 후 `ChannelState.suffix` 가 낡았다** -- `FILENAME` 질의가 충돌 상대(옛 파일)의 이름을 답했다. `Wrote` 논리 이름은 확정 suffix 를 인자로 받아 맞았으므로 **둘이 갈렸다**. 확정 번호로 채널 suffix 도 맞춘다.
- **`EXPNUM <n>` 이 번호 공간을 강제하지 않았다** -- 카운터로 들어오는 유일한 외부 경로인데 범위 검사가 없어 7자리 suffix·부호 있는 이름이 와이어로 나갈 수 있었다. `0 <= n < NUM_SPACE` 거부. 세 곳에 흩어져 있던 `% 100000` 매직넘버도 `rawpair.NUM_SPACE` 하나로 묶고 `next_suffix()` 에도 같은 순환을 적용했다(`peek_suffix()` 와 갈라져 있었다).

**구판부터 있던 결함 (오늘 함께 고침)**

- **파일명·헤더의 사이트가 실효 판정이 아니라 ini 원값이었다** (D-015 · 2.2절 위반). `_resolve_site()` 는 IP 판정을 `state.site_code` 에만 넣고 `cfg.node.telid` 는 그대로 두는데, `_store` 는 `cfg.node.telid` 를 읽었다 -- 판정과 ini 가 다르면 **관측일 경계는 판정값, 파일명 `<SITE>`·`OBSERVAT` 는 ini 값**이 되어 한 파일 안에서 사이트가 갈렸고, 기동 배너가 찍는 파일명 예시와도 어긋났다(배너가 거짓말을 했다). `st.site_code` 로 통일.
- **STOP 이 프레임 사이에서 안 지워졌다.** `GO n` 도중 STOP 이 오면 이벤트가 세워진 채 다음 프레임으로 넘어가 **남은 프레임 전부가 ~0초 노출**이 됐는데, 헤더 `EXPTIME` 은 요청값을 그대로 실으므로 정상으로 보이는 오염 프레임이 생산됐다. 프레임 개시 때 `clear()`.
- **ABORT 가 이전 프레임의 미완료 저장을 파괴했다.** `_writers` 전체를 취소해서, 이미 `Acquisition Complete.` 까지 발신한 앞 프레임의 파일이 기록 전에 사라졌다(그 프레임의 `Wrote` 는 영영 안 나가고 번호는 이미 소비돼 디스크에 구멍만 남는다). `_frame_writers` 로 **진행 중 프레임이 띄운 것만** 취소한다. 레거시는 CB 가 별도 프로세스라 앞 프레임을 끝까지 썼다.

**archon 스크립트 v1.1 (6건 전량 수정)**

- `fits_card` 가 폭 초과 문자열을 클램프하지 않아 80바이트에서 통째로 절단됐다 -- **닫는 인용부호와 comment 가 사라져** astropy·converter 가 파싱조차 못 한다(온도 13슬롯이면 실제로 그렇게 된다). 잘라내고 경고하는 쪽으로. `build_header` 의 `% 2880 == 0` 단언은 이 결함을 **원리상 못 잡는다** -- 모든 카드가 이미 80자로 강제되므로 총길이는 항상 정렬돼 있다.
- 텔레메트리 나열이 결측 항목을 **건너뛰어** "자리 = 항목"(5.6절)을 조용히 깼다 -- MOD3 결측이면 MOD4 값이 MOD3 자리에 앉고, volt/curr 의 항목 수가 서로 달라질 수 있었다. 자리마다 sentinel. 슬롯 목록을 `TEMP_MODS` 상수로 뽑았다(BACKPLANE + AD 모듈 4장 -- 매뉴얼 p.20 과 v1.0 의 `MOD5~8/PREAMPGAIN` 블록이 근거. **모듈 순서 정본은 규격 수록 예정**이라 그때 교체).
- 프레임 fetch 후·쓰기 전 구간에 미처리 예외 2종 -- STATUS 의 비수치 토큰 하나(`float()` 이 try 밖)와 `UNIT_CTRLTAG` 오타(`CHMAP[...]` KeyError)로 **이미 읽어낸 노출이 통째로 버려졌다**. 전자는 sentinel + 경고로, 후자는 기동 시점 1회 검증(`_check_identity_setup`)으로.
- `CTRL1*`/`C1_*` 에 자기 유닛 값을 넣어 5.9절을 위반했다 -- `C1_*` 는 "내 컨트롤러" 가 아니라 **컨트롤러 1 고정**이다. `UNIT_CTRLTAG` 로 색인 자리를 정한다(NT 유닛이면 `CTRL2*`/`C2_*`).
- `SITE_CODE` 를 주석 지시대로 관측소 코드로 바꾸면 `OBSERVAT` 가 `TESTBED` 로 남아 **규격의 유일한 하드 실패**가 났다(리터럴 하드코딩). `SITE_INFO` 표에서 `OBSERVAT`/`ORIGIN`/`TELESCOP` 를 유도한다.
- `OBJECT` 가 `filenum // 100` 역산을 써서 iFlat(116 프레임)의 `nframe >= 100` 구간에서 `DS<번호+1>` 이 됐다. 죽은 `prefix` 인자를 `datasetid` 로 교체해 호출측이 넘긴다.

수정 후 견본 바이트 재현(144카드, 불일치 0)과 converter end-to-end(69-HDU L0 MEF)는 그대로다.

**남긴 것 (목 판단 필요)**

1. **`IMAGETYP='STANDARD'`** -- `state.IMAGE_TYPES` 에 있고 레거시 명령 테이블에서 온 값인데 raw spec 5.4절 어휘(`BIAS`/`DARK`/`OBJECT`/`FLAT`/`SKY`/`DOMEFLAT`)에는 없다. **규격의 목록이 불완전한 것인지, 레거시 어휘를 버리는 것인지**가 판단 사항이라 코드를 손대지 않았다 -- 관측자가 쓰는 명령을 조용히 거부하는 쪽이 더 위험하다.
2. **견본 헤더의 `FILENAME`/`ORIGNAME` 날짜(`20260821`)가 견본 파일명·규격 2.3절 예시(`20260818`)와 어긋난다.** 규격으로 판정하면 **카드가 맞다** -- 견본 `DATE-OBS='2026-08-21T12:34:56.789'` 에 SSO 보정 −1:30 을 적용하면 관측일이 `20260821` 이다. 즉 견본 **파일 이름과 규격 2.3절 예시**가 틀렸다. 정본 견본이자 "아카이브 유일 키" 규칙의 유일한 바이트 기준물이 스스로 그 규칙을 깨고 있어 LEECU 가 오독할 여지가 있다. `test_raw_draft.py` 는 견본 값을 되먹여 대조하므로 **이 불일치를 구조적으로 못 잡는다**. 정본 문서 수정은 운영자 몫이라 손대지 않았다 (raw_fits_spec/SMC_CLAUDE.md 에 확인 항목으로 등재).

**시사점.** ① "시뮬이 고정값을 돌려줘서 시험이 통과하는" 결함이 두 건 나왔다(pair 동일성·메타데이터 경합) -- 값이 아니라 **질의 횟수·바인딩 시점**을 시험해야 잡힌다. ② 오늘 넣은 critical 은 "새 파싱을 추가할 때 그 입력이 어디서 오는지" 를 안 따라간 것이다. `cmd_expnum` 에는 범위 검사를 새로 넣으면서 **같은 카운터로 들어오는 다른 외부 경로(`cmd_initialize`)는 그대로 둔 채** 그 값을 하드 파싱했다 -- 입력 경로를 전수로 세는 습관이 필요하다.

### 11.21 `IMAGETYP` 어휘 정리 + raw spec v1.4 정합 (2026-08-22)

**`STANDARD` 폐지 (운영자 확정 -- "이제 안 쓴다").** 11.20 에서 목 판단으로 남겨 둔 2건 중 하나가 닫혔다. 레거시 명령 테이블에는 있고 핸들러도 있었지만 raw spec 5.4절 `IMAGETYP` 어휘(`BIAS`/`DARK`/`OBJECT`/`FLAT`/`SKY`/`DOMEFLAT`)에 없어, 그대로 두면 규격 밖 값이 헤더에 실렸다.

- 걷어낸 곳: `state.IMAGE_TYPES` · `commands.cmd_standard` · `emitter.KNOWN_COMMANDS` · `console` 도움말 · docstring 2곳. 이제 `standard` 는 `ROI`/`DISPL`/`MOVIE` 와 같이 `Didn't understand` 로 거부된다.
- **레거시와 갈라지는 지점이다** -- 그 셋과 달리 `STANDARD` 는 레거시에 있던 명령이다. 그래서 실사용 영향을 먼저 확인했다: `.osc` 관측 스크립트 **22개 전량**과 레거시 ISIS 로그 샘플에 용례가 **0건**이다. (검색 중 한 번 오독했다 -- `find` 출력을 grep 결과로 읽어 "실사용에 있다"고 잘못 봤다가 다시 세었다.)
- **어휘 일치를 시험으로 못박았다** (`test_command_vocabulary_equals_the_spec_vocabulary`): 명령 목록과 규격 5.4절 어휘의 **집합이 같은지** 본다. 한쪽만 늘어나면 걸린다 -- 운영자 지시가 "값 추가가 필요하면 그때 ics 코드와 raw spec 을 함께 고려한다" 였으므로, 그 "함께" 를 시험이 강제한다.

**raw spec v1.4 정합 (다른 세션 발행분).** 같은 날 규격이 v1.4 로 올랐다 -- 1~4장 검토 반영이고 5장 이후는 검토 전이다. 구현 영향은 없었지만 참조가 낡았으므로 정리했다:

- 규격 파일명 참조 6곳 `_v1.3.md` → `_v1.4.md`.
- **2.5절이 삭제됐다** (`Wrote` 통보 규약이 취득 SW 소관이라 규격에서 빠지고 정본이 DevNote 3.2 로 왔다). 그 절을 인용한 주석 9곳을 DevNote 3.2 로 돌렸다. ⚠️ `impv2.py`/`transport.py`/`test_impv2.py` 의 "스펙 2.5절" 은 **IMPv2 프로토콜 스펙**이라 무관 -- 건드리지 않았다. 규격에 남은 한 줄("`LASTFILE` 은 실재 경로가 아니다")은 2.3절 5항으로 흡수돼 그쪽을 가리킨다.
- **OI-15 종결** (4.1 `RRRRLLLL` 이 실제 획득 자료 육안 확인으로 확정). `XOSC_PATTERN` 과 `test_geometry_vs_converter.py` 의 "상충 증거 있음" 경고를 걷었다 -- 이제 그 시험은 *미확정 전제의 일관성*이 아니라 **확정된 규격과 converter 하드코딩의 일치**를 지킨다.
- 견본이 `KMTA.20260818.…` → **`KMTA.20260821.…`** 로 개명됐다 (파일명 == `FILENAME` 카드로 맞추는 정본 수정 -- 11.20 에서 등재한 확인 항목이 그렇게 닫혔다).

**⚠️ 그 개명이 바이트 대사 6개를 조용히 죽였다.** `test_raw_draft.py` 가 견본 경로를 **하드코딩**했고 없으면 `pytest.skip` 이었다 -- 개명 후 전체 스위트가 `312 passed, 6 skipped` 로 **초록**이었다. 견본과 구현이 갈라지는 것을 잡는 이 저장소의 유일한 수단이 꺼졌는데 시험 결과가 그걸 알려 주지 않았다. 고친 방식:

- 이름 대신 **패턴**으로 찾는다 (`_find_draft`, `KMT?.*.{MK,NT}.fits.header.v1.0.txt`) -- 다음 개명에는 안 깨진다.
- 못 찾으면 **skip 이 아니라 실패**다. 견본은 정본이므로 없는 것 자체가 결함이다.
- 여럿 찾으면 실패 -- 어느 것이 정본인지 알 수 없는 상태를 통과시키지 않는다.

같은 계열을 하나 더 정리했다 (2026-08-22, 확인 중 발견) -- `test_chmap_machine_copy_agrees_when_present` 도 기계 사본(채널맵 v1.0, raw spec 4.5절이 "기계 가독 정본"으로 규정)이 없으면 `skip` 이었다. 이름의 "있으면"(`when_present`) 이 그 헐거움을 드러내고 있었다. **정본이 사라져도 초록으로 지나가는 것은 같은 결함**이므로 실패로 바꾸고 이름도 `test_chmap_matches_the_machine_copy` 로 고쳤다. 이제 `test_raw_draft.py` 에 skip 경로가 **0개**다.

**시사점 (11.20 의 것과 같은 계열).** 11.20 이 "시뮬 고정값 때문에 통과하는 시험" 을 지적했는데, 이번 것은 한 단계 더 나쁘다 -- **시험이 아예 실행되지 않는데 초록이었다.** `skip` 은 "확인했다" 가 아니라 "확인하지 않았다" 인데 결과 화면에서 둘이 구별되지 않는다. 외부 자원(정본 문서·견본)에 의존하는 시험은 **없으면 실패**로 두고, 경로는 패턴으로 잡는 편이 맞다.

### 11.22 ics_archon 실험실 스크립트 투입 전 감사 -- 내가 넣은 회귀 4건 (2026-08-23)

`archon_kmtnet_labtest_v1.1.bigbuf.py` 를 실기에 걸기 직전, **"v1.0 에서는 되던 것이 v1.1 에서 깨졌나"** 만 물어보는 감사를 돌렸다(에이전트 21, 반박 검증 포함). blocker 는 0 이었지만 **확정 회귀 4건이 나왔고 전부 내가 v1.1 에서 넣은 자리**다. 넷의 공통점이 문제였다 -- **취득 중에는 아무 경고도 안 뜬다.** `v1.1.1` 에서 고쳤다.

**(1) `STATUS` 시한 초과가 프로토콜을 어긋냈다.** `archoncmd` 는 응답을 검증한 **뒤에야** `msgref` 를 올린다. 시한 초과로 빠져나가면 명령은 이미 나갔는데 `msgref` 는 그대로여서, 다음 명령이 같은 `msgref` 를 재사용하고 늦게 도착한 STATUS 응답의 헤더 `<NN` 가 그것과 맞아떨어진다 -- **다음 명령이 남의 응답을 먹고, 그 다음 명령이 `Invalid command packet header` 로 죽는다.** 루프백으로 재현했고 실제 순서까지 짚였다: `archon_status()` → `SetConfig('TRIGOUTFORCE', …)` 가 STATUS 본문을 삼킴 → `archoncmd('APPLYSYSTEM')` 예외.

> **`msgref` 만 올리는 것으로는 못 고친다.** 응답이 부분만 도착해 있었으면 소켓에 꼬리 바이트가 남아 바로 다음 명령을 죽이고, 늦은 응답이 몇 분 뒤 **다른 데이터셋**에서 튀어나올 수도 있다. 그래서 소켓을 버리고 새로 연다(`_resync_archon_link`) -- 설정·전원은 컨트롤러가 들고 있어 재접속으로 잃는 상태가 없다. 검증 하네스가 "순진한 수정"(msgref 만 +1)을 나란히 돌려 **여전히 깨지는 것**을 보여 준다.

내가 v1.1 에서 "한 번 실패하면 `TELEMETRY_ENABLE` 을 끄니까 안전하다" 고 적어 둔 것은 **틀렸다.** 끄는 것은 재발만 막고, **최초 오염은 이미 일어난 뒤**다.

**(2) 비ASCII 한 자가 FITS 를 통째로 못 읽게 만들었다.** 헤더는 문자 단위로 80자씩 조립하지만 파일에는 `bytes(head,'utf-8')` 로 쓴다. `build_header` 의 단정이 `len(head) % 2880` -- **문자 수**라서 한글이 섞이면 통과한다. `OBSERVER_NAME='HELab 차상목'` 실측: 문자 11520(통과) / 바이트 11526. 실제로 써서 읽으면 `OSError: Empty or corrupt FITS file`(`Header size is not multiple of 2880: 23046`)로 **HDU 전체가 죽는다.** v1.1 은 운영자 손편집 문자열(`OBSERVER_NAME`·`UNIT_CTRL_ID`·`UNIT_CTRL_SN`)을 헤더에 넣은 **첫 판**이라 이 위험이 새로 생겼다. 3중으로 막았다 -- `_check_identity_setup()` 이 기동에서 거부, `build_header` 단정을 **바이트 수**로, `fits_card` 가 새어 들어온 값을 `?` 로 치환(밖에서 오는 ACF 이름·STATUS 토큰용 마지막 방어선).

**(3) 데이터부 패딩(v1.1 신설)이 기하 불일치를 악화시켰다.** 패딩을 **실제 fetch 한 `fitsbuf.nbytes`** 에서 뽑았기 때문에, 실제가 선언(`NAXIS1*NAXIS2*2`)보다 길면 남는 꼬리가 2880 경계에 딱 맞아 astropy 가 그 뒤를 "다음 HDU" 로 읽고 `OSError: Header missing END card` 를 낸다. **v1.0 은 꼬리가 미정렬이라 경고만 내고 열렸다** -- 즉 진단 가능성을 내가 없앤 셈이다. 걸리는 경로는 실재한다: `samplemode`(32bit 표본 → `framesize = 4*w*h` 인데 `pixnum = framesize/2` 라 정확히 2배)와 ACF 기하 변경. fetch(25초) **앞에서** 바이트 수를 대조해 거부한다.

> 처음 넣은 대조는 `framew*frameh != NAXIS1*NAXIS2` 였는데 **samplemode 를 못 잡는다** -- 그 경우 기하는 선언과 같고 2배가 되는 것은 바이트 수다. 픽셀이 아니라 바이트로 비교해야 한다.

**(4) 예외가 나면 `POWEROFF` 를 건너뛴 채 끝났다.** v1.0 도 노출 루프를 감싸지 않았지만, v1.1 은 예외 원인을 새로 늘렸다((1)·(3)). 노출 루프를 `try/finally` 로 감싸 **무슨 예외가 나도 CCD 바이어스·클록은 끈다**(POWEROFF 자체가 실패하면 알리고 넘긴다 -- 원인을 가리지 않기 위해).

**함께 정리한 것: 재실행이 멱등하지 않다.** v1.0 은 같은 파일명을 `'wb'` 로 열어 덮어썼다. v1.1 은 D-016 선검사가 점유된 번호를 피해 올라가므로, **같은 UT 날짜에** 파일이 남은 DS 폴더를 `StartNum=0` 으로 다시 돌리면 재실행분이 다음 DS 의 번호 영역으로 넘어간다(실측 iFlat 116프레임: 321100~321215 → 321216~321331 → 321332~321447). 규격대로의 동작이지만 **`filenum - DatasetId*100 == nframe` 이라는 v1.0 의 불변식이 깨진다** -- 프레임 번호를 믿는 분석이 어긋난다. 데이터셋 시작에 경고를 넣고 운용 조치(폴더를 비우거나 옮기거나 `StartNum` 으로 이어받기)를 실행 안내에 적었다. **선검사 경로에 날짜가 들어 있으므로(D-011) 다음 날 같은 DS 를 다시 찍는 것은 충돌이 아니다** -- 처음 넣은 경고는 날짜를 안 보고 폴더 안의 모든 파일을 세어서, 실험실의 평상 재실행(다른 날 같은 DS)마다 헛경고를 냈다. 오늘 자 파일만 세도록 고쳤다. 성능은 문제 없다(프레임당 `os.path.exists` 2회, 3회차 누적 0.9초 대 프레임당 25초 독출).

**시사점 두 가지.**

- **"규격을 적용했다" 가 "취득이 안전해졌다" 가 아니다.** 네 건 모두 규격 적용의 부수 효과이고, 셋은 **v1.0 보다 나쁘게** 만들었다(오염 전파·파일 전체 손실·진단 가능성 상실). 검증된 코드에 개정을 얹을 때 물어야 할 것은 "규격에 맞나" 가 아니라 **"v1.0 에서 되던 것이 깨졌나"** 다. 감사를 그 질문 하나로 좁힌 것이 이 4건을 찾은 이유다.
- **11.21 의 교훈과 같은 계열이다.** 그때는 "실행되지 않는데 초록", 이번은 "**깨졌는데 조용함**". 넷 다 취득 중 신호가 없었다 -- 그래서 고침과 함께 `ics_archon/tests/verify_labtest_v11.py`(19항목, 가짜 Archon + astropy 실파일)를 남겼다. 실기가 없어도 매번 돌 수 있는 유일한 확인 수단이다.

### 11.23 `ics_archon` v0.0 -- `ics_sim` + labtest 합본 (2026-08-23)

**무엇을.** 실기 취득 프로그램 `ics_archon` 의 첫 판을 세웠다. 1단계(합본)의 전량이고, 목이 확정한 3단계 계획(① 통째로 세운다 ② 결정·검토사항을 보완한다 ③ 실기 시험 결과를 반영한다) 중 ①이다. `ics_sim` 은 **무개정**이고 -- 정확히는 확장점 6줄만 늘었다.

**핵심 판단 -- `ics_sim` 을 사본으로 뜨지 않는다.** "합본" 을 폴더 복제로 읽으면 `rawcards.py`(견본 v1.0 pair 의 기계 사본)가 **세 벌**이 된다: `ics_sim/rawcards.py` · labtest 스크립트 내장 `RAWCARDS` · 새 사본. raw spec 5장이 개정되면 셋을 다 고쳐야 하고, 바이트 대사 시험은 **자기 사본만** 지켜 주므로 어긋난 하나가 조용히 남는다. 그래서 `ics_archon` 은 형제 폴더를 `sys.path` 에 넣고(`_simpath.py`, 저장소에서 유일한 경로 손질) 백엔드를 `ics_sim.hardware.register_backend()` 로 끼운다. `ics_sim` 변경은 그 등록 훅 **6줄뿐**이고 그 자리가 원래 확장점이다 -- 시험 318개는 한 줄도 안 고치고 통과한다.

- **`ics_archon/ics_archon/`** -- `_simpath`(경로) · `__init__`(버전 `0.0.0` · `build_id`) · `config`(`[archon]` 절) · `app`(`IcsArchon(IcsSim)`) · `__main__`(진입점) + `archon/` 5모듈. `ics_sim` 의 인자 파서·로깅·콘솔을 **빌려 쓴다**(두 벌이 되면 한쪽에 옵션이 늘 때 다른 쪽이 뒤처진다).
- **`archon/protocol.py`** -- labtest 의 전역 함수 4개를 객체로. **매뉴얼 p.45 를 다시 읽어 셋을 고쳤다**: ① `?xx`(오류 응답)를 구분한다 -- labtest 는 `<xx` 만 대조해 컨트롤러의 거부를 `Invalid command packet header` 로 뭉갰다(원인이 "내 명령이 틀렸다" 인데 화면에는 "프로토콜이 깨졌다") ② 읽기 버퍼를 하나로 -- `archoncmd` 가 `msgbuf` 를 안 봐서 이진 꼬리를 놓칠 구멍이 있었다 ③ **참조번호를 보내기 전에 올린다** -- 시한 초과 뒤 늦은 응답이 다음 명령 번호와 맞아떨어지는 일이 원리상 없어진다(11.22 (1) 회귀의 근본 처방. 다만 부분 수신분은 그대로 남으므로 `resync()` 는 계속 필요하다).
- **`archon/parse.py`** -- `SYSTEM`/`STATUS`/`FRAME` 해석. **왕복이 없어** 실기 응답 한 줄을 붙여넣어 재현할 수 있다. `VOLT_RAILS` 는 사본을 두지 않고 `rawhdr` 의 것을 그대로 참조한다(시험이 `is` 로 못박는다).
- **`archon/controller.py`** -- 컨트롤러 한 대. 제어 시퀀스(POWERON → WCONFIG/APPLYALL → LOADPARAMS → FRAME 폴링 → FETCH)는 **v1.0 계보라 순서·명령을 바꾸지 않았다.** 바꾼 것은 껍데기다: 전역 상태 → 객체(과학 2대 + 가이드 1대이므로), 블로킹 → `asyncio.to_thread` + 락, **명령마다 상한**(프로토콜은 인식 못 한 명령에 무응답이라 오타 하나로 영구히 멈춘다).
- **`archon/fitswrite.py`** -- 견본 정본을 바이트로 낸다. astropy 를 쓰지 않은 이유 셋: ① 취득 경로에 라이브러리 의존을 넣지 않는다 ② 344 MiB 프레임의 사본을 안 만든다(`byteswap(inplace=True)` -- labtest 보다도 사본이 하나 적다) ③ 데이터부 2880B 패딩을 명시한다. `rawcards.CARDS` 템플릿을 직접 읽고, `render()` 가 내지 않는 구조 카드(`SIMPLE`~`BZERO`)만 채워 넣는다. `.part` 로 쓰고 `os.replace` -- 반쪽 파일이 최종 이름을 차지하면 D-016 선검사가 그 번호를 점유된 것으로 본다.
- **`archon/backend.py`** -- 계약(D-012)과 실기의 어긋남 셋을 흡수한다. **이것이 이 판의 실제 설계 작업이다**:
  1. `initialize(ccd, …)` 는 CCD 4회 오는데 컨트롤러는 2대다 -- suffix 로 중복을 걸러야 한다(`APPLYALL` 은 초 단위라 프레임마다 되풀이할 수 없다. 시험이 "`APPLYALL` 1회, `LOADPARAMS` 는 프레임당 2회" 로 못박는다).
  2. `erase(ccd)` 는 master 한 번만 온다 -- **두 대 다 비운다.** master 만 flushing 한 것은 레거시 IC 구조의 관례이고 실기의 사실이 아니다(NT 를 안 비우면 잔상이 남는다).
  3. **노출을 걸 자리가 계약에 없다** -- DARK/BIAS 는 시퀀서가 `_integrate_dark` 에서 백엔드를 아예 부르지 않는다. 그래서 셔터 노출은 `open_shutter()`, DARK/BIAS 는 `readout()` 첫머리에서 건다.
- **동기 접근자 셋은 스냅샷을 읽는다.** 시퀀서가 `controller_info`/`controller_telemetry`/`sensors` 를 `_backend_fact` 로 **동기 호출**하므로 이벤트 루프 안이고 소켓을 만질 수 없다. `initialize()` 에서 떠 둔 `SYSTEM`/`STATUS` 를 읽는다 -- labtest 도 같은 이유로 `STATUS` 를 노출 개시 전에 떴다(fetch 뒤에 물으면 다 읽어낸 노출을 잃는다).

**매뉴얼에서 새로 확정한 것 -- 진행률은 추정이 아니다.** labtest 는 프레임 번호가 바뀌기만 기다렸는데, `FRAME` 에 **`BUFnLINES`(라인 진행)** 과 `BUFnPIXELS`(픽셀 진행)이 있고 쓰기 중 버퍼가 `WBUF` 다(p.49-50). 그래서 `PCTREAD=` 를 컨트롤러 **보고값**으로 낼 수 있다 -- `readout()` 을 제너레이터로 만들어 둔 것이 여기서 값을 한다(9.1). 시험이 "ini 의 시뮬 모델(6/17/28…)이 새어 나오지 않는지" 를 본다. 100 은 **완료가 확정된 뒤에만** 낸다 -- 폴링이 99.6% 를 반올림해 보내면 프레임이 안 끝났는데 `Acquisition Complete.` 가 나간다.

**시험 48개 -- 실기 없이 도는 최대치.** 가짜 컨트롤러(`tests/fake_archon.py`)가 프레이밍·`SYSTEM`/`STATUS`/`FRAME`·`LOADPARAMS`→적분→독출→`FETCH` 를 규격대로 흉내내고, **프레임 버퍼 2~3개**를 순환하며 `LOCKn` 을 존중한다. 픽셀은 결정적 패턴(`프레임번호*1000 + y*width+x`)이라 배치·엔디언·`BZERO` 는 물론 **"어느 프레임의 자료인가" 까지 값으로** 확인된다.

- **견본 v1.0 pair 144카드 바이트 재현**(MK·NT, 불일치 0). 견본 카드 이미지를 되먹여 같은 80바이트가 나오는지 본다 -- 경로는 **패턴**으로 찾고 **없으면 실패**다(11.21 의 "실행되지 않는데 초록" 을 되풀이하지 않는다).
- **전 경로**: DARK·OBJECT 두 갈래 모두 `Acquisition Complete.` 4회 · `Wrote` 4회 · `EXPSTATUS=IDLE` 1회 → pair 2파일 · 픽셀 일치 · `CTRLnSN`(BACKPLANE_ID) · `Cn_TEMP` 5자리 · `Cn_VOLT/CURR` 7자리 · 5.9절 "양쪽 동일" · `CCDTEMP` sentinel.
- **회귀 못박음**: STATUS 시한 초과 뒤 다음 두 명령이 살아 있는지(11.22 (1)) · 비ASCII 치환(11.22 (2)) · samplemode 기하 불일치를 **fetch 앞에서** 거부(11.22 (3)) · 종료에서 `POWEROFF`(11.22 (4)) · 텔레메트리 실패가 프레임을 잃지 않음.
- 검토 중 자체 결함 2건을 잡았다: ① `FETCH` 오류 응답(`?xx\n`, 4바이트)을 블록 하나(1028바이트)가 모일 때까지 기다린 뒤에 판정해 **거부를 "느린 응답" 으로 오해**했다 -- 머리 4바이트를 먼저 본다. ② `progress_step=0` 이 폴링마다 같은 값을 되풀이 보냈다(폴링이 라인 진행보다 빠르다) -- "값이 바뀔 때마다" 로 읽는다.

**검토 중 나온 가장 큰 발견 — 프레임 버퍼가 저장보다 먼저 재활용된다.**

파이프라인 겹침을 시험으로 강제해 보고 알았다. **BIGBUF=1 은 프레임 버퍼가 2개**인데 **노출 1회가 프레임 2개**(flush + 취득)를 만든다 — 즉 다음 노출이 이 프레임의 버퍼를 **정확히** 덮는다. 그리고 저장은 `write_delay` 뒤에 백그라운드로 도는 일이다. 겹치면 무슨 일이 나나:

1. 프레임 상태를 컨트롤러 필드에 두면 뒤 프레임이 앞 프레임의 값을 덮는다 → 앞 프레임의 저장이 **엉뚱한 프레임을 기다리고**, 앞 프레임의 뒷정리가 뒤 프레임의 "노출을 걸었다" 표시를 지운다(**이중 노출**). → `FrameTicket` 으로 **프레임이 자기 상태를 들고 간다**. 저장 대기열은 FIFO 다. `ics_sim` 이 같은 부류를 두 번 겪었고(12.10 · 11.20 critical) 결론은 매번 같았다 — **프레임의 것은 프레임이 정하고 나중에 다시 읽지 않는다.**
2. 저장이 `FRAME` 의 **"최신 프레임"** 을 집으면 그 파일이 **남의 노출 픽셀**을 담는다. 헤더는 이 프레임의 것이므로 **아무 경고도 없다** — 아카이브에 들어가면 되돌릴 수 없다. → `parse.find_frame()` 이 **내 번호를 담은 버퍼**를 찾고, 없으면(= 덮였으면) **저장하지 않는다.** 파일 한 장을 잃는 편이 틀린 파일을 남기는 것보다 낫다.
3. fetch 동안 덮이는 것은 `LOCKn`(매뉴얼 p.50)이 막는다. **labtest 가 2026-05-28 에 뺀 명령**이고("remove to fetch debug") v0.0 이 되돌렸다 — 그래서 `[archon] lock_buffer` 로 끌 수 있게 두었다(끄면 labtest 와 같아지고, 위 2번의 대조는 그대로 남는다).

실기 값(프레임 ~40초 · `write_delay` 3.4초)이면 여유가 크지만 **독출 시간 실측이 나오기 전에는 알 수 없다.** 그리고 여유를 늘리는 손잡이가 둘 더 있다 — `full_flush_on_erase=false`(프레임 소비 절반), 스트리밍 저장(잠금 시간 단축).

> **시험이 이 발견을 만들었다.** 가짜 컨트롤러가 프레임마다 **같은** 픽셀을 주던 동안에는 두 결함이 다 초록이었다. 픽셀에 프레임 번호를 섞고 버퍼를 2개로 모델하자마자 둘 다 드러났다 — 11.20 의 "시뮬 고정값 때문에 통과하는 시험" 과 똑같은 구조다. 상대역이 **구별되는 값**을 주지 않으면 "누가 누구 것을 가져갔나" 를 어떤 단정으로도 잡을 수 없다.

**실기 첫 실행 도구 (`ics_archon/tools/probe_archon.py`).** 본편을 그냥 걸면 미검증 3자리가 한꺼번에 걸려 원인을 가릴 수 없다. 그래서 위험이 낮은 것부터 세 단계로 나눴다 -- ① **읽기 전용**(전원을 켜지 않고 `SYSTEM`/`STATUS`/`FRAME` 원문 + 가정 대조: AD 모듈 슬롯 5~8 · 온도 슬롯·전원 레일 결측 · 기하 · `BUFnLINES` 존재 · `Cn_*` 카드 폭) ② **ACF 대조**(`RCONFIG` 로 파라미터 슬롯의 줄 번호가 컨트롤러 메모리와 맞는지 확인만) ③ **프레임 1장**(`--expose` 를 준 경우에만 전원 ON, 셔터는 안 열고, 끝나면 무조건 `POWEROFF`). ③이 독출 실측 시간·FETCH MiB/s·FITS 1장을 낸다 -- `[timing]` 과 25초 `Wrote` 창의 근거가 그 값이다. **본편과 같은 모듈을 쓰므로 여기서 통과한 것은 본편에서도 통과한다.**

> **그 도구를 시험에 걸면서 첫 실행 결함 하나가 나왔다 (목 질문 중).** 전원을 켜고 **완료된 프레임이 하나도 없는** 컨트롤러(`RBUF=0`)에서 `parse.newest()` 는 `-1` 을 준다. 그런데 저장이 `prev + 1 = 0` 번 프레임을 기다렸고, 컨트롤러가 첫 프레임에 1 을 붙이는 순간 "0 을 지나쳤다"(버퍼 재활용 판정)가 되어 **첫 노출이 통째로 버려졌다.** 실기 첫 실행에서 곧바로 걸릴 자리였다 -- 가짜 상대역이 처음부터 "프레임 0 완료" 를 보고하고 있었기 때문에 48개 시험이 전부 초록이었다. 고침: `parse.next_frame()` 이 "prev 이후 **가장 이른** 완료 프레임" 을 찾고, `prev < 0` 이면 번호를 못박지 않는다. 가짜에 `fresh=True`(완료 프레임 없음 · `RBUF=0`)를 넣어 회귀로 묶었다. **시험 48 → 57개.**
>
> **같은 교훈이 세 번째다.** 11.20 "시뮬 고정값 때문에 통과", 11.21 "실행되지 않는데 초록", 11.22 "깨졌는데 조용함", 그리고 이번 "**상대역이 우리 가정대로 답해서 초록**". 가짜 컨트롤러가 편한 초기 상태(프레임 0 완료)를 주고 있었고, 그건 실기의 상태가 아니었다. 상대역을 만들 때 물어야 할 것은 "규격대로인가" 가 아니라 **"실물의 어느 순간을 흉내내는가"** 다.

**남긴 판단 -- 결정 15건 · 검토 A6/B10/C3.** 전량이 `ics_archon/SMC_CLAUDE.md` 의 표에 있다(되돌리는 방법까지 함께). 가장 큰 것 셋: ① `ics_sim` 을 가져다 쓰는 구조 ② 원시 바이트 저장 ③ **적분은 컨트롤러가 잰다**(시퀀서 카운트다운은 알림이고 하드웨어를 몰지 않는다 -- 그래서 `STOP` 은 적분을 자르지 못하고 셔터만 강제로 닫는다).

**시사점.**

- **"계약을 채운다" 가 "계약이 맞다" 는 뜻은 아니다.** 백엔드 계약은 CCD 단위로 말하고 하드웨어는 컨트롤러 단위로 움직인다. 그 어긋남 셋 중 둘(중복 `initialize`, master-only `erase`)은 **레거시 IC 구조의 흔적**이고 하나(노출 개시 훅이 없음)는 시뮬에서 필요가 없어 안 만든 것이다. 시뮬이 계약을 만족시켰다는 사실이 그 계약을 검증해 주지 않는다 -- 11.20 의 "시뮬 고정값 때문에 통과하는 시험" 과 같은 계열이다.
- **매뉴얼을 다시 읽은 값이 컸다.** 진행 카운터(`BUFnLINES`)·오류 응답(`?xx`)·무응답 규약·`FASTLOADPARAM` 넷 다 labtest 가 쓰지 않던 것이고, 셋은 곧바로 코드가 됐다. 검증된 코드를 옮길 때 "그 코드가 안 쓴 것" 을 규격에서 찾는 편이 낫다.

### 11.24 설정·오류 경로 전수 검토 -- 조용한 실패 9건 (2026-08-23)

**무엇을.** `ics_archon` v0.0 을 세운 뒤 목 지시로 두 가지를 전수 검토했다 -- ① **ini 설정이 다 적용되나**, 특히 판정 원장 v1.14 의 `Source = ICS INI` 카드가 파일까지 물고 들어오나 ② **실행 중 어떤 오류가 날 수 있나.** 결함 **9건**이 나왔고 전부 회귀 시험을 붙였다(시험 57 → **85개**). 아홉 중 **여덟이 "조용한 실패"** 였다 -- 오류도 경고도 없이 값만 틀리거나, 통보가 사라지거나, 영구히 멈춘다.

**ini -> FITS 대조 방법.** "ini 를 읽는가" 만 보면 "읽었지만 카드로 안 나갔다" 를 놓치고, 기본값과 같은 값을 넣으면 배선이 끊겨도 통과한다. 그래서 **기본값과 겹치지 않는 값**을 넣고 **파일에서 되읽었다**(`ics_archon/tests/test_ini_cards.py`). 결과: 키 125개 전부가 어느 한쪽 로더에 읽히고, `[archon]` 은 키 24 ↔ 필드 22 가 양방향 완전 대응(ini 로 못 바꾸는 필드 0 · 대응 없는 키 0), 원장의 `ICS INI` 17장이 **전부** ini 값을 싣는다. 함께 못박은 것 -- ini 가 백엔드 보고값(`BACKPLANE_ID`)을 이긴다 · 비우면 컨트롤러 값이 실린다 · `[node] site` 한 줄이 파일명 `<SITE>`·`OBSERVAT`·좌표·`ORIGIN` 을 **함께** 끌고 간다 · 테스트베드는 좌표가 sentinel.

**결함 9건.**

1. ⚠️ **D-016 충돌 선검사가 `[paths] write_fits` 에 묶여 있었다.** 시퀀서가 `resolve_pair_number(…, check=cfg.paths.write_fits)` 로 불렀는데, 그 플래그의 뜻은 **"시뮬이 더미 FITS 를 만드는가"** 다. 실기 백엔드는 그 값과 무관하게 항상 실파일을 쓰므로, 저장소 ini 의 **기본값 `false`** 로 실기를 돌리면 **선검사가 꺼진 채 실파일이 나가** 같은 이름을 조용히 덮어쓴다 -- D-016 이 막으려던 바로 그 일이다. 같은 날짜·번호로 두 번 저장해 실측 재현했다(파일 2개가 4개가 되지 않았다). **고침**: 게이트를 백엔드 속성 `writes_files` 로 옮겼다(`base.py` 계약에 등재, 시뮬은 종전대로 `write_fits` 를 따르므로 거동 무변경).

   > **한 겹 더 (목 승인 2026-08-23).** 선검사는 저장보다 `write_delay`+저장시간만큼 앞서므로 그 사이의 틈을 못 막는다 -- 같은 `data_dir` 에 ICS 두 개, 백업 되돌림, rsync 가 그 틈에 파일을 둘 수 있다. `fitswrite.write_frame` 이 `os.replace` 앞에서 존재를 확인하고 **거부**한다(실패 시 `.part` 도 지운다). 둘 중 하나를 잃어야 하면 **새 프레임을 버리는 쪽**이 맞다 -- 옛 프레임은 이미 아카이브에 들어갔을 수 있고 되돌릴 수 없는데, 새 프레임은 다시 찍을 수 있고 오류가 크게 뜬다. **이름 결정은 여전히 시퀀서 몫이다**(백엔드는 "덮지 않겠다" 고만 하므로 D-012 의 역할 분담을 넘지 않는다) -- 처음에 이 점을 "백엔드가 이름을 판정하기 시작한다" 고 반대 논거로 적었는데 **과장이었고 목에게 정정했다.** 정당한 재작성 경로는 지금 없다(중간에 죽은 파일은 `.part` 가 흡수한다).
2. **첫 전원 투입에서 첫 노출을 버렸다** -- 11.23 의 것과 같은 건이고 거기 적었다.
3. **프레임이 안 나오면 영구히 기다렸다.** labtest 는 `while True` 로 돌았고 사람이 화면을 보고 있었다. 본편의 상대는 OBSAgent 이므로 `EXPSTATUS=READOUT` 에 갇히면 관측자 화면이 멈추고 `force_idle` 타임아웃으로 `opause` 에 빠진다. **고침**: `[archon] frame_timeout`(기본 300초) -- 넘기면 레거시와 같은 `DMA WAIT TIMEOUT. EXPOSURES ABORTED.` 경로를 탄다. `full_flush_on_erase=true` 면 `ERASE` 국면에서 **더 먼저** 걸린다(노출 시간을 버리기 전이라 이른 발견이다).
4. ⚠️ **와이어는 ASCII 인데 오류 문구를 한글로 썼다.** 전송 계층이 `payload.decode('ascii', errors='replace')` 를 하므로(레거시 IMPv2 는 ASCII 프로토콜이다) `ICS>OBS ERROR: MK: FITS 저장 실패` 가 관측자에게는 `MK: FITS ?? ??` 로 간다. OS 오류 문구도 한국어 Windows 에서 한글로 온다(`[WinError 3] 지정된 경로를…`). **고침**: **사실은 로그에, 통보는 ASCII 로** 갈랐다 -- 백엔드가 내는 `BackendError` 7종을 ASCII 로 바꾸고 한글 진단은 `log.error` 로. 시험이 `m.isascii()` 를 단정한다.
5. **`numpy` 부재가 저장 태스크를 조용히 죽였다.** `to_fits_data()` 가 numpy 를 안에서 import 하는데 `write_frame` 이 `(OSError, ValueError)` 만 잡아서 `ImportError` 가 새고, `_store` 는 `BackendError` 만 잡으므로 fire-and-forget 태스크가 아무도 회수하지 않은 채 죽었다 -- **`Wrote` 0회 · 오류 0회.** 11.20 critical 과 같은 부류다. **고침**: `ImportError` 를 잡고, numpy 를 백엔드 기동에서 확인한다(없으면 그 자리에서 거부).
6. **`?xx` 거부에 재접속·재시도를 되풀이했다.** `apply_acf` 가 `ArchonError` 를 종류 구분 없이 잡아 `resync()` + 재시도를 돌렸는데, 컨트롤러가 거부한 것이면 같은 설정을 다시 밀어도 같은 거부가 온다 -- 그 사이 재접속이 4번 일어나 원인이 "망이 불안하다" 로 오인된다(실측: 접속 7회, `APPLYALL` 2회). **고침**: `reply_error` 는 즉시 실패.
7. **`initialize` 실패가 컨트롤러당 두 번 일어났다.** chip 이 둘이라 `prepare()` 가 두 번 시도되고 `APPLYALL` 같은 무거운 명령이 두 번 나갔다. **고침**: 성공만 기억하던 것을 **실패도 프레임 단위로** 기억한다(다음 프레임은 suffix 가 달라 자동 재시도).
8. ⚠️ **`time_scale != 1.0` 이 실기에서 노출을 잘라낸다.** 적분 길이를 재는 것은 컨트롤러(`IntMS`)이고 시퀀서의 카운트다운은 알림이다 -- 축척을 낮추면 카운트다운이 먼저 끝나 `close_shutter()` 가 적분 중에 불리고, 그것이 셔터를 강제로 닫는다. 그런데 헤더 `EXPTIME` 은 요청값 그대로라 **정상으로 보이는 오염 프레임**이 된다(9.2.3 이 AUX 시뮬을 물릴 때 같은 이유로 1.0 을 요구했다). 한쪽만 보면 둘 다 정상인 값이라 각자의 `validate()` 로는 안 걸린다 -- **교차 검사**(`_cross_checks`)를 신설했다. 함께: `close_shutter()` 에 여유 폭(1초)을 두어 **정상 경로에서는 셔터를 만지지 않는다** -- `int_until` 이 카운트다운 종료보다 몇 백 ms 늦어서, 여유가 없으면 매 노출마다 독출 시작 무렵에 `APPLYSYSTEM` 이 한 번 더 나갔다(그 안전성은 실기 확인 항목이다).
9. **`_head()` 가 `\#` 를 안 벗겼다.** `#` 가 값의 일부인 카드가 이 경로로 온다 -- `FPAID = FPA\#1` 이 `'FPA\#1'` 로 실렸다(`_text_or` 만 벗기고 있었다).

함께 정리한 것 -- `APPLYSYSTEM`/`LOADPARAMS` 에 `APPLYALL` 과 같은 60초 상한을 주고 있어서 **노출 안에서 60초를 매달릴 수 있었다**(무응답 명령이면 실제로 그랬다 -- 25초 `Wrote` 창을 훌쩍 넘는다). `T_SYSTEM = 15초` 로 갈랐다. 그리고 `[node] site_from_ip` 이 주석에만 있고 실제 키가 없어서 운영자가 찾을 수 없었다 -- 키로 노출했다.

**교차 검사 신설.** 한쪽만 보면 정상인 조합을 기동에서 알린다 -- `time_scale != 1.0` · `[auxcontrol] enabled=true` · `[behavior] inject` 켜짐 · **archon 이 보지 않는 설정**(`write_fits`·`fits_shape`)이 바뀌어 있음(고쳐도 아무 일이 없다는 사실 자체가 정보다).

**시사점.**

- **설정이 "읽히는가" 와 "쓰이는가" 는 다른 질문이다.** 9건 중 1·8은 값이 정확히 읽혔는데 **엉뚱한 것을 켜고 껐다**. 키 목록 대조로는 절대 안 잡히고, 값을 넣어 산출물에서 되읽어야 나온다.
- **시뮬 전용 플래그를 공용 경로의 게이트로 쓰면 안 된다.** 1번이 그 형태였고, 시뮬에서는 뜻이 맞아떨어져서 318개 시험이 전부 초록이었다. "이 플래그의 뜻이 무엇인가" 를 백엔드에게 묻는 형태(`writes_files`)로 바꾸는 것이 유일한 구조적 해법이다.
- **"조용한 실패" 가 8/9 다.** 11.21~11.23 의 교훈("실행되지 않는데 초록" · "깨졌는데 조용함" · "상대역이 우리 가정대로 답해서 초록")과 같은 계열이고, 이번에는 **설정 층**에서 나왔다. 오류 경로를 시험할 때 물어야 할 것은 "예외가 나나" 가 아니라 **"밖에서 무엇이 보이나"** 다 -- 그래서 `test_failures.py` 의 단정은 대부분 와이어에 나간 메시지다.

### 11.25 v0.0 커밋 + 두 컨트롤러 병렬 독출 계획 검토 (2026-08-24)

v0.0 을 커밋 2건으로 올렸다 -- `ecf3487`(ics_sim 확장점 + 결함 4건) ·
`6a94e57`(ics_archon 신설 + 문서). 검증 상태는 `ics_sim` 325 · `ics_archon` 98 ·
벤더 표류 없음. 브랜치 `ics-archon-v1.0-build`, **`main` 미합류**(v0 완성 또는
v1 즈음에 판단 -- 11.23).

**목이 다음 세션 일감을 정했다** -- 두 컨트롤러 병렬 독출 개정과 v0 세부 검토.
착수 전 계획·비용·의견을 요구했으므로 조사만 하고 코드는 안 건드렸다. 결론은
[`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "다음 세션 작업
지시" 에 있고, 여기에는 **왜 그 결론인가**를 남긴다.

**지시가 하나로 보였는데 셋이었다.** "FRAME 검사를 둘 다 동시에 + fetch 병렬 +
프레임별 `Acquisition Complete.`" 를 그대로 받으면 한 덩어리로 고치게 된다.
코드를 읽어 보니 성질이 갈렸다.

| | 상태 | 성질 |
|---|---|---|
| FRAME 검사 동시 | ❌ `readout()` 이 master 티켓만 폴링 | **결함** |
| fetch 병렬 | ✅ **이미 되어 있다** | 시험만 |
| 프레임별 획득 완료 | ❌ 지금은 같은 틱에 4개 | **선택 + 새 위험** |

**fetch 는 이미 병렬이었다.** `_store` 가 컨트롤러마다 별개 asyncio 태스크이고
(`sequencer.py` `asyncio.create_task(name='ics_sim.store.<tag>')`), 컨트롤러마다
자기 `asyncio.Lock` 과 자기 소켓을 갖고(`controller.py`), 모든 왕복이
`asyncio.to_thread` 로 루프 밖에 있다. 즉 MK 의 FETCH 가 도는 동안 NT 의 FETCH 가
같이 돈다. **"고쳐야 할 것" 으로 착수했으면 이미 되어 있는 것을 다시 만들었을
것이다** -- 지시를 코드로 확인하는 데 든 비용이 그 손실보다 훨씬 작았다.

**결함은 메시지 타이밍이 아니라 "NT 를 아예 기다리지 않는다" 였다.** `readout()`
은 master 프레임만 기다린 뒤 곧바로 `yield final` 을 낸다. 시뮬에서는 CCD 4개가
다 소프트웨어라 "master 가 끝났으면 나머지도 끝났다" 가 참이었고, 그래서 시험
325개가 전부 초록이었다. 실기는 컨트롤러가 **물리적으로 둘**이라 그 전제가
깨진다 -- 11.20~11.24 에서 되풀이된 "상대역이 우리 가정대로 답해서 초록" 과 같은
계열이고, 이번에는 **가정이 시뮬의 구조 자체**였다.

**그래서 결함 수정과 개선을 갈랐다.** 두 티켓을 `asyncio.gather` 로 함께 기다리고
진행률만 master 것을 흘려보내면 **획득 완료는 여전히 같은 틱에 4개**이므로
1.8초 창(3.3) 산포는 0 으로 남고 NT 실패는 그 자리에서 `DMA WAIT TIMEOUT` 으로
통보된다. **결함은 이것만으로 닫힌다.**

**프레임별 발신은 그 위에 얹는 별개 판단이고, 규약 위험을 새로 들여온다.**
4개의 산포가 **두 컨트롤러의 실제 시차**가 되기 때문이다. 지금은 같은 이벤트 루프
틱에서 내보내 산포가 사실상 0 이므로 3.3 의 1.8초 창이 **구조적으로** 보장돼
있는데, 그 보장이 없어진다(`obsagent_model.check_windows` 가
`spread = acq[3] - acq[0]` 로 검사하므로 시뮬에서는 잡힌다).

**그리고 OBSAgent 는 4개가 언제 왔는지를 창 검사 외에는 쓰지 않는다.** 즉 이
개정의 실익은 **사람 눈**에만 있고 기계 쪽에는 위험만 늘어난다. 정상 상황의 시차는
수십 ms 로 보이므로(같은 ACF · 같은 기하 · `gather` 로 동시 트리거) 화면 차이도
사람에게 안 보일 가능성이 크다. **실측 전에는 이득 크기를 알 수 없다** -- 그래서
스위치(`[readout] acq_per_frame`, 기본 `false`)와 시차 감시(`acq_skew_warn`, 기본
1.0초)를 함께 권했고, 기본값은 `probe_archon` 3단계 실측 뒤에 정하기로 했다.

**시사점.**

- **지시를 코드로 확인하기 전에 착수하지 않는다.** 셋 중 하나는 이미 되어 있었고
  하나는 결함이었고 하나는 취향이었다. 셋을 한 덩어리로 고치면 **위험 없는 수정과
  위험 있는 개선이 같은 커밋에 들어가** 되돌릴 때 함께 되돌아간다.
- **시뮬의 구조가 곧 가정이다.** "CCD 4개가 다 소프트웨어" 라는 사실이 코드 어디에도
  적혀 있지 않은 전제를 만들었고, 시험은 그 전제 안에서만 초록이었다. 실기와
  개수·경계가 다른 자리는 **시뮬 쪽에도 그 경계를 만들어야** 시험이 뜻을 갖는다
  -- 그래서 `ics_sim` 쪽 일이 `ics_archon` 쪽보다 크다.
- **규약을 여는 것과 어기는 것은 다르다.** 이 개정은 3.3 을 직접 건드리므로
  `ics_sim/SMC_CLAUDE.md` 의 "절대 깨뜨리면 안 되는 것" 5번 자리에 예고를 남겼다.
  목 지시로 여는 것이니 위반은 아니지만, **커밋에 그 사실을 적지 않으면 다음
  사람이 위반으로 읽는다.**
- **배치본의 "실패 0" 은 거짓이었다.** 형제 `ics_sim` 없이 `ics_archon/` 만 둔
  트리를 실제로 만들어 돌려 보니 **7 실패 / 91 통과**였다(견본 pair 원천 4 · 형제
  원천 3). 배치본에서는 그 실패가 정상인데 README 가 "실패 0 이어야 한다" 고
  적어 두어, 운영자가 **설치가 깨진 줄 알게** 되어 있었다. README 를 실측값으로
  고쳤고, 표식으로 자동 구분하는 것은 미해결(F11)로 남겼다.

### 11.26 병렬 독출 반영 + v0 미해결 F1~F12 처리 (2026-08-24)

11.25 에서 계획만 세워 둔 것을 **목이 결정하고 착수**했다.  결정의 요점은
`ics_sim` 의 몫을 줄인 것이다 -- 원문: *"ics_sim에서는 병렬독출 구현하지 말고,
간단히 모사만 하고 ics_archon에서만 구현하자. 작업1, 2, 둘다 진행해줘."*

**견적 ~300줄이 그 한마디로 반이 됐다.** 11.25 의 견적에서 가장 큰 덩어리는
`ics_sim` 의 `hardware/sim.py` 를 두 컨트롤러로 모사하고 시차 주입
(`[behavior] inject = acq_skew`)까지 붙이는 것이었는데, 그것을 **얕은 모사**로
바꿨다.  시뮬은 CCD 4개가 다 소프트웨어라 독출 경로에 컨트롤러라는 경계가
아예 없고, 그 경계를 진짜로 만들려면 `[readout]` 진행률 모델 자체를 나눠야
한다 -- 시뮬에서만 쓰는 구조를 실기 때문에 만드는 셈이다.

**다만 계약 훅 자체는 줄일 수 없었다.**  `Acquisition Complete.` 를 내보내는
것은 시퀀서이고 백엔드가 아니다.  그래서 "어느 컨트롤러가 끝났나" 가 계약을
건너야만 프레임별 발신이 가능하다 -- `DetectorBackend.readout_events()` 를
**선택 훅**으로 넣었다(없으면 `readout()` 로 떨어진다).  시퀀서는 훅이 있으면
그것을 쓰고, 그 경로를 `ics_sim` 시험도 밟게 하려고 시뮬에도 훅을 뒀다.
**시뮬이 훅을 안 내놓으면 새 분기가 실기에서 처음 돈다** -- 11.25 가 경고한
"시뮬의 구조가 곧 가정" 의 반대편 함정이다.

**1-A(결함)와 1-C(개선)를 갈라 넣었다.**

- **1-A** -- `readout()` 이 master 티켓만 폴링하던 것을 고쳤다.  두 컨트롤러의
  프레임을 함께 기다리고, 완료 통보는 **둘 다 끝난 뒤**에 낸다.  `Acquisition
  Complete.` 4개는 여전히 같은 틱이라 1.8초 창(3.3) 산포는 0 으로 남는다.
- **1-C** -- `[readout] acq_per_frame`(기본 `false`) 뒤에 뒀다.  꺼져 있으면
  종전 거동 그대로다.  함께 `acq_skew_warn`(기본 1.0초)을 넣었는데 **스위치와
  무관하게 시차는 잰다** -- 기본값을 정할 근거가 그 실측이기 때문이다.

**1-B(fetch 병렬)는 손대지 않았다.**  11.25 에서 이미 되어 있음을 확인했고,
이번에 시험으로 못박았다(느린 NT 로 겹침 확인).

**회귀 시험이 진짜로 결함을 잡는지 매번 확인했다.** 처음 쓴 1-A 시험은
**수정 없이도 통과**했다 -- `exp 1`(IntMS=1000ms)이 `frame_timeout=0.3` 보다
길어 MK 도 함께 시한 초과로 죽었고, 그래서 "획득 완료가 안 나갔다" 가 참이
됐다.  결함이 아니라 **시험 설정 때문에** 초록이었던 것이다.  적분을 0 으로
바꿔 NT 만 죽는 상황으로 좁히자 수정 전에는 4개가 그대로 나갔다.  이번 작업의
회귀 시험은 전부 **고치기 전 판으로 돌려 실패를 확인**하고 넣었다(F1·F3·F7·F8).

**미해결 F1~F12 를 코드로 재확인했다.**  11.25 가 "앞 세션 워크플로 결과를
근거로 쓰지 말라" 고 남긴 대로 항목마다 다시 읽었고, **F6 은 결함이 아니었다.**

| # | 판정 | 무엇을 했나 |
|---|---|---|
| F1 | 결함 | 작업 1-A 로 닫음 |
| F2 | 결함 | 취득 경로가 전원·과열을 한 번도 안 봤다 -> `parse.health_problems()`.  매뉴얼에서 **`POWER=n`(0~5)** 을 새로 찾았다 -- `POWERON` 이 성공 응답을 줘도 `POWER=3`(일부 모듈만 올라옴)일 수 있다 |
| F3 | 결함 | 종료가 저장 중인 프레임을 버렸다 -> `Sequencer.drain_writers()` + `[archon] shutdown_drain` |
| F4 | 결함 | `POWERON` 응답을 잃으면 `POWEROFF` 를 건너뛰었다 -> 확인된 상태(`powered`)와 시도(`power_attempted`)를 가름 |
| F5 | 미확정(실측 대기) | FETCH 상한을 `[archon] fetch_timeout` 으로 뺐고, `frame_timeout` 과 어긋나면 기동에서 알린다 |
| F6 | **결함 아님** | 아래 |
| F7 | 결함 | FITS 문자열 값의 `'` 를 안 겹쳤다 (표준 4.2.1) |
| F8 | 결함 | `STATUS` 실패 뒤 낡은 스냅샷을 실측값처럼 다시 실었다 |
| F9 | 결함 | `MODULE_TYPES` 에 13/14/15 결측 + **AD 판정이 `t == 2` 하나** |
| F10 | 이미 닫힘 | 2026-08-24 |
| F11 | 결함 | `repo_only` 표식으로 저장소/배치본을 가름 |
| F12 | 결함 | `sync_vendor` 가 `.py` 만 추적 -> 파생물만 빼고 전부 |

**F6 은 국면 불일치가 아니라 어휘의 한계였다.**  ERASE 실패가 `Failed to
initialize one or more ICs` 로 통보되는 것을 "국면이 안 맞는다" 고 적어 뒀는데,
**OBSAgent 가 알아듣는 ICS 오류 문구는 둘뿐이다**(3장) -- 그 둘 중에서는 ERASE
가 취득 개시 *전*의 준비 국면이므로 이쪽이 맞고, 새 문구를 지어내면 OBSAgent 가
못 알아듣는다.  즉 **고치면 규약을 깨는 자리**였다.  코드는 그대로 두고 그
근거를 주석으로 남겼다 -- 다음 사람이 같은 것을 결함으로 다시 올리지 않도록.

**F9 는 이름표가 아니라 판정이 문제였다.**  `MODULE_TYPES` 에 ADF/ADX/ADLN
(13/14/15)이 빠진 것은 표시상의 결함인데, 그보다 큰 것은 **AD 모듈 판정이
`t == 2` 하나**였다는 점이다.  그 셋 중 하나가 꽂힌 백플레인에서는
`tools/probe_archon.py` 1단계가 "AD 모듈을 못 찾았다" 를 내고, 그 화면이 실기
첫 실행에서 **가장 먼저 보는 것**이다 -- 슬롯 가정을 확인하라고 만든 탐침이
오경보로 진짜 문제를 덮는다.  매뉴얼 p.46 의 목록 전량을 넣고 판정을
`AD_TYPES` 로 바꿨다.

**F2 에서 막지 않기로 한 것.**  전원·과열 이상을 발견해도 **노출을 중단하지
않는다.**  이 필드들은 아직 실기 미검증(PROVISIONAL)이고, 오독 하나로 관측을
통째로 세우는 쪽이 더 나쁘다.  대신 크게 남기고, `probe_archon` 1단계가 같은
값을 눈으로 확인한다.  "보고하지 않는 필드는 이상으로 세지 않는다" 도 같은
이유다 -- 없는 필드를 이상으로 세면 첫 실행이 통째로 경보가 된다.

**검증.** `ics_sim` **330 통과**(325 -> 330) · `ics_archon` **110 통과**(98 ->
110) · 벤더 표류 없음.  배치본 기준은 `-m "not repo_only"` 로 **103 통과 / 실패
0** 이다(F11).

**시사점.**

- **지시를 좁히면 계약은 남는다.** "`ics_sim` 은 모사만" 으로 비용의 절반이
  사라졌지만 훅 자체는 못 줄였다 -- 발신 주체가 시퀀서이기 때문이다.  줄일 수
  있는 것과 없는 것을 가르는 기준은 "누가 그 일을 하는가" 였다.
- **회귀 시험은 고치기 전 판으로 돌려 봐야 회귀 시험이다.**  이번에 처음 쓴
  1-A 시험이 수정 없이 통과했고, 그대로 뒀으면 **아무것도 안 지키는 시험**이
  하나 늘 뻔했다.  11.20 의 "시뮬이 고정값을 돌려줘서 통과" 와 같은 계열이고,
  이번에는 그 원인이 **시험 자신의 설정**이었다.
- **미해결 목록은 재확인하고 쓰라던 경고가 옳았다.** 12건 중 1건(F6)이 결함이
  아니었고, 그것은 고쳤으면 **규약을 깨는** 자리였다.

### 11.27 사이트 판별을 OBSERVATORY 로 · 컨트롤러 대수를 ini 로 (2026-08-24)

운영자 지시 두 건을 함께 반영했다.  **둘 다 "설정 한 줄이 정본" 으로 옮기는
변경**이라 같이 묶었다.

**① 사이트는 `[node] observatory` 가 정한다 -- 호스트 IP 판정(D-015)은 폐지.**

종전 구조는 세 겹이었다: ini 의 `site` + `telid` 두 줄을 적고, `validate()` 가
정합을 검사하고, 그 위에서 **호스트 IP 판정이 ini 를 이겼다**.  D-015 는 "현장
장비가 잘못 배포된 ini 로 관측하는 것" 을 막으려는 것이었는데, 반대 위험을
안고 있었다 -- **NIC 이 내려가거나 낯선 대역에 붙으면 진짜 관측 자료가
`KMTT.…` 이름으로 저장된다.**  두 위험 중 어느 쪽을 택할지의 문제였고,
운영자가 **설정 쪽**을 택했다.

이제 `observatory`(`KASI`/`CTIO`/`SSO`/`SAAO`) 하나에서 `telid`(사이트 코드)와
`site`(`[site.<이름>]` 절 이름)가 **유도**된다.  그래서 파일명 `<SITE>` · 좌표 ·
`ORIGIN` · `INSTRUME`(`'<SITE> 18k CCD'`) 가 한 값에서 함께 따라오고, 두 줄이
어긋날 길 자체가 없어졌다.  **모르는 값은 기동을 거부한다** -- 종전
`normalize_site()` 처럼 조용히 테스트베드로 떨어뜨리지 않는다.  그 관대함이
위험한 이유는 관측소 자료가 벤치 이름으로 아카이브에 들어가도 **아무 오류가 안
나기** 때문이다.

검토 중에 어휘를 두 번 좁혔다.  처음에는 ini 값을 `KASI`/`CTIO`/`SSO`/`SAAO`
로 두려 했는데, `KMTT` 의 `OBSERVAT` 가 `TESTBED` 에서 `KASI` 로 바뀌면
**converter 의 `OBS_PREFIX` 에 `KASI` 가 없어 파일명 ↔ `OBSERVAT` 교차검증이
조용히 건너뛰어진다**(`obs_prefix=None` 이면 검사를 안 한다).  하드 실패가
나는 것이 아니라 **검사가 사라지는** 쪽이라 더 위험하다.  그래서 ini 어휘를
`CTIO`/`SSO`/`SAAO`/`TESTBED` 로 확정했다 -- **적은 값이 그대로 `OBSERVAT`
카드**가 되므로 규격·converter 와 어긋나는 자리가 **하나도 없다.**
(테스트베드의 `ORIGIN` 만 `KASI` 로 다른데, "이 파일이 생성된 곳" 이라 뜻이
다른 카드다.)

**② 컨트롤러 대수는 `[archon] n_controllers` 가 정한다.**

`1` 또는 `2` 만 받고 **그 밖은 기동을 거부**한다.  1대일 때 어느 쪽인지는
`[controllers] ctrl1_id`(→`MK`) / `ctrl2_id`(→`NT`) 의 **선언 여부**가 정하고,
둘 다 선언하면 거부한다 -- 정할 수 없는 상태로 진행하면 **엉뚱한 chip
이름으로 자료가 저장되고 파일만 봐서는 알 수 없다.**

종전에는 `active_tags()` 가 `[node] ccds` 만 보고 컨트롤러를 정했다.  그 주석에
"컨트롤러 목록을 따로 두면 두 설정이 어긋날 수 있다" 고 적혀 있었는데, 이제
명시적 대수가 생겼으므로 **교차검사**로 그 위험을 대신 막는다: `n_controllers=1`
인데 `ccds` 가 네 개면 기동에서 알린다.  그 조합이 위험한 이유는 시퀀서가 CCD
4개분 `Acquisition Complete.`/`Wrote` 를 내보내는데 파일은 한 컨트롤러분만
나오기 때문이다 -- **OBSAgent 는 4개를 다 받았으니 정상으로 보고, 없어진 파일은
아무도 알려주지 않는다.**

**③ 빠진 컨트롤러의 헤더 카드는 빼지 않는다 -- 값은 sentinel `NC`.**

카드를 빼면 pair 두 파일의 카드 수가 달라져 converter 와 견본 바이트 대사가
그것을 구조 변경으로 읽는다.  값 표기도 **새로 만들지 않았다** -- 처음에는
`none`("아예 없다")을 `NC`("못 읽었다")와 가르려 했는데, 규격 5.0절이 문자열
sentinel 을 `NC` 로 정해 두었으므로 이 셋만 다른 낱말을 쓰면 규격과 갈린다.

ini 에서 "없음" 은 **비워 두거나 `NC`** 다.  `NC` 는 헤더에 실릴 낱말과 같으므로
**적은 것이 그대로 카드가 된다** -- 표기가 하나여서 "어느 것이 맞나" 를 물을
일이 없다.  그래서 1대 운영을 두 방식으로 적을 수 있다: 한쪽만 적거나,
**2대 운영 ini 를 그대로 가져와 한 줄만 `NC` 로 바꾸거나.**
판정은 `ControllersCfg.is_absent()` 한 곳이 하고 대수 판정과 헤더가 같은 것을
쓴다 -- 두 자리가 갈리면 "ini 에 적었는데 한쪽만 반영" 이 된다.

**시사점.**

- **두 위험 중 하나를 고르는 판단이었다.**  D-015 는 틀린 설정을 막고, 이번
  변경은 틀린 판정을 막는다.  어느 쪽도 공짜가 아니므로 "무엇을 잃기로 했나" 를
  적어 두지 않으면 다음 사람이 되돌린다.
- ⚠️ **"시험이 초록" 과 "그 자리가 시험됐다" 는 다르다 -- 이번 작업에서 두 번
  겪었다.** ① 1-A 회귀 시험이 **수정 없이도 통과**했다(`exp 1` 의 IntMS=1000ms
  가 `frame_timeout=0.3` 보다 길어 MK 도 함께 죽었다 -- 결함이 아니라 시험
  설정 때문에 초록이었다).  ② `[node] observatory` 의 **데이터클래스 기본값**이
  어휘를 좁힌 뒤에도 `KASI` 로 남아 있었는데, 시험이 **전부 ini 를 읽어서**
  아무도 그 자리를 밟지 않았다 -- `SimConfig()` 를 바로 쓰는 코드는 기동에서
  죽는 상태였다.  둘 다 11.20/11.25 의 "상대역이 우리 가정대로 답해서 초록" 과
  같은 계열이고, 처방도 같다: **고치기 전 판으로 돌려 실패를 보고**, **기본값
  경로를 따로 밟는 시험**을 둔다 (`test_the_dataclass_default_is_itself_valid`).
- **어휘를 늘리면 그것을 읽는 바깥도 함께 늘어난다.**  `OBSERVAT` 에 `KASI` 를
  들이려던 순간 converter 의 표가 낡았고, 그 낡음이 **오류가 아니라 검사
  누락**으로 나타났을 것이다 -- 규격에 이미 있는 어휘(`TESTBED`·`NC`)를 그대로
  쓰기로 되돌리자 바깥을 고칠 일이 **하나도 남지 않았다.**  새 낱말을 만들기
  전에 "이것을 읽는 바깥이 몇 군데인가" 를 먼저 센다.

### 11.28 raw spec v1.5 반영 -- `main` 머지 + 전 계층 정합 (2026-08-26)

raw spec **v1.5** 가 5장(헤더 keyword) 검토 라운드를 마감하면서 값이 바뀌었다.
`main` 이 규격·견본·구판 `ics_sim` 에 먼저 반영했고(`13e02b2`),
`ics-archon-v1.0-build` 가 그것을 **머지해서** `observatory` 판별 구조 위에서
완결했다.  `13e02b2` 커밋 메시지가 충돌 해소 방침을 미리 적어 두었다 --
"해소는 `main` 값을 정본으로".

**바뀐 값** (근거는 `DECISION_LOG` D-017·D-018 과 raw spec v1.5 변경 이력):
사이트 코드 `KMTT`/`TESTBED` -> `KMTK`/`KASI` · 노출 번호 공간 `099999` ->
`999999` · HK 4장 폐지(`AIR_IN`/`AIR_OUT`/`GLYC_IN`/`GLYC_OUT`) · `CHMAP_*`
토큰 3자 -> 4자 `<chip><A|D><nn>` · `TELESCOP`/`FPAID` 사이트 유도(5.3.1절) ·
셔터 재질의 3초 -> 1초 · 견본 comment 오타 2건.

**머지에서 갈린 자리 -- 값은 `main`, 구조는 브랜치.**

지시는 "`main` 값을 정본으로" 였는데, `main` 의 `ics_sim` 은 **IP 판별 구판**이라
값과 구조가 섞여 들어온다.  넷을 갈랐다.

1. **`siteid.py` 는 삭제 유지.**  `main` 이 그 파일의 `BENCH_SITE` 를 고쳤으니
   머지는 modify/delete 로 물어 오는데, 되살리면 11.27 의 결정(D-015 폐지)이
   조용히 뒤집힌다.  값 반영이 구조 결정을 되돌리는 경로다.
2. **번호 공간 상수는 하나만.**  `main` 은 `state.EXPNUM_SPACE = 1_000_000` 을
   신설했는데 이 브랜치의 `state` 는 이미 `rawpair.NUM_SPACE` 를 쓰고 있었다 --
   받으면 같은 뜻의 상수가 둘이 된다.  값(1000000)만 `rawpair` 쪽에 넣었다.
   **사본을 늘리지 않는다** 는 이 폴더의 규약이 상수에도 적용된다.
3. **절 참조는 브랜치 것.**  `main` 주석의 `규격 5.1절`(ICSBUILD)은 구판 v1.2
   번호다.  v1.5 에서 그 카드는 5.5절이다.
4. **`FPAID` 는 여기서 처음 구현했다.**  `main` 은 5.3.1절을 문서에만 반영하고
   `rawhdr.FPAID = 'FPA#1'` 상수를 그대로 뒀다 -- 사이트를 바꿔도 FPA 번호가
   안 따라오는 상태였다.  `VERIFIED_SITES` 에 네 사이트분을 넣고 `fpaid_of()`
   를 세워 **모듈 상수를 없앴다**.  `[camera] fpaid` 오버라이드는 유지(현장이
   정본).

**직접 고친 결함 -- 카드가 줄자 labtest 헤더 조립이 통째로 거부됐다.**

값 카드가 135 -> 131 이 되면서 헤더가 140 레코드 = 11,200B 가 되는데 **2880 의
배수가 아니다.**  `ics_archon/archon/fitswrite.py::header_bytes` 는 `END` 뒤를
공백으로 채우고 있었고 주석이 그 이유를 예고해 두었다 -- "카드 수가 바뀌는
개정이 오면 여기서 조용히 흡수돼야 한다".  실제로 흡수됐다.  그런데 **labtest
스크립트의 `build_header` 는 패딩 없이 정렬 단정만** 두고 있어서 `AssertionError`
로 멈췄다.  같은 패딩을 넣었다.

교훈: **정렬 단정은 정렬을 만들지 않는다.**  단정은 "어긋났다" 를 알릴 뿐이고,
어긋남이 정상 개정에서 오는 자리라면 흡수하는 코드가 함께 있어야 한다.  두 사본
중 하나만 그렇게 되어 있었다는 것이 이번에 드러났다.

**규격 사본 셋 중 하나가 무방비였다.**

raw spec 5장의 기계 사본이 이 저장소에 셋이다 -- `ics_sim/rawcards.py` ·
`_vendor/ics_sim/rawcards.py` · labtest 내장 `RAWCARDS`.  앞의 둘은
`sync_vendor.py` + `test_vendor.py` 가 지키는데 **labtest 사본만 아무도 안
봤다.**  갈라져도 `ics_archon` 시험은 전부 초록이고, 실험실에서 찍은 파일만
카드 구성이 달라져 converter 가 **구조 변경**으로 읽는다 -- 발견 시점은 자료가
쌓인 뒤다.  `ics_archon/tests/test_labtest_spec_copy.py`(4항목)를 세워
`RAWCARDS`·`CHMAP`·`SITE_INFO`·번호 공간을 원천과 대조한다.  **표류를 한 자
주입해 실제로 잡히는 것을 확인했다** -- 새 시험이 헛도는지는 그렇게만 안다.

**11.27 의 판단 하나가 뒤집혔다 (기록으로 남긴다).**

11.27 은 `OBSERVAT` 에 `KASI` 를 들이려다 되돌리면서 이렇게 적었다 -- "규격에
이미 있는 어휘(`TESTBED`·`NC`)를 그대로 쓰기로 되돌리자 바깥을 고칠 일이
하나도 남지 않았다.  새 낱말을 만들기 전에 이것을 읽는 바깥이 몇 군데인가를
먼저 센다."

**D-017 이 그 낱말을 규격 층에서 채택했다.**  판단이 틀렸던 것은 아니다 --
그때는 ICS 혼자 어휘를 늘리는 일이었고 지금은 규격이 바꾼 것이라, 바깥을 고치는
비용이 **C-항목으로 등재돼 LEECU 소관이 됐다**(converter 파일명 정규식의 넷째
대안 · L0 MEF prefix `kmtt`->`kmtk`).  남는 교훈은 그대로다: 어휘를 늘리는
결정은 **규격 층에서** 내려야 하고, 그래야 바깥을 고치는 비용이 누구 몫인지가
함께 정해진다.

⚠️ **converter 가 아직 안 고쳐졌으면 KASI 자료는 짝 탐색에 안 걸린다** (D-017
영향 절).  실험실 산출물이 `KMTK.…` 로 나가기 시작하므로 그 전에 확인할 것.

**재검토 라운드에서 셋이 더 나왔다 (목 지시).**

1차 반영 뒤 v1.5 변경 이력 12항목을 코드와 하나씩 대조했다.

**① `Cn_TEMP` 가 자리 수부터 틀렸다.**  5.6.1절이 science **10자리**를
확정했는데 코드는 잠정 **5자리**(`BACKPLANE_TEMP`+`MOD5`~`MOD8`)였고, **견본
pair 의 `C1_TEMP` 는 처음부터 10개**였다 -- 잠정안이 견본과 갈려 있었는데
바이트 대사 시험이 그것을 못 잡았다.  대사가 **견본 값을 그대로 되먹이는**
경로라 `parse.telemetry_of()` 를 지나지 않기 때문이다.  견본 재현이 통과해도
**실기 경로가 같은 자리 수를 만든다는 보장은 아니다** -- 그 둘을 잇는 시험
(`test_cn_temp_slot_order_follows_spec_5_6_1`)을 새로 세웠다.

정본은 `rawhdr.TEMP_MODS` 에 두고 `parse` 가 참조한다.  자리 = 항목이라
순서가 하나만 밀려도 소비자가 **다른 모듈의 온도를 그 모듈 값으로** 읽는데,
값이 그럴듯해서 아무 경고도 안 뜬다.  `Mod6`·`Mod7` 은 자리를 차지하지
않으므로, 가짜 컨트롤러가 일부러 그 둘을 보고하게 두고 **배제되는 것**을
시험이 밟는다.

**② 5.7.1절 재질의 문턱을 밟는 시험이 하나도 없었다.**
`aux_requery_after_shopen` 은 지연이자 **문턱**인데(그 두 번째 뜻이 v1.5 에서
처음 명시됐다), 3.0->1.0 으로 내려도 아무 시험도 반응하지 않았다.
`tests/test_qdate_order.py`(8항목) -- 문턱 경계(`<=` 포함)·끄기·기본값·TC
무응답 폴백의 `UDATE` <= `QDATE`.  3.0 으로 되돌려 실패를 확인했다.

**③ `INSTALL.md` 와 코드가 서로 다른 값을 말하고 있었다.**  설치 문서는
`observatory = KASI` 로 두라고 적혀 있었는데 코드는 `TESTBED` 만 받았다 --
**문서대로 설치하면 기동이 거부되는** 상태였다.  D-017 이 문서 쪽으로
정리되면서 저절로 닫혔다.  배포 체크리스트도 폐지된 D-015 와 지워진
`siteid.py` 를 안내하고 있어 함께 고쳤다(`ACT-009` 포함).

교훈: **"견본을 바이트로 재현한다" 가 "실기 경로가 같은 것을 만든다" 는 아니다.**
두 경로가 만나는 자리를 따로 밟아야 한다 -- 11.20/11.25 의 "상대역이 우리
가정대로 답해서 초록" 과 같은 계열이다.

**④ `ics_archon.ini` 만 재질의 지연이 `3.0` 으로 남아 있었다.**  `ics_sim.ini`
는 고쳤는데 **실기가 읽는 ini** 를 빠뜨렸다 -- 코드 기본값만 맞고 운영값은
틀린, 가장 조용한 부류다.  배포 ini 두 벌을 규격값에 묶는 시험을 붙였다.

⚠️ **되돌림 시험이 `__pycache__` 를 오염시킬 수 있다** (이번에 겪었다).
기본값을 3.0 으로 되돌려 실패를 확인하고 곧바로 원복했는데, 같은 초 · 같은
크기라 `.pyc` 무효화 조건(mtime 초 + 크기)에 안 걸려 **낡은 바이트코드가
계속 쓰였다.**  그 뒤 전체 시험이 존재하지도 않는 값으로 한 건 실패했고, 원인을
찾는 데 시간이 들었다.  **되돌림 시험 뒤에는 `__pycache__` 를 지운다.**

**검증** -- `ics_sim` **322 통과**(종전 306) · `ics_archon` **146 통과**(종전
139, 배치본 모드 134) · 벤더 표류 없음 · labtest 하네스 **32항목 0실패**.
그리고 **견본 v1.5 pair 를 바이트 단위로 재현**한다(MK·NT, 불일치 0).
`main` 반영분의 "`pytest` 가 없어 시험 모음을 돌리지 못했다" 는 한계는
해소됐다 -- 이 환경에 `pytest` 를 넣고 전부 돌렸다.

⚠️ **벤치 설치본은 ini 를 고쳐야 기동한다** -- `[node] observatory = TESTBED`
는 이제 모르는 값이라 **기동을 거부**한다(조용히 떨어뜨리지 않기로 한 11.27 의
설계가 여기서 그대로 작동한다).  `KASI` 로 바꾸고 `[site.testbed]` 절도
`[site.kasi]` 로 고칠 것.

### 11.29 raw spec v1.6 -- 노출 정체성 카드를 `EXPID` 로 (2026-08-26)

운영자가 `FILENAME` comment 를 고치자는 데서 시작해 **정체성 카드 자체를
개정**하는 데까지 갔다.  규격·견본은 `main` 에서(커밋 `6d9c137`), 코드는 이
브랜치에서 처리했다 -- D-017 때 세운 방침 그대로다.

**무엇이 바뀌었나**

    ORIGNAME= 'KMTA.20260821.123450.MK' / Original filename assigned by ICS counter
        ↓
    EXPID   = 'KMTA.20260821.123450'    / Exposure identifier assigned by ICS counter

값에서 **컨트롤러 태그가 빠진 것**이 핵심이다.  그래서 pair 양쪽이 같은 값을
싣고, 5.9절 "반드시 상이" 가 **7장 -> 6장**이 되며, **짝을 잇는 단일 키**가
카드 추가 없이 생긴다 -- 폐지된 `PAIRFILE` 이 하려던 일이다.

함께 바뀐 것: `FILENAME` comment(`FITS file name as written to storage`) ·
견본 노출 번호 `012345`/`012340` -> `123456`/`123450`(+ **견본 파일 이름도**) ·
`Cn_*` 구분자 공백 -> **파이프** · comment `Ctr-n` -> `Ctrl-n` · 나열 결측
sentinel **`NC`** · 5.0절 **카드 폭 초과 규범** 신설.

**되살린 이름에 대한 판단**

`EXPID` 는 2026-08-12 에 **운영자가 직접 삭제한** 이름이다(D-013 · 구판 v1.2
2.3.1절).  그래서 되살리기 전에 당시 근거 셋을 하나씩 대조했다 -- 둘(중복
제거 · MEF 목적지 중복)은 `UNIQNAME`·`EXPNUM` 폐지로 이미 해소됐고, 이번엔
`ORIGNAME` 을 **대체**하므로 카드 수가 늘지 않는다.  남은 하나("이 저장소가
새로 만든 낱말")는 유효하지만 pair 단일 키 이득이 그것을 넘는다고 봤다.

⚠️ 당시 **실제 사고**가 있었다는 것이 더 중요했다 -- `EXPID='20260811.000001'`
이 실수 카드로 저장돼 zero-padding 이 파괴됐다(11.13.2).  지금 값은 `<SITE>`
접두로 시작해 **숫자로 읽힐 여지가 없어** 구조적으로 막힌다.  같은 이름을
되살리면서 같은 사고를 피한 것은 우연이 아니라 값 형식이 달라졌기 때문이다.

**구분자를 고르는 데 근거가 필요했다**

운영자가 `;` -> `/` 를 제안했을 때 실증으로 답했다: `/` 는 FITS 의 comment
구분자와 **같은 글자**라, 인용부호를 먼저 찾지 않는 파서에서 값이 첫 슬래시
에서 잘린다(`split('/')[0]` -> `'40.1`).  astropy 는 멀쩡하지만 하류가 어떻게
파싱할지는 우리가 정하지 못한다.  최종 선택 `|` 는 astropy 왕복도, `' / '`
절단도 값이 온전하다.

**폭 예산에서 규격의 빈틈이 드러났다**

`Cn_TEMP` 10자리를 폭 51에 담으면 **양수일 때만** 들어간다(49자).  음수 열
자리는 59자, 구 sentinel `-999.99` 열 자리는 **79자**로 넘친다.  운영자가
"80을 넘기면 comment 뒷부분을 자른다" 를 규범으로 정했고(5.0절 신설), 그것
만으로도 sentinel 전량은 못 담아서 **나열 카드의 결측 sentinel 을 `NC` 로**
갈랐다(29자).  ⚠️ 단일 HK 카드는 `-999.99` 그대로다 -- 두 sentinel 이 갈린
자리라 `test_labtest_spec_copy` 가 그것을 지킨다.

**코드에서 걸린 것 -- 저장 경로가 끊겼다**

`archon/backend.py` 의 `_frame_key()` 가 **`ORIGNAME` 카드로 프레임 표를
집고 있었다**(blocker B).  카드가 사라지자 표를 못 찾아 **두 번째 노출이
저장되지 않았고**, `test_d016_collision_check_is_on_even_when_write_fits_is_
false` 가 그것을 잡았다.  `EXPID` 로 바꾸니 파싱 규칙(`parts[1].parts[2]`)은
그대로 먹혔다 -- 태그가 없어져 오히려 pair 양쪽이 같은 키를 준다.

교훈: **카드 하나를 갈면 그 카드를 읽는 코드가 어디인지부터 세야 한다.**
헤더 카드는 산출물이면서 동시에 내부 배선이기도 하다.

**그 밖에 시험이 잡은 것 둘**

- `test_raw_header.py` 의 **폐지 카드 목록에 `EXPID` 가 있었다** -- D-013 이
  폐지했던 이름이라 당연히 거기 있었고, 되살렸으니 빼야 했다.  `EXPNUM` 은
  여전히 미도입이라 남긴다.
- `test_labtest_spec_copy`(11.28 에서 신설)가 **labtest 사본의 `FILENAME`
  comment 표류를 잡았다.**  브랜치를 `reset --hard` 로 되돌리는 과정에서 그
  한 줄이 딸려 돌아갔는데, 사람 눈으로는 못 봤을 자리다.  신설한 지 하루 만에
  값을 했다.

**검증** -- `ics_sim` **323 통과** · `ics_archon` **148 통과** · 벤더 표류 없음
· labtest 하네스 **32항목 0실패** · **견본 v1.6 pair 바이트 단위 재현**.

### 11.30 raw spec v1.6 전수 검사 -- 반영이 안 닿은 자리 넷 (2026-08-26)

11.29 로 v1.6 을 내린 **뒤에** 영향 범위를 처음부터 다시 셌다.  시험 471개가
전부 초록이었으므로 "다 됐다" 로 보이는 상태였는데, **넷이 남아 있었다.**  넷
다 시험이 없는 자리였다 -- 초록은 "확인했다" 가 아니라 "확인한 것만 통과했다"
다.

**(1) 규범을 고칠 때 사본을 하나 빠뜨렸다**

v1.6 이 5.0절에 **카드 폭 초과 규범**을 신설했다 -- 80자를 넘으면 comment 를
뒤에서 자르고 값은 자르지 않는다.  본편 `archon/fitswrite.card_image()` 는
그렇게 고쳐졌는데, **labtest 의 `fits_card()` 는 구 규칙 그대로였다** (값을
먼저 잘랐다).  같은 규격 조항의 구현이 저장소에 둘인데 한쪽만 움직인 것이다.

그러면 실험실 자료만 `Cn_*` 나열 카드의 **뒤 항목이 조용히 사라진다.**  자리가
곧 항목이라(5.6.1절) 읽는 쪽은 그 사실을 알 방법이 없고, 발견 시점은 자료가
쌓인 뒤다 -- `test_labtest_spec_copy` 가 막으려던 바로 그 부류인데, 그 파일이
**상수만 대조하고 동작은 안 봤다.**  이번에 동작 대조를 더했다.

> 옆에서 하나 더 나왔다 -- 값 안의 홑따옴표를 겹쳐 쓰는 방어(`O'Brien` ->
> `O''Brien`, FITS 표준 4.2.1)가 **본편에만 있고 labtest 사본에는 없었다.**
> 안 겹치면 그 자리가 값의 끝으로 읽혀 카드가 통째로 깨지는데 경고가 한 줄도
> 안 뜬다.  같이 옮겼다.

**(2) "자리는 비우지 않는다" 를 카드 전체가 빌 때 안 지켰다**

5.6.1절은 결측 자리를 `NC` 로 채우고 **자리를 건너뛰지 않는다**고 규정한다.
자리마다 결측일 때는 코드가 그렇게 하고 있었는데, **한 자리도 못 받았을 때**는
`'NC'` **한 토큰**을 냈다.  `rawhdr._join_readings()` 와 labtest 양쪽이 그랬다.

당시 근거는 "물어봤는데 다 결측" 과 "안 물어봤다" 를 헤더에서 가르자는 것이었다
-- 규격에 없는 구분이다.  그리고 대가가 크다: 5.6.1절이 **자리 수 자체를 모듈
구성 판별에 쓰라**고 하므로, 한 토큰짜리는 읽는 쪽에 **"모듈 한 장짜리
컨트롤러"** 로 보인다.  규격이 전 자리 결측(STATUS 무응답 · 미장착 모듈)을
"드물지 않다" 고 못박고 그 모습을 `'NC|NC|…'` **열 자리**로 보인 것이 이
때문이다.

⚠️ **우리 도구가 이미 그것을 규격 위반으로 짚고 있었다.**  `tools/probe_archon.py`
의 자리 표 대조가 `len(temps) != len(TEMP_MOD_LABELS)` 면 빨강을 낸다 -- STATUS
무응답이면 실기 첫 실행에서 그 빨강이 떴을 것이다.  **한 저장소 안에서 산출부와
검사부가 서로 다른 규격을 따르고 있었다.**

옆에서 하나 더: 목록 안에 `None` 이나 빈 문자열이 오면 `str(v)` 가 그대로 돌아
**`'None'` 이 자리에 실렸다.**  `parse.slot_value()` 가 이미 sentinel 로 채워
보내므로 실기에서는 안 왔겠지만, 나열 카드는 자리가 곧 항목이라 여기가 마지막
방어선이다.

**(3) 5.0절 둘째 문단이 `ics_sim` 쪽에 없었다**

규범의 첫 문단(comment 를 먼저 자른다)은 astropy 가 알아서 한다.  **둘째
문단은 아니다** -- 값만으로 68자를 넘으면 astropy 는 자르지 않고 `CONTINUE`
규약으로 **카드를 여러 장으로 늘린다.**  그 순간 견본이 못박은 **144 레코드 ·
11,520 바이트**가 깨지고, 경고는 한 줄도 안 뜬다.

`OBJECT`/`OBSERVER`/`PROJID` 는 **관측자가 치는 값**이라 길이가 바깥에서 온다
-- 규격이 정한 폭(18)을 넘겨 오는 것을 ICS 가 막을 방법이 없다.  실측으로
확인했다: `OBJECT` 에 100자를 먹이면 카드가 **세 장**이 됐다.  `fitsout` 에
`_fit_to_card()` 를 두어 규격대로 자르고 경고를 남긴다.

교훈은 11.29 의 것과 짝이다.  거기서는 "카드 하나를 갈면 그 카드를 **읽는**
코드를 세라" 였고, 여기서는 **"규범 하나를 세우면 그 규범을 구현하는 자리를
세라"** 다.  이 저장소에는 카드 이미지를 만드는 곳이 셋이다 --
`fitswrite.card_image()` · astropy(`fitsout`) · labtest `fits_card()`.

**(4) 동기화 도구가 초록이라고 말한 뒤에 시험이 빨갰다**

`tools/sync_vendor.py` 의 동기화 경로가 `read_manifest()` 의 **존재 여부**만
보고 "이미 동기 상태다" 로 빠져나갔다.  `--check` 는 매니페스트 **일치**까지
보는데 동기화 쪽만 안 봤다.

원천과 내장본을 **둘 다 손으로 같게 고치면**(개정 반영에서 흔한 일이고, 이번에
실제로 그랬다) 옮길 파일이 없어 그 경로를 탄다 -- 그때 매니페스트만 낡은 채로
남는다.  도구는 초록인데 `test_vendor.py` 2건이 빨갛고, **도구가 방금 "할 일
없다" 고 말한 뒤라 원인을 찾기 어려운 것이 요점이다.**  배포된 트리는 원천이
없어 매니페스트가 유일한 자가 확인 수단인데, 그것이 낡았다는 사실을 아무도
알려 주지 않는다.

두 경로가 같은 검사를 쓰게 하고, 파일이 이미 같으면 **매니페스트만 고치고**
나가게 했다.  회귀 시험을 `test_vendor.py` 에 남겼다.

**문서·주석 표류**

값이 아니라 설명이 낡은 자리를 함께 걷었다.  시험이 못 잡는 부류이고, 다음
사람이 읽는 것은 이쪽이다.

| 무엇 | 어디 |
|---|---|
| "pair 상이 **7장**" (v1.6 에서 6장) | `rawhdr.instrument_header` · `sequencer` · `ics_sim/README` · `test_raw_draft` 2곳 + **함수 이름** · `test_raw_header` 절 제목 + **함수 이름** · `test_backend` |
| 견본 파일 이름 `…012345…` (v1.6 에서 `123456`) | `rawcards` 머리말 · `test_raw_draft` 머리말 · labtest `RAWCARDS` 머리 주석 |
| 값 카드 **135** 장 (v1.5 에서 131) | `ics_sim/README` · `test_raw_header` · `README_labtest` · labtest ("144카드 = 4블록, 패딩 불필요" 도 함께 -- 실제로는 140 + 공백 4다) |
| 판 표기 v1.3/v1.4/v1.5 | `rawcards` 머리말 · `test_raw_draft`/`test_raw_header` 머리말 · labtest |
| `Cn_*` "공백 구분" | labtest `ctrl_telemetry_cards` · `test_raw_header` docstring |
| `Cn_TEMP` = "BACKPLANE + AD 모듈 온도" (v1.5 전 잠정 5자리의 잔재) | `README_labtest` |
| 폭 초과 시 "잘려서 실린다" (v1.6 에서 comment 가 먼저 준다) | `tools/probe_archon.py` · `ics_archon/README` |
| 줄바꿈이 깨져 문장이 두 동강 난 주석 | `emitter.py` (`충돌 사실은 … ≠ EXPID` / `값 비교로 남고`) |
| 시험 개수 | `ics_sim/README`(318) · `ics_archon/README` `repo_only` 표(13) |

**검증** -- `ics_sim` **329 통과**(신설 6) · `ics_archon` **152 통과**(신설 4,
배치본 모드 135 그대로) · 벤더 표류 없음 · 견본 v1.6 pair 바이트 단위 재현.

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
| **raw 헤더를 확정 초안 v0.3.5 에 동기화** | HK 블록은 완료(11.18). 남은 것: 노출·컨트롤러 블록 재편(`DARKTIME`/`TSHOPEN`/`TSHSHUT`/`NPHLINES`/`HEMODE`/`READMODE`/`CTR_CFG` 제거 · `CTRL1CFG`/`CTRL2CFG`/`TCSTIME` 신설 · `DATASRC` 값 체계) + **카드 comment 지원**(`fitsout._apply_header()`) | 높음 |
| ~~XIS 등록 방식 확정 (1안 vs 2안)~~ | **해결됨 (2026-08-04).** XIS 서버 소스로 테이블이 노드ID로만 키잉되고 주소 충돌 검사가 없음을 확인 → **1안 확정, 2안 불필요**(3.1.1) | 완료 |
| ~~`XIS>AL PING` 에 9개 PONG 응답~~ | **구현 완료 (2026-08-04)** — `cmd_ping()` 이 브로드캐스트면 9개 ID 전부로 PONG(3.1.1) | 완료 |
| **XIS `isis.ini` 에 시뮬 등록** | `UDPPort <sim_ip> <sim_port>` 한 줄 추가. ~~`MAXPRESET` 여유 확인 필요~~ → **선행 조건 해소 (2026-08-05).** 시험 벤치에서는 `127.0.0.1 6600` 한 줄로 **적용·검증 완료 (2026-08-11)**. **운영 허브 반영은 남아 있다** — 다만 xis.md 7절 경고대로 레거시 정지 또는 분리 인스턴스가 전제다 | 운영 측 |
| ~~**XIS 콘솔 `info` 로 `MaxPreset` 실측**~~ | **선행 조건에서 확인 절차로 격하 (2026-08-05).** 소스로 32 확정. 실물에서는 `VERSION`(2.9.1 인지) · `INFO`(`… of 32 max`) 로 판정만 재확인한다 | 중간 |
| ~~**`UDPPING` 으로 등록 선시험**~~ | **완료 (2026-08-11).** XIS 콘솔 `UDPPING 127.0.0.1 6600` 한 방에 9개 ID 전부가 PONG 했다 — XIS 재시작 후 재등록의 유일한 경로가 실물에서 확인됐다 | 완료 |
| ~~**자기 발신 에코 무시**~~ | **구현 완료 (2026-08-08, 3.1.2).** 점검에서 브로드캐스트 에코보다 심각한 **유니캐스트 루프백**(ERASE/SHOPEN 이중 실행)이 드러나(12.13) `_on_message` 초입 필터로 확대. 브로드캐스트 중복 억제·노드 ID 검증 포함, 테스트 15개 | 완료 |
| **`write_frame()` 실기 구현 (C-8)** | ics_archon 에서 실제 픽셀을 규격대로 저장. **계약 개정·파일 구성·이름·헤더는 2026-08-11 에 완료**(11.13, D-012) — 남은 것은 실물 크기(19200×9400) · `BITPIX=16`+`BZERO=32768`(3장) · 4장 픽셀 배치 · Archon 텔레메트리 카드(5.5·5.6절)다. 시뮬 백엔드가 참고 구현 | ics_archon |
| ~~**저장/통보 단위 분리 (C-16)**~~ | **완료 (2026-08-11, 11.13/D-012).** 물리 파일은 컨트롤러당 1개(`<SITE>.<날짜>.<번호>.<MK\|NT>.fits`), `Wrote` 는 CCD당 1회씩 4회를 논리 이름으로. 기존 규약 테스트 177개 무수정 통과 + 신규 20개(`test_raw_pair.py`) | 완료 |
| ~~**파일명 날짜 기준 확정 (raw_fits_spec OI-10)**~~ | **완료 (2026-08-13, 11.15/D-014).** 협의 결과 **사이트별 관측일**로 확정했다 — UT 에 사이트별 보정을 더한 뒤 날짜만 취하고, 경계는 세 사이트 모두 현지 12:30 이다. 잠정안(UT 날짜)의 결함은 SAAO 만이 아니라 **CTIO 에서도** 실재했다(현지 20시가 UT 자정). `rawpair.observing_date()` 로 옮기고 규격 2.3·9장을 함께 고쳤다. **OI-12 도 같은 변경으로 해소** | 완료 |
| **규격 대비 구현 구멍 16개 (ACT-011)** | converter 가 raw 에서 읽는데 `ics_sim` 이 안 쓰는 AUX 카드 16개 — 돔 10 · FSA 환경 4 · 영상 점검 2. 규격 5.10절은 "반드시 있어야 한다" 로 적고 있고, 지금은 카드가 없어 **MEF 에 빈 문자열이 조용히 들어간다**(11.17). sentinel 로 채울지 규격에서 뺄지 정해야 한다 | 중간 |
| ~~**sentinel 정렬 (C-9)**~~ | **완료 (2026-08-11).** `telemetry.fits_header_dict()` 를 분리해 정수 `-1`·실수 `-999.0`·문자열 `'NC'` 로. 메시지 계층의 `'0'` 채움(11.2)은 그대로 남긴다. `DATE-OBS` 는 결측 시 키를 넣지 않는다 | 완료 |
| ~~**EXPNUM 이 재실행마다 1 로 되돌아간다**~~ | **해결 (2026-08-11, 11.12).** 벤치에서 `FitsNum=00000000.000000` 으로 드러났다 — 번호가 겹쳐 파일명 fail-safe 가 `KMTN` 없는 이름을 쓰자 OBSAgent 파싱이 실패했다. 마지막으로 쓴 번호를 `[paths] expnum_file`(기본: 설정파일 옆)에 기록하고 기동 시 +1 부터 쓴다. 테스트 12개(`test_expnum_persist.py`) | 완료 |
| ~~**fail-safe 가 나면 검출기 식별이 복구 불가다**~~ (해결 2026-08-11 — 헤더에 `EXPID`/`CTRLTAG`/`CHIP1`/`CHIP2` 를 실어 개명과 무관하게 살아남게 했다. 규칙은 raw_fits_spec **2.3.1절** 신설) | 대체 이름 `<yymmdd>.<nnn>.fits` 에 검출기 식별이 없는데, **헤더에도 없다** — `telemetry.header_dict()` 는 AUX/TCS 필드 + sentinel + `TELID` + `DATE-OBS` 뿐이고 `DETECTOR`/`INSTRUME`/`CCDNAME`/`FILENAME`/`EXPID`/`CTRLTAG` 가 하나도 없다. 게다가 4개 CCD 가 `dict(header)` 로 **같은 헤더**를 받는다(`sequencer.py:285,289`). 즉 CCD 식별이 **파일명에만** 있었고, 이름이 바뀌면 파일만 보고는 되찾을 수 없다. 벤치에서 실제로 4개가 `260811.000`~`004` 로 흩어졌다(11.12 말미). **고치는 방향은 이미 규격에 있다** — `raw_fits_spec` README 가 *"아카이브·DTS 도구는 `LASTFILE` 대신 raw 헤더의 `FILENAME`/`EXPID`/`CTRLTAG` 를 근거로 삼아야 한다"* 고 정했다(D-010 의 부작용 절). 그 세 키워드가 헤더에 들어가면 대체 이름이 무엇이든 식별이 살아남고, raw pair 는 컨트롤러당 1파일이므로 `MK`/`NT` 태그도 함께 유지한다 | ics_archon |
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
- **`TCSAgent`·`OBSAgent` 보고서 12절 신설** — 현대 툴체인 재빌드(걸림돌 6종 + 실행으로 드러난 레거시 결함 2종)와 `~/AIC` 벤치 배치. **`build-local.sh` 두 개로 자동화**했다
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
