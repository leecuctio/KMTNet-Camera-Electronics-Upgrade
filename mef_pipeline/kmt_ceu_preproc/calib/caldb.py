"""Directory-based calibration DB with a JSON index.

Selection rule: match CALTYPE (+site, +filter when relevant), then pick the
record whose DATE-OBS is nearest to the science exposure's; ties/absent dates
fall back to the most recently registered record."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
from astropy.io import fits


def _parse_date(text) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


class MasterFile:
    """Read access to a master calibration MEF (per-amp float planes)."""

    def __init__(self, path):
        self.path = Path(path)
        self.hdul = fits.open(self.path, memmap=True)
        self.header = self.hdul[0].header
        self.name = self.path.name
        self.calver = str(self.header.get("CALVER", ""))
        self.caltype = str(self.header.get("CALTYPE", ""))

    def plane(self, extname: str) -> np.ndarray:
        return np.asarray(self.hdul[extname].data, dtype=np.float32)

    def ovsc_level(self, extname: str) -> float | None:
        """Bias-epoch raw overscan level (OVSCLVL, master bias only)."""
        v = self.hdul[extname].header.get("OVSCLVL")
        return float(v) if v is not None else None

    def extnames(self) -> list[str]:
        return [h.name for h in self.hdul[1:]]

    def close(self):
        self.hdul.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class CalDB:
    def __init__(self, root):
        self.root = Path(root)
        self.index_path = self.root / "index.json"
        self.records: list[dict] = []
        if self.index_path.exists():
            self.records = json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(self.records, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    def register(self, path, caltype: str, site: str = "", filt: str = "",
                 dateobs: str = "", calver: str = ""):
        path = Path(path)
        rec = {
            "path": str(path.resolve()),
            "caltype": caltype.upper(),
            "site": site.upper(),
            "filter": filt,
            "dateobs": dateobs,
            "calver": calver,
        }
        self.records = [r for r in self.records if r["path"] != rec["path"]]
        self.records.append(rec)
        self._save()
        return rec

    def find(self, caltype: str, site: str = "", filt: str | None = None,
             date: str = "") -> dict | None:
        cands = [r for r in self.records if r["caltype"] == caltype.upper()]
        if site:
            cands = [r for r in cands if r["site"] in ("", site.upper())]
        if filt is not None:
            cands = [r for r in cands if r["filter"] in ("", filt)]
        if not cands:
            return None
        want = _parse_date(date)
        if want is not None:
            def distance(rec):
                have = _parse_date(rec["dateobs"])
                if have is None:
                    return dt.timedelta(days=36500)
                return abs(have.replace(tzinfo=None) - want.replace(tzinfo=None))
            cands.sort(key=distance)
            return cands[0]
        return cands[-1]

    def open(self, caltype: str, site: str = "", filt: str | None = None,
             date: str = "") -> MasterFile | None:
        rec = self.find(caltype, site=site, filt=filt, date=date)
        if rec is None:
            return None
        return MasterFile(rec["path"])
