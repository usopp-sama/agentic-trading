# Quant Analytics Engine — Detailed Plan (2026-07-08)

Replicate the *deterministic* analytics layer of platforms like investing.com
— valuation, technical summary, levels, screeners, movers, calendars — on our
own data, with our own math, inside the three-loop architecture. The goal the
operator set, verbatim: **shift work away from the LLM wherever a formula can
do the job; keep AI as a last-resort tool for genuinely important synthesis.**

This is not a course change. It is an acceleration of the three-loop thesis:
*"LLMs leave the trade path; a deterministic quant core earns."* Every feature
below is a pure function + a service surface. None of them create a new path
to orders.

---

## 0. Ground rules (unchanged invariants — read first, Opus)

1. **One path to orders.** Analytics feed (a) dashboard pages, (b) features
   into strategies, (c) hypothesis registry entries. Anything that wants to
   *trade* becomes a strategy in `ats/services/strategies/`, enters `shadow`,
   and passes the walk-forward gate (`scripts/run_backtests.py`) before
   `paper`. No exceptions, no direct proposals from analytics.
2. **Pure math lives in `quant/`** with exact-assertion unit tests and no I/O,
   no settings, no DB. Services wire data to math; math never fetches.
3. **Missing data is missing** — never zero, never guessed. Every valuation
   output carries its assumptions explicitly. A model estimate is labelled a
   model estimate on every surface that shows it.
4. **No scraping investing.com** (ToS + robots + the investpy precedent).
   Everything below computes from data we legitimately have: yfinance bars +
   statements, NSE public archives (delivery/bulk deals — already built in
   `ats/services/flows/`), our own news archive, manual/paid exports the
   operator supplies through a provider interface.
5. **Tests green at every commit.** Suite currently: 419 passing. Each
   workstream lands with its own tests + the full suite green, one commit per
   workstream, message style `feat(analytics): ...`.

## 0.1 What we already have (do NOT rebuild)

| investing.com feature | Our existing code | Status |
|---|---|---|
| RSI / SMA / EMA / MACD / Bollinger / ATR / ADX / Donchian / Keltner | `quant/analysis/indicators.py` | done, tested |
| DCF + margin of safety + DDM + PEG | `quant/analysis/valuation.py` (`discounted_cash_flow`, `margin_of_safety`) | math done; **no data feed** (QA-5/6 fix this) |
| Screener filter engine | `quant/analysis/screener.py` (`Screener`, `min/max/between_filter`) | engine done; **no metrics table / UI** (QA-5/7) |
| FinBERT news sentiment + NER routing | `ats/services/nlp/` | done (real transformer, not word counting) |
| Volume-spike detection | market_data `Topic.VOLUME_SPIKE` (z-score) | done |
| Earnings/RBI/budget calendar + veto | `ats/services/risk/event_calendar.py` (WS-1) | done; QA-8 extends with estimates/surprise |
| Delivery % + bulk deals (flow data) | `ats/services/flows/` (WS-5) | done |
| Factor ranking sleeves (value/quality/size/low-vol) | `ats/services/strategies/library_factors.py` | done, shadow |
| Regime classification | `quant/analysis/regime.py` | done |
| Backtest gate (walk-forward + deflated Sharpe) | `quant/backtest/validation.py`, `scripts/run_backtests.py` | done |

The gap is **connective tissue** (a per-symbol analytics snapshot service +
API + pages) and **six new pure-math modules** (levels, patterns, composite
summary, intraday/VWAP, quality scores, statements-fed valuation).

## 0.2 Honest adaptations for India (differences from the docs)

- **Fed Rate Monitor → RBI.** The CME FedWatch math (`implied = 100 −
  futures`) needs 30-day fed-funds futures. India's equivalent (MIBOR OIS)
  has **no free reliable feed**. We build: MPC meeting calendar + repo-rate
  history + a dashboard panel showing days-to-MPC and last stance. The
  probability engine is **deferred** behind a data dependency — if the
  operator later buys an OIS/rates feed, `quant/analysis/rates.py` gains
  `implied_policy_probability()` with the same math. Do not fake it.
