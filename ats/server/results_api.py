"""Result-oriented read endpoints powering the redesigned dashboard.

These expose what the always-on services compute — opportunities, candles +
annotations, the trade blotter, the equity curve, the news feed/reader, and an
LLM-written brief — as plain JSON for the Today / Opportunities / Charts /
Portfolio / News pages.

All inputs are validated (symbol + interval allow-lists, paging caps). The
optional full-article fetch is domain-allow-listed with private-range blocking
(SSRF guard).
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import (
    Decision,
    Fill,
    Instrument,
    NewsItem,
    Ohlcv,
    Order,
    PnlDaily,
    SentimentScore,
    Signal,
    SmeOpinion,
)
from ats.services.opportunities import build_opportunities, opportunity_detail

log = get_logger("ats.results_api")
router = APIRouter(prefix="/api")

_SYMBOL_RE = re.compile(r"^[A-Za-z0-9_.&^\-]{1,24}$")
_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "60m", "1h", "1d", "1w"}


def _valid_symbol(sym: str) -> bool:
    return bool(sym and _SYMBOL_RE.match(sym))


def _orch(request: Request):
    return getattr(request.app.state, "orchestrator", None)


def _epoch(ts: datetime | None) -> int:
    if ts is None:
        return 0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return int(ts.timestamp())


# --------------------------------------------------------------------------- #
# Opportunities
# --------------------------------------------------------------------------- #
@router.get("/opportunities")
def opportunities(request: Request,
                  limit: int = Query(20, ge=1, le=100),
                  min_score: float = Query(0.0, ge=0.0, le=1.0)):
    items = build_opportunities(_orch(request), limit=limit, min_score=min_score)
    return {"opportunities": items, "count": len(items)}


@router.get("/opportunities/{symbol}")
def opportunity(symbol: str, request: Request):
    if not _valid_symbol(symbol):
        return {"error": "invalid symbol"}
    detail = opportunity_detail(_orch(request), symbol)
    if detail is None:
        return {"error": "not found", "symbol": symbol}
    return detail


# --------------------------------------------------------------------------- #
# Candles + annotations (Lightweight-Charts shaped)
# --------------------------------------------------------------------------- #
@router.get("/ohlcv")
def ohlcv(request: Request,
          symbol: str = Query(...),
          interval: str = Query("1d"),
          limit: int = Query(300, ge=1, le=2000)):
    if not _valid_symbol(symbol):
        return {"error": "invalid symbol"}
    if interval not in _INTERVALS:
        return {"error": "invalid interval", "allowed": sorted(_INTERVALS)}

    # Intraday from the live adapter when available; else the persisted store.
    candles: list[dict] = []
    orch = _orch(request)
    md = orch.get("market_data") if orch else None
    if interval != "1d" and md is not None and hasattr(md, "intraday"):
        try:
            for c in md.intraday(symbol, interval=interval, limit=limit) or []:
                candles.append(c)
        except Exception as exc:  # noqa: BLE001
            log.warning("intraday_failed", extra={"symbol": symbol, "error": str(exc)})

    if not candles:
        with session_scope() as s:
            rows = s.execute(
                select(Ohlcv).where(Ohlcv.symbol == symbol, Ohlcv.interval == interval)
                .order_by(Ohlcv.ts.desc()).limit(limit)
            ).scalars().all()
        for r in reversed(rows):
            candles.append({"time": _epoch(r.ts), "open": r.open, "high": r.high,
                            "low": r.low, "close": r.close, "volume": r.volume})
    return {"symbol": symbol, "interval": interval, "candles": candles, "count": len(candles)}


# What can move a stock — each event carries a short ``label`` (for a compact
# marker) and a fuller ``detail`` (shown on hover). ``kind`` drives the legend
# colour/shape on the client.
_KIND_META = {
    "fill":   {"color": "#34d399", "shape": "arrowUp", "icon": "🟢", "name": "Trade"},
    "signal": {"color": "#60a5fa", "shape": "circle",  "icon": "🔵", "name": "Signal"},
    "sme":    {"color": "#a78bfa", "shape": "square",  "icon": "🟣", "name": "Expert note"},
    "news":   {"color": "#fbbf24", "shape": "circle",  "icon": "📰", "name": "News"},
    "volume": {"color": "#f97316", "shape": "circle",  "icon": "📊", "name": "Volume spike"},
    "move":   {"color": "#e879f9", "shape": "circle",  "icon": "⚡", "name": "Big move"},
}


@router.get("/annotations")
def annotations(request: Request, symbol: str = Query(...),
                interval: str = Query("1d")):
    if not _valid_symbol(symbol):
        return {"error": "invalid symbol"}
    if interval not in _INTERVALS:
        interval = "1d"
    markers: list[dict] = []

    def add(kind, ts, label, detail, position):
        meta = _KIND_META.get(kind, {})
        markers.append({
            "time": _epoch(ts), "kind": kind, "position": position,
            "color": meta.get("color", "#94a3b8"), "shape": meta.get("shape", "circle"),
            "label": label[:48], "detail": detail[:240],
        })

    with session_scope() as s:
        for fill, order in s.execute(
            select(Fill, Order).join(Order, Fill.order_id == Order.id)
            .where(Order.symbol == symbol).order_by(Fill.id.desc()).limit(80)
        ).all():
            buy = (order.side or "").upper() == "BUY"
            add("fill", fill.ts, f"{order.side} {fill.qty}",
                f"Trade: {order.side} {fill.qty} @ ₹{round(fill.price, 2)} (fees ₹{round(fill.fees, 2)})",
                "belowBar" if buy else "aboveBar")
        for sg in s.execute(
            select(Signal).where(Signal.symbol == symbol).order_by(Signal.id.desc()).limit(60)
        ).scalars().all():
            add("signal", sg.ts, f"{sg.strategy}",
                f"Signal — {sg.strategy} turned {sg.stance} (conviction {round(float(sg.conviction or 0), 2)})",
                "aboveBar")
        for o in s.execute(
            select(SmeOpinion).where(SmeOpinion.symbol == symbol).order_by(SmeOpinion.id.desc()).limit(40)
        ).scalars().all():
            rat = (o.rationale or "").strip().split("\n")[0]
            add("sme", o.ts, f"{o.sme}: {o.stance}",
                f"{o.sme} — {o.stance} ({round(float(o.conviction or 0), 2)}). {rat}",
                "belowBar")
        for n in s.execute(
            select(NewsItem).order_by(NewsItem.id.desc()).limit(200)
        ).scalars().all():
            if symbol in (n.tickers or []):
                kind_tag = (n.event_type or "general")
                add("news", n.ts, (n.title or "")[:48],
                    f"News ({kind_tag}) · {n.source}: {(n.title or '')}",
                    "aboveBar")

        # Price-derived events: volume spikes and big daily moves from the bars
        # themselves — real factors that moved the stock, on the right date.
        bars = s.execute(
            select(Ohlcv).where(Ohlcv.symbol == symbol, Ohlcv.interval == interval)
            .order_by(Ohlcv.ts.desc()).limit(260)
        ).scalars().all()
    bars = list(reversed(bars))
    if len(bars) >= 25:
        vols = [float(b.volume or 0) for b in bars]
        for i in range(20, len(bars)):
            window = vols[i - 20:i]
            mean = sum(window) / len(window)
            sd = (sum((v - mean) ** 2 for v in window) / len(window)) ** 0.5
            z = (vols[i] - mean) / sd if sd > 0 else 0.0
            if z >= 3.0:
                add("volume", bars[i].ts, f"vol ×{round(vols[i]/mean, 1) if mean else 0}",
                    f"Volume spike: {round(z, 1)}σ above its 20-day average — unusual activity.",
                    "belowBar")
            prev = float(bars[i - 1].close or 0)
            cur = float(bars[i].close or 0)
            if prev > 0:
                ret = (cur - prev) / prev
                # 5–40% = a real outsized session; beyond that it is almost
                # always a split/adjustment artifact, so skip it.
                if 0.05 <= abs(ret) <= 0.40:
                    add("move", bars[i].ts, f"{'+' if ret>0 else ''}{round(ret*100, 1)}%",
                        f"Big move: closed {round(ret*100, 1)}% vs the prior day.",
                        "aboveBar")

    markers.sort(key=lambda m: m["time"])
    legend = [{"kind": k, "color": v["color"], "icon": v["icon"], "name": v["name"]}
              for k, v in _KIND_META.items()]
    return {"symbol": symbol, "markers": markers, "count": len(markers), "legend": legend}


# --------------------------------------------------------------------------- #
# Portfolio: trade blotter + equity curve
# --------------------------------------------------------------------------- #
@router.get("/trades")
def trades(request: Request, limit: int = Query(100, ge=1, le=500)):
    out: list[dict] = []
    with session_scope() as s:
        rows = s.execute(
            select(Fill, Order).join(Order, Fill.order_id == Order.id)
            .order_by(Fill.id.desc()).limit(limit)
        ).all()
        dec_ids = {o.decision_id for _, o in rows if o.decision_id}
        decs = {}
        if dec_ids:
            for d in s.execute(select(Decision).where(Decision.id.in_(dec_ids))).scalars().all():
                decs[d.id] = d
        for fill, order in rows:
            d = decs.get(order.decision_id)
            out.append({
                "ts": fill.ts.isoformat() if fill.ts else None,
                "symbol": order.symbol, "side": order.side, "qty": fill.qty,
                "price": round(fill.price, 2), "fees": round(fill.fees, 2),
                "value": round(fill.qty * fill.price, 2),
                "account": order.account, "broker": order.broker,
                "rationale": (d.rationale if d else "") or "",
                "why": (d.contributors if d else {}) or {},
            })
    return {"trades": out, "count": len(out)}


@router.get("/equity_curve")
def equity_curve(request: Request,
                 account: str = Query("paper"),
                 limit: int = Query(365, ge=1, le=2000)):
    if not _valid_symbol(account):
        return {"error": "invalid account"}
    with session_scope() as s:
        rows = s.execute(
            select(PnlDaily).where(PnlDaily.account == account)
            .order_by(PnlDaily.day.desc()).limit(limit)
        ).scalars().all()
    points = [{"day": r.day.isoformat(), "time": int(time.mktime(r.day.timetuple())),
               "equity": round(r.equity, 2), "net": round(r.net, 2),
               "drawdown": round(r.drawdown, 4)} for r in reversed(rows)]
    return {"account": account, "points": points, "count": len(points)}


# --------------------------------------------------------------------------- #
# Activity log: every order + the full "why" behind it
# --------------------------------------------------------------------------- #
@router.get("/activity")
def activity(request: Request, limit: int = Query(50, ge=1, le=200)):
    """Per-order audit trail: what we did and *why* — the CIO rationale, the
    contributing SME opinions (stance/conviction/rationale/risks), the strategy
    signals that fired (with their feature reasoning), and the risk rules that
    were applied. This is the dashboard "Activity" tab's data source."""
    out: list[dict] = []
    with session_scope() as s:
        rows = s.execute(
            select(Fill, Order).join(Order, Fill.order_id == Order.id)
            .order_by(Fill.id.desc()).limit(limit)
        ).all()
        dec_ids = {o.decision_id for _, o in rows if o.decision_id}
        decs: dict[int, Decision] = {}
        if dec_ids:
            for d in s.execute(select(Decision).where(Decision.id.in_(dec_ids))).scalars().all():
                decs[d.id] = d
        for fill, order in rows:
            d = decs.get(order.decision_id)
            why: dict = {"sme": [], "signals": [], "rules": []}
            if d is not None:
                window_start = (d.ts or datetime.utcnow()) - timedelta(days=2)
                ops = s.execute(
                    select(SmeOpinion).where(
                        SmeOpinion.symbol == order.symbol,
                        SmeOpinion.ts <= d.ts, SmeOpinion.ts >= window_start,
                    ).order_by(SmeOpinion.id.desc()).limit(14)
                ).scalars().all()
                seen_sme: set[str] = set()
                for o in ops:
                    if o.sme in seen_sme:
                        continue
                    seen_sme.add(o.sme)
                    why["sme"].append({
                        "sme": o.sme, "stance": o.stance,
                        "conviction": round(o.conviction, 2),
                        "horizon": o.horizon,
                        "rationale": (o.rationale or "")[:280],
                        "key_risks": (o.key_risks or [])[:3],
                    })
                sigs = s.execute(
                    select(Signal).where(
                        Signal.symbol == order.symbol,
                        Signal.ts <= d.ts, Signal.ts >= window_start,
                    ).order_by(Signal.id.desc()).limit(24)
                ).scalars().all()
                seen_strat: set[str] = set()
                for sg in sigs:
                    if sg.strategy in seen_strat:
                        continue
                    seen_strat.add(sg.strategy)
                    why["signals"].append({
                        "strategy": sg.strategy, "stance": sg.stance,
                        "conviction": round(sg.conviction, 2),
                        "features": sg.features or {},
                    })
                why["rules"] = d.rules_applied or []
            out.append({
                "ts": fill.ts.isoformat() if fill.ts else None,
                "symbol": order.symbol, "side": order.side, "qty": fill.qty,
                "price": round(fill.price, 2), "value": round(fill.qty * fill.price, 2),
                "fees": round(fill.fees, 2), "status": order.status,
                "decision_id": order.decision_id,
                "action": (d.action if d else order.side),
                "rationale": (d.rationale if d else "") or "",
                "contributors": (d.contributors if d else {}) or {},
                "why": why,
            })
    return {"activity": out, "count": len(out)}


