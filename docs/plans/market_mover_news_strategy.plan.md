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

A config-driven registry of tracked figures, each with a **weight** (how much the
market listens, 1–5), a **market scope**, and the **NSE read-through** (the actual
trade). Kept in a `figures.yaml`-style config so it's editable without code. The
list below is the seed; the `[data]` column flags where a *dated, mechanical*
historical feed exists (the §0 constraint).

### 2a. India — political & policy (the cleanest, most direct signal)
| Figure / body | Wt | NSE read-through | Data |
|---|---|---|---|
| **Narendra Modi** / PMO | 5 | infra, defence, PSU, railways, capex, "Make in India" | press, GDELT, X |
| **Nirmala Sitharaman** (Finance Min) / Union Budget | 5 | sector-specific per announcement; taxes; PSU banks | press, GDELT |
| **Nitin Gadkari** (Road Transport) | 4 | roads/infra (LT), autos, EV, cement, logistics | press, GDELT, X |
| **RBI Governor** (Sanjay Malhotra) / MPC | 5 | banks, NBFCs, autos, realty (rate-sensitive) | RBI releases, GDELT |
| **Piyush Goyal** (Commerce/Industry) | 3 | exports, trade deals, textiles, e-commerce | press, GDELT |
| **Ashwini Vaishnaw** (Rail/IT/Telecom) | 3 | railways, semiconductors, telecom, electronics | press, GDELT |
| **SEBI Chair** | 4 | brokers, AMCs, exchanges; F&O/margin rule changes | SEBI circulars |
| **Hardeep Puri** (Petroleum) | 3 | OMCs (BPCL/IOC/HPCL), gas, ONGC | press |
| **Amit Shah** (Home/Cooperation) | 3 | fertilizers, sugar/cooperatives, defence | press, GDELT |
| Chief Economic Advisor / Economic Survey | 3 | macro tilt (cyclicals vs defensives) | Gov releases |
| Key state CMs (UP/Maha/Guj/TN) | 2 | state-capex, power, realty in that state | press |

### 2b. India — business leaders (company/sector specific)
| Figure | Wt | NSE read-through | Data |
|---|---|---|---|
| **Mukesh Ambani** (Reliance) | 5 | RELIANCE, Jio/retail/energy, telecom | AGM, press |
| **Gautam Adani** (Adani Group) | 5 | ADANIENT/PORTS/POWER/GREEN, ports, power | press, GDELT |
| **N. Chandrasekaran** (Tata Sons) | 4 | TCS, TATAMOTORS, TATASTEEL, TATAPOWER, Titan | press |
| **Anand Mahindra** | 3 | M&M, autos, EV, farm equipment | X, press |
| **Uday Kotak** | 3 | KOTAKBANK, financials sentiment | X, press |
| **Kumar M. Birla** (Aditya Birla) | 3 | GRASIM, HINDALCO, UltraTech, telecom (Vi) | press |
| **Radhakishan Damani** | 2 | DMART, retail | filings, press |
| Sanjiv Bajaj (Bajaj) | 2 | BAJFINANCE, BAJAJFINSV, auto | press |

### 2c. US — political & central bank (global risk-on/off → NSE second-order)
| Figure / body | Wt | India read-through | Data |
|---|---|---|---|
| **Trump / White House** | 5 | tariffs→IT/pharma/metals; USD→IT; risk-on/off→broad | Truth Social, GDELT |
| **US Fed Chair (Powell)** / FOMC | 5 | rates→IT (USD), banks, gold/silver, FII flows | Fed, GDELT |
| US Treasury Secretary | 4 | sanctions, tariffs, USD, bond yields | press, GDELT |
| US Trade Rep (USTR) | 3 | trade deals, generic pharma, textiles, IT visas | press |
| SEC Chair | 2 | global risk sentiment, ADR-listed Indian names | SEC, press |
| Prominent stock-trading Congress members (Pelosi et al.) | 3 | sector tilt via disclosed trades (see §5) | **STOCK Act filings** |

