"""Research agent roles (plan §3.2): prompts, grounding, output contracts.

Five roles, small roster by design. Each role is a *scheduled* LLM call:
a system prompt (below), a grounded DATA envelope assembled from what the
system already knows (news archive, regime, sleeves, fundamentals — no new
spend), and a strict JSON output contract parsed by ``parse_output``.

Roles produce research artifacts only — hypotheses, notes, one bounded
allocation recommendation. Nothing here touches orders; that is the whole
point of the slow loop.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Fundamental, NewsItem, Position, SentimentScore, SleevePnl

log = get_logger("ats.research.roles")

MAX_CONTEXT_CHARS = 18_000  # keep autonomous research calls cheap by construction

_JSON_RULES = (
    "Answer with a single JSON object and nothing else - no prose, no code fences. "
    "If you lack evidence for a field, use an empty list/string rather than inventing facts."
)

ROLES: dict[str, dict] = {
    "macro_analyst": {
        "name": "Macro Analyst",
        "cadence": "weekly",
        "system": (
            "You are the macro analyst of a small Indian systematic fund. You digest "
            "RBI/fiscal/global inputs and the week's market news into regime commentary "
            "the allocation committee can use. You never recommend trades; you name "
            "conditions and risks. Be specific to the DATA provided; cite items you use. "
            + _JSON_RULES
            + ' Schema: {"commentary": str, "regime_view": str, "risk_flags": [str]}'
        ),
    },
    "fundamentals_analyst": {
        "name": "Fundamentals Analyst",
        "cadence": "weekly",
        "system": (
            "You are the fundamentals analyst of a small Indian systematic fund. Review "
            "the held and watchlist names in DATA (ratios, recent news). Flag names whose "
            "fundamentals or disclosures look deteriorating (red_flags) and names that "
            "remain sound (holds). You never size or time trades. "
            + _JSON_RULES
            + ' Schema: {"notes": str, "holds": [str], "red_flags": [{"symbol": str, "reason": str}]}'
        ),
    },
    "strategy_researcher": {
        "name": "Strategy Researcher",
        "cadence": "weekly",
        "system": (
            "You are the strategy researcher of a small Indian systematic fund. Mine the "
            "DATA (news archive digest, regime, sleeve performance) for candidate trading "
            "rules. Propose at most 2 hypotheses per pass, and only when the evidence is "
            "genuinely suggestive - zero is a fine answer. Each hypothesis MUST have an "
            "exact, backtestable rule (entry, exit, universe, holding period) - if you "
            "cannot specify it precisely, do not propose it. "
            + _JSON_RULES
            + ' Schema: {"hypotheses": [{"title": str, "thesis": str, "rule": str,'
              ' "params": object, "universe": [str], "evidence": str}]}'
        ),
    },
    "risk_reviewer": {
        "name": "Risk Reviewer",
        "cadence": "monthly",
        "system": (
            "You are the adversarial risk reviewer of a small Indian systematic fund. "
            "Attack the current sleeves using the DATA: drawdowns, correlation creep, "
            "regime dependence, crowding, 'what would break this'. Name the weakest "
            "sleeve and why. You never propose trades. "
            + _JSON_RULES
            + ' Schema: {"summary": str, "attacks": [{"sleeve": str, "weakness": str, "evidence": str}]}'
        ),
    },
    "committee": {
        "name": "Allocation Committee (CIO)",
        "cadence": "monthly",
        "system": (
            "You are the CIO synthesizing the month's research notes, risk review and "
            "sleeve performance (DATA) into ONE allocation recommendation for the human "
            "operator to approve. Express it as small tilts per sleeve id in [-0.10, "
            "+0.10] (fraction of current weight, 0 = unchanged). Tilt only sleeves you "
            "can justify from DATA; guardrails are outside your authority. "
            + _JSON_RULES
            + ' Schema: {"summary": str, "rationale": str, "tilts": {"<strategy_id>": float}}'
        ),
    },
}

WEEKLY_ROLES = [r for r, spec in ROLES.items() if spec["cadence"] == "weekly"]
MONTHLY_ROLES = [r for r, spec in ROLES.items() if spec["cadence"] == "monthly"]


# --- grounded context builders ---------------------------------------------------
def news_digest(days: int = 7, limit: int = 40) -> list[str]:
    """Recent archive headlines with per-item sentiment, newest first."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    with session_scope() as s:
        rows = s.execute(
            select(NewsItem).where(NewsItem.ts >= cutoff)
            .order_by(NewsItem.ts.desc()).limit(limit)
        ).scalars().all()
        sent = dict(
            s.execute(
                select(SentimentScore.news_id, func.avg(SentimentScore.score))
                .where(SentimentScore.ts >= cutoff, SentimentScore.news_id.isnot(None))
                .group_by(SentimentScore.news_id)
            ).all()
        )
    out = []
    for n in rows:
        score = sent.get(n.id)
        tick = ",".join(n.tickers or [])
        tag = f" [{tick}]" if tick else ""
        sc = f" (sent {score:+.2f})" if score is not None else ""
        out.append(f"{n.ts.date().isoformat()} {n.title.strip()[:140]}{tag}{sc}")
    return out


def sentiment_by_symbol(days: int = 7, min_count: int = 2) -> dict[str, float]:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    with session_scope() as s:
        rows = s.execute(
            select(SentimentScore.symbol, func.avg(SentimentScore.score), func.count())
            .where(SentimentScore.ts >= cutoff)
            .group_by(SentimentScore.symbol)
        ).all()
    return {sym: round(float(avg), 3) for sym, avg, n in rows if n >= min_count and sym}


