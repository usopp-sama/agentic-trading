# Quant Toolkit

A learning-oriented but production-minded toolkit for market analysis,
built alongside the [Quant Finance Learning Roadmap](./quant_finance_learning_roadmap_31d331f8.plan.md).

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
| `quant.analysis.indicators` | SMA, EMA, RSI (Wilder), MACD, Bollinger Bands, annualized vol. |
| `quant.analysis.valuation` | Two-stage DCF, dividend discount model, margin of safety, ETF NAV premium/discount, cost-of-carry futures price. |
| `quant.analysis.screener` | Declarative, rule-based screener with ranking. |
| `quant.backtest` | Vectorized, look-ahead-safe signal backtester + SMA-crossover baseline. |
| `quant.risk` | Kelly criterion (discrete + continuous), fractional Kelly, capped position sizing. |
| `quant.projects` | End-to-end mini-projects (SILVERBEES NAV analysis). |

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
analysis engine, signals + sizing) plus the first hands-on project.
Later phases — FinBERT sentiment, a Streamlit dashboard, and ML-based
signals with walk-forward validation — build on these primitives.