### 2d. US / global — business, tech & finance (theme → NSE sector)
| Figure | Wt | India read-through | Data |
|---|---|---|---|
| **Elon Musk** | 4 | EV/auto ancillaries, battery/metals, "X/AI" sentiment | X, GDELT |
| **Jensen Huang** (NVIDIA) | 4 | Indian IT, data-center/power, electronics | keynotes, GDELT |
| **Sam Altman** (OpenAI) | 3 | Indian IT (AI demand/disruption both ways) | X, press |
| Tim Cook (Apple) | 3 | Apple India suppliers (Dixon, electronics EMS) | press |
| Warren Buffett / Berkshire | 3 | value/insurance sentiment; 13F cloning (§5) | 13F, press |
| Jamie Dimon (JPMorgan) | 3 | global bank risk sentiment, credit | press |
| Larry Fink (BlackRock) | 3 | EM/India allocation flows (FII) | letters, press |
| Cathie Wood (ARK) | 2 | innovation/growth risk appetite; ARK holdings feed | ARK daily, press |
| Bill Ackman / Michael Burry | 2 | activist/short signals, macro risk tone | X, 13F |

### 2e. Global macro & commodities (India is a big importer → direct)
| Figure / body | Wt | India read-through | Data |
|---|---|---|---|
| **OPEC / Saudi energy minister** | 4 | crude→OMCs, paints (ASIANPAINT), aviation, tyres | OPEC, GDELT |
| ECB (Lagarde) / BoJ / PBoC | 3 | global liquidity → FII flows, metals (China) | press |
| Xi Jinping / China stimulus | 3 | metals (TATASTEEL/HINDALCO), chemicals | GDELT |
| IMF / World Bank / rating agencies | 3 | India rating/GDP → broad, banks, bond yields | reports |
| Putin / Zelensky / geopolitics | 2 | crude, defence, gold/silver, wheat/fertilizer | GDELT |

**Weights are a starting prior, not gospel** — Phase 4 should *learn* each figure's
realized hit-rate on NSE and down-weight the noisy ones (per-figure attribution
feeds straight back into the weight).

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

## 6b. Adjacent niche / high-yield strategy ideas (research shortlist)

Scouted from the quant/hedge-fund public domain. These are the "not just another
portfolio manager" ideas — most are **event/alt-data driven**, which is exactly
the muscle the Bellwether plumbing (dated events → sentiment/mapping → event
backtest) is building. Each is tagged **[NSE-ready]** (runs on data we can get for
India today), **[paid-data]** (needs an alt-data vendor), or **[US-only]**.
Rated by how well it fits *this* project.

### The "insider echo" family (highest thematic fit)
1. **Congressional / political disclosed trades** — trade in the direction of
   lawmakers' STOCK Act filings (the "Pelosi tracker" effect). Retail-tracked via
   **Quiver Quantitative** and **VertData** (43k+ congressional trades, Form-4
   insider buys, 25 superinvestor 13Fs, ARK holdings, short interest). **[US-only]**
   directly, but a natural extension of Bellwether's disclosed-trades track (§5),
   and a US read-through basket can tilt Indian sectors. **Fit: very high.**
2. **Corporate insider Form-4 clustering** — go long when *multiple* insiders buy
   the same name in a short window (cluster buys beat lone buys). India: NSE/BSE
   **insider-trading (SAST/PIT) disclosures** are public → **[NSE-ready]** with a
   scraper. **Fit: high.**
3. **13F superinvestor cloning** — replicate the quarterly holdings of proven
   managers (Buffett, etc.); mind the ~45-day filing lag. **[US-only]** (India MF
   monthly portfolio disclosures are the local analogue → **[NSE-ready]**).
4. **Promoter pledge / stake-change signal (India)** — rising promoter share
   pledges are a well-known red flag; promoter *buying* is a positive. Public in
   NSE/BSE filings. **[NSE-ready]. Fit: high, India-native.**

### Alternative-data signals
5. **Unexpected Government Receivables (UGR)** — long stocks whose government
   receivables jump; documented **5.4–7.1%/yr alpha**. Needs receivables data from
   filings. **[paid-data / hard]** but high-alpha. India analogue: govt-capex order
   wins (defence/rail/roads) — scrapeable from exchange announcements. **[NSE-ready]** in the India form.
6. **Government contract / order-win announcements** — buy on large order-book
   additions (defence: HAL/BEL; infra: LT; rail: titagarh/BEML). India exchange
   "corporate announcements" feed. **[NSE-ready]. Fit: high** — pairs perfectly
   with the Gadkari/Modi/defence figures above.
7. **Lobbying spend** (Quiver) — firms that lobby more tend to outperform. **[US-only]**.

