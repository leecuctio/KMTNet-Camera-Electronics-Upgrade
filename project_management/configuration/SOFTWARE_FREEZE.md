# KMTNet-CEU Software Freeze

최종 갱신일: 2026-06-22

Freeze date: 2026-09-15

## Freeze 전에 끝나야 하는 항목

- [ ] Bias acquisition
- [ ] Dark acquisition
- [ ] FITS generation
- [ ] Legacy software control path
- [ ] Archon interface configuration
- [ ] 관측 스크립트 기본 동작
- [ ] data transfer path
- [ ] rollback 가능한 baseline 생성

## Freeze 이후 허용 변경

- 현장 장애 대응 bug fix
- configuration typo 수정
- 검증된 driver/script compatibility fix
- site-specific network value 입력

## Freeze 이후 금지 변경

- 신규 기능 추가
- architecture 변경
- 검증되지 않은 timing/configuration 변경
- science data format을 바꾸는 변경

