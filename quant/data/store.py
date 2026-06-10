"""Local price storage backed by SQLite.

SQLite keeps the project dependency-free and portable for local
development. The schema and API are intentionally close to what you'd
use with PostgreSQL + TimescaleDB later: a single wide ``prices`` table
keyed by ``(symbol, date)``, upserted idempotently.

Migration note: to move to TimescaleDB, create the same table as a
hypertable on ``date`` and swap the connection; the query layer here
uses parameterized SQL so it ports directly.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    symbol TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL,
    high   REAL,
    low    REAL,
    close  REAL,
    volume REAL,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_prices_symbol ON prices(symbol);
"""


class PriceStore:
    """A tiny price database.

    Example
    -------
    >>> store = PriceStore("market.db")
    >>> store.save_prices("AAPL", df)
    >>> back = store.load_prices("AAPL")
    """

    def __init__(self, path: str | Path = "market.db") -> None:
        self.path = str(path)
        # Parameterized queries are used everywhere; never string-format SQL.
        self._conn = sqlite3.connect(self.path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save_prices(self, symbol: str, df: pd.DataFrame) -> int:
        """Upsert an OHLCV frame for ``symbol``. Returns rows written."""
        if df.empty:
            return 0
        records = self._to_records(symbol, df)
        self._conn.executemany(
            """
            INSERT INTO prices (symbol, date, open, high, low, close, volume)
            VALUES (:symbol, :date, :open, :high, :low, :close, :volume)
            ON CONFLICT(symbol, date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume
            """,
            records,
        )
        self._conn.commit()
        return len(records)

    def load_prices(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Load an OHLCV frame for ``symbol`` indexed by date."""
        query = "SELECT date, open, high, low, close, volume FROM prices WHERE symbol = ?"
        params: list = [symbol]
        if start:
            query += " AND date >= ?"
            params.append(start)
        if end:
            query += " AND date <= ?"
            params.append(end)
        query += " ORDER BY date"

        rows = self._conn.execute(query, params).fetchall()
        cols = ["date", "open", "high", "low", "close", "volume"]
        df = pd.DataFrame(rows, columns=cols)
        if df.empty:
            return df.set_index("date")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date").sort_index()

    def list_symbols(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT symbol FROM prices ORDER BY symbol"
        ).fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PriceStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @staticmethod
    def _to_records(symbol: str, df: pd.DataFrame) -> list[dict]:
        records = []
        for idx, row in df.iterrows():
            records.append(
                {
                    "symbol": symbol,
                    "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
                    "open": _opt(row.get("open")),
                    "high": _opt(row.get("high")),
                    "low": _opt(row.get("low")),
                    "close": _opt(row.get("close")),
                    "volume": _opt(row.get("volume")),
                }
            )
        return records


def _opt(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
