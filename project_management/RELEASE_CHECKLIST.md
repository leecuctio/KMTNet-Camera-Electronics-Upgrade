# KMTNet-CEU Release Checklist

최종 갱신일: 2026-06-22

## 1. 릴리스 전 기준 확인

- [ ] Release 대상 converter 파일을 확정했다.
- [ ] `SOFTWARE_VERSION`, `PRODUCT_VERSION`, `GEOMETRY_VERSION` 값을 확인했다.
- [ ] `CREATOR`, `PRODVER`, `PIPEVER`, `GEOMVER` keyword가 의도한 버전과 일치한다.
- [ ] ICD 기준 문서가 명확하다.
- [ ] README, work summary, keyword 문서의 버전 정보가 서로 일치한다.
- [ ] 대용량 raw/generated FITS 파일은 release ZIP 포함 대상에서 제외했다.

## 2. 샘플 변환

기준 command:

```bash
python3 kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  KMTN.20260116.000001.MK.fits \
  -o kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits \
  -f --gzip
```

확인 항목:

- [ ] MK input만 지정해도 NT counterpart를 찾는다.
- [ ] Output `.fits`가 생성된다.
- [ ] Output `.fits.summary.txt`가 생성된다.
- [ ] `--gzip` 사용 시 `.fits.gz`가 생성된다.
- [ ] `.fits.gz.sha256.txt`가 생성된다.

## 3. FITS 구조 검증

- [ ] Astropy FITS verification이 통과한다.
- [ ] HDU count가 69이다.
- [ ] 첫 HDU가 `PRIMARY`이다.
- [ ] Amp image HDU가 64개이다.
- [ ] Extension 순서가 M, K, N, T 순서이다.
- [ ] 각 chip 내 순서가 `01T..08T`, `01B..08B`이다.
- [ ] 마지막 binary tables가 `AMPINFO`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY` 순서이다.

## 4. 대표 값 검증

- [ ] `M01T` shape가 `(4616, 1200)`이다.
- [ ] `AMPINFO` row count가 64이다.
- [ ] `XTALKINFO` row count가 4096이다.
- [ ] `VOLTINFO` row count가 9이다.
- [ ] `TELEMETRY` row count가 2이다.
- [ ] `RAWNAX1=19200`, `RAWNAX2=9400`이다.
- [ ] `RAWXTILE=1200`, `AMPDATA=1152`, `OVERSCNX=48`, `MIDOVSCY=168`이다.
- [ ] `CHIPFLP=None`이다.
- [ ] Placeholder calibration 상태가 문서에 명시되어 있다.

## 5. 압축 및 checksum

- [ ] `gzip -t`가 통과한다.
- [ ] `.fits.gz.sha256.txt`의 checksum이 실제 파일과 일치한다.
- [ ] Release ZIP checksum을 생성했다.

## 6. Release package 구성

필수 포함:

- [ ] Converter script
- [ ] README
- [ ] Work summary
- [ ] ICD 문서
- [ ] 실행 예제 shell script
- [ ] Checksums

제외:

- [ ] Raw FITS sample pair
- [ ] Generated large `.fits`
- [ ] Generated large `.fits.gz`
- [ ] `__pycache__`
- [ ] 임시/빈 테스트 파일

## 7. 릴리스 후 기록

- [ ] `BACKLOG.md`의 완료 항목을 갱신했다.
- [ ] Product 또는 geometry 정책 변경이 있으면 `DECISION_LOG.md`를 갱신했다.
- [ ] Release ZIP 파일명과 checksum을 README 또는 work summary에 기록했다.
- [ ] 다음 P0/P1 작업을 명확히 남겼다.

