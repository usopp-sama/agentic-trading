# Live-Readiness + Multi-User Plan (2026-07-11)

Covers the operator's full punch list: Zerodha login plumbing, the three keyed
news APIs, the "why does the UI look the same" root cause, Ops Console on its
own port with expanded panels, user profiles + login, the Portfolio/Zerodha
console revamp, Kite as the live market-data source — and the go-live
checklist for the first 1-day and 1-week paper runs.

## ✅ Status (updated 2026-07-13) — where to resume

| Item | What it does | Status |
|---|---|---|
| stale-UI SW bug, Zerodha login, 3 keyed news APIs | see §0–§2 | ✅ **DONE** (merged) |
| **L1** | news-credits + LLM burn-down cards on `/ops` | ✅ **DONE** (merged) |
| **L2** | Kite as the live market-data source (`ATS_DATA_SOURCE=kite`, batched quotes, graceful fallback) | ✅ **DONE** (merged) |
| **L6** | go-live hardening: watchdog health alerts, 08:45 IST pre-open GO/NO-GO email, nightly DB backup | ✅ **DONE** (merged) |
| **L3** | Portfolio tab revamp + Zerodha console (live LTP rows, click-to-chart, Kite funds) | ⬜ **OPEN** (~2 d) |
| **L4** | Ops Console on its own port (`ATS_OPS_PORT`), operator-only | ⬜ **OPEN** (~1.5 d) |
| **L5** | user profiles + login portal (the multi-user groundwork) | ⬜ **OPEN** (~3 d, the big one) |

**Resume at L3** (portfolio/Zerodha console) — it's the highest day-to-day value
and doesn't touch the trade path. L4/L5 are observation/multi-user, buildable
during a paper run. Full specs below.

---

## 0. Root cause found: the stale-UI bug (FIXED this session)

Categorized news tabs, the Ops polish, and the Minecraft popover fix all
shipped earlier — but the PWA **service worker (v1) served every page
cache-first and never revalidated**, so the browser kept showing week-old
HTML forever. That one bug explains all three "it looks the same" reports.

**Fixed:** `sw.js` v2 — pages are now **network-first** (cache only as an
offline fallback), static assets are cache-first with background revalidate,
`/api` + `/ws` are never intercepted, and the cache name is bumped so old
caches are purged on activate.

**Operator action (once):** restart the server, then in the browser press
**Ctrl+Shift+R** (or DevTools → Application → Service Workers → Update/
Unregister, then reload). After that one hard reload the new worker takes
over and every future deploy shows up on a normal refresh. Also fixed as
belt-and-braces: the Minecraft theme popover now wraps its 4 theme buttons
2×2 (`themes/minecraft.css`).

## 1. Zerodha redirect URL — what Gemini meant, and what's already built

Gemini's explanation is correct, and **the "best practice" version it
recommends is already implemented in this repo** (commit `80dcc31`):

- The **Redirect URL** is not a server or a port — it's just the address
  Zerodha sends your browser back to after login, carrying a one-time
  `request_token` in the query string. Only one process listens on :8000
  (our dashboard), so nothing clashes.
- The flow: `GET /kite/login` → redirects you to Zerodha's login page →
  you log in → Zerodha redirects to **`http://127.0.0.1:8000/kite/callback?request_token=…`**
  → our handler exchanges `request_token + api_secret` for the day's
  `access_token` and stores it. One click a day (Zerodha tokens expire daily
  at ~6 AM by design — no way around that on a personal API key).