def sleeve_digest(days: int = 90) -> list[dict]:
    """Recent per-sleeve performance from the persisted virtual books."""
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
    with session_scope() as s:
        rows = s.execute(
            select(SleevePnl).where(SleevePnl.day >= cutoff)
            .order_by(SleevePnl.strategy, SleevePnl.day)
        ).scalars().all()
    by: dict[str, list[SleevePnl]] = {}
    for r in rows:
        by.setdefault(r.strategy, []).append(r)
    out = []
    for sid, series in by.items():
        rets = [r.ret for r in series]
        n = len(rets)
        if n < 5:
            continue
        mean = sum(rets) / n
        var = sum((x - mean) ** 2 for x in rets) / max(1, n - 1)
        sharpe = (mean / (var ** 0.5) * (252 ** 0.5)) if var > 0 else 0.0
        eq = [r.equity for r in series]
        peak, max_dd = eq[0] or 1.0, 0.0
        for v in eq:
            peak = max(peak, v)
            if peak > 0:
                max_dd = min(max_dd, v / peak - 1.0)
        out.append({
            "strategy": sid, "days": n,
            "cum_return": round(series[-1].equity / (series[0].equity or 1.0) - 1.0, 4),
            "sharpe": round(sharpe, 2), "max_dd": round(max_dd, 4),
        })
    out.sort(key=lambda r: -r["sharpe"])
    return out


def holdings_and_fundamentals(account: str = "paper", extra: list[str] | None = None) -> list[dict]:
    with session_scope() as s:
        held = [p.symbol for p in s.execute(
            select(Position).where(Position.account == account, Position.qty != 0)
        ).scalars().all()]
        symbols = list(dict.fromkeys(held + (extra or [])))[:20]
        out = []
        for sym in symbols:
            f = s.execute(
                select(Fundamental).where(Fundamental.symbol == sym)
                .order_by(Fundamental.as_of.desc()).limit(1)
            ).scalar_one_or_none()
            row = {"symbol": sym, "held": sym in held}
            if f is not None:
                row.update({"pe": f.pe, "pb": f.pb, "roe": f.roe,
                            "debt_to_equity": f.debt_to_equity,
                            "profit_margin": f.profit_margin})
            out.append(row)
        return out


def build_context(role: str, orchestrator=None, extra: dict | None = None) -> dict:
    """The grounded DATA envelope for one role run. Cheap by construction:
    everything comes from tables the system already fills."""
    ctx: dict = {"as_of": datetime.now(timezone.utc).isoformat()}
    regime = orchestrator.get("regime") if orchestrator else None
    if regime is not None:
        try:
            ctx["regime"] = regime.current().label
        except Exception:  # noqa: BLE001
            pass

    if role in ("macro_analyst", "strategy_researcher"):
        ctx["news"] = news_digest(days=7, limit=40)
        ctx["sentiment_by_symbol"] = sentiment_by_symbol()
    if role in ("strategy_researcher", "risk_reviewer", "committee"):
        ctx["sleeves"] = sleeve_digest()
    if role == "fundamentals_analyst":
        ctx["names"] = holdings_and_fundamentals()
        ctx["news"] = news_digest(days=7, limit=25)
    if role == "committee":
        ctx["recent_notes"] = (extra or {}).get("recent_notes", [])
        ctx["tradeable_sleeves"] = (extra or {}).get("tradeable_sleeves", [])
    if extra:
        for k, v in extra.items():
            ctx.setdefault(k, v)
    return ctx


def render_user_message(role: str, ctx: dict) -> str:
    """DATA envelope + task line, truncated to the research context budget."""
    data = json.dumps(ctx, ensure_ascii=False, default=str, indent=1)
    if len(data) > MAX_CONTEXT_CHARS:
        data = data[:MAX_CONTEXT_CHARS] + "\n…(truncated)"
    task = {
        "macro_analyst": "Write this week's regime commentary and risk flags.",
        "fundamentals_analyst": "Review the names in DATA; list holds and red flags.",
        "strategy_researcher": "Propose 0-2 precisely specified hypotheses from DATA.",
        "risk_reviewer": "Attack the current sleeves; where does this book break?",
        "committee": "Produce this month's bounded allocation recommendation.",
    }[role]
    return f"DATA:\n{data}\n\nTASK: {task}"


# --- output parsing ---------------------------------------------------------------
def parse_output(text: str) -> dict | None:
    """Extract the JSON object from a model reply; None if unparseable.

    Tolerates code fences and leading prose (the mock provider answers in
    plain text — that returns None and the caller stores the raw reply)."""
    if not text:
        return None
    cleaned = re.sub(r"^\s*```(?:json)?|```\s*$", "", text.strip(), flags=re.MULTILINE)
    try:
        out = json.loads(cleaned)
        return out if isinstance(out, dict) else None
    except Exception:  # noqa: BLE001
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                out = json.loads(match.group(0))
                return out if isinstance(out, dict) else None
            except Exception:  # noqa: BLE001
                return None
    return None


def clamp_tilts(tilts: dict, max_tilt: float, known_ids: set[str] | None = None) -> dict:
    """Bound committee tilts to ±max_tilt and drop unknown/invalid entries."""
    out: dict[str, float] = {}
    for sid, val in (tilts or {}).items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if known_ids is not None and sid not in known_ids:
            continue
        if v == 0.0:
            continue
        out[sid] = round(max(-max_tilt, min(max_tilt, v)), 4)
    return out
