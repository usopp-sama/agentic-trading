#!/usr/bin/env python
"""Run the server in DEV / DEMO mode - everything ticks, 24/7, isolated.

The normal server is event-driven and correctly goes quiet outside NSE market
hours: no fresh bars -> no strategy signals -> the agents/CIO/risk/execution
pipeline stays IDLE on the Ops Console (that is expected, not a bug). This
launcher flips the two switches that make the whole pipeline move continuously,
so you can watch it work at any time of day:

  * ATS_DATA_SOURCE=synthetic       -> a fresh bar every poll, regardless of the clock
  * ATS_RESPECT_MARKET_HOURS=false  -> polling never pauses for a closed market

It also uses a SEPARATE dev database and a mock LLM, so a demo run never
touches your real paper book or spends a rupee on the LLM. Any of these can be
overridden by exporting the env var yourself before running (your value wins).

Usage:
    python scripts/run_dev.py
    python scripts/run_dev.py --port 8123
    python scripts/run_dev.py --db sqlite:///var/scratch.db
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Runnable as a plain file path too (python scripts\run_dev.py): put the repo
# root on sys.path so the ats package resolves.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# The env that makes the pipeline tick continuously and keeps the demo isolated
# from your real book. Applied with setdefault, so anything you export wins.
_DEV_ENV = {
    "ATS_DATA_SOURCE": "synthetic",
    "ATS_RESPECT_MARKET_HOURS": "false",
    "ATS_LLM_PROVIDER": "mock",
    "ATS_DB_URL": "sqlite:///var/dev_demo.db",
    "ATS_HOST": "127.0.0.1",
    "ATS_PORT": "8123",
}


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run the ATS server in dev/demo mode (whole pipeline ticks 24/7).")
    ap.add_argument("--port", default=None, help="port to bind (default 8123)")
    ap.add_argument("--db", default=None, help="override the isolated dev DB URL")
    args = ap.parse_args()

    if args.port:
        _DEV_ENV["ATS_PORT"] = str(args.port)
    if args.db:
        _DEV_ENV["ATS_DB_URL"] = args.db
    for key, val in _DEV_ENV.items():
        os.environ.setdefault(key, val)  # your exported value wins over the default

    print("Starting ATS in DEV/DEMO mode:")
    print("  synthetic data + market-hours OFF -> the whole pipeline ticks continuously")
    print(f"  mock LLM + isolated DB ({os.environ['ATS_DB_URL']}) -> your real paper book is untouched")
    print(f"  open  http://{os.environ['ATS_HOST']}:{os.environ['ATS_PORT']}/  and  /ops")
    print("  Ctrl+C to stop.\n")

    # Import only after the env is set, so settings pick up the dev values.
    from ats.server.__main__ import main as run_server

    run_server()


if __name__ == "__main__":
    main()
