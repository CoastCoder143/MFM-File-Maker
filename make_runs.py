#!/usr/bin/env python3
"""Compatibility entry point for the canonical implementation in ``src/make_runs.py``.

Existing commands such as ``python make_runs.py`` continue to work while the
implementation lives in one place.
"""

from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(Path(__file__).parent / "src" / "make_runs.py", run_name="__main__")
