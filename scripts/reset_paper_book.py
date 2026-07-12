#!/usr/bin/env python
"""Reset the paper trading book to a clean starting state.

The early dev runs polluted the DB with synthetic-price marks and a few
duplicate fills, which made the dashboard's equity/P&L look random. This wipes
the *account + reasoning* rows (positions, orders, fills, decisions, signals,
opinions, attributions, daily P&L) and resets cash to the configured starting
capital, so the month-long paper run starts from honest, real numbers.

Reference/market data (instruments, OHLCV, news, sentiment, fundamentals,
strategies, rules) is left untouched.

Safety:
  * Backs up the SQLite file first (``ats.db`` -> ``ats.db.bak-<timestamp>``).
  * Refuses to run if real money is enabled.
  * STOP THE SERVER before running, so nothing writes mid-reset.

Usage:
    .venv/bin/python -m scripts.reset_paper_book            # with backup
    .venv/bin/python -m scripts.reset_paper_book --yes      # skip prompt
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select

from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.models import (
    AnalyticsSnapshot,
    Approval,
    Attribution,
    Decision,
    DematHolding,
    Fill,
    KvState,
    LedgerEntry,
    Order,
    PnlDaily,
    Position,
    PositionThesis,
    Signal,
    SleevePnl,
    SmeOpinion,
    ThesisRevision,
)

# Every table that records a trade, a holding, the reasoning behind it, or a
# derived P&L mark — cleared on reset (newest-first by FK depth). Reference and
# learning data (instruments, ohlcv, news, sentiment, fundamentals, strategies,
# rules, SME track records, knowledge) is deliberately left untouched.
_CLEAR = [
    Fill, Attribution, Approval, Order, Position, PnlDaily,
    Decision, Signal, SmeOpinion, SleevePnl,
    LedgerEntry,        # the cash passbook (journal)
    DematHolding,       # settled + pending share holdings
    PositionThesis, ThesisRevision,   # the written reasoning per open position
    AnalyticsSnapshot,  # derived equity/P&L history shown on the dashboard
]


def _backup_sqlite() -> str | None:
    url = get_settings().db_url
    if not url.startswith("sqlite"):
        print(f"DB is not SQLite ({url}); skipping file backup.", file=sys.stderr)
        return None
    db_path = Path(url.split("///", 1)[1])
    if not db_path.exists():
        print(f"No DB file at {db_path}; nothing to back up.")
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = db_path.with_suffix(db_path.suffix + f".bak-{stamp}")
    shutil.copy2(db_path, dest)
    print(f"Backed up {db_path}  ->  {dest}")
    return str(dest)


def _accounts(s) -> list[str]:
    """Every account that has ever had a ledger, plus the main paper account.

    Accounts are discovered from the ``ledger:<account>`` kv keys (main paper +
    any league solos / per-user books), so the reset wipes the *whole* book, not
    just the main account."""
    rows = s.execute(select(KvState.key)).scalars().all()
    found = {k.split(":", 1)[1] for k in rows if k.startswith("ledger:")}
    found.add("paper")
    return sorted(found)


def reset() -> dict:
    settings = get_settings()
    if settings.real_money_enabled:
        raise SystemExit("Refusing to reset: ATS_REAL_MONEY_ENABLED is true.")

    capital = settings.paper_starting_capital
    counts: dict[str, int] = {}
    with session_scope() as s:
        accounts = _accounts(s)
        for model in _CLEAR:
            existing = s.execute(select(model)).scalars().all()
            counts[model.__tablename__] = len(existing)
            s.execute(delete(model))

        # Reset every account's live ledger (cash + holds) and the legacy cash
        # mirror to starting capital, and clear its drawdown high-water mark.
        for account in accounts:
            _set_kv(s, f"ledger:{account}", {"cash": capital, "holds": {}})
            _set_kv(s, f"cash:{account}", {"cash": capital})
            peak = s.get(KvState, f"risk:peak_equity:{account}")
            if peak is not None:
                s.delete(peak)
    return {"cleared": counts, "cash_reset_to": capital, "accounts": accounts}


def _set_kv(s, key: str, value: dict) -> None:
    row = s.get(KvState, key)
    if row is None:
        s.add(KvState(key=key, value=value))
    else:
        row.value = value


def main() -> None:
    ap = argparse.ArgumentParser(description="Reset the paper book to clean starting capital.")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    ap.add_argument("--no-backup", action="store_true", help="do not back up the DB file first")
    args = ap.parse_args()

    cap = get_settings().paper_starting_capital
    print(f"This will WIPE the paper account + reasoning rows and reset cash to Rs{cap:,.0f}.")
    if not args.yes:
        if input("Type 'reset' to continue: ").strip().lower() != "reset":
            print("Aborted.")
            return
    if not args.no_backup:
        _backup_sqlite()
    result = reset()
    print("Cleared rows:")
    for table, n in result["cleared"].items():
        print(f"  {table:<18} {n}")
    print(f"Accounts reset ({len(result['accounts'])}): {', '.join(result['accounts'])}")
    print(f"Cash reset to: Rs{result['cash_reset_to']:,.0f} each")
    print("Done. Restart the server to begin a clean paper run.")


if __name__ == "__main__":
    main()
