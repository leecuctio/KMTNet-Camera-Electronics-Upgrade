# Archon 실험실 영상획득 스크립트 v2.0

최종 갱신일: 2026-07-25 | 상태: 시뮬레이터 검증 완료, **실 하드웨어 미검증**

## 1. 개요

`archon_kmtnet_labtest_v2.py`는 STA Archon 컨트롤러로 실험실 특성 측정
데이터셋(xTalk / Dark / iFlat / GxT)을 자동 취득하는 스크립트로,
`archon_kmtnet_labtest_v1.0.{smallbuf,bigbuf}.py`의 전면 재작성판이다.
운영 검증된 타 프로젝트 Archon 소프트웨어를 조사해 장점을 이식하고,
v1.0 분석에서 확인된 문제를 수정했다.

**조사 대상 프로젝트**

| 프로젝트 | 성격 |
| --- | --- |
| [sdss/archon](https://github.com/sdss/archon) | SDSS-V(LVM 등) 운영 라이브러리. asyncio 기반, 상태머신·타임아웃 체계 |
| [mplesser/azcam](https://github.com/mplesser/azcam) | Steward Observatory 범용 영상획득 프레임워크(Archon 백엔드) |
| [karpov-sv/ccdlab](https://github.com/karpov-sv/ccdlab) | FZU CCD 시험실 소프트웨어. Archon 하드웨어 시뮬레이터 보유 |

의존성은 v1.0과 동일하게 **Python 3.8+ 표준 라이브러리 + NumPy**뿐이다
(실험실 Windows PC 배포를 고려해 astropy를 요구하지 않는다).

## 2. 파일 구성

| 파일 | 내용 |
| --- | --- |
| `archon_kmtnet_labtest_v2.py` | 획득 스크립트 본체 (프로토콜 클라이언트 + 노출/데이터셋 로직 + CLI) |
| `campaign_example.ini` | 캠페인 설정 예제 (유닛/저장소/ACF/실행 목록) |
| `archon_simulator.py` | Archon 프로토콜 시뮬레이터 (무하드웨어 테스트용) |
| `test_archon_labtest_v2.py` | unittest — 시뮬레이터 대상 end-to-end 포함 10건 |
| `archon_kmtnet_labtest_v1.0.*.py` | 구판 (이력 보존, 실측 캠페인 기록 포함) |

## 3. v1.0 → v2.0 개선 사항 매핑

### 3.1 신뢰성 (통신·시퀀스)

| # | v1.0 문제 | v2.0 구현 | 출처 |
| --- | --- | --- | --- |
| 1 | `?xx` 오류 응답을 "Invalid packet header"로만 처리 → 원인 진단 불가 | `ArchonCommandError`로 구분, 거부된 명령 원문을 예외/로그에 포함 (`ArchonClient._check_reply`) | sdss |
| 2 | 수천 줄 WCONFIG 업로드 중 응답 유실 → 맹목적 재접속 재시도 | 업로드·검증 전 `POLLOFF`, 완료 후 `POLLON` (`LabArchon._upload_config`) | sdss |
| 3 | 업로드 "성공"이 실제 반영을 보장하지 않음 | `RCONFIG` 전량 되읽기 diff 검증 (`_verify_config`, 기본 활성) | azcam |
| 4 | FETCH 전 `LOCK` 이 디버그 중 주석 처리됨 | `LOCKn` → FETCH → `LOCK0` (finally 보장, `_fetch_locked`) | sdss·azcam |
| 5 | POWERON 후 12초 sleep뿐, 급전 상태 미확인 | `STATUS`의 `POWER=ON`+`POWERGOOD=1` 폴링 게이트 (`power_on`) | sdss·azcam |
| 6 | 리드아웃 대기에 타임아웃 없음(행업 시 무한 대기) | `IntMS + readout_timeout` 데드라인, 초과 시 FRAME 덤프와 함께 실패 (`_wait_frame`) | sdss |
| 7 | 재시도 카운터 불일치(`range(30)` vs 탈출 4회) | 단일 `acf_retries` 옵션으로 일원화 | — |
| 8 | Ctrl-C 시 CCD 바이어스 켜진 채 방치 | `finally`/`KeyboardInterrupt`에서 `POWEROFF` 보장 (`run_campaign`) | azcam(abort) |

### 3.2 데이터 품질

| # | v1.0 문제 | v2.0 구현 | 출처 |
| --- | --- | --- | --- |
| 9 | 노출 개시 시점 불확정(LOADPARAMS) → `SWSET_EXPWAIT` 수동 튜닝 | `HOLDTIMING` → `FASTPREPPARAM IntMS/Exposures` → `RELEASETIMING` (`expose`; `use_fast_params=false`로 v1 방식 폴백 가능) | sdss |
| 10 | DATE-OBS가 호스트 시각, 실측 노출시간 없음 | 트리거 상승/하강 에지 타임스탬프(10 ns tick)로 `EXPMEAS` 산출, `EXPTIME`(요청)과 분리 기록 | azcam |
| 11 | NAXIS1/2 = 19200×9400 하드코딩 → ACF 기하 불일치 시 깨진 FITS | FRAME 상태의 `BUFnWIDTH/HEIGHT`로 동적 설정 (`write_fits`) | sdss·azcam |
| 12 | FITS 데이터부 2880바이트 패딩 누락(표준 비준수) | 헤더·데이터 모두 2880 블록 패딩 | — |
| 13 | 헤더 메타데이터 빈약 | `EXPMEAS/IMAGETYP/FRAMENO/BUFNO/UNITID/DATASET/FILENUM/ACFFILE/BCKTEMP`(백플레인 온도) 등 추가 | sdss(텔레메트리) |
| 14 | 진행 표시가 벽시계 점 찍기 | `WBUF`의 `BUFnLINES/HEIGHT`로 실제 리드아웃 진행률 표시 | azcam |
| 15 | IntMS 20비트 한계(1,048,574 ms) 무검증 | 범위 검증 후 명확한 오류 (분할 노출은 §6 향후 과제) | azcam |
| 16 | 32비트 샘플모드 프레임을 u16으로 잘못 기록할 수 있음 | `BUFnSAMPLE=1`이면 명시적 오류 | — |

### 3.3 운영·유지보수

| # | v1.0 문제 | v2.0 구현 | 출처 |
| --- | --- | --- | --- |
| 17 | 유닛 ID/IP/실행 데이터셋/저장 드라이브가 소스 편집 사항 | 캠페인 INI 파일 + CLI (`campaign_example.ini`, `--run`, `--dry-run`) | — |
| 18 | 죽은 Twilio SMS 스텁 | 범용 웹훅 알림(`[notify] webhook`), 실패해도 획득 계속 | — |
| 19 | print 기반 출력만 존재 | `logging`(콘솔+`--log-file`), 알림 메시지도 로그에 남음 | — |
| 20 | 하드웨어 없이 검증 불가 | 프로토콜 시뮬레이터 + unittest 10건(end-to-end 포함) | ccdlab |
| 21 | smallbuf/bigbuf 두 파일 분기 | `BUFnBASE` 기반 FETCH 단일화(bigbuf 방식이 양쪽 호환) | v1.0 bigbuf |

데이터셋 정의(노출시간 사다리, 프레임 수, 기준/다크 인터리브 순서)와 파일
번호 체계 `[UnitID][TestSetup][DatasetType][FrameSN]`, 파일명
`<PREFIX>.<YYYYMMDD>.<FILENUM>.fits`는 **v1.0과 동일**하게 유지했다
(테스트가 xTalk 21 / Dark 63 / iFlat 116 / GxT 15 프레임을 고정 검증).

## 4. 사용법

```bash
# ① 캠페인 파일 작성 (예제 복사 후 수정)
cp campaign_example.ini u23_202604.ini

# ② 계획 확인 (하드웨어 불필요)
python3 archon_kmtnet_labtest_v2.py u23_202604.ini --dry-run

# ③ 획득 (전체 또는 특정 run만)
python3 archon_kmtnet_labtest_v2.py u23_202604.ini --log-file logs/u23.log
python3 archon_kmtnet_labtest_v2.py u23_202604.ini --run u23_fast_xtalk

# ④ 무하드웨어 테스트
python3 -m unittest test_archon_labtest_v2 -v
python3 archon_simulator.py 4242   # 독립 시뮬레이터 (수동 시험용)
```

캠페인 파일의 `[run:NAME]` 섹션이 v1.0 메인 스크립트의 `GetDataset()` 호출
한 줄에 대응한다. `dataset_id`의 마지막 자리가 데이터셋 종류를 결정한다
(1=xTalk, 2=Dark, 3/4=iFlat, 5=GxT — v1.0 규약 그대로).

## 5. 실 하드웨어 투입 전 확인 사항

시뮬레이터는 프로토콜 규약을 모사할 뿐이므로, 실제 컨트롤러에서 아래를
먼저 확인해야 한다. 확인 결과에 따라 `[options]`로 대응한다.

1. **`FASTPREPPARAM` 지원 여부** — 구형 펌웨어가 거부하면
   `use_fast_params = false`로 v1.0 호환 `LOADPARAMS` 경로 사용.
2. **`BUFnRETIMESTAMP`/`FETIMESTAMP` 의미** — 트리거 상승/하강 에지로
   가정했다(Archon 매뉴얼 대조 필요). 값이 0이면 `EXPMEAS=-1`로 기록될 뿐
   획득은 계속된다.
3. **타임스탬프 진법** — FRAME의 `*TIMESTAMP` 필드를 16진수로 파싱한다
   (sdss/archon과 동일). 실 응답과 대조할 것.
4. **`POLLOFF`/`RCONFIG` 동작** — 문제 시 `verify_acf = false`로 우회 가능.
5. **첫 프레임 육안 확인** — 기하·바이어스 레벨·오버스캔이 v1.0 산출물과
   일치하는지 기존 `kmt_cam_char/qc.py`로 교차 확인 권장.

## 6. 향후 과제

- **장노출 분할**: IntMS 20비트 한계 초과 시 azcam처럼 `NoIntMS`+배수
  분할로 확장 (현재는 명확한 오류로 차단).
- **32비트 샘플모드**: 필요 시 BITPIX 32 FITS 기록 추가.
- **sdss-archon 채택 검토**: 통신 계층을 `pip install sdss-archon`으로
  대체하고 KMTNet 데이터셋 로직만 유지하는 방안. asyncio 학습 비용과
  실험실 PC 배포 환경을 고려해 보류 중.
- **셔터 폐쇄 플러시 시퀀스**: v1.0의 `bWaitFlush`/`bFullFlush` 옵션은 실측
  캠페인에서 모두 False로 사용되어 v2.0에서 제거했다. ACF의 연속 플러시로
  불충분하면 재도입.

## 7. 버전 이력

| 버전 | 일자 | 내용 |
| --- | --- | --- |
| v0.9.1.gxtalk | 2025-04-18 | 가이드 xTalk 데이터셋 추가 (SMC) |
| v1.0 smallbuf | 2025-04-18 | 고정 주소 FETCH 판 (SMC) |
| v1.0 bigbuf | 2025-04-18 | `BUFnBASE` 기반 FETCH 판 (SMC) — U13/U23 실측 캠페인 사용 |
| **v2.0.0** | 2026-07-25 | 타 프로젝트 조사 기반 전면 재작성: 오류 응답 구분, POLLOFF/ON, ACF 검증, LOCK 복원, POWERGOOD 게이트, HOLDTIMING/RELEASETIMING, 실측 노출시간, 동적 FITS 기하+패딩, 캠페인 INI/CLI, 웹훅 알림, 시뮬레이터+테스트 |

## 8. 관련 자료

- v1.0 분석 및 타 프로젝트 조사: 본 문서 §3 표와
  [`../README.md`](../README.md)(cam_char 개요) 참고
- [sdss/archon](https://github.com/sdss/archon) ·
  [sdss-archon 문서](https://sdss-archon.readthedocs.io/en/latest/) ·
  [mplesser/azcam](https://github.com/mplesser/azcam) ·
  [karpov-sv/ccdlab](https://github.com/karpov-sv/ccdlab) ·
  [STA Archon](http://www.sta-inc.net/archon/)