**Operator action (once):** in the [Kite developer console](https://developers.kite.trade/apps),
set the app's Redirect URL to exactly `http://127.0.0.1:8000/kite/callback`,
and put `ATS_KITE_API_KEY` / `ATS_KITE_API_SECRET` in `.env`. Then each
morning: click **Login** in the Ops → Kite card. Docs: `docs/kite_setup.md`.

## 2. Keyed news APIs (BUILT this session)

Three collectors added alongside RSS/Marketaux, each self-throttled to its
free-tier daily budget so the 288 daily polls can't blow a quota:

| Source | Budget | Throttle | Note |
|---|---|---|---|
| newsapi.org | 100 req/day | 15 min (≈96/day) | business/top-headlines IN |
| newsdata.io | 200 credits/day | 15 min | **12 h delayed** — archive/slow-loop value, not breaking |
| currentsapi.services | ~1000 req/day | 10 min | business IN |

Every successful call bumps a per-source **daily credit counter** in kv
(`news_credits`), ready for the Ops Console panel (L4). All three keys live
in the gitignored `.env`. Items flow through the existing pipeline:
sanitize → dedupe → ticker-map → **categorize** → FinBERT → archive, so the
category tabs fill from all sources automatically.

> ⚠️ Key hygiene: these keys were pasted into a chat session. They're
> free-tier news keys (low blast radius), but rotate them at leisure and
> treat `.env` as the only home for keys going forward.

## 3. Remaining workstreams

### L1 — News credits + Gemini spend in Ops (0.5 d)
`GET /api/ops/news-credits` reading the `news_credits` kv + a card in
`/ops` next to Local models; LLM panel already shows est. spend — add the
month-to-date vs `ATS_LLM_MONTHLY_BUDGET_INR` burn-down bar (Gemini is now
live, ₹350/mo cap — the budget gate already enforces it for autonomous runs).

### L2 — Kite as the live market-data source (1.5 d)
`kite_history.py` already authenticates + pulls daily/intraday candles (used
by `--kite` backtests). Add a `KiteLiveSource` in
`ats/services/market_data/sources.py` implementing the same `poll()/intraday()`
protocol via Kite `quote/ohlc` + historical candles, registered as
`ATS_DATA_SOURCE=kite`, with **graceful fallback to nse_live when the daily
token is missing/expired** (never a dead feed at 9:15 because you hadn't
clicked Login yet). Rate limits: Kite allows 3 req/s on quotes — batch the
watchlist into one `quote()` call per poll (it accepts up to 500 symbols).
Instrument-token mapping comes from the instruments dump, cached daily.

### L3 — Portfolio tab revamp + Zerodha console (2 d)
One page, three layers:
1. **Accounts switcher**: paper (main) + league solos + (later) each user
   profile — same table schema for all.
2. **Holdings/positions with live values**: each row gains LTP (from the
   market-data cache — no extra network), current value, day P&L and total
   P&L; every row **click-through to `/charts?symbol=…`** (same pattern the
   Screener rows already use).
3. **Zerodha console card** (read-only mirror of the Kite app): funds/
   available cash (`kite.margins()`), real holdings (`kite.holdings()`),
   positions (`kite.positions()`), and order book — clearly badged REAL vs
   paper. No bank linking anywhere; cash lives in Zerodha, we just read it.
   Requires the daily Kite login; degrades to "login required" card.

### L4 — Ops Console as its own UI on its own port (1.5 d)
Same process (one Python, one DB — the laptop constraint), but a **second
uvicorn server task** bound to `ATS_OPS_PORT` (default 8001) serving an
ops-only FastAPI app that shares the orchestrator. `/ops*` and `/api/ops/*`
+ `/api/perf` + logs/LLM pages move there; the money dashboard on :8000
drops them from its nav (links point to :8001). Panels added: news credits
(L1), LLM burn-down, hardware (psutil — `pip install psutil`), broker usage
per strategy (order/fill counts + fees per account), bank(ledger)+demat
portal (exists), Kite session status. Optional shared-token gate reused.

### L5 — User profiles + login portal (3 d, the big one)
Groundwork for friends using it later:
- **Model**: `User` (id, email, password_hash — passlib/bcrypt, role:
  operator|viewer, created_ts) + `user_accounts` mapping user → trading
  account ids (each friend's profile = its own paper account with its own
  ledger + demat, exactly like league solos — the plumbing already exists).
- **Auth**: session-cookie login (`/login`, `/logout`, signed cookie via
  `itsdangerous`), middleware that scopes every accounts/portfolio API to
  the session user; `operator` sees everything + controls (mode/kill),
  `viewer` sees only their own portfolio, read-only. Kill/mode/approvals
  stay operator-only. The Ops port is operator-only.
- **UI**: login page + a profile chip in the header; Portfolio's account
  switcher lists only your accounts unless operator.
- Explicitly **not** multi-tenant real-money custody — friends get paper
  accounts under your instance; SEBI licensing is a hard wall before ever
  taking anyone's real money.

### L6 — Go-live hardening (1 d)
- Alerting on DEGRADED/DOWN health → email/Telegram (channels exist).
- Daily 08:45 IST pre-open self-check: feed up, Kite token fresh, disk OK,
  budget OK → one "GO/NO-GO" email.
- Nightly DB backup (`scripts/backup.sh` → Task Scheduler).

## 4. What blocks the first 1-day / 1-week paper run (the honest gate list)

Nothing *hard* blocks a paper run today — PAPER mode with nse_live works.
For a run worth trusting, in order:

1. **Host discipline (0 code):** never-sleep on AC, Task-Scheduler autostart,
   Defender exclusion for `var/`, pinned PWA window. (Plan §P0 of
   perf_and_ops_console — checklist already in README.)
2. **Backtest gate re-run (you're doing 3y tomorrow):** current 1y run shows
   **0 strategies cleared the deflated-Sharpe gate** — the turmoil year
   punished everything except `nav_premium` (Sharpe 2.17, DSR 0.58). A paper
   week is *evaluation*, fine — but position sizing should stay small and
   the league/shadow separation is what makes the week meaningful.
3. **L2 Kite live source** — better data than yfinance during the session
   (or accept nse_live for week 1; it works).
4. **L6 alerting + pre-open self-check** — so a silent failure doesn't waste
   the week.
5. **FinBERT + Gemini live** (done — verify `sentiment: finbert` and
   `llm: real` on /ops after restart) and news keys flowing (watch
   `news_credits` counters day 1).
6. Not needed for the week: L3/L4/L5 (UI/multi-user) — they improve
   observation, not the run itself.

**Suggested sequence:** L1 → L2 → L6 → start the 1-week paper run → build
L3/L4/L5 *during* the run (they don't touch the trade path).

## 5. Sequencing

| # | Item | Effort | Gate | Status |
|---|---|---|---|---|
| 1 | L1 credits panels | 0.5 d | news + LLM burn visible on /ops | ✅ done |
| 2 | L2 Kite live source | 1.5 d | `ATS_DATA_SOURCE=kite` polls the session; falls back cleanly | ✅ done |
| 3 | L6 hardening | 1 d | GO/NO-GO email fires at 08:45 IST | ✅ done |
| — | **Start 1-week paper run** | — | mode PAPER, small sizing, league on | ← next |
| 4 | L3 portfolio + Zerodha console | 2 d | live LTP rows, click-to-chart, Kite funds visible | ⏳ |
| 5 | L4 ops on :8001 | 1.5 d | two UIs, ops gated | ⏳ |
| 6 | L5 users + login | 3 d | friend logs in, sees only their paper book | ⏳ |

## 6. Build log (this session)

The three pre-run workstreams are built, tested (573 pass), and verified on a
live boot:

- **L1** — `GET /api/ops/news-credits` (per-source used/budget) + `GET
  /api/ops/llm-budget` (month-to-date vs cap), with two burn-down cards on
  `/ops` next to Local models. Verified live in the preview.
- **L2** — `KiteLiveSource` (`ats/services/market_data/sources.py`): daily
  `historical_data` with the last bar overlaid by a **batched** `quote()` LTP
  call (≤500/call), minute candles, and Kite→nse_live→synthetic fallback so the
  feed is never dead at 9:15. `ATS_DATA_SOURCE=kite` wired; degrades cleanly
  when `kiteconnect`/token are absent. Pure helpers unit-tested.
- **L6** — watchdog now edge-alerts on any service DEGRADED/DOWN
  (`diff_health` + `check_component_health`); a daily 08:45 IST
  `PreOpenCheckService` emails a GO/NO-GO readiness sweep (feed/kite-token/disk/
  budget/kill-switch); `scripts/backup.py` takes WAL-consistent nightly SQLite
  snapshots (Task Scheduler line in README).

**Operator note:** the stale-UI bug (§0) was confirmed again this session — a
v1 service worker was still serving cached HTML in the browser. One
**Ctrl+Shift+R** (or unregister the SW once) clears it for good.
