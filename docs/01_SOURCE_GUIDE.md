# 01 · Source Guide — how the code is laid out

A plain-language tour of the codebase for someone who is **not** a finance or
Python expert. It answers three questions: *what are the big pieces*, *how does
a price turn into a (paper) trade*, and *where do I look to change X*.

Read this with [architecture.md](architecture.md) open — that one is the
engineer's version with links straight into the code; this one is the friendly
map.

---

## The two halves

The repo has two independent halves that work together:

| Folder | Think of it as | Depends on the app? |
|---|---|---|
| **`quant/`** | A pure **math library** — price maths, indicators, a backtester, risk/statistics. No database, no web server, no LLM. You could lift it out and use it in a notebook. | No |
| **`ats/`** | The **running application** — the web dashboard, the background services, the event bus, the database. It *calls into* `quant/` for the maths. | Yes |

Everything else is support: **`scripts/`** (command-line tools you run by hand,
like the backtest), **`tests/`** (the test suite), **`var/`** (runtime data —
the SQLite database, logs, backups — *not* code), **`deploy/`** (Docker/systemd),
**`knowledge/`** + **`library/`** (reference material the experts read).

---

## `ats/` — the application

### `ats/core/` — the plumbing every service shares
- **`config.py`** — every setting (env vars like `ATS_DATA_SOURCE`,
  `ATS_LLM_MONTHLY_BUDGET_INR`). One giant settings object. Start here when you
  want to know "what can I tune?".
- **`events.py`** — the **event bus**. Services don't call each other directly;
  they publish events (a new `BAR`, a `VOLUME_SPIKE`, an `ALERT`) and others
  subscribe. This is how the whole system stays loosely coupled.
- **`db.py` / `models.py`** — the database (SQLite by default) and the table
  definitions (instruments, strategies, trades, news, LLM calls…).
- **`state.py`** — small shared bits of live state: the kill switch, key/value
  scratchpad (`get_kv`/`set_kv`), the audit trail.
- **`telemetry.py` / `perf.py` / `resources.py`** — the "how healthy am I"
  substrate that powers the Ops Console (component health, timings, memory).

### `ats/server/` — the web app and the conductor
- **`app.py`** — builds the FastAPI web application.
- **`orchestrator.py`** — the **conductor**: starts every service, owns the
  scheduler (the thing that runs jobs "every 60s" or "at 08:45 daily"), and
  shuts everything down cleanly.
- **`wiring.py`** — the single list of *which* services exist. Adding a service
  = adding one line here.
- **`dashboard.py`, `api.py`, `ops_api.py`, `results_api.py`, …** — the URL
  routes. `dashboard.py` serves the money dashboard; `ops_api.py` serves the
  `/api/ops/*` engine-room data; each `*_api.py` is one area of the API.
- **`templates/`** (HTML pages) and **`static/`** (CSS/JS/images) — the actual
  dashboard you see in the browser.

### `ats/services/` — the workers (one folder each)
Each service is a small worker that starts up, subscribes to events and/or runs
on a schedule. The important ones for the trade path:

- **`market_data/`** — fetches prices (synthetic / yfinance / **Kite**), stores
  bars, and is the in-process "price oracle" everyone else asks. Fixing *where
  prices come from* → `market_data/sources.py`.
- **`strategies/`** — the **26 textbook trading strategies** (trend, mean-
  reversion, factor, pairs…) and the **backtest harness**
  (`strategies/backtest.py`) that scores them. This is the heart of the
  "is a strategy any good?" question.
- **`risk/`** — the gates that can veto a trade (position limits, event-calendar
  vetoes, extreme-sentiment vetoes).
- **`execution/`** — turns an approved signal into a **paper** order, tracks the
  book, computes fees, reconciles. Real-money order submission is a deliberate
  stub (`kite_adapter.py`).
