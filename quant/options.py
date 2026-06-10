"""Options pricing and Greeks (roadmap Part 5, Phase 5; gates Part 7.7).

Black-Scholes-Merton for European options on dividend-paying underlyings,
the full Greeks, implied volatility, and a Cox-Ross-Rubinstein binomial
tree for American exercise. Pure ``math``-module functions (no scipy) so
they are dependency-light and trivially testable against textbook values.

Conventions
-----------
- ``t`` is time to expiry in YEARS (e.g. 30 calendar days -> 30/365).
- ``r`` and ``q`` (continuous dividend yield) are annualized decimals.
- ``sigma`` is annualized volatility as a decimal (0.20 = 20%).
- Theta is PER YEAR and negative for long options; divide by 365 for
  the per-calendar-day decay quoted on trading screens.
- Vega and rho are per 1.00 change (per 100 vol points / rate points);
  divide by 100 for the per-point convention.

The vol-premium sleeve (roadmap 7.7) builds on this module once an
options-chain data source exists: compare market IV against realized
vol, sell defined-risk structures when IV rank is high.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_SQRT_2 = math.sqrt(2.0)
_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT_2))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def _validate(spot: float, strike: float, t: float, sigma: float) -> None:
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if t < 0:
        raise ValueError("time to expiry cannot be negative")
    if sigma < 0:
        raise ValueError("volatility cannot be negative")


def _d1_d2(
    spot: float, strike: float, t: float, r: float, sigma: float, q: float
) -> tuple[float, float]:
    sig_sqrt_t = sigma * math.sqrt(t)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * t) / sig_sqrt_t
    return d1, d1 - sig_sqrt_t


def bs_price(
    spot: float,
    strike: float,
    t: float,
    r: float,
    sigma: float,
    kind: str = "call",
    q: float = 0.0,
) -> float:
    """Black-Scholes-Merton European option price.

    Degenerates gracefully: at ``t == 0`` or ``sigma == 0`` the price is
    the (discounted) intrinsic value.
    """
    _validate(spot, strike, t, sigma)
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    if t == 0.0:
        return max(spot - strike, 0.0) if kind == "call" else max(strike - spot, 0.0)
    if sigma == 0.0:
        fwd = spot * math.exp((r - q) * t)
        disc = math.exp(-r * t)
        intrinsic = fwd - strike if kind == "call" else strike - fwd
        return max(disc * intrinsic, 0.0)
    d1, d2 = _d1_d2(spot, strike, t, r, sigma, q)
    df_r = math.exp(-r * t)
    df_q = math.exp(-q * t)
    if kind == "call":
        return spot * df_q * _norm_cdf(d1) - strike * df_r * _norm_cdf(d2)
    return strike * df_r * _norm_cdf(-d2) - spot * df_q * _norm_cdf(-d1)


@dataclass(frozen=True)
class Greeks:
    delta: float
    gamma: float
    theta: float  # per year; /365 for per-calendar-day
    vega: float   # per 1.00 vol change; /100 for per vol point
    rho: float    # per 1.00 rate change; /100 for per rate point


def bs_greeks(
    spot: float,
    strike: float,
    t: float,
    r: float,
    sigma: float,
    kind: str = "call",
    q: float = 0.0,
) -> Greeks:
    """Analytic Black-Scholes-Merton Greeks."""
    _validate(spot, strike, t, sigma)
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    if t == 0.0 or sigma == 0.0:
        # At expiry (or zero vol) the option is its intrinsic: delta is a
        # step function, everything else is zero.
        itm = spot > strike if kind == "call" else spot < strike
        delta = (1.0 if kind == "call" else -1.0) if itm else 0.0
        return Greeks(delta=delta, gamma=0.0, theta=0.0, vega=0.0, rho=0.0)

    d1, d2 = _d1_d2(spot, strike, t, r, sigma, q)
    df_r = math.exp(-r * t)
    df_q = math.exp(-q * t)
    pdf_d1 = _norm_pdf(d1)
    sqrt_t = math.sqrt(t)

    gamma = df_q * pdf_d1 / (spot * sigma * sqrt_t)
    vega = spot * df_q * pdf_d1 * sqrt_t
    common_theta = -spot * df_q * pdf_d1 * sigma / (2.0 * sqrt_t)
    if kind == "call":
        delta = df_q * _norm_cdf(d1)
        theta = (
            common_theta
            - r * strike * df_r * _norm_cdf(d2)
            + q * spot * df_q * _norm_cdf(d1)
        )
        rho = strike * t * df_r * _norm_cdf(d2)
    else:
        delta = -df_q * _norm_cdf(-d1)
        theta = (
            common_theta
            + r * strike * df_r * _norm_cdf(-d2)
            - q * spot * df_q * _norm_cdf(-d1)
        )
        rho = -strike * t * df_r * _norm_cdf(-d2)
    return Greeks(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)


def implied_vol(
    price: float,
    spot: float,
    strike: float,
    t: float,
    r: float,
    kind: str = "call",
    q: float = 0.0,
    lo: float = 1e-4,
    hi: float = 5.0,
    tol: float = 1e-8,
    max_iter: int = 200,
) -> float:
    """Implied volatility by bisection (robust over Newton near zero vega).

    Raises ``ValueError`` when the price violates no-arbitrage bounds for
    any volatility in ``[lo, hi]``.
    """
    _validate(spot, strike, t, 0.0)
    if t == 0.0:
        raise ValueError("cannot imply volatility at expiry")
    p_lo = bs_price(spot, strike, t, r, lo, kind, q)
    p_hi = bs_price(spot, strike, t, r, hi, kind, q)
    if not (p_lo - tol <= price <= p_hi + tol):
        raise ValueError(
            f"price {price} outside attainable range [{p_lo:.6f}, {p_hi:.6f}]"
        )
    a, b = lo, hi
    for _ in range(max_iter):
        mid = 0.5 * (a + b)
        diff = bs_price(spot, strike, t, r, mid, kind, q) - price
        if abs(diff) < tol:
            return mid
        if diff > 0:
            b = mid
        else:
            a = mid
    return 0.5 * (a + b)


def crr_price(
    spot: float,
    strike: float,
    t: float,
    r: float,
    sigma: float,
    kind: str = "call",
    q: float = 0.0,
    steps: int = 200,
    american: bool = False,
) -> float:
    """Cox-Ross-Rubinstein binomial price (European or American).

    Converges to Black-Scholes for European options as ``steps`` grows;
    for American exercise it prices the early-exercise premium that has
    no closed form (the textbook case: deep ITM American puts).
    """
    _validate(spot, strike, t, sigma)
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if t == 0.0 or sigma == 0.0:
        return bs_price(spot, strike, t, r, sigma, kind, q)

    dt = t / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
    p = (math.exp((r - q) * dt) - d) / (u - d)
    if not 0.0 < p < 1.0:
        raise ValueError("arbitrage in tree parameters; reduce dt (more steps)")

    sign = 1.0 if kind == "call" else -1.0
    # Terminal payoffs.
    values = [
        max(sign * (spot * u**j * d ** (steps - j) - strike), 0.0)
        for j in range(steps + 1)
    ]
    # Backward induction.
    for i in range(steps - 1, -1, -1):
        for j in range(i + 1):
            cont = disc * (p * values[j + 1] + (1.0 - p) * values[j])
            if american:
                exercise = max(sign * (spot * u**j * d ** (i - j) - strike), 0.0)
                cont = max(cont, exercise)
            values[j] = cont
    return values[0]