- **The docs' FinBERT description** ("positive − negative words / total") is
  wrong; ours is the actual ProsusAI/finbert transformer. Keep ours.
- **The docs' streaming ring-buffer architecture** is for tick-level
  platforms. Our cadence is 60s polls + EOD passes; pandas over the existing
  `Ohlcv` store is correct at our scale. Do not add ZeroMQ/Redis streaming.
- **Analyst-ratings aggregation**: no free trustworthy source for NSE names;
  yfinance `recommendations` is sparse for India. Surface it when present,
  never depend on it.

---

## QA-1 — Levels: pivot points + Fibonacci (`quant/analysis/levels.py`)

Pure functions; feed the Charts page overlays, the technical summary (QA-3),
and future strategies.

```python
@dataclass(frozen=True) class PivotLevels:
    pivot, r1, r2, r3, s1, s2, s3: float

def classic_pivots(high, low, close) -> PivotLevels      # P=(H+L+C)/3 etc.
def fibonacci_retracements(high, low, direction="down") -> dict[str, float]
    # keys "0.236","0.382","0.5","0.618","0.786"; down = retrace from high
def nearest_level(price, levels: Iterable[float]) -> tuple[float, float]
    # (level, signed distance %) — for "sitting on support" confluence checks
def session_anchor(df, period="D") -> tuple[float, float, float]
    # prior session/week/month H,L,C from a daily frame (for pivot inputs)
```

Tests (`tests/test_levels.py`): hand-computed classic pivots for a known
H/L/C triple; fib levels for a 100→200 run; `nearest_level` sign convention;
weekly anchor from an engineered frame. ~10 tests.

## QA-2 — Candlestick patterns (`quant/analysis/patterns.py`)

Deterministic OHLC pattern flags, most-recent-bar oriented:

```python
def detect(df, lookback=3) -> list[PatternHit]   # PatternHit(name, direction, strength 0..1)
```

Implement exactly these eight (each a small pure predicate, individually
importable for tests): bullish/bearish engulfing, hammer, shooting star,
doji, morning star, evening star, marubozu. Definitions in docstrings with
the precise inequalities (e.g. engulfing: today's real body strictly
contains yesterday's real body AND opposite colors — use the doc's logic
but on real bodies, not H/L, which is the textbook-correct form).

Tests: one engineered 3-bar frame per pattern proving it fires, plus a flat
frame proving none fire. ~12 tests.

## QA-3 — Technical summary composite (`quant/analysis/summary.py`)

The "Strong Buy / Strong Sell" confluence engine — the highest-visibility
feature. **Score = deterministic vote over ~12 checks**, all from existing
`indicators.py` + QA-1/QA-2:

| # | Check | Bull vote when |
|---|---|---|
| 1 | price vs SMA-20 | above |
| 2 | price vs SMA-50 | above |
| 3 | price vs SMA-200 | above |
| 4 | SMA-20 vs SMA-50 (cross state) | 20 > 50 |
| 5 | EMA-12 vs EMA-26 | 12 > 26 |
| 6 | RSI-14 | <30 bull (oversold), >70 bear |
| 7 | MACD vs signal | above |
| 8 | ADX>20 trend direction (+DI vs −DI) | +DI > −DI |
| 9 | Bollinger %b | <0.05 bull, >0.95 bear |
| 10 | price vs classic pivot | above |
| 11 | latest candlestick pattern | bullish pattern |
| 12 | 5-day volume trend confirms direction | rising volume with move |

```python
@dataclass(frozen=True) class TechnicalSummary:
    symbol: str; score: int          # net = bulls − bears
    bulls: int; bears: int; neutral: int
    label: str                        # strong_buy / buy / neutral / sell / strong_sell
    components: list[dict]            # every check: name, vote, value — full "why"

def technical_summary(symbol, df) -> TechnicalSummary
# label thresholds: net ≥ +6 strong_buy; +3..+5 buy; −2..+2 neutral;
# −5..−3 sell; ≤ −6 strong_sell   (documented in the docstring, config-free)
```

