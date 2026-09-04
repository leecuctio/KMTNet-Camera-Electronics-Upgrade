#!/bin/sh
# kmt_cam_char 신규 분석 모듈 테스트 러너 (pytest 불필요 — 단독 assert 스크립트)
PY=${PY:-/opt/miniconda3/bin/python}
cd "$(dirname "$0")" || exit 1
fail=0
for t in test_*.py; do
  echo "== $t"
  "$PY" "$t" || { echo "** FAILED: $t"; fail=1; }
done
if [ $fail -eq 0 ]; then echo "ALL TESTS PASSED"; else echo "SOME TESTS FAILED"; fi
exit $fail
