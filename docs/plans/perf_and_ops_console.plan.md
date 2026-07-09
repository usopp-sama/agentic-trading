# Performance Fix + Ops Console — Plan (2026-07-09)

The operator's punch list, in priority order: (P0) the dashboard is unusably
slow — 1–2 minutes per page on localhost; (P1) a set of quick fixes (theme
popup overflow, FinBERT missing, the undervalued/overvalued surface); (P2) a
simulated **demat account** to complete the bank+broker simulation; (P3) a
categorized **news** section; (P4) a dedicated **Ops Console** — deep system
observability separate from the money dashboard; (P5) a decision on
browser vs. desktop shell.

Everything here follows the standing invariants: no new path to orders, pure
logic testable without the server, tests green per commit, and it all runs on
the Ryzen 5500U / 15.5 GB host.

---

## P0 — The dashboard is slow (root cause found; fix architecture below)

### 0.1 Diagnosis (verified in code + the operator's own logs)

**Root cause: blocking work runs on the asyncio event loop.** One process,
one loop — when the loop is busy, *everything* freezes: every HTTP response,
every WebSocket frame, every scheduled job. Evidence:

1. **`MarketDataService.poll_all` is `async def`** scheduled on the
   `AsyncIOScheduler` → it executes **on the loop**, and with
   `ATS_DATA_SOURCE=nse_live` it makes **synchronous yfinance/NSE network
   calls inside it** (per symbol, with the yfinance cookie/crumb dance and
   retries). The operator's logs show Yahoo degraded (DNS failures to
   `fc.yahoo.com`, `401` retry loops). Under that, a 54-symbol cycle pins the
   loop for **minutes per hour**, during which every page request queues.
   This is the 1–2-minute tab load.
2. **The event bus dispatches inline on the loop** (`await handler(event)` in
   `ats/core/events.py`): each BAR triggers strategy evaluation (pandas × ~24
   strategies), league marks, and analytics handlers as loop-blocking CPU
   bursts right after each poll.
3. **The scheduler warnings prove it**: `Run time of job
   "DashboardService.broadcast_snapshot" … was missed by 0:00:01–0:16:10` —
   jobs (and therefore responses) are starved for exactly the stretches the
   operator experiences.
4. **`build_snapshot` is recomputed from scratch** on every `/api/dashboard`
   GET *and* every 5 s broadcast, and contains an N+1 query (60 news rows ×
   one `SentimentScore` lookup each on the un-indexed `news_id` column).
   Today's DB is small (10 MB) so this is seconds not minutes — but it grows
   quadratically with data and must be fixed while we're here.
5. Boot: with `nse_live`, startup backfills history for the whole watchlist
   over the same degraded network, serially → the slow boot.

Not guilty (checked): API handlers are sync `def` (threadpool, correct);
SQLite is already WAL; `llm_status` reads cached state (no probe per call);
DB is tiny.

### 0.2 Fix workstreams (ordered; each independently shippable)

**P0.1 — Measure first (0.5 d).** Add a timing middleware that logs
`method path status duration_ms` for every request over 500 ms, an **event-
loop lag probe** (a 1 s heartbeat task that logs when its own wake-up is
> 250 ms late, with the currently-running job name), and per-job durations in
APScheduler listeners. Persist the last N slow samples to a ring buffer
exposed at `GET /api/perf`. This proves the diagnosis on the live box and
becomes the Ops Console's data feed (P4). Acceptance: after one market hour,
`/api/perf` names the offenders with numbers.

**P0.2 — Get the network off the loop (1 d). The big one.**
- In `MarketDataService.poll_all`, wrap every `source.poll(symbol)` in
  `await asyncio.to_thread(...)` (same for `intraday` on the charts request
  path and the boot backfill). The loop then only orchestrates; sockets wait
  in worker threads.
- Add hard timeouts to the nse_live/yfinance source (session-level, ~10 s)
  and **circuit-break**: after 3 consecutive symbol failures, skip the rest
  of the cycle and log one warning (the current per-symbol retry storm is
  what turns a bad network day into a frozen dashboard).
- Same `to_thread` treatment for any other scheduled `async def` that does
  sync I/O (scraper collect, options chain poll — audit all
  `scheduler.add_job` targets).
  Acceptance: with the network cable pulled mid-session, every page still
  loads in < 1 s.

