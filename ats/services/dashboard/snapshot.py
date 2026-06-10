"""Builds the full dashboard snapshot from services + DB."""

from __future__ import annotations

from sqlalchemy import select

from ats.core import state
from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Decision, NewsItem, SentimentScore, SmeOpinion

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

    nlp = orch.get("nlp") if orch else None
    portfolio = _safe(lambda: execution.get_snapshot(), {}) if execution else {}
    watchset = set(_safe(lambda: market.watchlist(), [])) if market else set()
    data_status = _safe(lambda: market.data_status(), {"mode": "synthetic"}) if market else {"mode": "synthetic"}

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
        # Recent news, with a flag + sentiment for items touching the watchlist.
        raw_news = s.execute(select(NewsItem).order_by(NewsItem.id.desc()).limit(60)).scalars().all()
        news, watchlist_news = [], []
        for n in raw_news:
            tickers = n.tickers or []
            relevant = [t for t in tickers if t in watchset]
            sent = None
            if relevant:
                row = s.execute(
                    select(SentimentScore).where(SentimentScore.news_id == n.id).limit(1)
                ).scalar_one_or_none()
                if row is not None:
                    sent = {"label": row.label, "score": round(row.score, 3)}
            item = {"ts": n.ts.isoformat(), "source": n.source, "title": n.title,
                    "url": n.url, "tickers": tickers, "watch": relevant, "sentiment": sent}
            news.append(item)
            if relevant and len(watchlist_news) < 12:
                watchlist_news.append(item)

    # Per-symbol sentiment board: watchlist names with recent news, ranked by
    # how strongly the news leans (positive or negative).
    sentiment_board: list[dict] = []
    if nlp is not None:
        for sym in watchset:
            agg = _safe(lambda sym=sym: nlp.recent_sentiment(sym), {"count": 0})
            if agg.get("count", 0) > 0:
                sentiment_board.append({"symbol": sym, **agg})
        sentiment_board.sort(key=lambda x: abs(x.get("mean_score", 0.0)), reverse=True)
        sentiment_board = sentiment_board[:10]

    return {
        "state": {
            "mode": state.get_mode(),
            "kill_switch": state.is_killed(),
            "real_money_enabled": settings.real_money_enabled,
            "real_money_active": state.real_money_active(),
            "data_source": settings.data_source,
            "data_status": data_status,
            "llm_provider": settings.llm_provider,
            "macro_tilt": round(agents.macro_tilt, 4) if agents else 0.0,
            "watchlist": len(watchset),
            "audit_chain_ok": _safe(state.verify_audit_chain, True),
        },
        "portfolio": portfolio,
        "decisions": decisions,
        "opinions": opinions,
        "news": news[:12],
        "watchlist_news": watchlist_news,
        "sentiment_board": sentiment_board,
        "approvals": _safe(lambda: execution.list_pending_approvals(), []) if execution else [],
        "leaderboard": _safe(lambda: learning.leaderboard(), []) if learning else [],
        "rulebook": _safe(lambda: rules.rulebook(), []) if rules else [],
    }