@router.get("/summary")
def summary(request: Request):
    """Deterministic 'what's going on right now' — same numbers as the digest
    emails. Drives the Activity tab header."""
    from ats.services.dashboard.summary import live_summary

    return live_summary(_orch(request))


# --------------------------------------------------------------------------- #
# News feed + reader
# --------------------------------------------------------------------------- #
@router.get("/news")
def news(request: Request,
         limit: int = Query(40, ge=1, le=100),
         offset: int = Query(0, ge=0, le=5000),
         ticker: str = Query("", max_length=24),
         sentiment: str = Query("", max_length=12)):
    if ticker and not _valid_symbol(ticker):
        return {"error": "invalid ticker"}
    sentiment = sentiment.lower()
    if sentiment and sentiment not in {"positive", "negative", "neutral"}:
        return {"error": "invalid sentiment"}
    items: list[dict] = []
    with session_scope() as s:
        q = select(NewsItem).order_by(NewsItem.id.desc()).limit(400)
        rows = s.execute(q).scalars().all()
        # sentiment per news id (one query)
        ids = [n.id for n in rows]
        sent_by_news: dict[int, dict] = {}
        if ids:
            for sc in s.execute(
                select(SentimentScore).where(SentimentScore.news_id.in_(ids))
            ).scalars().all():
                sent_by_news.setdefault(sc.news_id, {"label": sc.label, "score": round(sc.score, 3)})
        for n in rows:
            tickers = n.tickers or []
            if ticker and ticker not in tickers:
                continue
            sent = sent_by_news.get(n.id)
            if sentiment and (not sent or sent["label"] != sentiment):
                continue
            items.append({
                "id": n.id, "ts": n.ts.isoformat() if n.ts else None, "source": n.source,
                "title": n.title, "url": n.url, "tickers": tickers,
                "event_type": n.event_type, "sentiment": sent,
                "summary": (n.body or "")[:240],
            })
    page = items[offset: offset + limit]
    return {"news": page, "count": len(page), "total": len(items)}


