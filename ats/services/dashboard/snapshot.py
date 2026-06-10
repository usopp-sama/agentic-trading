"""Builds the full dashboard snapshot from services + DB."""

from __future__ import annotations

from sqlalchemy import select

from ats.core import state
from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Decision, NewsItem, SmeOpinion

log = get_logger("ats.dashboard")


def _safe(fn, default):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        log.warning("snapshot_section_failed", extra={"error": str(exc)})
        return default


def build_snapshot(orch) -> dict:
    settings = get_settings()
    execution = orch.get("execution") if orch else None
    agents = orch.get("agents") if orch else None
    learning = orch.get("learning") if orch else None
    rules = orch.get("rules") if orch else None
    market = orch.get("market_data") if orch else None
    strategies = orch.get("strategies") if orch else None
    regime = orch.get("regime") if orch else None

    portfolio = _safe(lambda: execution.get_snapshot(), {}) if execution else {}

    with session_scope() as s:
        decisions = [
            {"id": d.id, "ts": d.ts.isoformat(), "symbol": d.symbol, "action": d.action,
             "qty": d.target_qty, "status": d.status, "rules": d.rules_applied,
             "rationale": d.rationale}
            for d in s.execute(select(Decision).order_by(Decision.id.desc()).limit(12)).scalars().all()
        ]
        opinions = [
            {"ts": o.ts.isoformat(), "sme": o.sme, "symbol": o.symbol, "stance": o.stance,
             "conviction": o.conviction, "rationale": o.rationale}
            for o in s.execute(select(SmeOpinion).order_by(SmeOpinion.id.desc()).limit(12)).scalars().all()
        ]
        news = [
            {"ts": n.ts.isoformat(), "source": n.source, "title": n.title, "tickers": n.tickers}
            for n in s.execute(select(NewsItem).order_by(NewsItem.id.desc()).limit(10)).scalars().all()
        ]

    return {
        "state": {
            "mode": state.get_mode(),
            "kill_switch": state.is_killed(),
            "real_money_enabled": settings.real_money_enabled,
            "real_money_active": state.real_money_active(),
            "data_source": settings.data_source,
            "llm_provider": settings.llm_provider,
            "macro_tilt": round(agents.macro_tilt, 4) if agents else 0.0,
            "watchlist": len(market.watchlist()) if market else 0,
            "audit_chain_ok": _safe(state.verify_audit_chain, True),
            "regime": _safe(lambda: regime.current().label, "range/normal") if regime else "range/normal",
        },
        "sleeves": _safe(lambda: strategies.sleeve_stats(), []) if strategies else [],
        "portfolio": portfolio,
        "decisions": decisions,
        "opinions": opinions,
        "news": news,
        "approvals": _safe(lambda: execution.list_pending_approvals(), []) if execution else [],
        "leaderboard": _safe(lambda: learning.leaderboard(), []) if learning else [],
        "rulebook": _safe(lambda: rules.rulebook(), []) if rules else [],
    }
