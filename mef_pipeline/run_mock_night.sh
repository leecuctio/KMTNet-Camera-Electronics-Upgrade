#!/bin/bash
# Process the mock 2026-06-30 night (40 mock64 L0 exposures) end to end:
# master bias (5 BIAS) -> master flats (V, I; 3 each) -> BPM -> 28 OBJECT
# frames to L1 -> QA summary.
#
# Usage: bash mef_pipeline/run_mock_night.sh [DATA_DIR] [OUT_DIR]
#   DATA_DIR: directory containing kmtc.20260630.NNNNNN.ceu.l0amp.mock64.mef.fits
#             (default: current directory)
#   OUT_DIR : output root for caldb/, qa/ and L1 files (default: DATA_DIR/mef_pipeline_out)
set -euo pipefail

DATA=${1:-$(pwd)}
OUT=${2:-$DATA/mef_pipeline_out}
PIPE_DIR="$(cd "$(dirname "$0")" && pwd)"
PP="python3 $PIPE_DIR/kmt_preproc.py"

l0() { echo "$DATA/kmtc.20260630.0$1.ceu.l0amp.mock64.mef.fits"; }

BIAS=(); for n in $(seq 11092 11096); do BIAS+=("$(l0 $n)"); done
FLATV=(); for n in $(seq 11097 11099); do FLATV+=("$(l0 $n)"); done
FLATI=(); for n in $(seq 11100 11102); do FLATI+=("$(l0 $n)"); done
OBJ=(); for n in $(seq 11103 11130); do OBJ+=("$(l0 $n)"); done

echo "== master bias (${#BIAS[@]} frames)"
$PP calib-bias "${BIAS[@]}" -d "$OUT"

echo "== master flat V (${#FLATV[@]} frames)"
$PP calib-flat "${FLATV[@]}" -d "$OUT"

echo "== master flat I (${#FLATI[@]} frames)"
$PP calib-flat "${FLATI[@]}" -d "$OUT"

echo "== bad pixel mask (from I-band flat)"
$PP bpm --flat "$OUT/caldb/master_flat_I.fits" -d "$OUT"

echo "== pass 1: science frames without catalog (approximate WCS, WCSSOLVE=F)"
# --mask-file so the bootstrap catalog uses the same masked star detection
# (saturated blooming excluded) as the pass-2 astrometry
$PP run "${OBJ[@]}" -d "$OUT" -f --mask-file

echo "== bootstrap reference catalog from all pass-1 L1s (covers every field)"
L1S=(); for n in $(seq 11103 11130); do L1S+=("$OUT/kmtc.20260630.0$n.ceu.l1ccd.mef.fits"); done
$PP make-refcat "${L1S[@]}" -o "$OUT/caldb/refcat_night.fits" -d "$OUT"

echo "== pass 2: science frames with astrometry"
$PP run "${OBJ[@]}" -d "$OUT" -f --refcat "$OUT/caldb/refcat_night.fits"

echo "== QA summary"
$PP qa-summary -d "$OUT"