- **`agents/`** — the LLM "experts" (SMEs) and the CIO that weigh in on ideas.
- **`scraper/` + `nlp/`** — pull news and score its sentiment.
- **`research/`** — the slow, once-in-a-while LLM research passes (budget-gated).

Support services: **`accounts/`** (paper cash ledger + demat), **`analytics/`**,
**`metrics/`**, **`learning/`**, **`rules/`** (self-governing guardrails),
**`regime/`** (bull/bear/crisis detector), **`fundamentals/`**, **`flows/`**
(delivery %/bulk deals), **`options_data/` + `vol_premium/`**, **`email/` +
`telegram/`** (alerts), **`watchdog/`** (the dead-man's switch, health alerting,
and the daily pre-open GO/NO-GO check), **`dashboard/`** (assembles the numbers
the UI shows).

---

## `quant/` — the maths library
- **`quant/data/`** — fetching + generating price data (`fetch.py`, and
  `synthetic_prices` for offline testing).
- **`quant/analysis/`** — indicators (SMA, RSI, ADX…) and signal helpers.
- **`quant/backtest/`** — the **vectorized backtester** (`engine.py`: give it a
  price series + a position series, get back an equity curve and Sharpe) and the
  **anti-overfitting statistics** (`validation.py`: the deflated Sharpe ratio,
  walk-forward, Monte-Carlo drawdowns).
- **`quant/risk/`** — position sizing and risk maths.

The one idea worth knowing: a **backtest** replays a strategy over historical
prices to see how it *would* have done. The **deflated Sharpe ratio (DSR)** then
discounts that result for luck (because if you try 26 strategies, the best one
looks good by chance) — that's why the gate is strict.

---

## Follow one trade through the system

1. **`market_data`** fetches a new daily bar and publishes a `BAR` event.
2. **`strategies`** react: each strategy looks at the price history and emits a
   *stance* (BUY / SELL / NEUTRAL) with a conviction.
3. **`agents`** (the LLM experts / CIO) and **`risk`** weigh in — risk can veto.
4. **`execution`** turns an approved BUY into a **paper** order, updates the
   book and the cash ledger. (No real money — that path is stubbed off.)
5. **`dashboard`** + the **event bus** push the update to your browser live.

Nothing here touches real money: the system is paper-only by design until a long
paper track record justifies otherwise (see [roadmap.md](roadmap.md)).

---

## "I want to change X — where do I look?"

| I want to… | Look in |
|---|---|
| Change a setting / add a toggle | `ats/core/config.py` |
| Change where prices come from | `ats/services/market_data/sources.py` |
| Add or tweak a trading strategy | `ats/services/strategies/library*.py` |
| Change how strategies are scored / the promotion gate | `ats/services/strategies/backtest.py` |
| Run a backtest and read the results | `scripts/run_backtests.py` (see below) |
| Add an API endpoint | the matching `ats/server/*_api.py` |
| Change a dashboard page | `ats/server/templates/*.html` |
| Add a background job / service | write it under `ats/services/…`, register it in `ats/server/wiring.py` |
| Change alerts / emails | `ats/services/execution/notify.py`, `ats/services/email/` |

---

## Running the backtest (the thing you care about most)

```bash
# offline, synthetic prices (no network, fast to sanity-check):
python scripts/run_backtests.py --offline

# real Zerodha NSE history over 3 years:
python scripts/run_backtests.py --kite --period 3y
```

It now **streams live progress** — one plain-English line per strategy ("traded
30 stocks over 44 trades, made Rs 4,276 on Rs 1,00,000 — did NOT pass") — and
writes the whole run to `var/metrics/backtest_run_<date>.log` so the terminal is
never a frozen mystery. At the end it prints a **PLAIN ENGLISH** headline (how
many made money, the best one, how many cleared the gate) above the detailed
table. The strategy-improvement story behind those numbers is in
[plans/strategy_edge_improvement.plan.md](plans/strategy_edge_improvement.plan.md).
