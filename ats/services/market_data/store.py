"""OHLCV persistence helpers."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.models import Ohlcv


def upsert_bars(symbol: str, df: pd.DataFrame, interval: str = "1d") -> int:
    """Insert any bars not already stored. Returns count of new rows."""
    if df.empty:
        return 0
    with session_scope() as s:
        existing = set(
            s.execute(
                select(Ohlcv.ts).where(
                    Ohlcv.symbol == symbol, Ohlcv.interval == interval
                )
            ).scalars().all()
        )
        added = 0
        for idx, row in df.iterrows():
            ts = pd.Timestamp(idx).to_pydatetime().replace(tzinfo=None)
            if ts in existing:
                continue
            s.add(
                Ohlcv(
                    symbol=symbol,
                    ts=ts,
                    interval=interval,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0.0)),
                )
            )
            added += 1
        return added


def load_history(symbol: str, interval: str = "1d", limit: int = 250) -> pd.DataFrame:
    """Load recent OHLCV for a symbol indexed by timestamp."""
    with session_scope() as s:
        rows = s.execute(
            select(Ohlcv)
            .where(Ohlcv.symbol == symbol, Ohlcv.interval == interval)
            .order_by(Ohlcv.ts.desc())
            .limit(limit)
        ).scalars().all()
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    rows = list(reversed(rows))
    df = pd.DataFrame(
        {
            "open": [r.open for r in rows],
            "high": [r.high for r in rows],
            "low": [r.low for r in rows],
            "close": [r.close for r in rows],
            "volume": [r.volume for r in rows],
        },
        index=pd.DatetimeIndex([r.ts for r in rows], name="date"),
    )
    return df
