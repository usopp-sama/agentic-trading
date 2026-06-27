---
family: all
source: John C. Hull - Risk Management and Financial Institutions
doc_type: book
reliability: 95
tickers: []
---

## Risk is the raw material, not just a constraint
Financial institutions exist to **take risk intelligently** and be paid for it -
the job is measuring, pricing and controlling risk, not eliminating it. The main
categories: **market risk** (prices/rates move), **credit risk** (counterparties
default), **liquidity risk** (can't fund or exit), and **operational risk**
(process/people/system failures).

## Measuring market risk: VaR and its successor
- **Value at Risk (VaR):** the loss not exceeded with a given confidence over a
  horizon (e.g., "1-day 99% VaR = X"). Intuitive and standard, but it says
  nothing about **how bad** losses are in the tail and is not sub-additive
  (can discourage diversification).
- **Expected Shortfall (ES / CVaR):** the *average* loss beyond VaR - captures
  tail severity and is coherent. Modern practice prefers **ES** for exactly this
  reason.
Estimate via historical simulation, model-building (variance-covariance) or
Monte Carlo - each with trade-offs.

## Volatility, correlation and fat tails
Volatilities and correlations **cluster and change over time** (use EWMA/GARCH,
not a static number), and **correlations tend to spike toward 1 in crises** -
diversification fails exactly when you need it. Returns have **fatter tails**
than the normal distribution, so models assuming normality understate extreme
risk. Always stress the tail.

## Stress testing and scenario analysis
Because models are calibrated on normal times, **stress tests and historical
scenario replays** (2008, COVID shock, rate spikes) are essential to size losses
under regimes the statistics won't show. Back-test risk models (count VaR
breaches) to check they are honest.

## Capital, regulation and the system
Banks hold **capital** against unexpected losses; regulation (Basel) sets
minimums for credit, market and operational risk plus liquidity buffers. The
deeper lesson from crises: **leverage, funding liquidity and interconnection**
turn local shocks into systemic ones.

## How an SME should use it
Always pair a return view with a **risk view**: quantify downside with VaR/ES,
assume **volatility and correlations rise in stress**, and never rely on
diversification holding in a crisis. Stress-test theses against historical
shocks, respect **liquidity** (can the position be funded and exited?), and size
positions so a fat-tail event is survivable. Controlling tail risk and avoiding
forced unwinds matters more to long-run compounding than squeezing the last bit
of expected return.
