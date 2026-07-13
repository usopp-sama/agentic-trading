#!/usr/bin/env python
"""Bellwether P1 - collect the historical statement corpus from GDELT.

For each tracked figure, pull a daily tone + volume series and sample headlines
over N years, and write the corpus to var/bellwether/corpus/ (per-figure
parquet + jsonl + a manifest). This is the dated dataset the event-backtest
(P4) will trade on. Rate-limit aware (GDELT 429) via an inter-call delay +
exponential backoff - raise --delay if you still get throttled.

Usage:
    python scripts/bellwether_collect.py                        # full roster, 3y
    python scripts/bellwether_collect.py --figures modi,gadkari,rbi
    python scripts/bellwether_collect.py --years 3 --delay 8
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--figures", default=None, help="comma-separated figure keys (default: all)")
    ap.add_argument("--years", type=int, default=3, help="lookback window in years")
    ap.add_argument("--sample", type=int, default=25, help="headline samples per figure")
    ap.add_argument("--delay", type=float, default=8.0,
                    help="seconds between GDELT calls (GDELT allows ~1 / 5s)")
    ap.add_argument("--no-volume", action="store_true",
                    help="skip the daily-volume call (halves calls; tone is the signal)")
    ap.add_argument("--fail-fast", action="store_true",
                    help="give up immediately on a 429/timeout (no backoff) - use to probe "
                         "quickly whether your IP is un-throttled yet")
    ap.add_argument("--max-retries", type=int, default=4, help="backoff retries per call")
    ap.add_argument("--timeout", type=float, default=40.0, help="per-call HTTP timeout (s)")
    args = ap.parse_args()

    from ats.core.logging import configure_logging
    from ats.services.bellwether.collector import CORPUS_DIR, collect
    from ats.services.bellwether.gdelt import GdeltClient

    configure_logging("INFO")
    keys = [k.strip() for k in args.figures.split(",")] if args.figures else None
    max_retries = 0 if args.fail_fast else args.max_retries
    timeout = min(args.timeout, 10.0) if args.fail_fast else args.timeout
    client = GdeltClient(delay=args.delay, max_retries=max_retries, timeout=timeout)

    mode = "fail-fast" if args.fail_fast else f"{max_retries} retries w/ backoff"
    calls = 1 + (0 if args.no_volume else 1) + (1 if args.sample > 0 else 0)
    print(f"Bellwether collect: {args.years}y window, delay {args.delay}s, {mode}, "
          f"{calls} call(s)/figure. GDELT allows ~1 req/5s and penalises abusers.\n")
    manifest = collect(keys=keys, years=args.years, sample=args.sample, client=client,
                       with_volume=not args.no_volume)

    print(f"\n{'figure':12} {'verdict':11} {'points':>7} {'headlines':>10} {'mean tone':>10}")
    print("-" * 56)
    for r in manifest["figures"]:
        mt = r["mean_tone"] if r["mean_tone"] is not None else "n/a"
        print(f"{r['figure']:12} {r['verdict']:11} {r['tone_points']:>7} "
              f"{r['headlines']:>10} {str(mt):>10}")
    rich = manifest["rich"]
    print("\n" + "=" * 56)
    if rich:
        print(f"RICH corpus for: {', '.join(rich)}  ->  ready for P2 (map to tickers).")
    else:
        print("No figure came back RICH. If the errors were HTTP 429, your IP is throttled by")
        print("GDELT (it penalises high-traffic IPs) - WAIT a few hours or use a different")
        print("network, then retry. Use --fail-fast to probe quickly, --no-volume to halve calls.")
    print(f"Corpus written to {CORPUS_DIR}")


if __name__ == "__main__":
    main()
