# Quant Toolkit

A learning-oriented but production-minded toolkit for market analysis,
built alongside the [Quant Finance Learning Roadmap](./quant_finance_learning_roadmap_31d331f8.plan.md).

**Built for the Indian market.** The universe is NSE large caps +
indices + commodity ETFs; the base currency is INR; the fee model
charges brokerage, STT, exchange fees, stamp duty, and GST the Indian
way; market-data polling respects the NSE calendar (09:15–15:30 IST,
exchange holidays); fundamentals cover NSE symbols; the option-chain
monitor reads NIFTY IV; and the broker integration path is Zerodha
Kite, gated behind the real-money switch.

It implements the early build phases of the roadmap's market-analysis tool:
a data pipeline, technical + fundamental analysis, a screener, a
look-ahead-safe backtester, and risk-based position sizing.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick start

Run the full end-to-end demo (works offline with synthetic data):

```bash
python scripts/demo.py
```

Use real market data instead (needs internet):

```bash
python scripts/demo.py --online --ticker AAPL
```

Run the first roadmap mini-project (SILVERBEES NAV premium/discount):

```bash
python -m quant.projects.silverbees_nav            # live data
python -m quant.projects.silverbees_nav --offline  # synthetic data
```

## Package layout

| Module | What it does |
|---|---|
| `quant.data` | Fetch OHLCV via `yfinance`; persist to SQLite (`PriceStore`). Synthetic generator for offline use. |
| `quant.analysis.indicators` | SMA, EMA, RSI (Wilder), MACD, Bollinger Bands, ATR, Donchian channels, annualized vol. |
| `quant.analysis.regime` | Market regime classifier: trend (up/down/range) x volatility (calm/normal/crisis) + style tilt matrix. |
| `quant.analysis.valuation` | Two-stage DCF, dividend discount model, margin of safety, ETF NAV premium/discount, cost-of-carry futures price. |
| `quant.analysis.screener` | Declarative, rule-based screener with ranking. |
| `quant.backtest` | Vectorized, look-ahead-safe signal backtester + SMA-crossover baseline. |
| `quant.risk` | Kelly criterion (discrete + continuous), fractional Kelly, capped position sizing. |
| `quant.options` | Black-Scholes-Merton pricing + Greeks, implied vol (bisection), CRR binomial tree (American exercise). |
| `quant.projects` | End-to-end mini-projects (SILVERBEES NAV analysis). |

## Strategy library (roadmap Part 7)

Proven strategy families implemented in `ats.services.strategies.library`,
each tagged with a style the regime layer understands:

| Strategy | Family | Core rule |
|---|---|---|
| `donchian_trend` | Trend following (7.1) | Buy 55-bar breakout, exit below 20-bar low; conviction in ATR units. |
| `ts_momentum` | Time-series momentum (7.1/7.2) | Sign of 12-month return skipping the latest month; vol-scaled conviction. |
| `rsi2_reversion` | Short-term mean reversion (7.3) | RSI(2) < 10 above the 200-SMA buys the pullback; > 70 exits. |
| `pairs_zscore` | Pairs / stat arb (7.4) | Z-score of log price ratio; long the cheap leg past 2σ (long-only book). |
| `factor_composite` | Factor investing (7.10) | Top-N basket by momentum + low-vol percentile ranks; ~quarterly rebalance. |
| `sma_crossover` | Trend | 20/50 SMA crossover baseline. |
| `mean_reversion` | Mean reversion | Bollinger %b band reversion. |
| `volume_breakout` | Momentum | Price breakout confirmed by volume z-score. |

## India-market data layer

| Component | What it does |
|---|---|
| `ats.services.market_data.calendar` | NSE trading calendar: IST hours (09:15–15:30), 2026 holiday list, post-close grace window. Live-source polling pauses off-hours. |
| `ats.services.fundamentals` | Ratios for NSE equities (P/E, P/B, ROE, D/E, margins) via pluggable providers: yfinance (`.NS`) live, deterministic synthetic offline. Feeds value/quality factors, the screener, and agents. |
| `ats.services.market_data.option_chain` | NIFTY option chain via the nseindia.com API (cookie warm-up, browser headers, graceful failure) or a synthetic chain offline. |
| `ats.services.options_data` | Polls the chain, computes ATM IV, put-call ratio, and the IV premium over 20-day realized vol — the vol-risk-premium monitor that the future defined-risk options sleeve (7.7) will trade on. |

Four coordination layers keep multiple strategies from conflicting
(roadmap Part 8): the **CIO** nets opposing views into one proposal per
symbol; **virtual sleeves** (`ats.services.strategies.sleeves`) mark each
strategy's own book to market daily for attribution and flag decaying
sleeves (rolling-Sharpe alert); the **regime service**
(`ats.services.regime`) dampens conviction of styles that mismatch the
current market regime and halves new-exposure sizing in crisis volatility;
and the **capital allocator** (`ats.services.strategies.allocation`)
recomputes bounded risk-parity weights across sleeves daily — staging
automatically from inverse-vol to correlation-aware equal risk
contribution with a bounded performance tilt as sleeve history deepens —
applied as dampen-only conviction multipliers (the top sleeve keeps 1.0).

## Design notes

- **No look-ahead bias.** The backtester shifts signals by one bar before
  applying them — a signal generated on day *t* is traded on day *t+1*.
- **Offline-first.** Every module runs without internet via a deterministic
  GBM synthetic price generator, so demos and tests are reproducible.
- **TimescaleDB-ready.** `PriceStore` uses a `(symbol, date)` schema and
  parameterized SQL, so migrating from SQLite to PostgreSQL + TimescaleDB
  is a connection swap, not a rewrite.

## Tests

```bash
pytest
```

## Roadmap mapping

This repo covers **Phase 1–3** of Part 5 in the roadmap (data pipeline,
analysis engine, signals + sizing) plus the first hands-on project, and
now the first slices of the multi-strategy build: the proven-strategy
library (Part 7: trend, momentum, mean reversion, pairs, factor
composite), regime detection (Part 7.12), sleeve P&L attribution +
decay detection (Parts 8.2/8.5), regime-aware risk scaling, and
inverse-vol capital allocation across sleeves (Part 8.4, stage 2).
The options pricing/Greeks calculator (Phase 5) is in `quant.options`.
Still ahead — value/quality factors once a fundamentals pipeline
lands, the defined-risk vol-premium sleeve (needs an options-chain
data source on top of `quant.options`), FinBERT sentiment, and
ML-based signals with walk-forward validation.