@router.get("/news/{news_id}")
def news_reader(news_id: int, request: Request):
    with session_scope() as s:
        n = s.get(NewsItem, news_id)
        if n is None:
            return {"error": "not found", "id": news_id}
        sent = s.execute(
            select(SentimentScore).where(SentimentScore.news_id == news_id).limit(1)
        ).scalar_one_or_none()
        return {
            "id": n.id, "ts": n.ts.isoformat() if n.ts else None, "source": n.source,
            "title": n.title, "url": n.url, "body": n.body or "", "tickers": n.tickers or [],
            "event_type": n.event_type,
            "sentiment": {"label": sent.label, "score": round(sent.score, 3)} if sent else None,
        }


# --------------------------------------------------------------------------- #
# LLM brief (cached, refreshable)
# --------------------------------------------------------------------------- #
_brief_cache: dict = {"ts": 0.0, "text": "", "real": False}
_BRIEF_TTL = 120  # seconds


def _templated_brief(snap: dict, opps: list[dict]) -> str:
    st = snap.get("state", {})
    pf = snap.get("portfolio", {})
    lines = [
        f"Mode {st.get('mode','?')} · regime {st.get('regime','?')} · "
        f"equity ₹{pf.get('equity','?')} (unrealized ₹{pf.get('unrealized_pnl',0)}).",
    ]
    if opps:
        top = opps[0]
        lines.append(f"Top idea: {top['symbol']} — {top['setup']} "
                     f"({top['conviction']} conviction). {top['thesis']}")
        if len(opps) > 1:
            lines.append("Also watching: " + ", ".join(o["symbol"] for o in opps[1:5]) + ".")
    else:
        lines.append("No high-conviction opportunities right now; the algorithms are watching.")
    wn = snap.get("watchlist_news", [])
    if wn:
        lines.append(f"{len(wn)} news item(s) touch your watchlist; see the News page.")
    return " ".join(lines)


