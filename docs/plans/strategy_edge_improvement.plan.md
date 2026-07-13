# Strategy Edge Improvement Plan (2026-07-12)

## Why this plan exists

The 2026-07-12 3-year Kite backtest (`var/backtest_3y.log`) ran cleanly end to
end — real authenticated NSE history, 50/54 symbols, the fundamentals
circuit-breaker firing correctly — and returned **0 of 26 strategies clearing
the deflated-Sharpe (DSR) gate**, both as a dry run and with `--apply`. Nothing
was promoted; the paper book is unchanged (every strategy remains `shadow`).

This is not a bug and not evidence the strategies are broken. It is the
multiple-testing correction (`quant.backtest.validation.deflated_sharpe_ratio`,
Bailey & Lopez de Prado 2014) doing exactly its job: when 26 strategies are
tested at once (`n_trials=26` in `ats/services/strategies/backtest.py`), the
best-looking one is *expected* to look good by chance alone, so the gate
subtracts that expected noise-max before calling anything real. Best result —
`core_allocation`, Sharpe 1.10 — clears only 45% confidence (DSR 0.45) against
the 90% bar. That is a genuinely high standard, deliberately.

This plan is about **raising real DSR, not lowering the bar.** Six
workstreams, ordered by expected leverage per unit of effort. Every item below
was diagnosed from the actual code paths (cited), not generic advice.

---

## E1 — Fix the long-only flattening of stat-arb strategies (0.5 d)

**Diagnosis:** `ats/services/strategies/backtest.py::_stance_position` maps
`BUY→1.0`, everything else (including `SELL`) `→0.0`. `pairs_zscore` and
`coint_pairs` are inherently long-short — the backtest harness silently
discards their short leg and measures them as long-only, which cannot
represent what they actually do. Their reported Sharpe (0.27, 0.45) is not
their real Sharpe; it's a mutilated long-only proxy of it.

**Fix:** add a `replay_long_short` path (mirrors `replay_per_symbol` /
`replay_universe`) that maps `BUY→+1.0`, `SELL→-1.0`, `NEUTRAL→0.0`, and route
strategies that declare a `long_short = True` class attribute through it.
Re-score `pairs_zscore` and `coint_pairs` with the corrected harness before
touching anything else — this alone may change their standing materially.

**Acceptance:** both strategies show a distinct Sharpe under long-short replay
vs. the current long-only number; a unit test proves a synthetic mean-reverting
pair (short the rich leg, long the cheap leg) produces a *positive* return
series that the long-only replay would have scored ~0 or negative on.

## E2 — Wire the existing walk-forward evaluator into the gate (1.5 d)

**Diagnosis:** `quant/backtest/validation.py` already has `walk_forward()`
(train on a rolling window, trade the *next* unseen window, stitch only the
out-of-sample returns) and `plateau_ratio()` (is the best parameter on a
robust plateau, or a curve-fit spike?) — **both fully built and unit-tested,
neither wired into `run_gate()`**. The gate currently backtests each
strategy's *fixed, already-chosen* logic once over the full static 3-year
panel — a single in-sample fit, not a genuine walk-forward test.

**Fix:** for strategies with tunable parameters (most `library_trend_mr.py` /
`library_factors.py` sleeves), add an opt-in walk-forward mode to `run_gate`:
`train=252, test=63` (1yr train / 1 quarter test, rolling), report
`oos_sharpe` from the stitched out-of-sample curve instead of (or alongside)
the static full-period Sharpe, and add `plateau_ratio` as a printed diagnostic
column — flag `< 0.6` as "likely curve-fit, treat DSR with suspicion" even if
it technically clears the bar.

**Acceptance:** `run_gate(..., walk_forward=True)` produces an `oos_sharpe`
per strategy; a strategy with a known parameter cliff (test fixture) shows
`plateau_ratio < 0.6` and is flagged.

## E3 — Broaden the universe for cross-sectional strategies (1 d)

