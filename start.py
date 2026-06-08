#!/usr/bin/env python3
"""Root entry point for m3_model_power.

Usage:
    python start.py             # dev (default)
    python start.py dev         # dev mode
    python start.py doctor      # environment check
    python start.py install     # install dependencies
    python start.py check       # run guard scripts
    python start.py build       # build frontend + compile backend
    python start.py backend     # start backend only
    python start.py frontend    # start frontend only
    python start.py clean       # clean runtime artifacts
    python start.py stop        # inspect occupied ports
    python start.py stop --kill # inspect and stop occupied port processes
    python start.py --help      # show this help
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEV_SCRIPT = ROOT / "scripts" / "dev.py"


def main() -> None:
    args = sys.argv[1:] or ["dev"]
    if "--help" in args or "-h" in args:
        print(__doc__)
        return
    raise SystemExit(
        subprocess.call([sys.executable, str(DEV_SCRIPT), *args], cwd=ROOT)
    )


if __name__ == "__main__":
    main()
