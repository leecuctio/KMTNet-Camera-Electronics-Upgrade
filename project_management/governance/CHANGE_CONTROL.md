# KMTNet-CEU Change Control

최종 갱신일: 2026-07-02

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

- CR-001 검증: `KMTN.20260116.000001.MK/NT.fits` 샘플 재변환 후 `|(JD−2400000.5)−MJD-OBS| = 0 s` (기준 < 1e-4 s), astropy `verify('exception')` 통과 (HDU 69개). 종전 v2.1.1 산출물은 동일 검사에서 14.7 s 불일치.

## 기록 원칙

- Freeze 이전이라도 site baseline에 영향을 주는 변경은 기록한다.
- 현장 작업 중 적용한 임시 수정은 site report와 이 문서에 모두 남긴다.
- rollback이 불가능한 변경은 Gate Review에서 별도 위험으로 다룬다.

