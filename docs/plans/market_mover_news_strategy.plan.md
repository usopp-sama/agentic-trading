# Market-Mover News Strategy ("Bellwether") — Plan (2026-07-13)

## The idea (operator's framing)

Powerful people move markets with their words and their disclosed trades. Collect
the **public** statements + disclosures of market-moving figures — Trump / the
White House / US agencies, Musk, Jensen Huang, Modi, Gadkari, the RBI, etc. —
score them for sentiment and map them to affected stocks/sectors, and trade the
reaction. Backtest it **event-driven** over our 3 years of Kite price history:
as the backtest clock reaches a statement's timestamp, *release* that statement
to the strategy, which buys/sells the affected name(s); measure how much money
the reaction earns.

This is **news trading on public information** — legal, and different from
insider trading (acting on material *non-public* info). The edge, if any, is
being a fast, disciplined reader of the public firehose. This plan is honest
about where that edge is real and where the data makes it a mirage.

---

## 0. The one thing that makes or breaks this: historical data

The strategy is only as good as a **complete, correctly-dated, point-in-time**
corpus of statements. This is the hard part, and it must be de-risked first
(Phase 0) before writing any trading logic.

**What we already have (live, not historical):** the news pipeline
(`ats/services/scraper/collectors.py`) with RSS + newsapi/newsdata/currents/
marketaux, FinBERT sentiment (`ats/services/nlp`), a ticker-mapper, and the
category taxonomy. These collect *going forward* — they do **not** give us a
3-year back-archive.

**Candidate historical sources (ranked by feasibility):**

| Source | Coverage | Cost | Dated? | Notes |
|---|---|---|---|---|
| **GDELT 2.0 GKG** | Global news 2015→now, every 15 min, with person/org/theme/tone extraction | **Free** | Yes (15-min buckets) | The backbone. Query "articles mentioning person X" with tone + date. BigQuery or raw CSV. |
| **Congressional/insider disclosures** (STOCK Act, Capitol Trades, Quiver) | US politician trades 2012→now | Free/freemium | Yes (filing date) | The literal "disclosed stock options" signal — high value, but **US equities**. |
| Trump archive (thetrumparchive.com) | Trump tweets 2009–Jan 2021 | Free dump | Yes | Ends at the 2021 ban; post-2023 Truth Social needs GDELT news proxy. |
| X/Twitter API | 2006→now | **Paid/restricted** | Yes | Historical access is expensive + gated now. **Avoid**; use GDELT news coverage as the proxy for "what they said." |
| newsdata.io / marketaux archive | ~2y | Paid tier | Yes | Backup for recent windows. |

**Decision:** GDELT is the primary historical source (free, dated, entity-aware).
Direct tweet scraping is out (cost + the ban gap). Congressional-disclosure data
is a strong **optional second track** but is US-centric (see §5).

**Selection-bias warning (the #1 way this lies to us):** if we only collect the
statements we *remember* moved markets, the backtest will look brilliant and be
worthless. The corpus must be built by a **mechanical rule** (every GDELT record
for figure X above a relevance threshold), never a hand-picked "greatest hits."

---

## 1. FinBERT's actual role (managing the expectation)

The operator's phrasing is "have FinBERT suggest what stocks to invest in."
Precisely: **FinBERT scores *tone* (positive/negative/neutral), it does not pick
stocks.** Stock selection needs an **entity→ticker/sector map**. So the pipeline
is three separate jobs, not one:

```
statement → (a) entity extraction  → which companies/sectors/policies?
          → (b) relevance + mapping → which tradeable NSE symbols?
          → (c) FinBERT sentiment   → buy (positive) / sell (negative) / skip
          → sized, decaying signal per symbol
```

(a)+(b) are where the alpha lives and where we have real control; (c) is the
existing FinBERT. The existing **SME/LLM layer** can optionally do (a)+(b) for
fuzzy cases, but the deterministic dictionary comes first (auditable, free, fast).

---

## 2. The figure registry + India relevance mapping

A config-driven registry of tracked figures, each with a **source weight** (how
much the market cares) and a **market scope**:

| Figure / body | Weight | Direct market | India read-through (the NSE trade) |
|---|---|---|---|
| Trump / White House | high | US | tariffs→IT/pharma/metals; risk-on/off→broad |
| US Fed / Treasury | high | US/global | rates→banks, IT (USD), gold/silver |
| Elon Musk | med | US (TSLA) | EV/auto ancillaries, battery/metals |
| Jensen Huang (NVIDIA) | med | US (semis) | Indian IT, data-center/power proxies |
| **Modi / PMO** | high | **India** | infra, defence, PSU, capex names — direct |
| **Nitin Gadkari** | med | **India** | roads/infra (LT), autos, EV, cement — direct |
| RBI Governor | high | India | banks, NBFCs, rates-sensitive |
| Finance Minister / Budget | high | India | sector-specific per announcement |

**Two signal channels by scope:**
- **Direct (Indian figures):** statement → NSE sector/name directly. Cleanest,
  strongest link. *Start here.*
- **Indirect (US/global figures):** statement → global theme → NSE **sector
  basket** (e.g. "Trump tariff on generic drugs" → short pharma exporters). Noisier,
  second-order, but this is where the "everyone reacts to Trump" intuition lives.

The mapping table reuses the `sector` field already on every symbol in
`ats/services/reference.py::UNIVERSE`, so "buy the auto basket" is one lookup.

---

## 3. Signal → trade logic

Per released statement, for each mapped symbol:
- **Direction:** FinBERT tone × the statement's stance toward the entity
  (praise vs threat) → BUY / SELL.
- **Size:** `source_weight × sentiment_confidence × relevance`, capped.
- **Aggregate:** net all same-day statements per symbol (a barrage on one name =
  one bounded position, not ten).
- **Decay/hold:** news alpha is short-lived — hold `N` days (config, default 3–5)
  then flatten, or exit early on an opposing statement. This is the key knob and a
  natural target for the E2 walk-forward + plateau check we just built.
- **Gate:** only trade statements above a relevance threshold that map to a
  tradeable, liquid symbol; everything else is logged, not traded.

Long-only first (matches the paper sleeve), long-short as a follow-up (reuse the
E1 machinery) so "threat to sector X" can actually short it.

---

## 4. The event-driven backtest engine (the new piece)

Our current gate replays **daily bars**. This strategy is driven by **timestamped
events**, so we add a thin event overlay that still reuses the existing panel,
fee model, and DSR/Sharpe/drawdown stats (so results are comparable and honestly
judged):

1. Build a **timeline**: `(timestamp, figure, statement, sentiment, mapped_symbols)`
   from the Phase-1 corpus, sorted.
2. Walk the daily price panel. On each day `t`, release only statements with
   `timestamp ≤ close(t)` and act on the **next** bar's open/close (no look-ahead:
   you cannot trade a tweet before it exists, and same-bar fills are cheating).
