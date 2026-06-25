"""Deterministic "what's going on right now" summary.

Shared by the dashboard (`/api/summary`) and the intraday email digests. It is
intentionally LLM-free so it always renders and always sends, even when the
model provider is rate-limited or offline. It reads the same snapshot the rest
of the dashboard uses, so the numbers match what the operator sees on screen.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.models import PnlDaily
from ats.services.dashboard.snapshot import build_snapshot

_MOVE_THRESHOLD_PCT = 3.0


def _day_net(account: str = "paper") -> float:
    with session_scope() as s:
        row = s.execute(
            select(PnlDaily).where(PnlDaily.account == account, PnlDaily.day == date.today())
        ).scalar_one_or_none()
        return float(row.net) if row else 0.0


def _movers(positions: list[dict], threshold_pct: float = _MOVE_THRESHOLD_PCT) -> list[dict]:
    out: list[dict] = []
    for p in positions:
        cost = abs(p.get("avg_price", 0.0) * p.get("qty", 0))
        if cost <= 0:
            continue
        pct = 100.0 * p.get("unrealized_pnl", 0.0) / cost
        if abs(pct) >= threshold_pct:
            out.append({"symbol": p["symbol"], "pct": round(pct, 1),
                        "unrealized_pnl": round(p.get("unrealized_pnl", 0.0), 0)})
    out.sort(key=lambda m: abs(m["pct"]), reverse=True)
    return out


def live_summary(orch) -> dict:
    """Structured snapshot of the desk's current state."""
    snap = build_snapshot(orch)
    st = snap.get("state", {})
    pf = snap.get("portfolio", {})
    positions = pf.get("positions", [])
    opps = snap.get("opportunities", []) or []
    data_status = st.get("data_status", {}) or {}
    return {
        "mode": st.get("mode"),
        "kill_switch": st.get("kill_switch"),
        "regime": st.get("regime"),
        "feed": data_status.get("mode", st.get("data_source")),
        "equity": pf.get("equity", 0.0),
        "cash": pf.get("cash", 0.0),
        "unrealized_pnl": pf.get("unrealized_pnl", 0.0),
        "realized_pnl": pf.get("realized_pnl", 0.0),
        "day_net": round(_day_net(), 2),
        "open_positions": len(positions),
        "movers": _movers(positions),
        "top_opportunities": [
            {"symbol": o.get("symbol"), "score": o.get("score"), "thesis": o.get("thesis", "")[:80]}
            for o in opps[:3]
        ],
    }


def digest_text(orch, label: str = "Update") -> tuple[str, dict]:
    """A compact multi-line email/notify body + the structured payload."""
    s = live_summary(orch)
    cur = "Rs"
    lines = [
        f"{label} — {date.today().isoformat()}",
        f"Mode {s['mode']} | kill={'ON' if s['kill_switch'] else 'off'} | "
        f"regime {s['regime']} | feed {s['feed']}",
        f"Equity {cur}{s['equity']:,.0f} | day P&L {cur}{s['day_net']:+,.0f} | "
        f"unrealized {cur}{s['unrealized_pnl']:+,.0f} | cash {cur}{s['cash']:,.0f}",
        f"{s['open_positions']} open positions.",
    ]
    if s["movers"]:
        movers = ", ".join(f"{m['symbol']} {m['pct']:+.1f}%" for m in s["movers"])
        lines.append(f"Big moves: {movers}")
    if s["top_opportunities"]:
        tops = "; ".join(
            f"{o['symbol']} ({o['score']})" if o.get("score") is not None else str(o["symbol"])
            for o in s["top_opportunities"]
        )
        lines.append(f"Top opportunities: {tops}")
    return "\n".join(lines), s
