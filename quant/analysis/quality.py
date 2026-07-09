"""Fundamental quality scores — pure math over statement dicts.

Piotroski F-Score, dividend payout ratio, Altman Z-Score (manufacturing form),
and the "top dividend" safety screen from the reference docs. All functions
take plain dicts of statement lines (keys match ``FinancialStatements``
columns) and never fetch anything. **A missing input is a failed/None result,
never a guessed value or a free point** — the whole point of the exercise is an
honest score.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FScore:
    score: int                       # 0..9 passed checks
    checks: list[dict] = field(default_factory=list)  # {name, passed, value}
    max_score: int = 9

    def as_dict(self) -> dict:
        return {"score": self.score, "max": self.max_score, "checks": self.checks}


def _num(d: dict, key: str) -> float | None:
    v = d.get(key)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # drop NaN


def _ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _check(name: str, passed: bool, value) -> dict:
    if isinstance(value, float):
        value = round(value, 6)
    return {"name": name, "passed": bool(passed), "value": value}


def piotroski_f(cur: dict, prev: dict) -> FScore:
    """The 9-point Piotroski F-Score from consecutive annual statements.

    Profitability (4): ROA>0, CFO>0, ΔROA>0, accruals (CFO>NI).
    Leverage/liquidity (3): Δleverage<0, Δcurrent-ratio>0, no dilution.
    Efficiency (2): Δgross-margin>0, Δasset-turnover>0.
    Every check with a missing input fails and is reported.
    """
    roa_c = _ratio(_num(cur, "net_income"), _num(cur, "total_assets"))
    roa_p = _ratio(_num(prev, "net_income"), _num(prev, "total_assets"))
    cfo_c = _num(cur, "cfo")
    ni_c = _num(cur, "net_income")
    lev_c = _ratio(_num(cur, "total_debt"), _num(cur, "total_assets"))
    lev_p = _ratio(_num(prev, "total_debt"), _num(prev, "total_assets"))
    cr_c = _ratio(_num(cur, "current_assets"), _num(cur, "current_liabilities"))
    cr_p = _ratio(_num(prev, "current_assets"), _num(prev, "current_liabilities"))
    sh_c = _num(cur, "shares_outstanding")
    sh_p = _num(prev, "shares_outstanding")
    gm_c = _num(cur, "gross_margin")
    gm_p = _num(prev, "gross_margin")
    at_c = _ratio(_num(cur, "revenue"), _num(cur, "total_assets"))
    at_p = _ratio(_num(prev, "revenue"), _num(prev, "total_assets"))

    checks = [
        _check("roa_positive", roa_c is not None and roa_c > 0, roa_c),
        _check("cfo_positive", cfo_c is not None and cfo_c > 0, cfo_c),
        _check("roa_increasing", roa_c is not None and roa_p is not None and roa_c > roa_p, roa_c),
        _check("accruals_cfo_gt_ni", cfo_c is not None and ni_c is not None and cfo_c > ni_c, None if cfo_c is None or ni_c is None else cfo_c - ni_c),
        _check("leverage_decreasing", lev_c is not None and lev_p is not None and lev_c < lev_p, lev_c),
        _check("current_ratio_increasing", cr_c is not None and cr_p is not None and cr_c > cr_p, cr_c),
        _check("no_dilution", sh_c is not None and sh_p is not None and sh_c <= sh_p, sh_c),
        _check("gross_margin_increasing", gm_c is not None and gm_p is not None and gm_c > gm_p, gm_c),
        _check("asset_turnover_increasing", at_c is not None and at_p is not None and at_c > at_p, at_c),
    ]
    return FScore(score=sum(1 for c in checks if c["passed"]), checks=checks)


def payout_ratio(dividends_paid: float | None, net_income: float | None) -> float | None:
    """Dividends / net income. ``None`` when NI is missing or ≤ 0 (a payout
    ratio on zero/negative earnings is meaningless). Dividends are taken as a
    magnitude (cash-flow statements report them as a negative outflow)."""
    if dividends_paid is None or net_income is None or net_income <= 0:
        return None
    return abs(dividends_paid) / net_income


def altman_z(cur: dict, market_cap: float | None) -> float | None:
    """Altman Z-Score (original manufacturing form).

    ``Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5`` where
    X1=working capital/TA, X2=retained earnings/TA, X3=EBIT/TA,
    X4=market cap/total liabilities, X5=revenue/TA. Returns ``None`` if any
    input is missing (including a zero/absent total-assets or total-liabilities
    denominator) — we do not partial-credit a solvency score.
    """
    ta = _num(cur, "total_assets")
    tl = _num(cur, "total_liabilities")
    ca = _num(cur, "current_assets")
    cl = _num(cur, "current_liabilities")
    re = _num(cur, "retained_earnings")
    ebit = _num(cur, "ebit")
    rev = _num(cur, "revenue")
    mc = None if market_cap is None else float(market_cap)
    if None in (ta, tl, ca, cl, re, ebit, rev, mc) or ta <= 0 or tl <= 0:
        return None
    x1 = (ca - cl) / ta
    x2 = re / ta
    x3 = ebit / ta
    x4 = mc / tl
    x5 = rev / ta
    return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5


def altman_zone(z: float | None) -> str | None:
    """Distress (<1.81) / grey (1.81–2.99) / safe (≥2.99)."""
    if z is None:
        return None
    if z < 1.81:
        return "distress"
    if z < 2.99:
        return "grey"
    return "safe"


def dividend_safety(
    yield_pct: float | None,
    payout: float | None,
    f_score: int | None,
    growth_years: int | None,
) -> dict:
    """The 4-filter "top dividend" screen: high yield (≥4%), safe payout
    (≤60%), healthy (F≥7), growing (≥5 consecutive years). ``safe`` is the AND
    of all four; each filter is reported so a dividend trap (high yield, unsafe
    payout) is visible rather than hidden behind one flag."""
    is_high_yield = yield_pct is not None and yield_pct >= 0.04
    is_safe_payout = payout is not None and payout <= 0.60
    is_healthy = f_score is not None and f_score >= 7
    is_growing = growth_years is not None and growth_years >= 5
    return {
        "safe": bool(is_high_yield and is_safe_payout and is_healthy and is_growing),
        "checks": {
            "high_yield": bool(is_high_yield),
            "safe_payout": bool(is_safe_payout),
            "healthy_fscore": bool(is_healthy),
            "growing_5y": bool(is_growing),
        },
        "yield_pct": yield_pct,
        "payout": payout,
        "f_score": f_score,
        "growth_years": growth_years,
    }
