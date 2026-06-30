"""Strategy auto-trader.

Bridges the quant strategy layer to the order path. Strategy signals are
published on ``Topic.SIGNAL`` but, by design, no service used to act on them —
they only fed the Opportunities UI and the virtual sleeve P&L. This service
turns a *consensus* of the ``paper``-status strategies into proposals that flow
through the SAME ``Risk -> Execution`` rails the LLM/SME pipeline uses, so all
sizing, guardrails, the long-only clamp, the rate limit and the duplicate-fill
guard apply unchanged.

Why a consensus (not one order per signal): several strategies often fire on
the same name in one poll cycle; netting their signed convictions per symbol
avoids whipsawing the book with conflicting single-strategy orders.

No LLM/Gemini spend on this path — it is pure quant. Strategy signals only fire
on ``BAR`` events, which only arrive during the NSE polling window, so trades
are naturally session-bound.
"""

from __future__ import annotations

import time

from ats.core.config import get_settings
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.schemas import Stance

log = get_logger("ats.strategy_trader")

_STANCE_NAME = {2: "strong_buy", 1: "buy", 0: "neutral", -1: "sell", -2: "strong_sell"}


class StrategyTraderService:
    name = "strategy_trader"

    def __init__(self) -> None:
        self._bus: EventBus | None = None
        self._execution = None
        # views[symbol][strategy_id] = (direction:int, conviction:float)
        self._views: dict[str, dict[str, tuple[int, float]]] = {}
        # symbol -> monotonic ts of last strategy-driven proposal (anti-churn)
        self._last_trade: dict[str, float] = {}

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._execution = ctx.orchestrator.get("execution")
        ctx.bus.subscribe(Topic.SIGNAL, self._on_signal)
        s = get_settings()
        log.info(
            "strategy_trader_started",
            extra={
                "enabled": s.strategy_autotrade_enabled,
                "buy_threshold": s.strategy_trade_buy_threshold,
                "min_agree": s.strategy_trade_min_agree,
            },
        )

    async def _on_signal(self, evt) -> None:
        await self.handle_signal(evt.payload)

    async def handle_signal(self, payload: dict) -> dict:
        settings = get_settings()
        if not settings.strategy_autotrade_enabled:
            return {"status": "disabled"}

        symbol = payload.get("symbol")
        strategy = payload.get("strategy")
        if not symbol or not strategy:
            return {"status": "skipped"}
        # Indices / reference feeds are never tradeable; don't even propose.
        if symbol.startswith("^"):
            return {"status": "not_tradeable"}

        try:
            direction = Stance(payload.get("stance", "neutral")).direction
        except ValueError:
            direction = 0
        conviction = float(payload.get("conviction", 0.0) or 0.0)

        # Record/refresh this strategy's vote on the symbol.
        self._views.setdefault(symbol, {})[strategy] = (direction, conviction)

        if self._execution is None:
            return {"status": "no_execution"}

        net, bull_agree, voters = self._net_score(symbol)
        snap = self._execution.get_snapshot()
        positions = {p["symbol"]: p for p in snap.get("positions", [])}
        current_qty = positions.get(symbol, {}).get("qty", 0)
        holding = current_qty > 0

        # Decide action from the consensus.
        if not holding and net >= settings.strategy_trade_buy_threshold and bull_agree >= settings.strategy_trade_min_agree:
            action, target_weight, conv = "BUY", settings.max_position_pct, min(1.0, max(0.0, net))
        elif holding and net <= settings.strategy_trade_exit_threshold:
            action, target_weight, conv = "SELL", 0.0, min(1.0, abs(net))
        else:
            return {"status": "no_action", "net": round(net, 3)}

        # Per-symbol cooldown (anti-churn). Views still update above so the next
        # eligible signal acts on a fresh consensus.
        now = time.monotonic()
        last = self._last_trade.get(symbol, 0.0)
        if now - last < settings.strategy_trade_cooldown_s:
            return {"status": "cooldown", "net": round(net, 3)}

        proposal = self._build_proposal(symbol, action, target_weight, conv, net, bull_agree, voters)
        self._last_trade[symbol] = now
        if self._bus is not None:
            await self._bus.publish(Topic.PROPOSAL, proposal)
        log.info(
            "strategy_proposal",
            extra={"symbol": symbol, "action": action, "net": round(net, 3), "voters": voters},
        )
        return {"status": "proposed", "action": action, "net": round(net, 3)}

    # --- helpers -----------------------------------------------------------
    def _net_score(self, symbol: str) -> tuple[float, int, int]:
        """Net strategy score for a symbol.

        ``(Σ bullish conviction − Σ bearish conviction) / voters`` in [-1, 1],
        plus the count of bullish voters and total voters.
        """
        votes = self._views.get(symbol, {})
        if not votes:
            return 0.0, 0, 0
        bull = sum(c for d, c in votes.values() if d > 0)
        bear = sum(c for d, c in votes.values() if d < 0)
        voters = len(votes)
        bull_agree = sum(1 for d, _ in votes.values() if d > 0)
        return (bull - bear) / voters, bull_agree, voters

    def _build_proposal(
        self, symbol: str, action: str, target_weight: float, conviction: float,
        net: float, bull_agree: int, voters: int,
    ) -> dict:
        votes = self._views.get(symbol, {})
        strategies = [
            {"strategy": s, "stance": _STANCE_NAME.get(d, "neutral"), "conviction": round(c, 3)}
            for s, (d, c) in sorted(votes.items(), key=lambda kv: -abs(kv[1][0] * kv[1][1]))
        ]
        lean = "bullish" if action == "BUY" else "bearish/neutral"
        detail = ", ".join(f"{v['strategy']} {v['stance']}({v['conviction']:.2f})" for v in strategies)
        rationale = (
            f"Strategy consensus {lean} on {symbol}: net {net:+.2f} across {voters} "
            f"strateg{'y' if voters == 1 else 'ies'} ({detail})."
        )
        return {
            "symbol": symbol,
            "action": action,
            "target_weight": target_weight if action == "BUY" else 0.0,
            "conviction": conviction,
            "rationale": rationale,
            "contributors": {
                "source": "strategy_consensus",
                "net_score": round(net, 3),
                "voters": voters,
                "bull_agree": bull_agree,
                "strategies": strategies,
            },
        }

    # --- introspection (for the /strategies dashboard page) ----------------
    def live_views(self) -> dict[str, dict]:
        """Per-symbol consensus snapshot for the dashboard."""
        out: dict[str, dict] = {}
        for symbol in self._views:
            net, bull_agree, voters = self._net_score(symbol)
            out[symbol] = {"net_score": round(net, 3), "bull_agree": bull_agree, "voters": voters}
        return out
