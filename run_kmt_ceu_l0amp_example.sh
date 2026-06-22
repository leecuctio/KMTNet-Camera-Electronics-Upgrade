#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-KMTN.20260116.000001.MK.fits}"
OUTPUT="${2:-kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits}"

python3 kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  "$INPUT" \
  -o "$OUTPUT" \
  -f --gzip
