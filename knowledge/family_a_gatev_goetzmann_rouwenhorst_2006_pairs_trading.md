---
family: A
source: Gatev, Goetzmann & Rouwenhorst (2006) - Pairs Trading
doc_type: paper
reliability: 95
date: 2006
tickers: []
---

## Distance-based pairs trading
Find two stocks whose normalized prices historically move together; when they
diverge, short the outperformer and go long the underperformer, betting on
convergence. It is a classic market-neutral relative-value rule and the
intuition behind statistical-arbitrage pairs and cointegration sleeves.

## Formation: the distance method
Over a 12-month formation window, normalize each stock to a cumulative
total-return price index and compute the sum of squared deviations (SSD) between
candidates. Select the pairs with the smallest SSD - the tightest historical
co-movement. Maps to coint_formation (~252 days).

## Trading rule and thresholds
Over the next ~6-month trading window, open the pair when the normalized spread
diverges by >= 2 historical standard deviations and close it when the spread
converges back. Legs are dollar-neutral. Maps to coint_entry_z 2.0 and
coint_exit_z 0.5; wait one day after the signal to avoid bid-ask bounce.

## Returns and market-neutrality
Historically the rule earned roughly 11% annualized with low market beta - the
return is relative-value, not directional. It survived conservative
transaction-cost assumptions, though profits shrank as the trade became crowded
in later decades.

## Risks and caveats
Divergence can persist or be structural - if one firm fundamentally changes,
convergence may never come, so stop-losses and periodic re-selection are needed.
Sensitive to execution costs, short availability, and "pair breaks". Distinguish
a temporary dislocation from a regime change.

## How an SME should use it
Treat a large, statistically unusual spread between historically tight peers as a
mean-reversion opportunity - but first screen for a fundamental reason the
relationship broke; if there is one, do not trade it. Convergence is a bet, not a
certainty.
