---
family: A
source: Moskowitz, Ooi & Pedersen (2012) - Time Series Momentum
doc_type: paper
reliability: 95
date: 2012
tickers: []
---

## Time-series (absolute) momentum: the core finding
An asset's **own past return predicts its own future return**. Instruments with
positive returns over the past ~12 months tend to keep rising; those with
negative past returns tend to keep falling. This is distinct from
cross-sectional momentum (winners vs losers): here each asset is judged against
**zero**, not against peers.

## Pervasive across asset classes
The effect shows up consistently across ~58 liquid futures and forwards -
equity indices, bonds, currencies, commodities - over decades. It is a
macro-level continuation phenomenon, not a stock-picking quirk, which is why it
underpins managed-futures / trend-following ("CTA") strategies.

## Construction
Go long if the past 12-month excess return is positive, short if negative, and
**scale each position by its volatility** (smaller size in more volatile
instruments) so no single market dominates risk. Roughly a 1-month holding /
rebalance. The 12-month look-back with vol-scaling is the canonical recipe.

## Why it works + the reversal bracket
Consistent with **under-reaction then delayed over-reaction**: returns continue
for ~12 months, then **partially reverse** beyond a year. Speculators (trend
followers) profit while hedgers pay the premium. Horizon matters: follow the
trend in the 1-12 month window, expect reversal much further out.

## Risk: the trend-reversal crash
The worst losses come at **sharp turning points** - when a long-running trend
abruptly reverses (e.g., a V-shaped market bottom), trend positions are
maximally wrong-footed. Performance is roughly uncorrelated with traditional
assets in normal times but can suffer in whipsaw regimes.

## How an SME should use it
Treat a persistent 12-month directional trend (price vs ~12-months-ago, or
above/below the long moving average) as a **continuation signal**, sized
inversely to volatility. This is the natural diversifier to cross-sectional and
fundamental views because it pays in sustained trends and crises but bleeds in
choppy, mean-reverting markets - so cut size when trends are weak or volatility
spikes near suspected turning points.