**Diagnosis:** the momentum/factor family did worst this run
(`xs_momentum` -0.37, `factor_composite` -0.59, `dual_momentum` -0.09,
`high_52w` -0.15) — and the current universe is ~50 large-caps. Cross-sectional
strategies need *dispersion* between names to find an edge; in a turmoil year
where large-caps move together on macro shocks (correlations spike toward 1),
a 50-name large-cap-only universe minimizes exactly the dispersion these
strategies are trying to harvest.

**Fix:** extend `ats/services/reference.py`'s instrument universe with NIFTY
Midcap 150 constituents (Kite's instrument dump already covers them — no new
data source needed, just a longer symbol list), gated behind a config flag
(`ATS_UNIVERSE_INCLUDE_MIDCAP`) so the smaller/original universe stays
available for comparison runs.

**Acceptance:** re-running the gate with the expanded universe shows measurably
higher return dispersion (cross-sectional daily return stdev) for the same
3-year window, and the four worst-performing strategies above are re-scored.

## E4 — Two-stage gate to reduce the multiple-testing tax honestly (1 d)

**Diagnosis:** `n_trials=26` charges every strategy the full 26-way
multiple-testing penalty even though these are 26 *structurally different*
hypotheses (trend, mean-reversion, factor, stat-arb, seasonal), not 26 blind
re-tries of the same idea. Lopez de Prado's own guidance is that `n_trials`
should reflect genuine search breadth, and that **staged screening** (a wide,
lenient first pass to cut the field, then a much smaller, honest confirmatory
pass on fresh/held-out data) is the correct way to avoid both p-hacking *and*
over-penalizing real structural diversity. Doing this properly — not just
lowering the bar — requires new out-of-sample data for stage 2, which the
walk-forward split in E2 naturally provides.

**Fix:** Stage 1 — lenient screen (`sharpe > 0`, `n ≥ min_obs`) on the full
panel, cuts ~26 down to a shortlist (this run: ~20 have `sharpe > 0`). Stage 2
— re-score *only the shortlist* (`n_trials = len(shortlist)`, materially
smaller) on the E2 walk-forward out-of-sample returns only. This is the
statistically honest way to lower the effective multiple-testing tax without
weakening the standard.

**Acceptance:** documented in `run_gate`'s docstring with the Lopez de Prado
citation for the staged-screening rationale; a strategy that only looks good
because of stage-1 luck (verified via a synthetic all-noise fixture) still
fails stage 2.

## E5 — Improve the two closest strategies directly (1.5 d)

**`core_allocation`** (Sharpe 1.10, DSR 0.45, best dd95 of the top group at
-17.6%): regime-aware ETF ballast (`ats/services/strategies/core_allocation.py`)
across NIFTYBEES/GOLDBEES/SILVERBEES/LIQUIDBEES. Add a defensive tilt during
`regime.is_crisis()` (partial LIQUIDBEES/cash weight instead of staying fully
invested through the whole 3-year window) — the plan §7 regime classifier
already exists and is already wired to other sleeves; `core_allocation` isn't
using it defensively yet. Also sweep `core_alloc_rebalance_days` (currently 7)
against {5, 10, 14, 21} — rebalance cadence is untested against this data.

**`st_reversal`** (Sharpe 1.08, DSR 0.44, worst-in-class drawdown of the pair
at -25.85%): short-term mean-reversion's classic failure mode is reverting
*into* a strong trend. Add a trend filter (skip entries when ADX > 25 in the
adverse direction, using the existing `quant.analysis.indicators.adx`) so it
stops fighting strong trends — this should cut the drawdown tail without
necessarily hurting the Sharpe, which raises DSR from both sides (higher
Sharpe stability + the dd95 side benefit informs sizing later).

**Acceptance:** both re-run individually (not as part of the 26-way gate) show
DSR improvement over their 2026-07-12 baseline; the trend filter's win/loss
attribution shows fewer whipsaw entries against strong trends.

## E6 — Ensemble instead of solo promotion (1 d, exploratory)

