#!/usr/bin/env python3
"""Show recorded Gemini/LLM usage and an estimated cost.

This reads the local ``llm_calls`` table (populated since the call recorder was
enabled) and prints token totals + an estimated spend per model. It is an
ESTIMATE from per-response token counts — Google's billing console is the
source of truth (context caching, free-tier allowances, and rounding differ).

Usage:
    .venv/bin/python scripts/llm_usage.py            # all recorded calls
    .venv/bin/python scripts/llm_usage.py --days 1   # last 24h
    .venv/bin/python scripts/llm_usage.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as a file path (python scripts/llm_usage.py) or module (-m).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=None, help="limit to the last N days")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    from ats.core.db import init_db
    from ats.services.agents.llm_log import usage_summary

    init_db()
    u = usage_summary(days=args.days)

    if args.json:
        print(json.dumps(u, indent=2))
        return

    print("LLM usage (recorded)" + (f" — last {args.days}d" if args.days else ""))
    if u.get("since"):
        print(f"  window: {u['since']}  →  {u['until']}")
    print(f"  ok calls: {u.get('ok_calls', 0)}   failed (unbilled): {u.get('failed_calls', 0)}")
    print(f"  tokens:   in={u.get('input_tokens', 0):,}  out={u.get('output_tokens', 0):,}")
    print()
    print(f"  {'model':24s} {'calls':>6s} {'in_tok':>10s} {'out_tok':>9s} {'est_usd':>9s}")
    for r in u.get("by_model", []):
        print(f"  {r['model']:24s} {r['calls']:>6d} {r['input_tokens']:>10,} "
              f"{r['output_tokens']:>9,} {r['est_usd']:>9.4f}")
    print()
    print(f"  estimated total: ${u.get('est_usd', 0):.4f}  (≈ ₹{u.get('est_inr', 0):.2f} "
          f"@ ₹{u.get('usd_inr', 0)}/$)")
    print(f"  note: {u.get('note', '')}")


if __name__ == "__main__":
    main()
