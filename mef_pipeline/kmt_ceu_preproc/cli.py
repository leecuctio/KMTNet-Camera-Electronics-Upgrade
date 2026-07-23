"""Command-line interface.

    kmt_preproc.py calib-bias   bias1.fits ...      -d OUTROOT
    kmt_preproc.py calib-flat   flat1.fits ...      -d OUTROOT [--bias PATH]
    kmt_preproc.py calib-fringe object1.fits ...    -d OUTROOT [--bias/--flat PATH]
    kmt_preproc.py calib-illum  object1.fits ...    -d OUTROOT [--bias/--flat PATH]
    kmt_preproc.py bpm          [--flat PATH]       -d OUTROOT
    kmt_preproc.py run          object1.fits ...    -d OUTROOT [-f] [--no-flat ...]
    kmt_preproc.py qa-summary                       -d OUTROOT [-o OUT.md]

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
from .calib.masters import (build_master_bias, build_master_flat,
                            build_master_fringe, build_master_illum)
from .pipeline import PipelineConfig, process_exposure
from .qa.report import batch_summary, write_qa


def _add_common(p):
    p.add_argument("-d", "--outroot", default="mef_pipeline_out",
                   help="output root (caldb/, qa/, L1 files)")


def _config_from(args) -> PipelineConfig:
    cfg = PipelineConfig()
    if getattr(args, "overscan_cols", None):
        cfg.overscan_cols = args.overscan_cols
    if getattr(args, "no_bias", False):
        cfg.do_bias = False
    if getattr(args, "no_flat", False):
        cfg.do_flat = False
    if getattr(args, "no_fringe", False):
        cfg.do_fringe = False
    if getattr(args, "no_illum", False):
        cfg.do_illum = False
    if getattr(args, "no_bpm", False):
        cfg.do_bpm = False
    if getattr(args, "cr", None):
        cfg.cr_mode = args.cr
    if getattr(args, "cr_sigma", None):
        cfg.cr_sigma = args.cr_sigma
    if getattr(args, "sky", None):
        cfg.sky_mode = args.sky
    if getattr(args, "no_zp", False):
        cfg.do_zp = False
    if getattr(args, "with_var", False):
        cfg.with_var = True
    ampmatch = getattr(args, "ampmatch", None)
    if ampmatch:
        cfg.ampmatch = {"mult": "multiplicative", "add": "additive"}.get(ampmatch, ampmatch)
    if getattr(args, "mask_file", False):
        cfg.with_mask_file = True
    if getattr(args, "refcat", None):
        cfg.refcat = args.refcat
    if getattr(args, "gaia_local", None):
        cfg.gaia_local = args.gaia_local
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

    p = sub.add_parser("calib-fringe",
                       help="build a master fringe pattern from flat-fielded "
                            "science frames of different pointings (one filter)")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--bias", default="auto",
                   help="master bias path, 'auto' (caldb), or 'none'")
    p.add_argument("--flat", default="auto",
                   help="master flat path, 'auto' (caldb), or 'none'")
    p.add_argument("-o", "--output", default=None)
    _add_common(p)

    p = sub.add_parser("calib-illum",
                       help="build a dark-sky illumination correction from "
                            "flat-fielded science frames of different pointings")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--bias", default="auto",
                   help="master bias path, 'auto' (caldb), or 'none'")
    p.add_argument("--flat", default="auto",
                   help="master flat path, 'auto' (caldb), or 'none'")
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
    p.add_argument("--no-fringe", action="store_true",
                   help="skip fringe subtraction even when a master exists")
    p.add_argument("--no-illum", action="store_true",
                   help="skip illumination correction even when a master exists")
    p.add_argument("--no-bpm", action="store_true")
    p.add_argument("--cr", choices=["flag", "off"], default="flag",
                   help="cosmic-ray flagging into MASK bit 64 (default flag; "
                        "pixel values are never modified)")
    p.add_argument("--cr-sigma", type=float, default=None,
                   help="CR detection significance (default 6.0)")
    p.add_argument("--sky", choices=["measure", "sub", "off"], default="measure",
                   help="sky model: measure keywords only (default), "
                        "sub also subtracts, off disables")
    p.add_argument("--no-zp", action="store_true",
                   help="skip the approximate Gaia-G photometric zero point")
    p.add_argument("--with-var", action="store_true",
                   help="also write VAR planes (omitted by default; reconstructible)")
    p.add_argument("--ampmatch", choices=["auto", "mult", "add", "off"], default="auto",
                   help="amp-boundary harmonization mode (default auto)")
    p.add_argument("--mask-file", action="store_true",
                   help="also write MASK planes to a separate .mask.mef.fits")
    p.add_argument("--refcat", default=None,
                   help="astrometric reference catalog (FITS RA/DEC table); "
                        "without it WCSSOLVE=F is flagged")
    p.add_argument("--gaia-local", default=None,
                   help="local Gaia store directory (gaia-ingest); the "
                        "reference cone is resolved per exposure from the "
                        "pointing keywords - no network needed")
    p.add_argument("--no-strict", action="store_true",
                   help="continue despite L0 validation issues")
    p.add_argument("--no-sha256", action="store_true",
                   help="skip input SHA256 provenance (faster)")
    p.add_argument("--overscan-cols", type=int, default=None,
                   help="override number of BIASSEC columns used in the fit")
    p.add_argument("--amps", type=int, default=64,
                   help="expected amp count (0 disables the check)")
    _add_common(p)

    p = sub.add_parser("gaia-ingest",
                       help="build/extend a local Gaia store from FITS refcats "
                            "or ESA gaia_source csv(.gz) files")
    p.add_argument("inputs", nargs="+", help="refcat FITS or gaia_source csv(.gz)")
    p.add_argument("--store", required=True, help="local Gaia store directory")
    p.add_argument("--gmax", type=float, default=None,
                   help="magnitude cut applied while ingesting csv files")
    _add_common(p)

    p = sub.add_parser("fetch-gaia",
                       help="download a Gaia DR3 reference catalog cone (VizieR; network)")
    p.add_argument("--like", default=None,
                   help="FITS file whose primary RA/DEC keywords set the cone center")
    p.add_argument("--ra", type=float, default=None, help="cone center RA [deg]")
    p.add_argument("--dec", type=float, default=None, help="cone center DEC [deg]")
    p.add_argument("--radius", type=float, default=100.0,
                   help="cone radius [arcmin] (mosaic diagonal ~96')")
    p.add_argument("--gmax", type=float, default=19.0, help="Gmag limit")
    p.add_argument("-o", "--output", default=None)
    _add_common(p)

    p = sub.add_parser("make-refcat",
                       help="extract an astrometric reference catalog from L1 file(s)")
    p.add_argument("l1file", nargs="+")
    p.add_argument("-o", "--output", default=None, help="output catalog FITS path")
    p.add_argument("--nmax", type=int, default=200, help="max stars per chip")
    p.add_argument("--sigma", type=float, default=5.0, help="detection threshold [sigma]")
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

    if args.command in ("calib-fringe", "calib-illum"):
        def resolve(kind, value):
            if value == "auto":
                filt = str(fits.getheader(args.inputs[0], 0).get("FILTER", "")).strip()
                rec = caldb.find(kind, filt=filt if kind == "MFLAT" else None)
                if rec is None:
                    print(f"WARNING: no {kind} in caldb; building without it",
                          file=sys.stderr)
                    return None
                return rec["path"]
            if value.lower() == "none":
                return None
            return value
        bias_path = resolve("MBIAS", args.bias)
        flat_path = resolve("MFLAT", args.flat)
        kind = "fringe" if args.command == "calib-fringe" else "illum"
        if args.output:
            out = Path(args.output)
        else:
            filt = str(fits.getheader(args.inputs[0], 0).get("FILTER", "X")).strip() or "X"
            out = outroot / "caldb" / f"master_{kind}_{filt}.fits"
        builder = build_master_fringe if kind == "fringe" else build_master_illum
        res = builder(args.inputs, out, caldb, PipelineConfig(),
                      bias_path=bias_path, flat_path=flat_path)
        for w in res["warnings"]:
            print(f"WARNING: {w}", file=sys.stderr)
        extra = (f"median_amp={res['median_amp']:.2e}" if kind == "fringe"
                 else f"max_dev={res['max_dev']:.4f}")
        print(f"{out}  CALVER={res['calver']}  filter={res['filter']}  {extra}")
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
                import numpy as _np
                zps = [c["photzp"]["zp"] for c in qa["ccds"].values()
                       if c.get("photzp", {}).get("measured")]
                zptxt = f"  ZP={_np.median(zps):6.3f}" if zps else ""
                print(f"{qa['l1_file']}  {qa['imagetyp']:>6} {qa['filter']:>2} "
                      f"{qa['exptime']:5.0f}s  max|seam|={seam:6.2f} e-{zptxt}  "
                      f"{qa['runtime_s']:.0f}s")
            except Exception as err:
                failed.append((inp, err))
                print(f"FAILED: {inp}: {err}", file=sys.stderr)
                traceback.print_exc()
        if failed:
            print(f"{len(failed)}/{len(args.inputs)} exposures failed", file=sys.stderr)
            return 1
        return 0

    if args.command == "gaia-ingest":
        from .gaialocal import GaiaLocal, ingest_fits_refcat, ingest_gaia_csv
        cat = GaiaLocal(args.store)
        total = 0
        for inp in args.inputs:
            if inp.endswith((".csv", ".csv.gz")):
                n = ingest_gaia_csv(cat, inp, gmax=args.gmax)
            else:
                n = ingest_fits_refcat(cat, inp)
            total += n
            print(f"  {Path(inp).name}: +{n} rows")
        st = cat.stats()
        print(f"{args.store}: {st['rows']} rows in {st['cells']} cells "
              f"({st['size_mb']} MB); added {total}")
        return 0

    if args.command == "fetch-gaia":
        from .astrometry import fetch_gaia_cone, parse_pointing
        if args.like:
            pt = parse_pointing(fits.getheader(args.like, 0))
            if pt is None:
                print(f"ERROR: no usable RA/DEC keywords in {args.like}", file=sys.stderr)
                return 1
            ra, dec = pt
        elif args.ra is not None and args.dec is not None:
            ra, dec = args.ra, args.dec
        else:
            print("ERROR: give --like FILE or --ra/--dec", file=sys.stderr)
            return 1
        out = Path(args.output) if args.output else outroot / "caldb" / "refcat_gaia.fits"
        data = fetch_gaia_cone(ra, dec, radius_arcmin=args.radius,
                               gmax=args.gmax, out_path=out)
        print(f"{out}  n_stars={len(data)}  center=({ra:.4f},{dec:+.4f}) r={args.radius}'")
        return 0

    if args.command == "make-refcat":
        from .astrometry import make_refcat
        out = Path(args.output) if args.output else outroot / "caldb" / "refcat.fits"
        res = make_refcat(args.l1file, out, nmax_per_chip=args.nmax, sigma=args.sigma)
        print(f"{out}  n_stars={res['n_stars']}")
        return 0

    if args.command == "qa-summary":
        out = batch_summary(outroot / "qa", args.output)
        print(out)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