Every component is included in `components` so the dashboard can show the
full breakdown — **explainability is the point**, we never show a bare label.

Tests: engineered strong-uptrend frame → strong_buy with ≥6 bull components;
engineered crash frame → strong_sell; flat frame → neutral; component list
always has 12 entries; oversold-in-uptrend mixes votes correctly. ~8 tests.

## QA-4 — Intraday analytics: VWAP + movers (`quant/analysis/intraday.py`)

```python
def vwap(df) -> pd.Series            # cum(TP*V)/cum(V), TP=(H+L+C)/3; intraday frame
def daily_vwap_approx(df) -> float   # single-day approximation from one daily bar
def movers(latest: dict[str, DayStat], min_volume_x=1.5) -> dict
    # {"gainers":[...], "losers":[...], "volume_confirmed":[...]}
    # DayStat = (pct_change, volume, avg_volume_20d); junk filter = the doc's
    # rule: flag legitimate only when volume ≥ min_volume_x × 20d average
```

Service wiring (in QA-7): movers computed on each poll cycle from the
existing store; VWAP overlays on the Charts page when the intraday cache has
bars (nse_live), daily approximation otherwise.

Tests: hand-computed VWAP over 3 synthetic intraday bars; movers ranking +
volume-confirmation filter; empty-input behavior. ~6 tests.

## QA-5 — Statements data layer + quality scores

**The data unlock for everything fundamental.** Current `Fundamental` table
holds ratios only; Piotroski/payout/DCF need statement lines.

1. Model `FinancialStatements` (`ats/core/models.py`): symbol, period
   (annual/quarterly), as_of, and nullable floats: revenue, ebit, net_income,
   cfo, capex, dna, total_assets, total_debt, current_assets,
   current_liabilities, shares_outstanding, gross_margin, dividends_paid,
   net_debt, tax_rate, source. Unique (symbol, period, as_of).
