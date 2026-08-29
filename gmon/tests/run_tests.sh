#!/bin/sh
# gmon v2 테스트 러너 — 각 test_*.py는 독립 실행 가능한 assert 스크립트 (pytest 불필요)
PY=${PY:-/opt/miniconda3/bin/python}
cd "$(dirname "$0")" || exit 1
fail=0
for t in test_*.py; do
  echo "== $t"
  "$PY" "$t" || { echo "** FAILED: $t"; fail=1; }
done
if [ $fail -eq 0 ]; then echo "ALL TESTS PASSED"; else echo "SOME TESTS FAILED"; fi
exit $fail