@router.get("/brief")
def brief(request: Request, refresh: bool = Query(False)):
    now = time.time()
    if not refresh and _brief_cache["text"] and now - _brief_cache["ts"] < _BRIEF_TTL:
        return {"brief": _brief_cache["text"], "cached": True, "real": _brief_cache["real"]}

    from ats.services.dashboard.snapshot import build_snapshot

    orch = _orch(request)
    snap = build_snapshot(orch)
    opps = build_opportunities(orch, limit=6)
    text = _templated_brief(snap, opps)
    real = False
    try:
        from ats.services.agents.llm_client import build_llm_client

        client = build_llm_client("cio")
        if getattr(client, "is_real", False):
            system = ("You are the CIO of an Indian-equity paper-trading desk. Write a "
                      "crisp 4-6 sentence morning brief in plain English: what the system "
                      "sees, the top opportunities and why, portfolio status, and key risks. "
                      "No fabricated numbers — use only what is provided.")
            payload = {
                "state": snap.get("state", {}), "portfolio": snap.get("portfolio", {}),
                "opportunities": opps,
                "watchlist_news": [w.get("title") for w in snap.get("watchlist_news", [])][:6],
            }
            out = client.chat(system, [{"role": "user", "content": str(payload)}])
            if out and out.strip():
                text, real = out.strip(), True
    except Exception as exc:  # noqa: BLE001
        log.warning("brief_llm_failed", extra={"error": str(exc)})

    _brief_cache.update({"ts": now, "text": text, "real": real})
    return {"brief": text, "cached": False, "real": real, "opportunities": opps}


