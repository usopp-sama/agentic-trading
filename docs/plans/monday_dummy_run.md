# Monday Dummy-Run Plan — strategies trade a ₹1 lakh paper book

**Goal:** By Monday market open (09:15 IST), the quant **trading strategies place
real paper orders on their own** against a **₹1,00,000** paper book, you can
**watch them act on a dedicated dashboard page**, and the book is a clean
"demat"-style ledger (no selling what we don't hold, exits handled). News keeps
flowing, the server runs non-stop, and held names get extra news attention.

This is a *dress rehearsal* before the month-long run. Paper money only.

---

## 0. What already exists (verified in code)

| Capability | Status | Where |
|---|---|---|
| 25+ coded strategies (SMA, Donchian, RSI2, 12-1 momentum, mean-rev, pairs, factor, NAV-arb, …) | ✅ live, emit signals | `ats/services/strategies/library*.py`, registry in `reference.py:84` |
| Signal → DB + Opportunities UI + virtual sleeve P&L | ✅ | `strategies/service.py` |
| **Signal → actual order** | ❌ **missing** — `Topic.SIGNAL` has no execution subscriber | — |
| LLM pipeline trades (SME→CIO→Risk→Execution) on spikes/news | ✅ | `agents/`, `risk/`, `execution/` |
| Risk guardrails (position/sector/gross caps, daily-loss kill, rate limit, long-only clamp) | ✅ reusable | `risk/service.py`, `risk/guardrails.py` |
| Paper broker, positions table, cash/equity, blotter | ✅ | `execution/`, `/portfolio` page |
| No-naked-sell (SELL clamped to holdings), duplicate-fill guard | ✅ | `portfolio.py:70`, `execution/service.py:183` |
| Always-on scheduler (market poll 60s, news 300s, digests, watchdog) | ✅ | `server/orchestrator.py` + each service |
| Dashboard: today / opportunities / charts / portfolio / activity / news / experts / llm / logs / system | ✅ | `server/templates/` |
| **`/strategies` page (strategies in action)** | ❌ **missing** | — |
| Holdings-scoped news boost | ❌ news is global | `scraper/service.py` |

**Conclusion:** the strategies are built and computing — they're just not
plugged into the order path, and there's no screen to watch them. That's the gap.

---

## 1. Workstreams

### WS1 — ₹1 lakh capital (config only, no code-default change)
- Set in `.env`: `ATS_PAPER_STARTING_CAPITAL=100000`, `ATS_VOL_SLEEVE_CAPITAL=10000`.
- Reset the live book so the DB cash + positions match: `scripts/reset_paper_book.py`.
- Acceptance: dashboard header + `/portfolio` show equity ≈ ₹1,00,000, zero positions, P&L 0.

### WS2 — Strategy auto-trade wiring (**the core**)
New service `StrategyTraderService` (`ats/services/execution/strategy_trader.py`):
- Subscribes to `Topic.SIGNAL` (only `paper`-status strategies publish there).
- Keeps a per-symbol consensus: `views[symbol][strategy] = (direction, conviction)`.
- On each actionable signal, recompute a **net strategy score** for the symbol:
  - `bull = Σ conviction(direction>0)`, `bear = Σ conviction(direction<0)`
  - `net = (bull - bear) / max(1, n_voters)`, plus a count of agreeing strategies.
- Decide (debounced by a per-symbol cooldown):
  - **Not holding & `net ≥ buy_threshold` & agree ≥ min_agree →** publish a
    `PROPOSAL` `{action: BUY, target_weight: max_position_pct, conviction: net}`.
  - **Holding & `net ≤ exit_threshold` →** publish a `PROPOSAL`
    `{action: SELL, target_weight: 0}` (reduce to flat — clean exit).
- `contributors` carries the exact strategy votes + a plain-English `rationale`
  ("3 strategies bullish: sma_crossover 0.6, donchian_trend 0.5, rsi2 0.4") so the
  **`/activity` "why" shows what each strategy thought** — your requirement.
- **Reuses Risk + Execution unchanged**: sizing (`desired_target_qty` → fractional
  Kelly capped at `max_position_pct`), all guardrails, rate limit, paper fill,
  positions, blotter, duplicate-fill guard, feed-degraded entry block.
- **Safety:** master switch `ATS_STRATEGY_AUTOTRADE=true`; signals only arrive
  during the polling window (BARs only fire in-session), so trades are naturally
  market-hours bound; long-only; no LLM/Gemini cost on this path (pure quant).

Config additions (`config.py`): `strategy_autotrade_enabled`, `strategy_trade_buy_threshold`
(0.12), `strategy_trade_exit_threshold` (0.0), `strategy_trade_min_agree` (1),
`strategy_trade_cooldown_s` (300).

### WS3 — Sizing for a small book
- `ATS_MAX_TRADE_VALUE=15000` (per-order cap; `max_position_pct` 10% = ₹10k/name still binds).
- Net effect at ₹1L: up to ~10 names of ~₹10k each → fully invested, no single
  order can dominate the book.

### WS4 — `/strategies` dashboard page (watch them act)
- `StrategyService.live_state()` → roster (id/name/type/status), latest signal per
  strategy (symbol, stance, conviction), sleeve stats (equity, rolling Sharpe, weight).
- `GET /api/strategies` in `results_api.py`; template `strategies.html` with the
  signature-based render (no collapse-on-refresh bug); nav link in `base.html`.
- Shows: which strategies are **paper vs shadow**, their **current live calls**,
  and recent **strategy-driven orders** (filtered from the decisions/blotter).

### WS5 — Demat / holdings integrity (verify + harden)
- Confirm long-only sell-clamp + guardrails prevent selling unheld/over-held qty.
- Add a unit test (`test_no_naked_sell`) asserting a SELL with no/short holdings
  is clamped to 0/holdings.
- `/portfolio` already shows holdings + avg price + blotter; confirm it reconciles.

### WS6 — Holdings-scoped news monitoring
- In the agent news handler, **always evaluate held symbols** on relevant news
  (bypass per-symbol cooldown + universe filter, rank them first) so we react to
  news on what we own. Keeps global news flowing; just prioritizes the book.

### WS7 — End-to-end verification (always-on)
- Restart server; confirm scheduler jobs (market poll, news poll, digests, watchdog)
  are registered and firing.
- Run a **synthetic** in-session simulation (bypass market hours) to prove the full
  chain: BAR → strategy signal → PROPOSAL → Risk → DECISION → paper FILL → position
  on `/portfolio` and a card on `/strategies` + `/activity`.

---

## 2. Monday run procedure (operator checklist)
1. Sun night / Mon pre-open: `git pull`, ensure `.env` has the ₹1L + autotrade vars.
2. Reset book: `.venv/bin/python scripts/reset_paper_book.py`.
3. Start server (detached) → open dashboard; verify equity ₹1,00,000, autotrade ON.
4. 09:15 IST: watch `/strategies` (signals) and `/portfolio` + `/activity` (fills).
5. EOD: check daily digest email + P&L; review what each strategy did and why.

## 3. Risks & safeguards
- Long-only, paper-only, real-money gate hard-off.
- `max_position_pct` 10%, `max_trade_value` ₹15k, daily-loss kill 3%, rate limit 30/min.
- Master `ATS_STRATEGY_AUTOTRADE` kill switch; per-symbol cooldown stops churn.
- Strategies are mostly swing (multi-day) — expect a few entries Mon, not hyperactivity.
  No forced intraday square-off (these aren't intraday strategies); exits fire when
  strategies flip. (Say the word if you want EOD flatten instead.)

## 3a. Verification status (built + tested 27 Jun)
- ₹1L book live: reset script wiped the old 10L state, cash/equity = ₹1,00,000.
- StrategyTrader wired + unit-tested (7 tests) and registered in the orchestrator.
- `/strategies` page + `/api/strategies` live (HTTP 200; 9 paper, 16 shadow).
- **End-to-end synthetic smoke (throwaway DB):** strategy signals → consensus →
  PROPOSAL → Risk → DECISION → Execution → **paper fills, 14 positions opened**
  (SBIN, RELIANCE, TECHM, ONGC, BPCL, TMPV…). Risk guardrails confirmed firing
  (rate-limit, not-tradeable rejects). Holdings-scoped news path added.
- Server runs detached (`start_new_session=True`); always-on scheduler intact.
- Pending live proof: actual fills at Monday 09:15 open (no bars fire weekends).

## 4. After Monday → month-long run
- Promote/retire strategies by sleeve Sharpe; tune thresholds from Monday's behavior.
- Optional: move to always-on host (mini-PC/Pi). NLP runs locally; Gemini stays API.
