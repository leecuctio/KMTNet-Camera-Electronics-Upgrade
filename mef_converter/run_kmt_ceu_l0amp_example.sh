#!/usr/bin/env bash
set -euo pipefail

# This script lives in mef_converter/. Resolve its own directory and the repo
# root so it works regardless of the current working directory.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Sample MK/NT raw inputs and the output live at the repo root; override via $1/$2.
INPUT="${1:-$ROOT/KMTN.20260116.000001.MK.fits}"
OUTPUT="${2:-$ROOT/kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits}"

python3 "$HERE/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py" \
  "$INPUT" \
  -o "$OUTPUT" \
  -f --gzip
