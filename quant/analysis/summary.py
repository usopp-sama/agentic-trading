"""Technical summary — a deterministic "Strong Buy / Strong Sell" composite.

Runs a symbol's OHLCV frame through ~12 independent technical checks and nets
their votes into a single score and label. **Every check is reported** in
``components`` (name, vote, value) so the dashboard can show the full "why" —
we never surface a bare label. This is the investing.com "Technical Summary"
tool, built on our own ``indicators`` + ``levels`` + ``patterns`` modules.

Pure: takes a frame, returns a dataclass. A missing indicator (e.g. SMA-200 on
a short history) votes neutral with ``value=None`` — it never fabricates a
number and never drops the component.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant.analysis import indicators, patterns
from quant.analysis.levels import classic_pivots


@dataclass(frozen=True)
class TechnicalSummary:
    symbol: str
    score: int              # net = bulls - bears
    bulls: int
    bears: int
    neutral: int
    label: str              # strong_buy / buy / neutral / sell / strong_sell
    components: list[dict]   # one entry per check: {name, vote, value}

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol, "score": self.score,
            "bulls": self.bulls, "bears": self.bears, "neutral": self.neutral,
            "label": self.label, "components": self.components,
        }


def summary_label(score: int) -> str:
    """Map a net score to a five-way label (config-free thresholds)."""
    if score >= 6:
        return "strong_buy"
    if score >= 3:
        return "buy"
    if score <= -6:
        return "strong_sell"
    if score <= -3:
        return "sell"
    return "neutral"


def _last(series: pd.Series) -> float | None:
    """Last finite value of a series, or None."""
    if series is None or len(series) == 0:
        return None
    v = series.iloc[-1]
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    return float(v)


def _comp(name: str, vote: int, value) -> dict:
    if isinstance(value, float):
        value = round(value, 4)
    return {"name": name, "vote": int(vote), "value": value}


def technical_summary(symbol: str, df: pd.DataFrame) -> TechnicalSummary:
    """Composite technical read for ``symbol`` from an OHLCV daily frame.

    Requires ``close``; uses ``high``/``low``/``volume`` where present. Any
    check whose inputs are unavailable votes 0 (neutral). Always returns
    exactly 12 components.
    """
    close = df["close"] if "close" in df else pd.Series(dtype=float)
    has_hlc = all(c in df.columns for c in ("high", "low", "close"))
    comps: list[dict] = []

    price = _last(close)

    # 1-3: price vs SMA-20 / 50 / 200
    for w in (20, 50, 200):
        sma_v = _last(indicators.sma(close, w)) if len(close) >= 1 else None
        vote = 0
        if price is not None and sma_v is not None:
            vote = 1 if price > sma_v else -1 if price < sma_v else 0
        comps.append(_comp(f"price_vs_sma{w}", vote, sma_v))

    # 4: SMA-20 vs SMA-50
    s20 = _last(indicators.sma(close, 20))
    s50 = _last(indicators.sma(close, 50))
    vote = 0
    if s20 is not None and s50 is not None:
        vote = 1 if s20 > s50 else -1 if s20 < s50 else 0
    comps.append(_comp("sma20_vs_sma50", vote, None if s20 is None or s50 is None else s20 - s50))

    # 5: EMA-12 vs EMA-26
    e12 = _last(indicators.ema(close, 12))
    e26 = _last(indicators.ema(close, 26))
    vote = 0
    if e12 is not None and e26 is not None:
        vote = 1 if e12 > e26 else -1 if e12 < e26 else 0
    comps.append(_comp("ema12_vs_ema26", vote, None if e12 is None or e26 is None else e12 - e26))

    # 6: RSI-14 — oversold (<30) is bullish, overbought (>70) is bearish
    rsi_v = _last(indicators.rsi(close, 14))
    vote = 0
    if rsi_v is not None:
        vote = 1 if rsi_v < 30 else -1 if rsi_v > 70 else 0
    comps.append(_comp("rsi14", vote, rsi_v))

    # 7: MACD vs signal line
    macd_vote, macd_val = 0, None
    if len(close) >= 26:
        m = indicators.macd(close)
        ml, sl = _last(m["macd"]), _last(m["signal"])
        if ml is not None and sl is not None:
            macd_vote = 1 if ml > sl else -1 if ml < sl else 0
            macd_val = ml - sl
    comps.append(_comp("macd_vs_signal", macd_vote, macd_val))

    # 8: ADX>20 trend direction (+DI vs -DI); no trend => neutral
    adx_vote, adx_val = 0, None
    if has_hlc and len(df) >= 15:
        a = indicators.adx(df)
        adx_v = _last(a["adx"])
        pdi, mdi = _last(a["plus_di"]), _last(a["minus_di"])
        adx_val = adx_v
        if adx_v is not None and adx_v > 20 and pdi is not None and mdi is not None:
            adx_vote = 1 if pdi > mdi else -1 if pdi < mdi else 0
    comps.append(_comp("adx_direction", adx_vote, adx_val))

    # 9: Bollinger %b — at/below lower band bullish, at/above upper bearish
    bb_vote, bb_val = 0, None
    if len(close) >= 20:
        bb = indicators.bollinger_bands(close)
        pb = _last(bb["pct_b"])
        bb_val = pb
        if pb is not None:
            bb_vote = 1 if pb < 0.05 else -1 if pb > 0.95 else 0
    comps.append(_comp("bollinger_pct_b", bb_vote, bb_val))

    # 10: price vs classic pivot (pivot from the prior session)
    piv_vote, piv_val = 0, None
    if has_hlc and len(df) >= 2 and price is not None:
        prev = df.iloc[-2]
        piv = classic_pivots(prev["high"], prev["low"], prev["close"]).pivot
        piv_val = piv
        piv_vote = 1 if price > piv else -1 if price < piv else 0
    comps.append(_comp("price_vs_pivot", piv_vote, piv_val))

    # 11: latest candlestick pattern (net signed strength)
    pat_vote, pat_val = 0, None
    if all(c in df.columns for c in ("open", "high", "low", "close")):
        hits = patterns.detect(df)
        if hits:
            net = sum(h.direction * h.strength for h in hits)
            pat_vote = 1 if net > 0 else -1 if net < 0 else 0
            pat_val = ",".join(h.name for h in hits)
    comps.append(_comp("candlestick", pat_vote, pat_val))

    # 12: 5-day volume trend confirms the 5-day move
    vol_vote, vol_val = 0, None
    if "volume" in df.columns and len(df) >= 6:
        move = float(close.iloc[-1] - close.iloc[-6])
        vol_now = float(df["volume"].iloc[-1])
        vol_prior = float(df["volume"].iloc[-6:-1].mean())
        vol_val = vol_now - vol_prior
        rising = vol_now > vol_prior
        if rising and move > 0:
            vol_vote = 1
        elif rising and move < 0:
            vol_vote = -1
    comps.append(_comp("volume_trend", vol_vote, vol_val))

    bulls = sum(1 for c in comps if c["vote"] > 0)
    bears = sum(1 for c in comps if c["vote"] < 0)
    neutral = sum(1 for c in comps if c["vote"] == 0)
    score = bulls - bears
    return TechnicalSummary(
        symbol=symbol, score=score, bulls=bulls, bears=bears,
        neutral=neutral, label=summary_label(score), components=comps,
    )
