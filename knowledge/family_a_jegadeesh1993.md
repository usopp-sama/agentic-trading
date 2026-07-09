---
family: A
source: Jegadeesh & Titman (1993) - Returns to Buying Winners and Selling Losers
doc_type: paper
reliability: 95
date: 1993
tickers: []
---

## Cross-sectional momentum: the core finding
Stocks that outperformed over the past 3-12 months ("winners") keep beating past
"losers" over the next 3-12 months. A zero-cost portfolio long winners and short
losers earned roughly 1% per month in US stocks (1965-1989). This is the
empirical foundation of cross-sectional (relative-strength) momentum.

## Formation and holding windows (the J/K strategy)
Rank stocks by return over a J-month formation window (3/6/9/12) and hold for K
months (3/6/9/12). The 6-12 month formation with a 3-6 month hold is among the
strongest. In this system that maps to xs_mom_formation (~252 days) and the
rebalance cadence.

## Skip the most recent month
Skip the latest ~1 week to 1 month before ranking. Very recent returns reverse
(short-term reversal, bid-ask bounce), so skipping them isolates the medium-term
continuation signal. Maps to xs_mom_skip (~21 days).

## Decay and the reversal bracket
Momentum accrues over ~3-12 months, then decays; past ~12 months and out to 3-5
years returns partially reverse (the De Bondt-Thaler overreaction effect). So
momentum is a medium-horizon effect bracketed by short-term and long-term
reversal. Horizon decides whether you follow or fade.

## Risks: momentum crashes and costs
Momentum has infrequent but severe crashes - sharp losses when a beaten-down
market rebounds and past losers spike. Profits are not explained by market, size,
or value betas. High turnover means transaction and shorting costs materially
erode the long-short return.

## How an SME should use it
Favor names with strong, persistent 6-12 month relative strength (skipping the
last month); size by conviction; de-risk after large market drawdowns or
volatility spikes when crash risk is highest. Treat extreme very-recent moves as
reversal-prone, not as momentum.
