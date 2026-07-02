"""L0 64-amp MEF reader driven by header/AMPINFO geometry.

No section values are hardcoded: DATASEC/BIASSEC/CCDSEC/DETSEC come from each
amp extension header, with the AMPINFO binary table as fallback. This makes
mock uniform DATA_LEFT packing and the real ICD packing (overscan on the
readout-node side) both work unchanged.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from astropy.io import fits

from .geometry import AmpGeom, parse_section

TABLE_EXTNAMES = ("AMPINFO", "XTALKINFO", "VOLTINFO", "TELEMETRY")


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class L0Exposure:
    """One L0 amp-raw MEF exposure (context manager)."""

    def __init__(self, path):
        self.path = Path(path)
        # do_not_scale_image_data: read raw int16 and apply BZERO/BSCALE
        # manually per amp, so astropy never caches 64 scaled float copies.
        self.hdul = fits.open(self.path, memmap=True, do_not_scale_image_data=True)
        self.primary = self.hdul[0].header
        self._ampinfo = self._load_ampinfo()
        self.amp_names = [
            hdu.name for hdu in self.hdul[1:]
            if hdu.header.get("XTENSION", "").strip() == "IMAGE"
            and hdu.name not in TABLE_EXTNAMES
        ]
        self.amps = [self._load_geom(name) for name in self.amp_names]

    # -- lifecycle ---------------------------------------------------------
    def close(self):
        self.hdul.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- metadata ----------------------------------------------------------
    @property
    def is_mock(self) -> bool:
        return bool(self.primary.get("MOCKDATA", False))

    @property
    def chips(self) -> list[str]:
        chiplist = str(self.primary.get("CHIPLIST", "")).strip()
        if chiplist:
            return [c.strip() for c in chiplist.split(",") if c.strip()]
        seen = []
        for g in self.amps:
            if g.chip not in seen:
                seen.append(g.chip)
        return seen

    def amps_of_chip(self, chip: str) -> list[AmpGeom]:
        return [g for g in self.amps if g.chip == chip]

    def ctrl_groups(self) -> list[list[AmpGeom]]:
        """Amps grouped by science controller (crosstalk coupling domain)."""
        groups: dict[int, list[AmpGeom]] = {}
        for g in self.amps:
            groups.setdefault(g.ctrlid, []).append(g)
        return [groups[k] for k in sorted(groups)]

    def sha256(self) -> str:
        return sha256_file(self.path)

    # -- pixel access ------------------------------------------------------
    def read_amp(self, extname: str) -> np.ndarray:
        """Full amp image (overscan included) as float32 with BZERO applied."""
        hdu = self.hdul[extname]
        bzero = _to_float(hdu.header.get("BZERO", 0.0))
        bscale = _to_float(hdu.header.get("BSCALE", 1.0), 1.0)
        data = np.asarray(hdu.data, dtype=np.float32)
        if bscale != 1.0:
            data = data * np.float32(bscale)
        if bzero != 0.0:
            data = data + np.float32(bzero)
        return data

    # -- crosstalk ---------------------------------------------------------
    def xtalk_matrix(self) -> tuple[np.ndarray | None, bool]:
        """(matrix[source-1, target-1], enabled). enabled follows XTALKCAL."""
        if "XTALKINFO" not in self.hdul:
            return None, False
        tbl = self.hdul["XTALKINFO"].data
        n = len(self.amps)
        mat = np.zeros((n, n), dtype=np.float64)
        src = np.asarray(tbl["SOURCE_AMP"], dtype=int)
        tgt = np.asarray(tbl["TARGET_AMP"], dtype=int)
        coef = np.asarray(tbl["XTALK_COEF"], dtype=np.float64)
        ok = (src >= 1) & (src <= n) & (tgt >= 1) & (tgt <= n)
        mat[src[ok] - 1, tgt[ok] - 1] = coef[ok]
        enabled = bool(self.primary.get("XTALKCAL", False)) and bool(np.any(mat))
        return mat, enabled

    # -- geometry loading ----------------------------------------------------
    def _load_ampinfo(self) -> dict[str, dict]:
        if "AMPINFO" not in self.hdul:
            return {}
        tbl = self.hdul["AMPINFO"].data
        rows = {}
        for row in tbl:
            rec = {name: row[name] for name in tbl.names}
            rows[str(rec.get("EXTNAME", "")).strip()] = rec
        return rows

    def _load_geom(self, extname: str) -> AmpGeom:
        hdr = self.hdul[extname].header
        info = self._ampinfo.get(extname, {})

        def get(key, default=None):
            v = hdr.get(key)
            if v is None or (isinstance(v, str) and not v.strip()):
                v = info.get(key, default)
            return v

        def sec(key):
            v = get(key)
            if v is None:
                raise ValueError(f"{self.path.name}[{extname}]: missing {key}")
            return parse_section(v)

        # AMPINFO uses SATLEVEL for the header's SATURAT
        saturate = get("SATURAT")
        if saturate is None:
            saturate = info.get("SATLEVEL", 0)
        return AmpGeom(
            extname=extname,
            chip=str(get("CHIPID", extname[:1])).strip(),
            ampid=int(_to_float(get("AMPID", 0))),
            ctrlid=int(_to_float(get("CTRLID", 1), 1.0)),
            datasec=sec("DATASEC"),
            biassec=sec("BIASSEC"),
            ccdsec=sec("CCDSEC"),
            detsec=sec("DETSEC"),
            gain=_to_float(get("GAIN", 0.0)),
            rdnoise=_to_float(get("RDNOISE", 0.0)),
            saturate=_to_float(saturate),
            linmax=_to_float(get("LINMAX", 0.0)),
        )

    # -- validation ----------------------------------------------------------
    def validate(self, expected_amps: int | None = 64) -> list[str]:
        """Structural checks per keyword spec section 11. Returns issue list."""
        issues = []
        n_amp = len(self.amp_names)
        for t in TABLE_EXTNAMES:
            if t not in self.hdul:
                issues.append(f"missing table extension {t}")
        n_expected = 1 + n_amp + sum(1 for t in TABLE_EXTNAMES if t in self.hdul)
        if len(self.hdul) != n_expected:
            issues.append(f"HDU count {len(self.hdul)} != {n_expected}")
        if expected_amps is not None and n_amp != expected_amps:
            issues.append(f"amp HDU count {n_amp} != {expected_amps}")
        if self._ampinfo and len(self._ampinfo) != n_amp:
            issues.append(f"AMPINFO rows {len(self._ampinfo)} != {n_amp} amps")
        if "XTALKINFO" in self.hdul:
            nx = len(self.hdul["XTALKINFO"].data)
            if nx != n_amp * n_amp:
                issues.append(f"XTALKINFO rows {nx} != {n_amp * n_amp}")
        for g in self.amps:
            hdu = self.hdul[g.extname]
            ny, nx = int(hdu.header["NAXIS2"]), int(hdu.header["NAXIS1"])
            for label, s in (("DATASEC", g.datasec), ("BIASSEC", g.biassec)):
                if s[1] > nx or s[3] > ny:
                    issues.append(f"{g.extname} {label} {s} exceeds image {nx}x{ny}")
            dx = set(range(g.datasec[0], g.datasec[1] + 1))
            bx = set(range(g.biassec[0], g.biassec[1] + 1))
            if dx & bx:
                issues.append(f"{g.extname} DATASEC/BIASSEC overlap in x")
        return issues