# --------------------------------------------------------------------------- #
# Watchlist editing (toggles Instrument.active)
# --------------------------------------------------------------------------- #
class WatchlistBody(BaseModel):
    symbol: str = Field(..., max_length=24)
    action: str = Field("add")  # add | remove


@router.get("/watchlist")
def get_watchlist(request: Request):
    orch = _orch(request)
    md = orch.get("market_data") if orch else None
    if md and hasattr(md, "watchlist"):
        syms = md.watchlist()
    else:
        with session_scope() as s:
            syms = list(s.execute(select(Instrument.symbol).where(Instrument.active.is_(True))).scalars().all())
    return {"watchlist": sorted(syms), "count": len(syms)}


@router.post("/watchlist")
def edit_watchlist(body: WatchlistBody, request: Request):
    sym = body.symbol.strip().upper()
    if not _valid_symbol(sym):
        return {"error": "invalid symbol"}
    if body.action not in {"add", "remove"}:
        return {"error": "invalid action"}
    with session_scope() as s:
        inst = s.get(Instrument, sym)
        if body.action == "add":
            if inst is None:
                s.add(Instrument(symbol=sym, name=sym, active=True))
            else:
                inst.active = True
        else:
            if inst is not None:
                inst.active = False
    orch = _orch(request)
    md = orch.get("market_data") if orch else None
    if md and hasattr(md, "reload_watchlist"):
        try:
            md.reload_watchlist()
        except Exception as exc:  # noqa: BLE001
            log.warning("watchlist_reload_failed", extra={"error": str(exc)})
    return get_watchlist(request)


# --------------------------------------------------------------------------- #
# "Explain this" — short plain-English explanation (LLM if available)
# --------------------------------------------------------------------------- #
class ExplainBody(BaseModel):
    context: str = Field(..., max_length=600)
    question: str = Field("Explain this in plain English for a novice investor.", max_length=200)


@router.post("/explain")
def explain(body: ExplainBody):
    ctx = body.context.strip()[:600]
    if not ctx:
        return {"text": "Nothing to explain.", "real": False}
    text = f"{ctx} — in short: this is a signal the system surfaced; review the thesis, the key risks, and the invalidation level before acting. Paper-only, not advice."
    real = False
    try:
        from ats.services.agents.llm_client import build_llm_client

        client = build_llm_client("cio")
        if getattr(client, "is_real", False):
            out = client.chat(
                "You explain trading concepts to a novice in 2-3 plain sentences. "
                "No fabricated numbers; never give financial advice.",
                [{"role": "user", "content": f"{body.question}\n\nContext: {ctx}"}],
            )
            if out and out.strip():
                text, real = out.strip(), True
    except Exception as exc:  # noqa: BLE001
        log.warning("explain_failed", extra={"error": str(exc)})
    return {"text": text, "real": real}


# --------------------------------------------------------------------------- #
# Daily digest archive (from the equity curve + that day's activity)
# --------------------------------------------------------------------------- #
@router.get("/digest")
def digest(request: Request, days: int = Query(14, ge=1, le=120)):
    out: list[dict] = []
    with session_scope() as s:
        rows = s.execute(
            select(PnlDaily).where(PnlDaily.account == "paper")
            .order_by(PnlDaily.day.desc()).limit(days)
        ).scalars().all()
        for r in rows:
            move = "up" if r.net > 0 else "down" if r.net < 0 else "flat"
            out.append({
                "day": r.day.isoformat(), "equity": round(r.equity, 2),
                "net": round(r.net, 2), "drawdown": round(r.drawdown, 4), "move": move,
                "summary": f"Equity ₹{round(r.equity,0):,.0f}, day P&L ₹{round(r.net,0):,.0f} ({move}).",
            })
    return {"digest": out, "count": len(out)}
