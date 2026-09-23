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
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  raw/science/archon+header/KMTK.20260915.000034.MK.fits \
  -o kmtk.20260915.000034.ceu.l0amp.mef.fits \
  -f --gzip
# D-011(2026-08-10) 이전에 만든 샘플 raw(KMTN.*)를 쓸 때는 pair 양쪽을
# 사이트 코드 이름(KMTC/KMTS/KMTA/KMTK — 샘플의 OBSERVAT 기준)으로 개명해서 쓴다.
```

확인 항목:

- [ ] MK input만 지정해도 NT counterpart를 찾는다.
- [ ] Output `.fits`가 생성된다.
- [ ] Output `.fits.summary.txt`가 생성된다.
- [ ] Output `.fits.hdu_verify.txt`가 생성된다 (v2.2.0 신설 — 구조 검증 결과를
      산출물에서 읽어 적는다. §3·§4 점검의 상당 부분이 여기 이미 들어 있다).
- [ ] `--gzip` 사용 시 `.fits.gz`가 생성된다.
- [ ] `.fits.gz.sha256.txt`가 생성된다.

## 3. FITS 구조 검증

- [ ] Astropy FITS verification이 통과한다.
- [ ] `fitsverify`가 0 error로 통과한다. ⚠️ Astropy 쪽만으로는 부족하다 —
      v2.4.0까지 문자열 값이 free format이라 `XTENSION= 'IMAGE'`가 고정형식
      규칙을 어겼는데 Astropy는 통과시켰고 `fitsverify`는 129 error로 거부했다
      (D-023). 두 검사는 겹치지 않는다.
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
- [ ] `VOLTINFO` row count가 37이다 (CCD bias/clock placeholder 9 +
      컨트롤러 레일 실측 28 = `C1`/`C2` × 7 rail × 전압·전류). ⚠️ 이 값은
      고정이 아니다 — 레일·컨트롤러 구성이 바뀌면 달라지므로 `VOLTINFO`
      헤더의 `NVOLT`와 실제 row count가 일치하는지로 점검한다 (C-18, D-023).
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

- [ ] `planning/BACKLOG.md`의 완료 항목을 갱신했다.
- [ ] Product 또는 geometry 정책 변경이 있으면 `governance/DECISION_LOG.md`를 갱신했다.
- [ ] Release ZIP 파일명과 checksum을 README 또는 work summary에 기록했다.
- [ ] 다음 P0/P1 작업을 명확히 남겼다.
