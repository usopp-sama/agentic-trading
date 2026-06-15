# Risk management primer (RISK family)

## Survival first
The job of risk is to keep the account alive so the edge has time to compound.
A 50% drawdown needs a 100% gain to recover. Capping losses matters more than
maximising any single win.

## Position sizing
Risk a small, fixed fraction of capital per trade (often 0.5–2%). Size from
volatility: smaller positions in volatile names, larger in calm ones, so each
position contributes similar risk. The Kelly criterion gives a theoretically
optimal fraction from edge and odds, but full Kelly is too aggressive in
practice — use a fraction (quarter to half Kelly) because estimates are noisy.

## Diversification & correlation
Uncorrelated bets reduce portfolio volatility without sacrificing expected
return. In a crisis correlations spike toward 1 — "diversification fails when
you need it most" — so also cap gross exposure and concentration. Limits here:
max per-name weight, max per-sector weight, max gross exposure.

## Drawdown discipline
Define a daily loss limit and an absolute drawdown that triggers de-risking or a
full stop (kill switch). Pre-commit to these rules when calm; do not renegotiate
them mid-drawdown.

## Stops and exits
Plan the exit before entry: a stop (often ATR-based) and a target. Trends use
trailing exits; mean-reversion uses time/level exits. The worst outcome is a
small loss allowed to become a large one.

## Guardrails vs adaptive rules
Some limits are immutable guardrails — no model, however confident, may breach
them (per-name cap, daily loss kill, no leverage). Other rules adapt with
evidence. A confident expert can still be wrong or manipulated; guardrails are
the backstop that makes letting models reason safe.

## The risk lens on any proposal
Ask: what is the worst case, how correlated is this to what we already hold, does
it breach any limit, and is the size justified by conviction and volatility?
Risk never picks direction — it clamps size and vetoes breaches.
