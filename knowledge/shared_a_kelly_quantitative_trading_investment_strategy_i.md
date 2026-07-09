---
family: all
source: The Kelly Criterion - Quantitative Position Sizing
doc_type: note
reliability: 95
tickers: []
---

## What the Kelly criterion answers
Given an edge, Kelly tells you **how much to bet** to maximise the long-run
(geometric) growth rate of capital. It is the bridge from "I have a good signal"
to "what position size does that justify". Sizing, not signal, is what compounds
or ruins capital over time.

## The intuition / formula
For a simple bet, optimal fraction **f\* = edge / odds** (e.g., for even-money
bets, f\* = p - q = 2p - 1). For continuous returns, the optimal fraction is
roughly **expected excess return / variance** (mean over sigma-squared). The size
**rises with edge and falls sharply with variance** - more uncertainty means
smaller bets.

## Why full Kelly is too aggressive in practice
Full Kelly maximises growth but produces **brutal drawdowns** and is acutely
sensitive to estimation error: if you overestimate your edge, you over-bet and
can blow up. Because edges are noisy and non-stationary in markets, practitioners
use **fractional Kelly** (e.g., half- or quarter-Kelly), trading a little growth
for far less volatility and ruin risk.

## Estimation risk is the real danger
Kelly assumes you *know* the true probabilities/return distribution. You don't -
you estimate them. Overestimated edge + full Kelly = catastrophic risk. So treat
Kelly as an **upper bound** on sizing and haircut it for parameter uncertainty.

## How an SME should use it
Use Kelly as the principled link between **conviction (edge) and position size**,
scaled inversely to **volatility/uncertainty**: bigger size only when the edge is
strong *and* well-estimated. Default to **fractional Kelly** for safety, cap any
single position, and shrink sizing when confidence is low or the regime is
unstable. Never let a high-conviction call translate into an un-survivable bet -
geometric growth rewards avoiding ruin.