### Market-microstructure / derivatives edges
8. **Options dealer gamma exposure (GEX)** — when dealers are **short gamma** they
   hedge pro-cyclically and *amplify* moves (trend/breakout regime); **long gamma**
   dampens moves (mean-revert/fade regime). Used to pick which regime to run. NSE
   has deep index/stock options → computable from the option chain. **[NSE-ready]**
   (index first: NIFTY/BANKNIFTY). **Fit: high, and genuinely "quant-desk".**
9. **F&O open-interest build-up** — long/short buildup vs long/short unwinding from
   price+OI changes; classic NSE derivatives read. **[NSE-ready].**
10. **Overnight vs intraday return decomposition** — a large body of research shows
    most of the equity premium accrues **overnight**; buy-at-close/sell-at-open
    variants. Trivially **[NSE-ready]** from OHLC we already store. **Fit: high,
    cheap to test.**

### Flow & positioning
11. **FII/DII daily cash-flow signal (India)** — NSE/BSE publish daily net
    FII/DII buy/sell; the structural **SIP/DII bid** is a real regime input.
    **[NSE-ready], India-native. Fit: high.**
12. **Short-interest / squeeze** — high short interest + a positive catalyst.
    India short data is thin; **[US-only]** in the clean form.

### Behavioural / anomaly (classic but underused here)
13. **Reversal-in-PEAD** — the drift eventually over-shoots and reverses; a
    second-leg trade after our existing `pead_drift`. **[NSE-ready].**
14. **Lottery-stock avoidance / bet-against-beta** — we already have `low_vol_bab`;
    the "avoid high-MAX lottery stocks" screen is a cheap overlay. **[NSE-ready].**

**How these connect to Bellwether:** #1–#7 are all *dated-event → map-to-symbol →
hold* strategies — **the same event-backtest engine (§4) runs all of them.** Build
the engine once for the political-statement track, and these become mostly a new
event source + mapping. #8–#11 are separate (microstructure/flow) sleeves that
plug into the existing `run_gate`. Recommended near-term picks for *this* project:
**gamma-exposure regime (#8), government order-wins (#6), promoter-pledge (#4),
and FII/DII flow (#11)** — all NSE-ready, all genuinely "quant" rather than
portfolio-manager, and all reusing plumbing we already have.

> Sources: [Quiver Quantitative — Strategies](https://www.quiverquant.com/strategies/),
> [QuantConnect × Quiver: Insider Trading dataset](https://www.quantconnect.com/docs/v2/writing-algorithms/datasets/quiver-quantitative/insider-trading),
> [AInvest — Congressional trading patterns 2025](https://www.ainvest.com/news/political-insider-trading-dynamics-leveraging-congressional-patterns-strategic-investing-2025-2512/),
> [QuantPedia — Six alt-data strategies (incl. UGR)](https://quantpedia.com/six-examples-of-trading-strategies-that-use-alternative-data/),
> [QuantPedia — Post-Earnings Announcement Drift](https://quantpedia.com/strategies/post-earnings-announcement-effect),
> [QuantPedia — Reversal in PEAD](https://quantpedia.com/strategies/reversal-in-post-earnings-announcement-drift),
> [MenthorQ — Gamma in the real world](https://menthorq.com/guide/gamma-in-the-real-world/),
> [NSE — FII/DII activity reports](https://www.nseindia.com/reports/fii-dii),
> [awesome-quant (libraries/data)](https://github.com/wilsonfreitas/awesome-quant).

---

## Phase 0 — status (2026-07-13): tool built, awaiting a local run

`scripts/gdelt_spike.py` is the Phase-0 probe. It queries the **free GDELT 2.0
DOC API** (no key) for a roster of figures (Modi, Gadkari, RBI, Trump, Musk) and
reports, per figure: how many **dated tone-points** GDELT returns over 3 years,
day-coverage %, mean tone, and a sample of real dated headlines — then a plain
**RICH / THIN / UNAVAILABLE** verdict. Output saved to
`var/bellwether/gdelt_spike/`.

It could **not** be validated from the build sandbox (no outbound internet — DNS
`getaddrinfo` failures; a shared-IP GDELT `429` on the web-tool fallback). **Run
it on your machine to get the real answer:**

```
python scripts/gdelt_spike.py                 # 5 figures, 3 years
python scripts/gdelt_spike.py --delay 10      # if you hit HTTP 429, slow down
```

If the Indian-direct figures (Modi/Gadkari/RBI) come back **RICH**, Phase 0
passes → proceed to P1. If everything is THIN even on an open network, pivot to
the live-forward version (collect from today, trade paper, skip the 3y backtest).

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
