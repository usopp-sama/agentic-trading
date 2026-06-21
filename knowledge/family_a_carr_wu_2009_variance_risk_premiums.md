---
family: A
source: Carr & Wu (2009) - Variance Risk Premiums
doc_type: paper
reliability: 95
date: 2009
tickers: []
---

## The variance risk premium
Option-implied (risk-neutral) variance is systematically higher than the variance
that subsequently realizes. Selling variance - via variance swaps or short option
structures - earns a premium because buyers pay up for protection against
volatility and crash risk. This is the academic basis for short-volatility
sleeves.

## How it is measured
Synthesize risk-neutral expected variance from a strip of out-of-the-money
options (the model-free, VIX-style replication) and compare it to realized
variance. The gap is the variance risk premium; for equity indices it is large
and negative, meaning variance buyers lose on average.

## Index vs single names
The premium is strongly significant for stock indices (e.g., S&P 500) but weak or
insignificant for many individual stocks. Index variance carries a systematic,
priced volatility-risk component that single-name variance largely lacks - so
harvest it at the index level.

## Not explained by standard factors
The premium is not captured by market, size, value, or momentum exposures - it
compensates for a separate volatility/jump-risk factor. It spikes against sellers
precisely in market stress, when realized vol blows through implied.

## Practical mapping (defined-risk only)
This underpins the vol-premium sleeve: sell rich index implied vol versus realized
(enter when ATM IV minus realized exceeds the premium threshold, take profit at a
fraction of the credit, hard-stop on a multiple of it). Always use defined-risk
structures because rare large losses dominate the P&L distribution.

## How an SME should use it
When index implied vol sits well above realized, flag a harvestable premium - but
size small and cap tail risk. The trade "picks up pennies" and blows up in
volatility shocks, so it must never be run naked or oversized.
