# KMTNet-CEU Change Control

최종 갱신일: 2026-09-11

## 기준

- Software Freeze Date: 2026-09-15
- Freeze 이후 허용: bug fix, 현장 장애 대응 수정
- Freeze 이후 금지: 신규 기능 추가, architecture 변경, 검증되지 않은 설정 변경
- Change Approval: 이충욱 승인, 차상목/홍성욱 기술 검토
- Configuration Owner: 김동진

## Change Request Log

상태 값: `Proposed`, `Approved`, `Rejected`, `Applied`, `Rolled Back`

| CR ID | Date | Area | Description | Reason | Reviewer | Approver | Status | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CR-001 | 2026-07-02 | MEF converter (FITS generation) | `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` v2.1.1 → v2.1.2: header float 카드를 shortest round-trip 표기로 기록. 기존 `%.10G` 포맷이 `JD`를 10 유효숫자로 절삭해 `MJD-OBS`와 ~15–30 s 불일치 발생 (실제 CEU L0 제품에 영향) | L0 primary header 시각 keyword 정밀도 bug fix. mock 변환기 `kmt_ceu_legacy32_to_l0amp_mef_v2.py`의 `fits_value()`에 이미 적용·검증된 수정과 동일 | 차상목/홍성욱 (검토 예정) | 이충욱 | Applied | git revert로 v2.1.1 복원 |
| CR-002 | 2026-07-02 | MEF converter (FITS generation) | `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` v2.1.2 → v2.1.3: `PIX_SCALE` 0.400 → 0.395 arcsec/px (`PIXSCALE` 카드와 placeholder CD 행렬에 반영) | Gaia DR3 대비 astrometry 실측: 2026-06-30 프레임 16개 칩 해에서 plate scale 0.3952±0.00001″/px 확인 (기존 0.400 명목값은 1.3% 오차로 WCS 초기값 매칭 실패 유발) | 차상목/홍성욱 (검토 예정) | 이충욱 | Applied | git revert로 v2.1.2 복원 |
| CR-003 | 2026-09-11 | ICS/ICG (`ics_archon`, raw FITS header) | 돔 방위 세 카드(`DSTELAZ`·`DSAZ`·`DAZERR`)의 원천을 **돔 제어 프로그램의 redis**(`127.0.0.1:6379`)로 확정하고 ICS·ICG 취득 경로에 읽기를 넣었다. 키 TTL(수백 ms)이 지나 키가 없으면 카드는 sentinel `NC` — 옛 값을 이어 싣지 않는다 (D-021) | ⭐ TC 는 그 필드를 **아예 보내지 않는다**는 것이 레거시 원천으로 확인됐다(`TCSAgent` 트리에 `DSAZ`/`DSTELAZ` 0건) — 그 셋은 종전에 영구 `NC` 였다. raw spec 5.7절이 출처를 `TCS relay or REDIS` 로 이미 규정하고 있어 규격 밖 변경이 아니다.  ⭐ **설치 사이트에 redis 가 이미 구현돼 있다**(운영자 확인 2026-09-11) -- 새 의존을 들이는 것이 아니라 **이미 있는 것을 읽는 것**이다 | 차상목 (작성) · 홍성욱 (검토 예정) | 이충욱 | Applied | ini `[dome] source = off` 한 줄 (코드 기본값이라 되돌리면 종전 거동) |

- CR-003 검증: ⭐ **설치 사이트에 redis 가 이미 구현돼 있다** (운영자 확인 2026-09-11) — 그래서 Software Freeze(2026-09-15) 나흘 전이지만 **현장에 없는 것을 더하는 변경이 아니다**. 우리는 그 서버를 읽기만 한다(`MGET`). ⭐ 되돌리기는 ini 한 줄(`[dome] source = off`)이고, 서버가 내려가도 세 카드가 `NC` 로 나가며 **노출은 막지 않는다**. 실기 확인 절차는 `ics_archon/bench_test_plan.md` **1-C 단계**. ⛔ `ics_archon` 은 아직 `main`(site baseline)에 합류하지 않았으므로 이 행은 **합류 시점에 baseline 변경으로 다시 걸린다.**
- CR-001 검증: `KMTN.20260116.000001.MK/NT.fits` 샘플 재변환 후 `|(JD−2400000.5)−MJD-OBS| = 0 s` (기준 < 1e-4 s), astropy `verify('exception')` 통과 (HDU 69개). 종전 v2.1.1 산출물은 동일 검사에서 14.7 s 불일치.

## 기록 원칙

- Freeze 이전이라도 site baseline에 영향을 주는 변경은 기록한다.
- 현장 작업 중 적용한 임시 수정은 site report와 이 문서에 모두 남긴다.
- rollback이 불가능한 변경은 Gate Review에서 별도 위험으로 다룬다.

