"""Local Gaia reference catalog: partitioned all-sky store with fast cone
queries, replacing per-field VizieR downloads (the dominant cost of the
astrometry batch: ~65 of 79 minutes for one night, and a hard network
dependency at the observing sites).

Layout (pure numpy, no external dependencies):

    <root>/meta.json                     dec_band/ra_bin sizes, epoch, counts
    <root>/d{DD}_r{RRR}.npy              one structured array per sky cell
                                         (dec band x RA bin), fields:
                                         ra, dec [deg, f8], gmag [f4],
                                         pmra, pmdec [mas/yr, f4; NaN=none]

Sizing: Gaia DR3 G<19 all-sky is ~7e8 rows -> ~20 GB in this format
(28 B/row); a cone of the KMTNet mosaic (r~1.7 deg) touches a handful of
cells and reads in well under a second from local disk.

Build paths (gaia-ingest CLI):
  - FITS refcat tables (RA/DEC[/GMAG/PMRA/PMDEC]) e.g. fetch-gaia output
  - ESA Gaia bulk csv(.gz) files (gaia_source: ra, dec, phot_g_mean_mag,
    pmra, pmdec columns are picked by header name)
Ingest deduplicates by ~0.3 arcsec cell (keeps the first/brightest entry),
so overlapping cones can be ingested safely."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
from astropy.io import fits

DEC_BAND_DEG = 1.0
RA_BIN_DEG = 15.0
GAIA_EPOCH = 2016.0
DEDUP_ARCSEC = 0.3

DTYPE = np.dtype([("ra", "f8"), ("dec", "f8"), ("gmag", "f4"),
                  ("pmra", "f4"), ("pmdec", "f4")])


def _cell_name(dec_band: int, ra_bin: int) -> str:
    return f"d{dec_band:+03d}_r{ra_bin:03d}.npy"


class GaiaLocal:
    """Reader/writer for the partitioned local catalog."""

    def __init__(self, root):
        self.root = Path(root)
        meta_path = self.root / "meta.json"
        if meta_path.exists():
            self.meta = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            self.meta = {"version": 1, "dec_band_deg": DEC_BAND_DEG,
                         "ra_bin_deg": RA_BIN_DEG, "epoch": GAIA_EPOCH,
                         "n_rows": 0, "source": []}

    # -- geometry helpers ---------------------------------------------------
    def _bands(self):
        return float(self.meta["dec_band_deg"]), float(self.meta["ra_bin_deg"])

    def _cell_of(self, ra: np.ndarray, dec: np.ndarray):
        db, rb = self._bands()
        dband = np.floor(dec / db).astype(int)
        rbin = (np.floor((ra % 360.0) / rb).astype(int)
                % int(round(360.0 / rb)))
        return dband, rbin

    def _cells_for_cone(self, ra0: float, dec0: float, radius_deg: float):
        db, rb = self._bands()
        n_ra = int(round(360.0 / rb))
        cells = []
        b_lo = int(np.floor(max(dec0 - radius_deg, -90.0) / db))
        b_hi = int(np.floor(min(dec0 + radius_deg, 89.999) / db))
        for band in range(b_lo, b_hi + 1):
            dec_edge = max(abs(band * db), abs((band + 1) * db))
            cosd = np.cos(np.radians(min(dec_edge, 89.0)))
            half = min(radius_deg / max(cosd, 1e-6) + rb, 180.0)
            r_lo = int(np.floor(((ra0 - half) % 360.0) / rb))
            n_bins = min(int(np.ceil(2 * half / rb)) + 1, n_ra)
            for k in range(n_bins):
                cells.append((band, (r_lo + k) % n_ra))
        return sorted(set(cells))

    # -- write path ----------------------------------------------------------
    def ingest_arrays(self, ra, dec, gmag=None, pmra=None, pmdec=None,
                      source: str = "") -> int:
        """Merge rows into the store (per-cell concat + positional dedup)."""
        n = len(ra)
        rec = np.zeros(n, dtype=DTYPE)
        rec["ra"] = np.asarray(ra, dtype=np.float64) % 360.0
        rec["dec"] = np.asarray(dec, dtype=np.float64)
        rec["gmag"] = (np.asarray(gmag, dtype=np.float32)
                       if gmag is not None else np.float32(np.nan))
        rec["pmra"] = (np.asarray(pmra, dtype=np.float32)
                       if pmra is not None else np.float32(np.nan))
        rec["pmdec"] = (np.asarray(pmdec, dtype=np.float32)
                        if pmdec is not None else np.float32(np.nan))
        self.root.mkdir(parents=True, exist_ok=True)
        added = 0
        dband, rbin = self._cell_of(rec["ra"], rec["dec"])
        for band, rb_ in {(int(b), int(r)) for b, r in zip(dband, rbin)}:
            sel = rec[(dband == band) & (rbin == rb_)]
            path = self.root / _cell_name(band, rb_)
            n_old = 0
            if path.exists():
                old = np.load(path)
                n_old = len(old)
                merged = np.concatenate([old, sel])
            else:
                merged = sel
            merged = self._dedup(merged)
            np.save(path, merged)
            added += len(merged) - n_old
        # recount lazily: track approximate additions
        self.meta["n_rows"] = int(self.meta.get("n_rows", 0)) + max(added, 0)
        if source:
            self.meta.setdefault("source", []).append(source)
        (self.root / "meta.json").write_text(
            json.dumps(self.meta, indent=1), encoding="utf-8")
        return max(added, 0)

    @staticmethod
    def _dedup(rec: np.ndarray) -> np.ndarray:
        if len(rec) < 2:
            return rec
        order = np.argsort(np.where(np.isnan(rec["gmag"]), 99.0, rec["gmag"]))
        rec = rec[order]
        cell = DEDUP_ARCSEC / 3600.0
        key_dec = np.round(rec["dec"] / cell).astype(np.int64)
        key_ra = np.round(rec["ra"] * np.cos(np.radians(rec["dec"])) / cell
                          ).astype(np.int64)
        _, first = np.unique(np.column_stack([key_ra, key_dec]),
                             axis=0, return_index=True)
        return rec[np.sort(first)]

    # -- read path -------------------------------------------------------------
    def cone(self, ra0: float, dec0: float, radius_deg: float,
             gmax: float | None = None, max_refs: int | None = None,
             epoch: float | None = None) -> np.ndarray:
        """(n, 2) [ra, dec] within the cone; brightest-first magnitude cut
        when max_refs is exceeded; proper motion propagated to `epoch`
        (decimal year) where pm values exist."""
        parts = []
        for band, rb_ in self._cells_for_cone(ra0, dec0, radius_deg):
            path = self.root / _cell_name(band, rb_)
            if path.exists():
                parts.append(np.load(path))
        if not parts:
            return np.empty((0, 2))
        rec = np.concatenate(parts)
        if gmax is not None:
            rec = rec[np.where(np.isnan(rec["gmag"]), True, rec["gmag"] < gmax)]
        dra = (rec["ra"] - ra0 + 180.0) % 360.0 - 180.0
        sep = np.hypot(dra * np.cos(np.radians(rec["dec"])), rec["dec"] - dec0)
        rec = rec[sep <= radius_deg]
        if max_refs is not None and len(rec) > max_refs:
            g = np.where(np.isnan(rec["gmag"]), 99.0, rec["gmag"])
            rec = rec[np.argsort(g)[:max_refs]]
        ra = rec["ra"].astype(np.float64)
        dec = rec["dec"].astype(np.float64)
        if epoch is not None:
            dt = float(epoch) - float(self.meta.get("epoch", GAIA_EPOCH))
            pmra = np.where(np.isnan(rec["pmra"]), 0.0, rec["pmra"])
            pmdec = np.where(np.isnan(rec["pmdec"]), 0.0, rec["pmdec"])
            ra = ra + dt * pmra / (3.6e6 * np.cos(np.radians(dec)))
            dec = dec + dt * pmdec / 3.6e6
        return np.column_stack([ra, dec])

    def stats(self) -> dict:
        files = sorted(self.root.glob("d*_r*.npy"))
        n = sum(len(np.load(f, mmap_mode="r")) for f in files)
        size = sum(f.stat().st_size for f in files)
        return {"cells": len(files), "rows": int(n),
                "size_mb": round(size / 1e6, 1)}


# -- ingest sources -------------------------------------------------------------

def ingest_fits_refcat(cat: GaiaLocal, path) -> int:
    """FITS bintable with RA/DEC (deg) and optional GMAG/PMRA/PMDEC columns."""
    with fits.open(path) as hdul:
        for hdu in hdul[1:]:
            names = {n.upper(): n for n in hdu.columns.names}
            if "RA" not in names or "DEC" not in names:
                continue
            def col(key):
                return (np.asarray(hdu.data[names[key]], dtype=np.float64)
                        if key in names else None)
            return cat.ingest_arrays(col("RA"), col("DEC"), col("GMAG"),
                                     col("PMRA"), col("PMDEC"),
                                     source=Path(path).name)
    raise ValueError(f"No RA/DEC binary table in {path}")


def ingest_gaia_csv(cat: GaiaLocal, path, gmax: float | None = None,
                    chunk_rows: int = 500_000) -> int:
    """ESA Gaia bulk csv(.gz) (gaia_source): picks ra, dec,
    phot_g_mean_mag, pmra, pmdec by header name; streams in chunks."""
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    added = 0
    with opener(path, "rt") as f:
        header = f.readline().strip().split(",")
        idx = {name: header.index(name) for name in
               ("ra", "dec", "phot_g_mean_mag", "pmra", "pmdec")
               if name in header}
        if "ra" not in idx or "dec" not in idx:
            raise ValueError(f"{path.name}: no ra/dec columns")

        def flush(buf):
            if not buf:
                return 0
            arr = np.array(buf, dtype=np.float64)
            return cat.ingest_arrays(arr[:, 0], arr[:, 1], arr[:, 2],
                                     arr[:, 3], arr[:, 4],
                                     source=path.name)

        def fval(parts, key):
            i = idx.get(key)
            if i is None or i >= len(parts) or parts[i] in ("", "null"):
                return np.nan
            return float(parts[i])

        buf = []
        for line in f:
            parts = line.rstrip("\n").split(",")
            g = fval(parts, "phot_g_mean_mag")
            if gmax is not None and not (np.isnan(g) or g < gmax):
                continue
            buf.append((fval(parts, "ra"), fval(parts, "dec"), g,
                        fval(parts, "pmra"), fval(parts, "pmdec")))
            if len(buf) >= chunk_rows:
                added += flush(buf)
                buf = []
        added += flush(buf)
    return added
