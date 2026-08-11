# SMC_CLAUDE.md

`OBSAgent/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md) 참고.

## 이 폴더가 다루는 것: OBS Agent (레거시 관측 제어 프로그램)

**OBS Agent**(실행파일 `obstool` / `obstart`, ICIMACS 노드명 **`OBS`**)는 관측자가 실제로 앞에 앉아 쓰는 **명령줄 관측 프로그램 + 스크립트 자동관측 엔진**이다. 카메라(ICS)와 망원경(TCS Agent) 양쪽을 하나의 콘솔에서 제어하며, `.osc` 관측 스크립트를 읽어 야간 관측을 자동 수행한다. KMTNet의 실질적 end-user 관측 소프트웨어.

**현재 상태 (2026-07-29 기준)**
- 이 폴더의 자료(공식 매뉴얼 초안, 개발자 레퍼런스 3종, v1.2.0 소스, 실제 운영 스크립트, **공식 릴리스노트 v1.1.3, 사이트별 ini, csh 래퍼, READMEold까지**)를 **검토 완료**하고 분석 보고서로 정리해 둠.
- **핵심 산출물**: [obsagent_report.md](obsagent_report.md) — 시스템 내 위치, 전체 명령어 레퍼런스, `.osc` 스크립트 문법, 노출 상태머신, 상태 파일 포맷, 버전 이력, 신규 구현 시 고려사항. **이 소프트웨어를 파악할 때는 원본 PDF/소스를 다시 파기 전에 이 보고서부터 읽을 것.**
- 분석 대상 버전: **v1.2.0** (`OBSAgent.latest/KMTObs/obstool.h`의 `APP_VER` 기준)

## 핵심 사실 요약 (자세한 근거는 보고서 참고)

- **계보**: 독자 개발이 아니라 **TCSAgent v1.6.1 코드베이스를 재사용해 2017년에 시작**됐다. 이후 2024년까지 독립적으로 크게 확장되어 지금은 TCSAgent보다 훨씬 큰 프로그램이 됐다. `copt` 포인팅 보정, `offset_blg()` 등은 TCSAgent와 공유한다. 물증: `KMTObs/READMEold`가 옛 TCSAgent README 원본 그대로다.
- **운영 배치**: **Science server(ICSci)**에서 실행(`obstool`/`obstart`), 관측 전 실행·관측 후 종료. 실체는 `/home/kasi/OBSAgent/KMTObs/obstool` + `ini/obstool.ini`. TCSAgent는 반대로 Guide server(ICGui)에서 상시 실행 — 두 WARNING("PC-TCS disconnected"+"AUX Ctrl. disconnected") 동시 출력 시 TCSAgent부터 재시작.
- **통신 경로 3종**:
  - ICIMACS 쪽 ← **UDP/IMPv2** → `ICS`(카메라) 및 `TC`(TCS Agent). ICS·TCS Agent의 명령어를 사실상 전부 감싸서 제공한다.
  - 돔 회전/조명/거울셀 팬 ← **HTTP(Web Relay, ezCurl)** → ICS/TCS Agent를 거치지 않는 독자 경로
  - 돔 상태 등 ← **Redis**(2023년 이후 도입된 "newTCS" 상태 서버)
- **자체 상태머신 보유**: ICS가 뿌리는 원시 텍스트 메시지(`EXPSTATUS=...`, `Shutter=Open`, `PCTREAD=...`, `Wrote ...`)를 실시간 파싱해 `CamStatus`(15단계)와 `ExpStatus`를 유지한다. 스크립트 엔진은 ICS 원시 메시지가 아니라 **이 상태만 보고** 다음 행동을 결정한다.
  - 제약: `EXP`/`OBJECT`/`PROJID` 등 설정 명령은 `CamStatus == READY`일 때만, `GO`는 `IDLE_3`/`READY`일 때만 유효.
- **GMON과의 관계(정확한 표현)**: GMON은 UDP로 OBS 노드에 `sysstatus`를 초당 질의하고 `GetSysStatus()` 문자열을 응답받는다. `/data/Logs/ObsStatus.txt`(5초마다 덮어씀)는 같은 정보의 파일 채널일 뿐이다. (ics_legacy 보고서에서 정체 불명이던 GMON 채널을 이어붙인 지점)
- **`.osc` 스크립트**: 한 줄 = 명령 1개(`+`로 시작) 또는 노출 1장(10개 컬럼: `LABEL RA DEC COPT IMGTYP OBJECT FILTER EXPTIME UTOBS UTTOL`). `+ostart <줄번호>`로 구간 반복 루프를 만든다 — 실측 로그에서 본 BLG 필드 반복 관측이 이 메커니즘의 산물.

## 폴더 구성과 자료 상태

| 항목 | 내용 | 검토 |
|---|---|---|
| `KMTNet 스크립트 관측 방법 (Rev.0.1).pdf` | 공식 매뉴얼(관측자용) | 완료 — 단 **"Rev.0.1 초안"**이라 곳곳에 "자세한 설명 필요" 메모가 남은 미완성 문서 |
| `OBSAgent.latest/Commands.v1.0.txt` | 최신 전체 명령어 목록 | 완료 — 매뉴얼보다 최신·완전(돔/릴레이/Redis/유틸 계열 포함) |
| `OBSAgent.latest/Functions.v1.0.txt` | 소스 함수/선언 목록 | 완료 |
| `OBSAgent.latest/Ref.ObsStatus.txt` | 상태 파일 포맷 상세 정의 | 완료 |
| `OBSAgent.latest/UpdateNotes.v1.1.txt` | v0.0.5~v1.2.0(예정) 버전 이력 | 완료 — 이 프로그램 이해에 가장 유용한 단일 문서 |
| `OBSAgent.latest/KMTObs/` | v1.2.0 소스 + `ini`/`csh`/`osc` | 완료(구조 파악 수준) |
| `OBSAgent.latest/KMTObs/osc/` | **실제 운영에 쓰인 관측 스크립트 다수** (BLG 서베이, SN, NEO, 돔플랫, 공학점검 `eng/`, 사이트확장 `site.23.10/`) | 대표 예시만 검토 — **신규 구현의 회귀 테스트 자산으로 가치 높음** |
| `OBSAgent.latest/ISISclient/` | ISIS 클라이언트 라이브러리 (TCSAgent 쪽과 동일 파일 확인) | [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 7절에서 분석 완료 |
| `OBSAgent.latest/hiredis/` | Redis C 클라이언트 (newTCS 연동용, v0.9.3부터) | 외부 오픈소스, 미검토 |
| `OBSAgent_release_note_v1.1.3_R240718.pdf` | v1.1.3 공식 릴리스 노트(한국어) | **검토 완료(2026-07-29)** — 보고서 8.1절에 요약. UpdateNotes와 중복이 아니라 **운영 배경 정보의 보고**(서버 배치, MPNARFcp 좌표보정 차이, Redis SHUTTER 정의, 돔 모니터링 복구 절차, dtchk 상세). `.docx`는 동일 내용이라 미검토 |
| `CCD status (20220826.emaitoSET).pdf` | CCD 상태 문서 | **`ics_legacy/`에서 이 폴더로 이동해온 파일**(2026-07-28). 미검토, OBSAgent 분석과 직접 관련은 낮음 |

**git 상태**: 커밋되어 있다 — **169 파일 추적 중**(2026-08-11 확인). *"아직 커밋되지 않았다"* 던 2026-07-29 자 서술은 낡은 것이라 정정했다. `*.zip`(배포본), `test.*`(테스트 ini/osc — 특히 `osc/` 안의 `test.*.osc` 몇 개), `hiredis` 의 `.o`/`.a`/`.so`(자체 `.gitignore`)는 제외된다. **hiredis 는 소스만 있으므로 clone 한 머신에서 직접 빌드해야 한다.**

## 재빌드와 실행 (2026-08-11 실측)

**[`build-local.sh`](build-local.sh)** 한 줄이면 된다. 저장소를 건드리지 않고 `~/AICS` 아래 작업 사본에서 빌드하고 설정까지 만든다.

```bash
./build-local.sh --site kmtna
~/AICS/build/OBSAgent/KMTObs/obstool ~/AICS/Config/obstool.ini
```

Ubuntu 24.04 / g++ 13.3.0 에서 빌드해 **신규 `ics`(ics_sim)를 실제 XIS 허브 너머로 몰았다** — `status`/`kstatus` 왕복, DARK 노출 사이클 전 구간이 경고 없이 통과했다. 상세는 [obsagent_report.md](obsagent_report.md) **12절**.

걸림돌은 TCSAgent 와 대부분 공유한다(코드베이스를 복사해 출발했으니 **결함도 같은 줄에 그대로 있다**). OBSAgent 고유는 셋:

1. **hiredis 를 직접, 그것도 정적으로** — `all:` 타겟이 `.so` 만 만드는데 `-lhiredis` 는 그걸 우선 잡아서 **빌드는 되고 실행이 안 되는 바이너리**가 나온다. `make static` + `.a` 경로 직접 링크.
2. **`libcurl4-openssl-dev` 추가 필요** (v1.0.0 부터 `-lcurl`). TCSAgent 에는 없다.
3. **하드코딩 경로 다섯 곳** (`obstool.h:158-162`) — 로그 넷과 `ObsStatus.txt`. ini 로는 못 고친다.

> `DEFAULT_OBSSTAT`(`ObsStatus.txt`)을 쓰기 가능한 경로로 옮겨 두면 **`CamStatus`/`ExpStatus`/`FitsSaved` 를 5초마다 실시간으로 볼 수 있어** 연동 시험에서 아주 유용하다 — `watch -n 1 cat ~/AICS/Logs/ObsStatus.txt`.
>
> ⚠️ 포트 **6650** 은 `ics_sim/tools/xis_probe.py` 도 쓴다. `obstool` 기동 전에 프로브를 끌 것.

## 신규 Python 시스템에서 OBSAgent의 위치 (2026-07-29 확정)

- 신규 카메라 SW는 `ics`(과학: ICS+IC×4+CB×4 통합)와 `icg`(가이드: ICG+G.IC+G.CB 통합) 두 프로그램으로 분리 개발한다.
- **OBSAgent는 개정하지 않기로 확정됐다.** 대신 신규 `ics`가 **기존과 동일한 메시지를 그대로 발신**해서(특히 CCD별 "Acquisition Complete." 4회) OBSAgent의 `CamStatus` 상태머신이 무개정으로 동작하게 한다.
- 따라서 이 폴더의 [obsagent_report.md](obsagent_report.md) **6절 "상태 전이의 정확한 규약"**이 사실상 **신규 `ics`가 지켜야 할 인터페이스 규격서**가 된다. 소스(`commands.c` 748~865행) 실측 기반이며, 신규 개발 측 정리는 [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 8.0.1절에 있다.
- 그 과정에서 발견한 **문서-소스 불일치**: 릴리스노트와 `obstool.h` 주석은 `READY`를 "Disk Write Complete on all ICs"로 설명하지만 소스에 그 파서가 없다. 실제로는 `IDLE_3` 후 ~12.2초 타이머로만 전이된다(6절 참고).
- OBSAgent를 나중에 개편하게 된다면 최우선 후보: `IDLE_1`/`IDLE_2`의 "4개 IC" 전제 제거, `READY` 12초 지연 단축, 원시 문자열 파싱 → 구조화 이벤트 전환.

## 관련 문서 (같은 시스템의 다른 조각)

- [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) — **ICS**(카메라 통합제어) + IMPv2.5 프로토콜 + ISIS/XIS 허브. 이 프로그램이 `OBS>ICS ...`로 보내는 명령의 수신측.
- [../TCSAgent/tcsagent_report.md](../TCSAgent/tcsagent_report.md) — **TCS Agent**(망원경). 이 프로그램의 코드 조상이자, `OBS>TC ...` 명령의 수신측.

## ▶ 다음 세션에서 바로 할 일 — 신규 ICS 연동 시험 계속

`obstool` 이 **SSO AIC 리눅스(`kmtnet-sso`)에 빌드돼 떠 있고**, 실제 XIS 허브 너머로 신규 `ics`(ics_sim)를 몰아 DARK 사이클을 통과시킨 상태다. 여기서 이어간다:

| 순서 | 할 일 | 판정 |
|---|---|---|
| **1** | **`ExpNum` 교정 재확인** — 노출 2회 돌려 두 번째 진행 중 `ee` | `ExpNum` 이 그 노출의 파일 번호와 같은가, 끝난 뒤 `ExpNum`==`FitsNum` 인가. 지난번 `000001` vs `000002` 로 어긋났던 자리 |
| **2** | **`GO n` 다중 노출** | `Image k of n complete. EXPSTATUS=IDLE` 경로(§6.1 d)와 프레임 겹침에서 `Wrote` 카운트가 유지되는가 |
| **3** | **`.osc` 스크립트 관측** | 명령마다 응답을 판정하는 경로(§6.1 e). `osc/` 의 실사용 스크립트를 회귀 자산으로 쓸 수 있다 |
| **4** | **결함 주입 6종** (`ics_sim --inject`) | **이 프로그램의 경보·`opause` 경로를 확인하는 유일한 수단.** 정상 경로만 통과시킨 지금은 `acq_short`(획득완료 3회 → `opause`) · `wrote_drop`(`FitsSaved` 안 섬) 같은 분기가 실제로 도는지 모른다 |

**상태를 실시간으로 보려면** `watch -n 1 cat ~/AICS/Logs/ObsStatus.txt` (§7 의 그 파일, 5초 주기 갱신).

벤치 구성은 [`../ics_sim/SMC_CLAUDE.md`](../ics_sim/SMC_CLAUDE.md) "이어서 시작하는 자리", 빌드는 [`build-local.sh`](build-local.sh).

## 다음에 이어서 할 만한 일

- 매뉴얼(Rev.0.1)이 미완성이므로, **NST(비항성추적) / UTOBS·UTTOL(시각지정 관측) / `copt` 포인팅 보정** 세 기능은 소스 수준에서 재확인 후 정식 스펙으로 문서화 필요 — 셋 다 실운영 핵심 기능인데 문서화가 가장 부실하다. (NST의 하부 수단 후보는 PC-TCS의 `BIASRA`/`BIASDEC` 레이트 명령 — [../TCSAgent/tcsagent_report.md](../TCSAgent/tcsagent_report.md) 9.2절 참고)
- `osc/` 폴더의 실제 스크립트들을 정리해 신규 시스템의 호환성 테스트 케이스로 만들기
- v1.2.0 "reserved" 항목(모터/창문/HVAC 제어) 미구현 상태 확인 — 신규 시스템 요구사항인지 판단 필요
- 신규 Python 구현 착수 시: 보고서 11절(신규 구현 고려사항) 참고. 릴리스노트 기반 8.1절(MPNARFcp 우회책, Redis SHUTTER, 자가 비활성화 로직)은 "신규 시스템에서 불필요해질 레거시 우회책" 목록으로도 유용
