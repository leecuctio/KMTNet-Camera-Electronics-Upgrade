# KMTNet-CEU Calibration Tracker

최종 갱신일: 2026-06-22

## L0 MEF Placeholder 해소 항목

| 항목 | 현재 상태 | 필요 조치 | Owner | Target | 완료 조건 |
| --- | --- | --- | --- | --- | --- |
| `GAIN` | Placeholder | Amp별 gain 측정 | 김재우 | Rehearsal | Header/table에 실측값 반영 |
| `RDNOISE` | Placeholder | Amp별 read noise 측정 | 김재우 | Rehearsal | Header/table에 실측값 반영 |
| `SATURAT` | Placeholder | Saturation level 측정 | 김재우 | Rehearsal | 운영 기준값 확정 |
| `LINMAX` | Placeholder | Linearity limit 측정 | 김재우 | Rehearsal | 운영 기준값 확정 |
| `XTALKINFO` | Placeholder | 64 x 64 crosstalk coefficient 측정 | 김재우 | Rehearsal/Site | `XTALKCAL=True`, `XTALKVER` 유효 |
| `VOLTINFO` | Placeholder | Bias/clock voltage telemetry 연결 | 차상목, 김동진 | Site | 운영 telemetry 반영 |
| `TELEMETRY` | Placeholder | Archon controller status/readout telemetry 연결 | 차상목, 김동진 | Site | 운영 telemetry 반영 |
| `READDIR` | Placeholder | flat/star sequence test | 김재우, 차상목 | Rehearsal/Site | TOP/BOT read direction 확정 |

