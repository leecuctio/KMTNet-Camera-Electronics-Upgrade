"""Command-line interface.

    kmt_preproc.py calib-bias  bias1.fits ...      -d OUTROOT
    kmt_preproc.py calib-flat  flat1.fits ...      -d OUTROOT [--bias PATH]
    kmt_preproc.py bpm         [--flat PATH]       -d OUTROOT
    kmt_preproc.py run         object1.fits ...    -d OUTROOT [-f] [--no-flat ...]
    kmt_preproc.py qa-summary                      -d OUTROOT [-o OUT.md]

OUTROOT holds the calibration DB (OUTROOT/caldb), L1 products (OUTROOT) and
QA records (OUTROOT/qa)."""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from astropy.io import fits

from . import VERSION
from .calib.bpm import build_bpm
from .calib.caldb import CalDB
from .calib.masters import build_master_bias, build_master_flat
from .pipeline import PipelineConfig, process_exposure
from .qa.report import batch_summary, write_qa


def _add_common(p):
    p.add_argument("-d", "--outroot", default="l1_out",
                   help="output root (caldb/, qa/, L1 files)")


def _config_from(args) -> PipelineConfig:
    cfg = PipelineConfig()
    if getattr(args, "overscan_cols", None):
        cfg.overscan_cols = args.overscan_cols
    if getattr(args, "no_bias", False):
        cfg.do_bias = False
    if getattr(args, "no_flat", False):
        cfg.do_flat = False
    if getattr(args, "no_bpm", False):
        cfg.do_bpm = False
    if getattr(args, "with_var", False):
        cfg.with_var = True
    ampmatch = getattr(args, "ampmatch", None)
    if ampmatch:
        cfg.ampmatch = {"mult": "multiplicative", "add": "additive"}.get(ampmatch, ampmatch)
    if getattr(args, "amps", None) is not None:
        cfg.expected_amps = args.amps or None
    if getattr(args, "no_strict", False):
        cfg.strict = False
    if getattr(args, "no_sha256", False):
        cfg.compute_sha256 = False
    return cfg


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="kmt_preproc",
        description=f"KMT-CEU L0->L1 preprocessing pipeline {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("calib-bias", help="build master bias from L0 bias frames")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output", default=None, help="output master bias path")
    _add_common(p)

    p = sub.add_parser("calib-flat", help="build master flat from L0 flat frames")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--bias", default="auto",
                   help="master bias path, 'auto' (caldb), or 'none'")
    p.add_argument("-o", "--output", default=None)
    _add_common(p)

    p = sub.add_parser("bpm", help="build bad pixel mask from a master flat")
    p.add_argument("--flat", default="auto", help="master flat path or 'auto'")
    p.add_argument("--low", type=float, default=0.5)
    p.add_argument("--high", type=float, default=2.0)
    p.add_argument("-o", "--output", default=None)
    _add_common(p)

    p = sub.add_parser("run", help="process L0 science exposures to L1")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-f", "--force", action="store_true", help="overwrite existing L1")
    p.add_argument("--no-bias", action="store_true")
    p.add_argument("--no-flat", action="store_true")
    p.add_argument("--no-bpm", action="store_true")
    p.add_argument("--with-var", action="store_true",
                   help="also write VAR planes (omitted by default; reconstructible)")
    p.add_argument("--ampmatch", choices=["auto", "mult", "add", "off"], default="auto",
                   help="amp-boundary harmonization mode (default auto)")
    p.add_argument("--no-strict", action="store_true",
                   help="continue despite L0 validation issues")
    p.add_argument("--no-sha256", action="store_true",
                   help="skip input SHA256 provenance (faster)")
    p.add_argument("--overscan-cols", type=int, default=None,
                   help="override number of BIASSEC columns used in the fit")
    p.add_argument("--amps", type=int, default=64,
                   help="expected amp count (0 disables the check)")
    _add_common(p)

    p = sub.add_parser("qa-summary", help="aggregate QA JSON records to markdown")
    p.add_argument("-o", "--output", default=None)
    _add_common(p)

    args = parser.parse_args(argv)
    outroot = Path(args.outroot)
    outroot.mkdir(parents=True, exist_ok=True)
    caldb = CalDB(outroot / "caldb")

    if args.command == "calib-bias":
        out = Path(args.output) if args.output else outroot / "caldb" / "master_bias.fits"
        res = build_master_bias(args.inputs, out, caldb, PipelineConfig())
        for w in res["warnings"]:
            print(f"WARNING: {w}", file=sys.stderr)
        print(f"{out}  CALVER={res['calver']}  n={len(args.inputs)}")
        return 0

    if args.command == "calib-flat":
        bias_path = None
        if args.bias == "auto":
            rec = caldb.find("MBIAS")
            bias_path = rec["path"] if rec else None
            if bias_path is None:
                print("WARNING: no master bias in caldb; flats built without bias",
                      file=sys.stderr)
        elif args.bias.lower() != "none":
            bias_path = args.bias
        if args.output:
            out = Path(args.output)
        else:
            filt = str(fits.getheader(args.inputs[0], 0).get("FILTER", "X")).strip() or "X"
            out = outroot / "caldb" / f"master_flat_{filt}.fits"
        res = build_master_flat(args.inputs, out, caldb, PipelineConfig(),
                                bias_path=bias_path)
        for w in res["warnings"]:
            print(f"WARNING: {w}", file=sys.stderr)
        print(f"{out}  CALVER={res['calver']}  filter={res['filter']}")
        return 0

    if args.command == "bpm":
        if args.flat == "auto":
            rec = caldb.find("MFLAT")
            if rec is None:
                print("ERROR: no master flat in caldb", file=sys.stderr)
                return 1
            flat_path = rec["path"]
        else:
            flat_path = args.flat
        out = Path(args.output) if args.output else outroot / "caldb" / "bpm.fits"
        res = build_bpm(flat_path, out, caldb, low=args.low, high=args.high)
        total = sum(res["n_bad"].values())
        print(f"{out}  CALVER={res['calver']}  n_bad_total={total}")
        return 0

    if args.command == "run":
        cfg = _config_from(args)
        failed = []
        for inp in args.inputs:
            try:
                qa = process_exposure(inp, caldb, outroot, cfg, force=args.force)
                write_qa(qa, outroot / "qa")
                seam = max((c["seam_max_abs_e"] for c in qa["ccds"].values()), default=0.0)
                print(f"{qa['l1_file']}  {qa['imagetyp']:>6} {qa['filter']:>2} "
                      f"{qa['exptime']:5.0f}s  max|seam|={seam:6.2f} e-  "
                      f"{qa['runtime_s']:.0f}s")
            except Exception as err:
                failed.append((inp, err))
                print(f"FAILED: {inp}: {err}", file=sys.stderr)
                traceback.print_exc()
        if failed:
            print(f"{len(failed)}/{len(args.inputs)} exposures failed", file=sys.stderr)
            return 1
        return 0

    if args.command == "qa-summary":
        out = batch_summary(outroot / "qa", args.output)
        print(out)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