**P0.3 — Get heavy CPU off the loop (1 d).**
- Bus fan-out: strategy evaluation on BAR is the biggest CPU burst. Either
  run `StrategyService`'s evaluation body in `asyncio.to_thread` (it's pure
  pandas; publish results back on the loop), or batch: collect the cycle's
  bars and evaluate once per cycle in one worker thread instead of per-bar.
- `AnalyticsService.run_poll_pass` and league marks: same `to_thread`.
  Acceptance: loop-lag probe (P0.1) shows p99 lag < 100 ms during a poll
  cycle.

**P0.4 — Stop recomputing the dashboard snapshot (0.5 d).**
- `DashboardService` computes the snapshot once per broadcast tick (in a
  worker thread), stores it; `GET /api/dashboard` serves the **cached** dict.
- Kill the N+1: one `SELECT … WHERE news_id IN (…)` (or a join), and add
  `index=True` to `SentimentScore.news_id` (plus a tiny migration:
  `CREATE INDEX IF NOT EXISTS ix_sentiment_scores_news_id …` on init).
- Trim the payload: the 5 s broadcast doesn't need 60 news items; 15 is
  plenty, pages fetch more on demand.
  Acceptance: `/api/dashboard` p95 < 50 ms.

**P0.5 — Boot time (0.5 d, lower priority as agreed).**
- Skip the boot backfill for symbols whose stored history is < 3 days stale;
  fetch the rest in a background task *after* the server is listening (the
  dashboard shows "warming up" instead of blocking startup).
- Defer `AnalyticsService.run_close_pass()` on boot to a background task too.
  Acceptance: `Uvicorn running` within ~10 s of launch on nse_live.

**P0.6 — Client-side polish (0.5 d).**
- Pages render their skeleton immediately and fill panels as fetches land
  (most already do; audit any page that awaits before first paint).
- Pause WS-driven re-rendering when `document.hidden` (saves the laptop's
  browser RAM/CPU too — see P5).

## P1 — Quick fixes

**P1.1 — Theme popup overflow (15 min).** Four theme buttons now overflow the
230 px popover and "Minecraft" escapes the box. Fix in `app.css`: let the
segment wrap — `.popover{width:260px}` and
`#segTheme{flex-wrap:wrap}` with `.seg button{flex:1 1 45%}` (2×2 grid).
Check both variants + the Liquid Glass frosted popover.

**P1.2 — FinBERT "missing" (0.5 d).** Not a bug — the transformer weights
were never provisioned on this laptop, so the scorer correctly falls back to
VADER (`finbert_unavailable_using_vader` in the logs; by design the server
never downloads at boot). Make it a one-command fix + visible:
- `scripts/provision_finbert.py`: one-time ~440 MB download of
  `ProsusAI/finbert` into the local HF cache (uses `truststore` for corporate
  TLS), prints verification; after it, restarts load FinBERT offline.
- Surface the active sentiment backend on the System page and in
  `/api/health` (`sentiment: finbert|vader`), so "is FinBERT on?" is a glance,
  not a log dig. Remember the RAM cost (~800 MB) — on this laptop VADER is a
  legitimate default; document both in `.env`.

**P1.3 — Undervalued/overvalued surface (1 d).** The math shipped (QA-6
fair-value verdicts) but there are two gaps: (a) **no data yet** — the
statements refresh is cron'd for Sun 18:00 IST and has never run on this
machine, so `fair_value` correctly refuses for every symbol and every verdict
is empty; (b) **no dedicated page section**. Fix both:
- Add a "Refresh statements now" button on the Screener page (POST
  `/api/analytics/refresh-statements`, runs in a worker thread with progress)
  + run it once at install time.
- Add **Undervalued / Overvalued tabs** on the Screener page fed by
  `verdict == undervalued|overvalued`, sorted by margin-of-safety, showing
  intrinsic vs price, the sensitivity range, and the F-score. Add an
  "Valuation" card on Today listing the top 5 undervalued names (verdict
  chips link to the Control Room drawer, which already renders the full DCF
  breakdown).

## P2 — Simulated demat account (1.5 d)

We have the bank ledger (`AccountLedger`) and the broker (`BrokerSim`) but
holdings live only as broker positions — real Indian plumbing has a third
box: the **demat account** where settled securities sit. Model it:

- **`DematAccount`** (`ats/services/accounts/demat.py` + models): one per
  trading profile (main + each league solo account), fields: `account_id`,
  `dp_name` (fake DP, e.g. "ATS Depository"), `bo_id` (generated 16-digit),
  linked `ledger_account_id`.
- **`DematHolding`** rows: (account, symbol, qty_settled, qty_pending,
  avg_cost). **T+1 settlement**: a BUY fill creates `qty_pending`; a
  scheduled settlement pass (or the next daily close) moves pending →
  settled, mirroring how Indian T+1 works. SELLs debit settled qty (and
  refuse to over-sell settled+pending — a *real* constraint the broker sim
  currently doesn't enforce).
- **Wiring**: `BrokerSim` posts every fill to the profile's demat account the
  same way it already posts cash to the ledger. Reconciliation gains a third
  check: broker positions == demat (settled+pending) per account.
- **UI**: an **Accounts** view (lives in the Ops Console, P4.6) listing every
  profile with its bank ledger (balance, statement) and demat account
  (BO ID, holdings, pending settlements, holding statement CSV export).
- Tests: fill → pending → settled lifecycle; over-sell refusal; recon check;
  league solo accounts each get their own demat pair.

## P3 — Categorized news (1.5 d)

Replace the flat list with an investing.com-style taxonomy. We already have
NER ticker mapping + `event_type` on `NewsItem`; add a deterministic
classifier at ingest:

- **Categories** (config-free enum): `stock_markets`, `earnings`,
  `analyst_ratings`, `commodities`, `currencies`, `crypto`, `economy`,
  `economic_indicators`, `ipo`, `breaking`. (No "Pro News" — that's a
  paywall tier, not a category.)
- **Classifier** (`ats/services/scraper/categorize.py`, pure):
  keyword/regex + signal rules — e.g. `earnings` on "Q[1-4]|results|profit
  rises|guidance"; `analyst_ratings` on "upgrade|downgrade|target price|
  buy rating"; `economic_indicators` on "CPI|GDP|IIP|PMI|repo rate";
  `commodities` on gold/crude/metals terms or commodity tickers; `breaking`
  when a high-impact keyword (acquisition, bankruptcy, fraud, SEBI order,
  default) hits — breaking items also fire a toast. One category per item
  (first match by priority), stored on `NewsItem.category` (indexed);
  a backfill script recategorizes the archive.
- **UI**: tab bar on `/news` with per-category counts + a "Breaking" strip
  pinned on top when non-empty; `GET /api/news?category=…`. Sentiment dots
  and the reader stay as they are.
- Tests: classifier fixtures per category; API filter; backfill idempotence.

## P4 — The Ops Console (the big one, ~5 d)

A **dedicated observability surface, separate from the money dashboard** —
"the engine room" vs "the trading desk". Same process (no second server on
this laptop), mounted under `/ops/*` with its own nav zone so the two worlds
don't mix visually. Reuses Control-Room styling. Six panels:

**P4.1 Instrumentation substrate (build first — everything reads from it).**
- A `@instrument("component.fn")` decorator + `span("...")` context manager
  (`ats/core/telemetry.py`): records start/duration/outcome into an
  in-memory ring buffer (last ~5 000 spans) and rolls up per-component
  counters (calls, errors, p50/p95, last_error). Zero I/O on the hot path;
  a 60 s job flushes hourly rollups to a `telemetry_rollups` table for
  history. Outcomes are a defined enum: `OK | SLOW | ERROR | SKIPPED |
  DEGRADED` (the operator's "function calls mapped to defined enums").
- Apply to every service's public entry points (poll, evaluate, collect,
  research pass, broker ops) — a mechanical sweep, ~40 call sites.
- **Health model**: per-service `HealthState = OK | IDLE | DEGRADED | DOWN`
  derived from heartbeats + error rates + staleness (e.g. market_data is
  DEGRADED when >30 % of symbols fall back to synthetic; DOWN when the last
  successful poll is > 5 min old in-session). One registry, `GET
  /api/ops/health`.

**P4.2 System map.** A live node graph of the pipeline (we already have
`TOPIC_STAGE` + the bus counters): services as nodes colored by
`HealthState`, edges = topics with events/min flowing along them (animated
dots under `data-motion=full`). Click a node → its panel: recent spans,
error samples, p95s, its scheduler jobs + next run times. This is the
existing `/system` pipeline view, deepened and moved here.

**P4.3 Resources.** Process RSS/CPU via `psutil` (one new lightweight dep),
sampled every 15 s into the ring buffer: total + per-component *attributed*
costs where knowable (FinBERT model bytes via torch, DataFrame cache sizes,
DB file size, WAL size, log dir size). Honest labeling: Python doesn't give
true per-module RAM; we show measured process totals + attributed estimates,
clearly marked. Sparkline history per metric.

**P4.4 Models panel.** Local model observability: sentiment backend
(finbert/vader) + scoring latency + label distribution over 24 h; LLM panel
**moved here from the money dashboard** (`/llm` page relocates): every
prompt/response, tokens, cost, budget burn-down, provider health/cooldowns,
and the mock-vs-real chip. Regime classifier state + flip history.

**P4.5 Perf panel.** The P0.1 feed made visible: slow-request table,
event-loop lag chart, per-job durations, "missed jobs" log — the page the
operator opens instead of grepping logs when things feel slow.

**P4.6 Accounts & demat review.** Every trading profile (main + 9 solo
league accounts): bank ledger balance + statement, demat holdings + pending
settlements (P2), equity curve, last reconciliation result. The full
"which profile holds what, where" audit in one table.

- **Placement of existing pages**: `/logs`, `/llm`, and `/system` move under
  Ops; the money dashboard keeps Today/Control/Opportunities/Charts/
  Portfolio/League/Research/News/Screener. Old routes 308-redirect.
- Order: P4.1 → P4.5 (needs only P0.1+P4.1) → P4.2 → P4.3 → P4.4 → P4.6.

## P5 — Browser vs. desktop app (decision + rationale)

The instinct is right that a Chrome tab is heavy, but the ranking on *this*
laptop is unambiguous:

| Option | Extra RAM | Effort | Verdict |
|---|---|---|---|
| **Installed PWA in Edge** (already built, QA-11) | ~lowest — Edge is already resident on Win 11; an app-mode window shares its process pool | 0 (done) | **Do this now**: `Install app` from Edge, or a shortcut to `msedge --app=http://127.0.0.1:8000`. No tabs, no chrome, its own taskbar icon. |
| **pywebview / WebView2 shell** | Low — WebView2 runtime also ships with Win 11 | ~1 d | The upgrade path *if* we ever want tray icon / native menus / auto-start bundling. A 40-line wrapper, same dashboard inside. |
| **Electron** | **Worst** — bundles a second full Chromium (~300–500 MB RSS + disk) | days + build pipeline | Rejected: it re-adds exactly the cost being avoided. |
| **Native exe rewrite** (Qt etc.) | lowest at runtime | weeks–months, duplicate UI | Rejected: not worth it for one operator. |

Also note P0.6 (pause rendering when hidden) cuts the browser's steady-state
cost regardless of shell. Recommendation: PWA now, `pywebview` later only if
a tray icon is genuinely wanted.

## Sequencing & effort

| Order | Item | Effort | Gate |
|---|---|---|---|
| 1 | P0.1 measure | 0.5 d | `/api/perf` names offenders with numbers |
| 2 | P0.2 network off loop | 1 d | pages < 1 s with network unplugged |
| 3 | P0.3 CPU off loop | 1 d | loop-lag p99 < 100 ms during polls |
| 4 | P0.4 snapshot cache + index | 0.5 d | `/api/dashboard` p95 < 50 ms |
| 5 | P1.1 popup CSS + P1.2 FinBERT + P1.3 valuation surface | 1.5 d | all three visible in UI |
| 6 | P0.5 boot + P0.6 client | 1 d | boot < 10 s; skeleton-first pages |
| 7 | P2 demat | 1.5 d | T+1 lifecycle + recon tests green |
| 8 | P3 news categories | 1.5 d | tabbed /news, classifier fixtures |
| 9 | P4 Ops Console | ~5 d | six panels live; /llm /logs /system relocated |
| 10 | P5 | 0 d | PWA install documented in README |

Total ≈ 13–14 working days. P0 items 1–4 are the "make it usable again"
block — do them first and in order (measure → fix → verify with the same
measurements). Tests green at every commit, as always.