**Diagnosis:** the research factory's committee-tilt machinery
(`ats/services/research/factory.py`, `apply_committee_tilt`) already exists to
blend multiple sleeves' views with bounded tilts — but the backtest gate only
ever evaluates strategies *solo*. An equal-weight ensemble of the current
top-4 by DSR (`core_allocation`, `st_reversal`, `quality_qmj`, `sma_crossover`)
diversifies away idiosyncratic variance without requiring any single strategy
to individually clear 0.90 DSR — this is the same math that makes diversified
portfolios have higher Sharpe than their average constituent.

**Fix:** add an `evaluate_ensemble(strategy_ids, weights)` helper next to
`evaluate_strategy` in `backtest.py` that averages the constituent return
series and scores the blend through the same DSR/Monte-Carlo pipeline — with
`n_trials=1` (one ensemble is one trial, not four), since testing pre-selected
diversifiers is a different statistical question than searching 26 strategies.

**Acceptance:** the top-4 ensemble's DSR is reported and compared honestly
against the solo-strategy results from this run; not treated as "cheating"
the bar, since it's evaluated once as its own hypothesis, and blend weights
are declared before scoring, not chosen after seeing the result.

## E7 — Data gaps to close (0.5 d)

`nav_premium` and `news_sentiment` returned `n=0 active obs` — not a
performance verdict, a data gap. `nav_premium` needs the ETF's live NAV series
(check whether Kite's historical fetch covers the NAV-vs-price differential
the strategy needs, or whether it needs a separate feed);
`news_sentiment` needs historical sentiment scores over the 3-year window,
which the backtest replay currently has no source for (sentiment only exists
going forward from when the scraper started running). Document the gap
honestly in the gate's output rather than silently reporting a 0 that looks
like "evaluated, failed."

## Sequencing

| Order | Item | Effort | Why this order | Status |
|---|---|---|---|---|
| 1 | E1 long-short replay fix | 0.5 d | Cheapest, most likely single high-value insight (pairs/coint are probably being underrated right now) | ✅ done |
| 2 | E7 data-gap labeling | 0.5 d | Cheap correctness fix, unblocks honest reporting | ✅ done |
| 3 | E2 walk-forward wiring | 1.5 d | Foundational — E4 and E5's trend filter both benefit from genuine OOS evaluation | ◑ partial (time-based OOS done; param-grid plateau deferred) |
| 4 | E4 two-stage gate | 1 d | Needs E2's OOS data to be statistically honest | ⏳ |
| 5 | E3 universe broadening | 1 d | Independent; re-run after E1-E4 land so the comparison is against the improved harness | ⏳ |
| 6 | E5 core_allocation + st_reversal tuning | 1.5 d | Targeted improvement on the two closest strategies | ⏳ |
| 7 | E6 ensemble evaluation | 1 d | Exploratory finish — try combining what E1-E5 produced | ⏳ |

### Build log (this session)

- **E1 done.** `_stance_position(stance, long_short=True)` maps `SELL→-1`;
  `replay_per_symbol`/`replay_universe` take a `long_short` flag;
  `portfolio_returns` now averages over `|pos|>0` (keeps short legs).
  `pairs_zscore` + `coint_pairs` declare `long_short = True` and are routed
  through it — they now show a `[L/S]` tag in the report and trade their short
  leg. Unit-tested (`tests/test_strategy_edge.py`).
- **E7 done.** `evaluate_strategy` distinguishes a *data gap* (no return series /
  never traded) from a real hold; the report shows `skip (data gap)` for
  `news_sentiment`/`nav_premium`/etc. instead of a misleading 0.
- **Observability (operator ask).** The gate now streams a plain-English line
  per strategy to the terminal AND `var/metrics/backtest_run_<date>.log`
  ("traded 30 stocks over 44 trades, made Rs 4,276 on Rs 1,00,000 — did NOT
  pass"), and `report.summary()` opens with a PLAIN ENGLISH headline (how many
  made money, the best, how many cleared the gate) above the detail table with
  trades / stocks / Rs P&L / win% columns.
