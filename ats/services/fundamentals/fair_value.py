"""Per-symbol fair value — the existing DCF engine wired to real statements.

Turns ``FinancialStatements`` (QA-5) into an intrinsic value with a mandatory
sensitivity grid and an explicit assumption set. **Refuses rather than guesses**:
returns ``None`` when there are < 2 annual statements, a non-positive base FCF,
or no share count — a bad DCF is worse than no DCF. Every number it does return
is labelled a model estimate and shown with its ± range on the dashboard.
"""

from __future__ import annotations

from ats.core.logging import get_logger
from quant.analysis.quality import piotroski_f
from quant.analysis.valuation import discounted_cash_flow, margin_of_safety

log = get_logger("ats.fair_value")

_WACC_DEFAULT = 0.12          # India equity discount rate (rough ERP + rf)
_TERMINAL_DEFAULT = 0.04
_YEARS = 5
_GROWTH_FLOOR, _GROWTH_CAP = 0.02, 0.15
_UNDERVALUED_MOS = 20.0       # margin-of-safety % thresholds for the verdict
_OVERVALUED_MOS = -20.0


def _fcf(st: dict) -> float | None:
    cfo, capex = st.get("cfo"), st.get("capex")
    if cfo is None or capex is None:
        return None
    return float(cfo) - float(capex)   # capex stored as a positive magnitude


def _cagr(chrono: list[float]) -> float:
    """FCF CAGR over the (oldest→newest) series, clamped to [floor, cap]."""
    if len(chrono) < 2 or chrono[0] <= 0 or chrono[-1] <= 0:
        g = 0.08
    else:
        n = len(chrono) - 1
        g = (chrono[-1] / chrono[0]) ** (1.0 / n) - 1.0
    return max(_GROWTH_FLOOR, min(_GROWTH_CAP, g))


def _per_share(base_fcf, growth, wacc, terminal, net_debt, shares) -> float:
    return discounted_cash_flow(
        base_fcf=base_fcf, growth_rate=growth, discount_rate=wacc,
        terminal_growth=terminal, years=_YEARS, net_debt=net_debt,
        shares_outstanding=shares,
    ).per_share_value


def fair_value(
    symbol: str,
    price: float | None = None,
    statements: list[dict] | None = None,
    *,
    wacc: float = _WACC_DEFAULT,
    terminal_growth: float = _TERMINAL_DEFAULT,
) -> dict | None:
    """Intrinsic value for ``symbol`` from its annual statements.

    ``statements`` (newest-first dicts) may be injected for tests; otherwise
    they are read from the DB. ``price`` (last close) drives the margin-of-
    safety verdict; without it the intrinsic is still returned with a
    ``no_price`` verdict. Returns ``None`` when inputs are too thin to trust.
    """
    if statements is None:
        from ats.services.fundamentals.statements import latest_statements
        statements = latest_statements(symbol, "annual", 4)
    if not statements or len(statements) < 2:
        return None

    # Free cash flow per year (newest-first); need at least 2 computable.
    fcfs = [f for f in (_fcf(st) for st in statements) if f is not None]
    if len(fcfs) < 2:
        return None
    recent = fcfs[:3]
    base_fcf = sum(recent) / len(recent)
    if base_fcf <= 0:                      # negative FCF trend: refuse
        return None

    chrono = list(reversed(fcfs))          # oldest -> newest for CAGR
    growth = _cagr(chrono)

    latest = statements[0]
    shares = latest.get("shares_outstanding")
    if shares is None or float(shares) <= 0:
        return None                        # no per-share basis: refuse
    shares = float(shares)
    nd = latest.get("net_debt")
    net_debt = float(nd) if nd is not None else float(latest.get("total_debt") or 0.0)

    # keep discount rate strictly above terminal across the whole grid
    terminal = min(terminal_growth, (wacc - 0.02) - 0.01)

    intrinsic = _per_share(base_fcf, growth, wacc, terminal, net_debt, shares)

    verdict, mos_pct = "no_price", None
    if price is not None and intrinsic > 0:
        mos_pct = round(margin_of_safety(intrinsic, float(price)) * 100.0, 2)
        if mos_pct >= _UNDERVALUED_MOS:
            verdict = "undervalued"
        elif mos_pct <= _OVERVALUED_MOS:
            verdict = "overvalued"
        else:
            verdict = "fair"

    # 3x3 sensitivity: wacc ±2% x growth ±5% (the range matters, not a point).
    wacc_axis = [round(wacc - 0.02, 4), round(wacc, 4), round(wacc + 0.02, 4)]
    growth_axis = [round(max(0.0, growth - 0.05), 4), round(growth, 4),
                   round(growth + 0.05, 4)]
    grid = [
        [round(_per_share(base_fcf, g, w, min(terminal, w - 0.03), net_debt, shares), 2)
         for g in growth_axis]
        for w in wacc_axis
    ]

    f = piotroski_f(statements[0], statements[1])

    return {
        "symbol": symbol,
        "intrinsic": round(intrinsic, 2),
        "price": None if price is None else round(float(price), 2),
        "margin_of_safety_pct": mos_pct,
        "verdict": verdict,
        "assumptions": {
            "base_fcf": round(base_fcf, 2),
            "growth": round(growth, 4),
            "wacc": round(wacc, 4),
            "terminal_growth": round(terminal, 4),
            "years": _YEARS,
            "net_debt": round(net_debt, 2),
            "shares_outstanding": round(shares, 2),
            "n_statements": len(statements),
        },
        "sensitivity": {"wacc": wacc_axis, "growth": growth_axis, "grid": grid},
        "quality": {"f_score": f.score, "f_max": f.max_score},
        "is_model_estimate": True,
    }