3. Open the sized position, hold `N` days, mark-to-market against the panel,
   charge the **realistic Indian costs** (the `fees.cost_bps` model we just wired).
4. Emit a return series → score with the **same `run_gate` statistics**
   (Sharpe, deflated Sharpe, MC drawdown, plateau/OOS) → the same legible
   plain-English + `Rs P&L` report, plus **per-figure attribution** ("Modi
   statements made Rs X, Trump statements lost Rs Y").

Point-in-time integrity is enforced by construction: the timeline is the only
input, and it is filtered by `timestamp ≤ t` every step.

---

## 5. Optional second track — disclosed trades ("insider echo")

The operator's "disclosed stock options" point: US **STOCK Act** filings
(congressional trades) and executive Form-4s are public, dated, and a *literal*
"what insiders did" signal — arguably stronger than sentiment. Free datasets
exist (Capitol Trades / Quiver). Caveat: it's **US equities**, and filings lag
the trade by up to 45 days (the alpha may be gone). Fit for us:
- **v1:** skip for NSE (the India link is too indirect to backtest cleanly).
- **later:** a separate US-market sleeve, or an India read-through basket
  (e.g. heavy congressional buying of US semis → tilt Indian IT). Flagged, not
  built, until the sentiment track proves the plumbing.

---

## 6. Honest reality checks (read before believing any P&L)

- **Selection bias** (§0) — the biggest risk; enforced away by mechanical corpus
  building.
- **Alpha decay / latency** — by the time free data (GDELT ~15 min; RSS slower)
  surfaces a statement, fast money has often moved. A *daily* backtest is a coarse,
  optimistic proxy for a latency-sensitive edge. We will **not** claim intraday
  precision we can't backtest.
- **India second-order noise** — US-figure → NSE links are weak and regime-dependent;
  expect the **direct Indian-figure** channel to carry most of any real edge.
- **Look-ahead & survivorship** — enforced by point-in-time release; symbols must
  exist and be liquid on the trade date.
- **Multiple testing** — every figure×sector×hold-period combo is a "trial." The
  deflated-Sharpe gate (n_trials-aware) and the plateau check will punish a
  configuration that only looks good because we tried many. Good — that's the point.

If, after all that, a **direct-Indian-figure** sleeve clears the gate with
realistic costs, it's a genuine, tradeable edge. If it doesn't, we'll have learned
that cheaply and honestly — which is the whole discipline of this project.

---

## 7. Phased implementation (each phase independently useful)

| Phase | Deliverable | Effort | De-risks |
|---|---|---|---|
| **P0 — data spike** | Prove we can pull 3y of dated, mechanical GDELT records for 3–4 figures (Modi, Gadkari, Trump, Musk) with tone. A notebook/script + a saved sample corpus. | 1 d | The whole idea — do this FIRST |
| **P1 — figure registry + collector** | `figures.py` registry (config-driven) + a historical collector → a dated `statements` table (source, ts, figure, text, url). | 1.5 d | corpus completeness |
| **P2 — entity→symbol mapper** | Deterministic dictionary (figure/theme → NSE sector → symbols), reusing `reference.py` sectors; optional LLM fallback. Unit-tested on canned statements. | 1.5 d | the alpha logic |
| **P3 — signal generator** | statement → FinBERT tone → sized, decaying per-symbol signal. Reuses `ats/services/nlp`. | 1 d | direction/sizing |
| **P4 — event backtest harness** | Timeline replay reusing the panel + `fees` + `run_gate` stats + per-figure attribution + plain-English `Rs` report. | 2 d | honest measurement |
| **P5 — results + report** | Run 3y, produce the money/hit-rate/attribution report with the §6 caveats surfaced in-line. | 0.5 d | the answer |
| **P6 — live wiring (optional)** | Plug the signal into the live paper book so it reacts in real time during a paper run. | 1 d | going live |

**Suggested first step:** P0 only. If GDELT gives us a clean, dated, mechanical
corpus for the Indian figures, the rest is straightforward and reuses ~70% of what
we already built (FinBERT, sectors, fees, the gate). If P0 is thin, we rescope to
the live-forward version (collect from today, trade paper, no 3-year backtest)
before sinking effort into a backtest the data can't honestly support.

## What this plan deliberately avoids
- No paid/scraped Twitter data; no acting on non-public info.
- No claim of intraday precision a daily backtest can't support.
- No hand-picked "greatest-hits" corpus — mechanical collection only.
