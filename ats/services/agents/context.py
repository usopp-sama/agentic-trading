"""Deterministic context assembly.

Turns raw grounded data (from the read-only tools) into normalized directional
signals in [-1, 1] plus an evidence bundle. Determinism matters: the same
inputs always produce the same context, which makes opinions cacheable and
reproducible. Personas declare which signals they consume.
"""

from __future__ import annotations

import math

from ats.core.config import get_settings
from ats.services.agents import tools
from ats.services.agents.directives import get_directive_store
from ats.services.agents.knowledge_base import get_knowledge_base, keywords
from ats.services.agents.tools import Providers


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _sign(x: float) -> float:
    return 1.0 if x > 0 else -1.0 if x < 0 else 0.0


class ContextAssembler:
    def __init__(self, providers: Providers) -> None:
        self.p = providers

    def assemble(self, persona: dict, symbol: str) -> dict:
        needed = set(persona.get("inputs", []))
        tech = tools.get_technical(self.p, symbol)
        vol = tools.get_volume(self.p, symbol) if {"volume_thrust"} & needed else {}
        sent = tools.get_sentiment(self.p, symbol) if {"sentiment", "news_flow"} & needed else {}
        news = tools.get_news(self.p, symbol, k=3) if {"sentiment", "news_flow"} & needed else []
        profile = tools.get_instrument_profile(self.p, symbol) if "profile_fit" in needed else {}

        signals: dict[str, float] = {}
        for name in needed:
            val = self._signal(name, symbol, tech, vol, sent, profile)
            if val is not None:
                signals[name] = round(val, 4)

        news_texts = [n["text"][:120] for n in news]
        knowledge = self._retrieve_knowledge(persona, symbol, news_texts)
        directives = self._retrieve_directives(persona, symbol, news_texts)
        evidence = {
            "technical": tech,
            "volume": vol,
            "sentiment": sent,
            "news": news_texts,
            "profile": {k: profile.get(k) for k in ("sector", "themes") if k in profile},
            "knowledge": [k["text"] for k in knowledge],
            "directives": [d["text"] for d in directives],
        }
        evidence_count = sum(1 for v in (tech, vol, sent, news, profile) if v)

        return {
            "symbol": symbol,
            "persona_id": persona.get("id"),
            "signals": signals,
            "evidence": evidence,
            "evidence_count": evidence_count,
            "risks": self._risks(tech, sent),
            "news": news_texts,
            "knowledge": knowledge,
            "directives": directives,
        }

    def _retrieve_knowledge(self, persona: dict, symbol: str, news_texts: list[str]) -> list[dict]:
        """Pull domain-relevant primer/research chunks for this expert.

        The query blends the symbol, the persona's declared inputs, its name,
        and recent headlines so retrieval reflects both the expert's lens and
        what is happening now. Scoped to the persona's family + shared pool.
        """
        try:
            kb = get_knowledge_base()
            if len(kb) == 0:
                kb.ingest_all(self.p.knowledge)
            query = " ".join(
                [
                    symbol,
                    persona.get("name", ""),
                    " ".join(persona.get("inputs", [])),
                    keywords(" ".join(news_texts), limit=10),
                ]
            ).strip()
            k = get_settings().knowledge_retrieval_k
            return kb.retrieve(query, family=persona.get("family"), k=k)
        except Exception:  # noqa: BLE001 - grounding is best-effort, never fatal
            return []

    def _retrieve_directives(self, persona: dict, symbol: str, news_texts: list[str]) -> list[dict]:
        """Pull expert-authored knowledge directives relevant to this symbol.

        Context only: directives sharpen reasoning, they never change risk or
        sizing (that path is the Rule engine + guardrails).
        """
        try:
            store = get_directive_store()
            query = " ".join(
                [symbol, " ".join(persona.get("inputs", [])), keywords(" ".join(news_texts), limit=8)]
            ).strip()
            return store.retrieve(query, symbol=symbol, family=persona.get("family"),
                                  k=get_settings().knowledge_retrieval_k)
        except Exception:  # noqa: BLE001
            return []

    def _signal(self, name, symbol, tech, vol, sent, profile) -> float | None:
        if name == "momentum" and tech:
            return _clip(math.tanh(tech.get("sma_gap", 0.0) * 12))
        if name == "trend_strength" and tech:
            return _clip((tech.get("rsi", 50) - 50) / 30)
        if name == "mean_reversion" and tech:
            return _clip(-(tech.get("pct_b", 0.5) - 0.5) * 2)
        if name == "sentiment" and sent:
            return _clip(sent.get("mean_score", 0.0))
        if name == "news_flow" and sent:
            # magnitude scaled by how many articles corroborate.
            n = min(sent.get("count", 0), 5) / 5.0
            return _clip(sent.get("mean_score", 0.0) * (0.5 + 0.5 * n))
        if name == "volume_thrust" and vol:
            return _clip(math.tanh(vol.get("vol_z", 0.0) / 3) * _sign(vol.get("ret1", 0.0)))
        if name == "valuation" and tech:
            return self._valuation_signal(symbol, tech)
        if name == "macro_regime":
            return self._macro_signal()
        if name == "profile_fit":
            return _clip(float(profile.get("thematic_fit", 0.0))) if profile else 0.0
        return None

    def _valuation_signal(self, symbol: str, tech: dict) -> float | None:
        # Real fundamentals first; price-based proxy only as the fallback.
        fundamental = self._fundamental_valuation(symbol)
        if fundamental is not None:
            return fundamental
        if not self.p.market_data:
            return None
        df = self.p.market_data.get_history(symbol)
        if df is None or len(df) < 60:
            return None
        mean60 = float(df["close"].tail(60).mean())
        price = float(df["close"].iloc[-1])
        if price <= 0:
            return None
        return _clip((mean60 / price - 1.0) * 4)

    def _fundamental_valuation(self, symbol: str) -> float | None:
        """Cheapness vs the universe: median P/E and P/B over this name's.

        A stock at half the universe's median multiples scores strongly
        positive; one at double scores negative. Both ratios must be
        positive to count (negative P/E means losses, not cheapness).
        Requires a handful of peers so the median means something.
        """
        if not self.p.fundamentals:
            return None
        universe = self.p.fundamentals.all_latest() or {}
        mine = universe.get(symbol)
        if not mine:
            return None
        components: list[float] = []
        for field, weight in (("pe", 1.5), ("pb", 1.0)):
            value = mine.get(field)
            peers = [
                f[field] for f in universe.values()
                if f.get(field) is not None and f[field] > 0
            ]
            if value is None or value <= 0 or len(peers) < 5:
                continue
            peers.sort()
            median = peers[len(peers) // 2]
            # median/value - 1: positive when cheaper than the universe.
            components.append(math.tanh((median / value - 1.0) * weight))
        if not components:
            return None
        return _clip(sum(components) / len(components))

    def _macro_signal(self) -> float | None:
        if not self.p.market_data:
            return None
        df = self.p.market_data.get_history("^NSEI")
        if df is None or len(df) < 50:
            return None
        from quant.analysis import indicators

        gap = (
            float(indicators.sma(df["close"], 20).iloc[-1])
            - float(indicators.sma(df["close"], 50).iloc[-1])
        ) / float(indicators.sma(df["close"], 50).iloc[-1])
        macro_sent = 0.0
        if self.p.nlp:
            # Overall world/market news mood (every headline feeds MARKET),
            # falling back to the index symbol if the accessor is unavailable.
            getter = getattr(self.p.nlp, "market_sentiment", None)
            agg = getter() if getter else self.p.nlp.recent_sentiment("^NSEI")
            macro_sent = agg.get("mean_score", 0.0)
        return _clip(math.tanh(gap * 10) * 0.7 + macro_sent * 0.3)

    @staticmethod
    def _risks(tech: dict, sent: dict) -> list[str]:
        risks = []
        if tech.get("rsi", 50) > 75:
            risks.append("overbought (RSI>75)")
        if tech.get("rsi", 50) < 25:
            risks.append("oversold; possible falling knife")
        if sent.get("label") == "negative":
            risks.append("negative news flow")
        return risks or ["standard market risk"]