- **E2 partial.** `run_gate(walk_forward=True)` (CLI `--walk-forward`) now
  reports a **time-based out-of-sample Sharpe** per strategy: hold out the first
  `wf_train=252` bars as burn-in, score only the stitched later `wf_test=63`
  windows (`walk_forward_oos` → `oos_sharpe`), and flag `[decay]` when the full
  Sharpe was positive but the held-out Sharpe fell below half of it. A new
  `oos_sh` column + headline line surface it. Unit-tested.
  - **Deferred (the other half of E2):** the *parameter-grid* `plateau_ratio`
    check needs each strategy to expose a `signal_fn(prices, **params)` +
    param grid so `quant.backtest.validation.walk_forward()` can refit per
    window. The stance-based strategies don't expose that yet; wiring it is a
    per-strategy effort (own workstream). The time-based OOS above is the
    honest, no-refit approximation that works on every strategy today.
- **Realistic costs (operator ask).** The gate previously charged a flat 5 bps
  on turnover — ~half the real Indian round-trip and blind to buy/sell
  asymmetry. It now defaults to the **same charge stack the paper broker uses**
  (`fees.cost_bps`: brokerage + STT + exchange + GST + SEBI + stamp) as
  per-side rates (~5.5 bps buy / ~14 bps sell; STT is sell-side, stamp buy-side).
  `backtest_signals` gained `buy_bps`/`sell_bps`; `run_gate`/`portfolio_returns`
  default to the Indian model (`fee_bps` still overrides for a flat cost). The
  report headline now states the assumption. This makes high-churn strategies
  (turn_of_month, tech_confluence) pay honestly for their turnover — results get
  slightly worse but truer. Unit-tested.
- **E5 done.** `st_reversal` got the falling-knife trend filter: it no longer
  BUYs a loser that is in a *confirmed* strong downtrend (ADX > `adx_max`=25
  AND -DI > +DI), via `quant.analysis.indicators.adx` — config knobs
  `st_reversal_adx_window`/`st_reversal_adx_max` (set max<=0 to disable). For
  `core_allocation` the two E5 asks were **already in the code**: the crisis
  defensive tilt (`_WEIGHTS["crisis"]` = 15/35/50 equity/gold/cash, applied on
  `VOL_CRISIS` and rebalanced immediately on a regime flip) and a config-driven
  cadence (`core_alloc_rebalance_days`, wired in `library.py`) — so the residual
  is a *data* exercise: sweep the cadence on real Kite history. Tooling added:
  `run_backtests.py --only <ids>` (test a subset in isolation) and `--n-trials N`
  (pin the DSR penalty so a subset stays comparable to the 26-way baseline);
  `run_gate` gained an `n_trials` override. Unit-tested.
  - **To confirm on real data (needs your Kite token):**
    `python scripts/run_backtests.py --kite --period 3y --only st_reversal --n-trials 26`
    and compare DSR to the 0.44 baseline; sweep core_allocation with e.g.
    `... --only core_allocation` after setting `ATS_CORE_ALLOC_REBALANCE_DAYS`
    to each of {5,10,14,21}.

**Still open (larger, multi-day):** E2 param-grid plateau, E4 two-stage gate,
E3 midcap universe, E6 ensemble.

Total ≈ 7 working days. Re-run `python scripts/run_backtests.py --kite
--period 3y` after each workstream to track DSR movement — that number, not
raw Sharpe, is the one to watch improve.

## What this plan does NOT do

- **Does not lower the DSR bar.** 0.90 stays 0.90. The fixes target the
  measurement (E1, E7), the methodology (E2, E4), the opportunity set (E3),
  the strategies themselves (E5), and honest diversification (E6) — never the
  threshold.
- **Does not promote anything without re-clearing the gate.** Every fix here
  still routes through the same shadow→paper promotion path.
- **Does not touch live/paper capital.** All work here is offline backtest
  methodology; the running paper book is unaffected until a future gate run
  clears with these fixes in place.