2. Provider (`ats/services/fundamentals/statements.py`):
   `fetch_statements(symbol) -> list[StatementSnapshot]` from yfinance
   `Ticker.financials/balance_sheet/cashflow` (last 4 annuals), EQ-only via
   the instrument-type cache (pattern from `FundamentalsService`), best-effort
   with per-symbol failure isolation, weekly refresh cron (Sunday 18:00 IST —
   off-hours, before research nightly). **Provider interface takes a
   `source` arg** so a paid/manual CSV provider (screener.in export, the
   operator's investing.com export) can slot in later without code changes:
   `ats/services/fundamentals/import_csv.py` + `scripts/import_statements.py`
   (schema documented in the script docstring).
3. Quality math (`quant/analysis/quality.py`) — pure, statement-dicts in:

```python
def piotroski_f(cur: dict, prev: dict) -> FScore   # 0..9 + per-check breakdown
def payout_ratio(dividends_paid, net_income) -> float | None
def altman_z(cur: dict, market_cap: float) -> float | None      # manufacturing form
def dividend_safety(yield_pct, payout, f_score, growth_years) -> dict
    # the doc's 4-filter "top dividend" logic, each check reported separately
```

All nine Piotroski checks per the standard definition (ROA>0, CFO>0, ΔROA>0,
CFO>NI (accruals), Δleverage<0, Δcurrent-ratio>0, no dilution, Δgross-margin>0,
Δasset-turnover>0), each returning None-safe when inputs are missing —
**a missing input is a failed check counted separately, never a free point.**

Tests: fixture statement dicts (no network) with a hand-scored F=8 company
and an F=2 company; payout edge cases (zero/negative NI → None); Altman
bands; dividend-safety trap case (12% yield, 95% payout → rejected). ~14 tests.

## QA-6 — Valuation surface (fair value per symbol)

Wire the **existing** `discounted_cash_flow` to real inputs:

`ats/services/fundamentals/fair_value.py`:

```python
def fair_value(symbol) -> dict | None
# inputs from FinancialStatements: base_fcf = cfo − capex (3y average);
# growth = clamp(3y FCF CAGR, 0.02, 0.15); wacc default 0.12 (India ERP),
# terminal 0.04 ≤ wacc − 0.04; net_debt, shares from latest statement.
# output: {intrinsic, price, margin_of_safety_pct, verdict, assumptions{...},
#          sensitivity: {wacc±2% × growth±5%} 3×3 grid, quality: FScore}
# verdict: undervalued if MoS ≥ +20%, overvalued if ≤ −20%, else fair —
# the doc's margin-of-safety rule, using quant.analysis.valuation.margin_of_safety.
```

Rules: refuses (returns None) when < 2 annual statements or negative
base-FCF trend — a bad DCF is worse than no DCF. The 3×3 sensitivity grid is
mandatory in the payload; the dashboard must show the *range*, not one number.

Tests: deterministic fixture statements → exact intrinsic value (assert to
the rupee against a hand computation); refusal paths; clamps; verdict
boundaries at exactly ±20%. ~8 tests.

## QA-7 — AnalyticsService + API + dashboard surfaces

The connective tissue. New service `ats/services/analytics/service.py`
(name `analytics`, register in `wiring.py` after `strategies`):

- **Close pass** (cron 15:50 IST + on start): for every watchlist symbol,
  compute `technical_summary`, `classic_pivots` (from prior session),
  `fibonacci_retracements` (from 52w H/L), `patterns.detect`, latest
  `fair_value` (weekly refresh is enough for fundamentals), movers stats →
  persist one `AnalyticsSnapshot` row per symbol/day (new model: symbol, day,
  JSON payload, unique (symbol, day)) so the dashboard reads instantly and
  history accrues for research.
- **Poll pass** (every market-data cycle, in-memory only): movers + VWAP.
- API (`ats/server/analytics_api.py`):
  - `GET /api/analytics/{symbol}` — full snapshot (summary components,
    levels, patterns, fair value w/ sensitivity, flow signature from WS-5)
  - `GET /api/analytics` — table for all symbols (the Screener page feed)
  - `GET /api/movers` — gainers/losers/volume-confirmed
  - `GET /api/screener?filters=...` — runs `quant.analysis.screener.Screener`
    over the metrics table; 4 canned presets: value (PE<15 & MoS>20%),
    dividend-safety (QA-5 logic), quality (F≥7), momentum (near 52w high +
    volume). Presets are config-free constants; custom filters via query.
- Dashboard:
  - **Charts page**: pivot/fib overlay toggles; VWAP line when intraday.
  - **Opportunities page**: each card gains the technical-summary badge with
    expandable 12-component breakdown + fair-value verdict chip. (Also fixes
    the "empty page" complaint — see §Post-plan note.)
  - **New `/screener` page**: preset tabs + results table + CSV export,
    every row linking to Charts + Analytics detail.
  - **Today page**: movers panel (volume-confirmed only).

Tests: service pass over a fake MD (patterns from the flows tests), snapshot
persistence + idempotence per day, API endpoints via TestClient with seeded
rows, screener presets against fixture metrics. ~12 tests.

## QA-8 — Loop integration (where this earns money)

1. **Confluence strategy (medium loop candidate).** New shadow strategy
   `tech_confluence` (`library.py`): BUY when `technical_summary` ≥ +6 AND
   price within 1% of a pivot/fib support (QA-1 `nearest_level`); exit at
   net ≤ 0. Registered via the **hypothesis registry** (agent: "human",
   title "Confluence: composite summary + level support"), stage SPECIFIED →
   run `scripts/run_backtests.py` → attach gate result → SHADOW. It earns
   `paper` + a league solo account **only through the existing gate.**
2. **Economic calendar + surprise.** Extend `var/event_calendar.yaml` schema
   with optional `estimate`/`actual` fields per event;
   `surprise_pct = (actual − estimate)/|estimate| × 100` computed in
   `event_calendar.py`; shown on the events panel; a released surprise ≥
   |2σ| of its own history writes a ResearchNote (slow loop reads it Saturday).
3. **Screener presets → research.** Weekly research pass (existing factory)
   gets `screener_hits` in its DATA envelope (top-10 per preset) — the
   strategy researcher mines *our* screens instead of asking the LLM to
   remember fundamentals. This **reduces prompt size and LLM dependence** —
   the point of this whole plan.
4. **Fundamentals red-flags without LLM**: fundamentals_analyst role's DATA
   gains F-scores + payout + Altman columns; with those present the weekly
   fundamentals pass becomes optional (config `research_fundamentals_llm:
   bool = false` default false → the note is generated deterministically
   from threshold rules; the LLM version stays available for manual runs).

## QA-9 — "Control Room" dashboard (fundamental information architecture redesign)

The operator wants something fundamentally different — not just colors, but a
completely different way of consuming information. Instead of a grid-card
page-based layout, **Control Room** is a **command-driven, real-time heatmap
+ drill-down architecture** inspired by mission control and Bloomberg Terminal.

Think: centre stage is a **live heatmap** of all symbols (color = technical
signal strength, size/pulse = activity), right rail scrolls active
opportunities, top bar shows system state, bottom is a command palette. Click
any symbol to drill into detail. It's intentionally *not* a better way to do
the same things — it's a different way to *think* about the dashboard
(data-first, action-oriented, minimal cognitive load).

### 9.1 Wireframe (the three-pane model)

```
┌─────────────────────────────────────────────────────────────────────┐
│ ⚡ ATS  │ Today │ Control │ Research │ ...  [L/M/S] Eq:– Mode:PAPER Kill│
├─────────────────────────────────────────────────────────────────────┤
│                             ║                          ║             │
│    ┌──────────────────────┐ ║ ┌────────────────────┐  ║    STATUS   │
│    │                      │ ║ │  Active Signals    │  ║   ┌──────┐  │
│    │  MARKET HEATMAP      │ ║ │  ─────────────────  │  ║   │Eq:   │  │
│    │  (54 symbols color-  │ ║ │ INFY    +6  BUY    │  ║   │+2.8% │  │
│    │   coded by tech      │ ║ │ TCS     +4  HOLD   │  ║   │Mode: │  │
│    │   score, pulse on    │ ║ │ HDFCBANK -2  SELL  │  ║   │PAPER │  │
│    │   recent signal)     │ ║ │ ...               │  ║   │Ready │  │
│    │                      │ ║ │                    │  ║   └──────┘  │
│    │ ▓▓▓▓▓ INFY      +6  │ ║ └────────────────────┘  ║             │
│    │ ▓▓▓ TCS         +4  │ ║                         ║   NEXT REBAL │
│    │ ▓▓ HDFCBANK    -2  │ ║    [scroll]             ║   in 2h 43m  │
│    │ ▓ WIPRO        -4  │ ║                         ║             │
│    │ ░░░ TATASTEEL  -8  │ ║                         ║   LLM MODE  │
│    │                      │ ║                         ║   mock (✓)  │
│    └──────────────────────┘ ║                         ║             │
└────────────────────────────────────────────────────────────────────┘
│ > [search symbol | type command]                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 9.2 The three zones (all respond to live data every poll cycle)

**LEFT: Market Heatmap** — Read-only, background color-coded by technical_summary
score:
- Dark green (#00e5a0) = strong buy (+6)
- Green = buy (+3–+5)
- Gray = neutral (−2 to +2)
- Red = sell (−5 to −3)
- Dark red (#ff5c7a) = strong sell (≤−6)

Block height or glyph size = absolute momentum magnitude. Pulse or glow when
there's a fresh signal (< 60s old). Hovering a symbol shows tooltip:
`INFY | Score: +6 | Lev: R1 | Vol: 2.1M | Price: ₹2140`. Clicking drills
to the symbol detail (overlay modal or right-pane swap).

**CENTRE: Scrolling Ticker** — Live opportunities + movers filtered for the
human (high conviction only, QA-7 min_score filter). Format per row:
`SYMBOL | conviction | direction | driver | status`. Rows auto-update with
animations (fade in new, fade out acted). Clicking a row drills its detail.

**RIGHT: Status Panel** — Four fixed stacks (equity, mode, next event, LLM):
- **Equity**: huge mono numeral + %change, colored by direction
- **Trading Mode**: SELECT dropdown (OFF/PAPER/APPROVAL/AUTO) + Kill button
- **Next Rebalance**: clock countdown (from the medium loop)
- **System Health**: loop status (3 glow dots), LLM mode (real/mock), DB size,
  active connections

**BOTTOM: Command Palette** — `>` prompt, instant search (type `INFY` → jump
to that symbol, type `dashboard` → swap panes, type `export` → trigger a
report). Keep it minimal; most commands are symbol names (common case).

### 9.3 Interactions (non-modal, low-latency feel)

- **Hover symbol block**: tooltip with key data (3s delay, max 200px wide,
  no modal bloat).
- **Click symbol**: detail drawer slides in from right (≤500px wide) showing
  Charts + Fundamentals + Flow signature. Drawer is independent — left/centre
  keep updating.
- **Click opportunity row**: same drawer, pre-scrolled to that symbol.
- **Mode/Kill**: existing buttons, keep visible (already in the right panel).
- **Search/command**: ">" prompt in bottom bar, blur toggles it, ESC dismisses.

**No page navigation from this view** — everything is modal drawers or
pane swaps. The existing "Today/Opportunities/Research/Charts" nav links
stay in the header for deep dives; Control Room is the persistent monitoring
view.

### 9.4 Visual system (pure CSS + light HTML layer)

Create `ats/server/templates/control_room.html`:
- Single `.control-root` flex container (left/centre/right zones + bottom bar)
- `.heatmap` SVG or CSS grid of colored blocks (54 symbols, responsive columns)
- `.ticker` scrolling list (JavaScript updates, WebSocket feed)
- `.status-panel` four boxes, live-updating via JS
- `.command-palette` hidden input + results, reveal on focus or `>`

CSS for the look (not a separate theme; baked into the new template):
- **Backdrop**: matte dark (e.g., `#0a0f1a`) — less "glowy" than Nightdesk,
  more business-like.
- **Heatmap blocks**: 18×18px each, 2px gap, rounded corners. Background
  color from score, semi-transparent (#80 alpha). On hover: brighten + 1px
  accent border + tooltip (absolutely positioned).
- **Ticker rows**: `height:28px`, tabular mono numerals, row hover = light
  tint. Status pill right-aligned, auto-colored by stage (acted=green,
  proposed=amber, etc.).
- **Status numerals**: `font-size:36px`, `font-family: "Cascadia Code"`,
  tabular, glowing text-shadow on the equity figure only (subtle, not garish).
- **Command bar**: ` backdrop-filter: blur(10px)`, `position: sticky bottom: 0`,
  `:focus` expands prompt width.

### 9.5 File structure + acceptance

- `ats/server/templates/control_room.html` (new; 200–250 lines, uses the
  existing base.html for header/footer)
- `ats/server/static/control_room.css` (new; ~300 lines, *not* a theme —
  scoped CSS, plain classes, zero `:root` tokens)
- `ats/server/static/control_room.js` (new; ~250 lines: WebSocket handler
  for heatmap/ticker updates, command palette logic, drawer toggle)
- `ats/server/dashboard.py`: add `@app.get("/control")` route returning the
  new template (pass live market_data snapshot + opportunities)
- `ats/server/templates/base.html`: add Control Room to nav (first, before
  Today)

Acceptance:
- Page loads in <500ms without spinner (initial render from DB snapshots).
- Heatmap updates per-poll (60s), no flicker, smooth color transitions.
- Clicking a symbol shows its detail drawer with charts (reuse the existing
  Charts page logic, but in a narrower modal).
- Command palette responds to typing (< 50ms lag, server-side search via
  symbol watchlist).
- Responsive down to tablet (heatmap cols reflow, right panel becomes
  scroll-able strip below centre on <768px).
- All numerals are mono + tabular (the Cascadia covenant).
- Works fully offline (synthetic source); API calls for `/api/dashboard`
  (new summary endpoint) + `/api/movers` (QA-7) cache-local on first load.

### 9.6 The intent

This is not "a prettier dashboard." It's **a workflow redesign**: instead of
"I click a menu, wait for page load, find the right card, read the data,"
you get "glance at the heatmap, see coloured blocks shift, spot the high
scores, click to drill." It's the trading equivalent of a weather radar —
you read patterns at a glance, not data rows. It rewards long lookups (which
you'll do for 24/7 runs) and makes boredom *harder* — colour + motion + real
state = engagement.

## QA-10 — Running it all on the host laptop (Ryzen 5 5500U · 15.5 GB · Win 11)

Everything runs on this one machine. The architecture is already shaped for
it — **single Python process, asyncio + APScheduler, SQLite, in-memory
bus** — so the main job is *not adding* heavy things, plus a few host
settings. Opus: treat every rule here as a constraint on all QA workstreams.

### 10.1 Memory budget (the scarce resource)

| Consumer | Typical | Notes |
|---|---|---|
| Windows 11 + drivers/UI | ~4.5–5.5 GB | fixed cost |
| ATS server process | 0.6–0.9 GB | pandas + 54-symbol history + services |
| + FinBERT (torch, CPU) | +0.7–0.9 GB | the single biggest optional slug |
| Browser tab (dashboard) | 0.3–0.8 GB | one tab, one machine |
| **Headroom** | **~7 GB** | comfortable — no swap pressure expected |

Rules that keep it that way:
- **`workers=1` forever.** All state (bus, caches, league broker) is
  in-process; a second uvicorn worker would double RAM *and* split the bus.
  This is already the case (`ats/server/__main__.py`) — never "optimize" it.
- **FinBERT is the lever.** `ATS_NLP_SENTIMENT_MODEL=vader` drops ~800 MB
  instantly (VADER is lexical, no torch) at modest quality cost. Keep
  `auto` by default; document vader as the low-RAM mode in `.env`.
  Verify FinBERT loads lazily (first scored headline, not import time) —
  if it loads at startup today, make it lazy in QA-7's commit.
- **No new infra.** No Docker on this host (WSL2 VM reserves 1–2 GB), no
  Redis, no Postgres, no browser automation. SQLite + memory bus stay.
- **Analytics snapshots are rows, not caches**: QA-7 persists one JSON row
  per symbol/day and reads it back — the dashboard never triggers
  recomputation, and process RAM doesn't grow with history.
- **DataFrames**: always via `market_data.get_history(limit=400)` (shared
  LRU); never hold frames on `self` across cycles in new services.

### 10.2 CPU (6 cores / 12 threads — plenty, if we keep spikes off-session)

- The 60s poll + 24 strategies over ~54 symbols costs well under one core.
  Keep new per-poll work (QA-4 movers/VWAP) O(watchlist) with no I/O.
- Heavy passes are **scheduled off-hours by design** — keep it that way:
  statements refresh Sun 18:00, flows 19:00, research nightly 20:00,
  analytics close-pass 15:50. Never put statements/DCF work in the poll path.
- Backtests (`scripts/run_backtests.py`) are the one true CPU burn: run them
  manually or schedule ≥ 20:00 IST, and set `OPENBLAS_NUM_THREADS=4` /
  `MKL_NUM_THREADS=4` in that script's env so BLAS doesn't oversubscribe
  all 12 threads while the server polls.

### 10.3 SQLite + disk

- Add (if absent) on engine init: `PRAGMA journal_mode=WAL` and
  `PRAGMA synchronous=NORMAL` — fewer write stalls with our many small
  writers (bars, signals, snapshots, journal). One-line check in
  `ats/core/db.py`.
- Logs are already capped (10 MB × 10). `var/ats.db` growth is dominated by
  `ohlcv` + `llm_calls` + `analytics_snapshots`; add a monthly retention
  job later (out of scope here) — at current rates the DB stays < 1 GB for
  months.
- Exclude `var/` from Windows Defender real-time scanning (Settings →
  Virus & threat → Exclusions): SQLite's write pattern triggers rescans and
  costs real latency on every commit.

### 10.4 Windows host checklist (the operator does these once)

1. **Power: never sleep on AC.** The `Run time of job ... was missed by
   1:53:38` warnings in the logs are literally the laptop sleeping.
   Settings → System → Power: *Never* sleep when plugged in; lid-close =
   do nothing (if it runs closed). USB selective suspend off is unnecessary.
2. **Autostart**: Task Scheduler → new task, trigger *At log on*, action
   `C:\Users\go4av\work\agentic-trading\.venv\Scripts\python.exe -m ats.server`,
   start-in the repo dir, "run whether user is logged on" unchecked (keep
   it simple), restart-on-failure ×3. (This is the Windows equivalent of
   `deploy/ats.service`.)
3. **Browser**: one pinned tab; Edge/Chrome sleeping-tabs whitelist for
   `127.0.0.1:8000` so the WebSocket stays alive.
4. Optional heads-up: Windows Update *active hours* set to market hours so
   a 3 AM reboot doesn't kill a research night — autostart makes even that
   self-healing.

## QA-11 — Mobile (deferred, decided direction only)

Native app: not now. The cheap 90% is a **PWA**: `manifest.json` + icon +
a ~30-line service worker (cache-shell strategy), plus a responsive audit
pass over the templates (they already carry the viewport meta). Result:
"Add to Home Screen" on the phone, full-screen dashboard over LAN/VPN.
≈ 0.5 day, schedule after QA-9 lands. Anything push-notification-shaped
stays on the existing email/Telegram channels.

## Sequencing, effort, acceptance

| Order | WS | Effort | Acceptance gate |
|---|---|---|---|
| 1 | QA-1 levels | 0.5 d | tests green; hand-computed values match |
| 2 | QA-2 patterns | 0.5 d | each pattern provable on an engineered frame |
| 3 | QA-3 summary | 1 d | 12 components always present; labels correct on 3 engineered regimes |
| 4 | QA-4 intraday | 0.5 d | VWAP hand-check; junk filter drops zero-volume movers |
| 5 | QA-5 statements+quality | 1.5 d | F-score fixture scores exact; provider survives offline |
| 6 | QA-6 fair value | 1 d | rupee-exact fixture DCF; refuses thin data |
| 7 | QA-7 service+UI | 2 d | /screener + badges live; snapshot survives restart; suite green |
| 8 | QA-8 integration | 1 d | tech_confluence in registry as SPECIFIED w/ backtest attached; surprise% on events panel |
| 9 | QA-9 Control Room | 2 d | heatmap renders live, ticker scrolls, command palette responsive, drawers drill into charts |
| 10 | QA-11 PWA | 0.5 d | installable on phone; offline shell loads |

QA-10 is an ops constraint set, not a build item — apply it throughout;
its only code artifacts are the WAL pragma + FinBERT lazy-load check.

Total ≈ 11 working days. Commit per row. Full pytest green at every commit
(419 now; expect ~+70). Everything runs offline (synthetic source) except
statement refresh, which degrades gracefully like fundamentals does today.

## What this does to LLM reliance (the operator's actual goal)

Before: SME fan-out on news/spikes (now config-gated), research roles read
raw news dumps. After this plan: the medium loop's *entire* daily read —
summary, levels, patterns, movers, valuation, quality, screens — is
formula-derived at zero marginal cost; the slow loop's prompts shrink to
pre-digested tables (cheaper per call); the fundamentals weekly pass stops
using the LLM by default (QA-8.4). The LLM's remaining jobs: weekly strategy
research over the archive, the monthly committee synthesis, and anything the
operator clicks manually. That is "AI as last-resort decision body" —
implemented, not aspirational.

## Explicitly out of scope

- Scraping investing.com (ToS/robots/precedent — settled earlier).
- RBI rate-probability engine (blocked on paid OIS data; math stub noted in
  §0.2 for when data exists).
- Tick-level streaming infra (wrong scale for us).
- Options analytics beyond the existing vol_premium sleeve.
- Any new order path. If it wants to trade, it goes through the gate.
