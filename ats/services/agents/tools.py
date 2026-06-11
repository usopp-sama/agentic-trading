"""Read-only tools available to agents.

Each tool fetches grounded data from a service; none can mutate state or place
orders (defense in depth: the LLM never touches execution). The context
assembler calls these to build an evidence-linked context. A registry is kept
so tool use can be audited and, later, exposed to real LLM tool-calling.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant.analysis import indicators


@dataclass
class Providers:
    """Handles to the services tools read from."""

    market_data: object | None = None
    strategies: object | None = None
    nlp: object | None = None
    knowledge: object | None = None
    fundamentals: object | None = None


def get_price(p: Providers, symbol: str) -> dict:
    px = p.market_data.latest_price(symbol) if p.market_data else None
    return {"symbol": symbol, "price": px}


def get_technical(p: Providers, symbol: str) -> dict:
    if not p.market_data:
        return {}
    df = p.market_data.get_history(symbol)
    if df is None or len(df) < 50:
        return {}
    close = df["close"]
    sma20 = float(indicators.sma(close, 20).iloc[-1])
    sma50 = float(indicators.sma(close, 50).iloc[-1])
    rsi = float(indicators.rsi(close, 14).iloc[-1])
    bb = indicators.bollinger_bands(close, 20, 2.0)
    pct_b = float(bb["pct_b"].iloc[-1])
    ret5 = float(close.iloc[-1] / close.iloc[-6] - 1.0) if len(close) > 6 else 0.0
    gap = (sma20 - sma50) / sma50 if sma50 else 0.0
    return {
        "sma_gap": round(gap, 4),
        "rsi": round(rsi, 2),
        "pct_b": round(pct_b, 3),
        "ret5": round(ret5, 4),
        "price": round(float(close.iloc[-1]), 2),
    }


def get_volume(p: Providers, symbol: str) -> dict:
    if not p.market_data:
        return {}
    df = p.market_data.get_history(symbol)
    if df is None or len(df) < 21:
        return {}
    vol = df["volume"].to_numpy()
    hist, last = vol[-21:-1], float(vol[-1])
    mean, std = float(np.mean(hist)), float(np.std(hist))
    z = (last - mean) / std if std > 0 else 0.0
    ret1 = float(df["close"].iloc[-1] / df["close"].iloc[-2] - 1.0) if len(df) > 1 else 0.0
    return {"vol_z": round(z, 2), "ret1": round(ret1, 4)}


def get_sentiment(p: Providers, symbol: str) -> dict:
    if not p.nlp:
        return {"count": 0, "mean_score": 0.0, "label": "neutral"}
    return p.nlp.recent_sentiment(symbol)


def get_news(p: Providers, symbol: str, k: int = 3) -> list[dict]:
    if not p.nlp:
        return []
    return p.nlp.search_symbol(symbol, k=k)


def get_instrument_profile(p: Providers, symbol: str) -> dict:
    if not p.knowledge:
        return {}
    return p.knowledge.get_profile(symbol)


def get_fundamentals(p: Providers, symbol: str) -> dict:
    if not p.fundamentals:
        return {}
    return p.fundamentals.get(symbol) or {}


REGISTRY = {
    "get_price": get_price,
    "get_technical": get_technical,
    "get_volume": get_volume,
    "get_sentiment": get_sentiment,
    "get_news": get_news,
    "get_instrument_profile": get_instrument_profile,
    "get_fundamentals": get_fundamentals,
}
