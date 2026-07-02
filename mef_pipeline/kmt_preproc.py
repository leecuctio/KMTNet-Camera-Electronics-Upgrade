#!/usr/bin/env python3
"""Entry point wrapper so the pipeline runs without installation:

    python3 mef_pipeline/kmt_preproc.py <command> ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kmt_ceu_preproc.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
