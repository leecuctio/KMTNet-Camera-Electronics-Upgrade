#!/usr/bin/env bash
set -euo pipefail

# This script lives in mef_converter/. Resolve its own directory and the repo
# root so it works regardless of the current working directory.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Verification sample that actually exists in the tree; override via $1/$2.
# The old default (raw/KMTA.20260116.000001.MK.fits) used a pre-D-011 prefix
# and was not present, so this script could not run as shipped.
INPUT="${1:-$ROOT/raw/science/archon+header/KMTK.20260915.000034.MK.fits}"
# Leave $2 empty to let the converter derive the name from the filename site
# code (KMTK -> kmtk), cross-checked against OBSERVAT (D-011, D-017).
OUTPUT="${2:-}"

if [ -n "$OUTPUT" ]; then
  python3 "$HERE/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py" \
    "$INPUT" -o "$OUTPUT" -f --gzip
else
  python3 "$HERE/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py" \
    "$INPUT" -d "$ROOT" -f --gzip
fi
