# Bellwether — Literature Survey (2026-07-14)

*A review of the prior art behind the "trade what market-movers say/do" idea:
what others attempted, what they achieved, what made them better, and what we
should borrow or change. Companion to `market_mover_news_strategy.plan.md`.*

---

## Executive summary — the 8 things worth knowing

1. **The effect is real but small, short-lived, and concentrated.** Trump's
   company-specific tweets move the named stock ~**±0.25%** same-day and spike
   volume/volatility ~**+19%** — but JPMorgan's *Volfefe* index found only
   **146 of ~4,000** market-hours tweets actually moved rates. **Filtering to the
   ~4% that matter is the entire game**, not scoring everything.
2. **The famous "Twitter predicts the market" result did not replicate.** Bollen
   (2011) claimed 86.7% directional accuracy; re-tests with the discarded data
   found *nothing* — textbook data-snooping / multiple-comparison bias. This is
   the cautionary tale that **validates our DSR / walk-forward / mechanical-corpus
   discipline** — most retail attempts skip it and fool themselves.
3. **GDELT tone is a validated signal** — but tone alone is leaving money on the
   table. Studies use **tone + attention (volume) + tone-dispersion (disagreement)**;
   all four predict returns and volatility. We currently store only tone+volume.
4. **The practitioner gold standard (RavenPack) reaches Information Ratios of
   ~2.6 (1-week) to 4.8 (1-day)** — but the edge is biggest in **less-liquid
   (mid/small-cap)** names and gets much stronger when **combined with a second
   signal** (e.g. insider trades: IR 1.8–2.6, 8–14%/yr).
5. **Holding period must match the figure.** Trump ≈ intraday/1-day; **RBI
   communication moves the Sensex over 10–30 days** (a slow drift). One fixed
   hold is wrong.
6. **Direction can be counter-intuitive and reflexive.** Markets often *lead*
   central-bank sentiment (they price it first); one study finds a *dovish* RBI
   shift → Sensex *down* ~150 bps over 30 days. **Learn each figure's realized
   sign; never hard-code it.**
7. **Scheduled events are priced in — trade the *surprise*.** India's 2024
   election counting day saw +2.03% abnormal return, but around elections/budgets
   the average abnormal return is often *not* significant (semi-strong efficiency).
   The edge is deviation-from-expectation, not the event.
8. **LLMs now beat FinBERT at this** (GPT-4: ~90% initial-reaction hit-rate,
   predicts drift) — but returns decay as adoption rises, and **look-ahead bias
   is a real trap** with LLMs. We have an SME/LLM layer; use it as an option,
   carefully.

**Bottom line: we are not first, the edge is thin and decaying, but it is real —
and our anti-overfit rigor already puts us ahead of the naive attempts. The wins
are in *filtering, multi-dimensional signals, per-figure holding/sign, less-liquid
names, and combining sources* — all of which we can add.**

---

## 1. Individual figures → specific stocks (the Trump-tweet literature)

The most-studied version of exactly our idea.

- **Magnitude:** company-specific Trump tweets produce **~±0.25% same-day abnormal
  return** in the tweet's direction, and **+19% abnormal volume & volatility**
  regardless of sentiment (Univ. of Richmond; PLOS One "Under his thumb").
- **Asymmetry & timing:** *positive* tweets hit immediately and are (unusually)
  *stronger* than negative; negative tweets act with a **delay**. Impact is far
  larger **during market hours**.
- **The skeptical camp:** several studies find tweets raise *activity* but leave
  **no lasting price effect** — the tweet often *comments on* prior events rather
  than adding information; aggregated across topics, **no significant index effect**.
- **Volfefe (JPMorgan, 2019, revived 2024):** ML model showing Trump tweets
  explain a "measurable fraction" of **rate/swaption volatility** (2–5y > 10y).
  Crucially: **only 146 of ~4,000** market-hours tweets moved the market;
  movers cluster on **trade / tariffs / "China" / "billion" / "dollars"**.

**What this tells us:** the signal exists but is (a) tiny per event, (b) mostly
**intraday**, (c) **topic-concentrated** (trade/tariffs), and (d) mostly for the
*named* company. A daily backtest that trades *every* statement will drown the
signal in noise — a **materiality filter** is essential.

> [Under his thumb (PLOS One)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0229931) ·
> [Richmond honors thesis](https://scholarship.richmond.edu/honors-theses/1484/) ·
> [Heroes just for one day (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S2214635021001386) ·
> [Volfefe index (CNBC)](https://www.cnbc.com/2019/09/08/donald-trump-is-tweeting-more-and-its-impacting-the-bond-market.html) ·
> [Volfefe (Wikipedia)](https://en.wikipedia.org/wiki/Volfefe_index)

## 2. The cautionary tale (Bollen 2011 and its failed replication)

- **Claim:** "Twitter Mood Predicts the Stock Market" — a Twitter "calm" index
  Granger-caused the DJIA with **86.7% directional accuracy** (2,500+ citations).
- **Reality:** re-analysis including the **discarded 2007/early-2008 data** found
  **no statistically significant relationship** — consistent with **data snooping**
  and **multiple-comparison bias** from high-dimensional text.

**What this tells us:** this is *the* reason our project's discipline exists.
Every figure × sector × horizon is a "trial"; the deflated-Sharpe gate, the
walk-forward `[decay]` flag, and the mechanical-corpus rule are precisely the
defenses these authors lacked. **We keep them; they are our edge over the crowd.**

> [Econ Journal Watch — "Shy of the Character Limit"](https://econjwatch.org/articles/shy-of-the-character-limit-twitter-mood-predicts-the-stock-market-revisited)

## 3. GDELT-tone strategies (our own data source)

- **China market:** GDELT **tone, optimism, attention, and tone-dispersion** all
  have significant predictive power for returns *and* volatility.
- **A DJ30 news backtest** reported **50.63% over 28 months**, beating buy&hold
  (one study, likely optimistic — treat as existence proof, not a target).
- GDELT variables **improve on a purely-macro model** for the US equity market.
- Tone scale is **-100..+100** (0 neutral).

**What this tells us:** GDELT is a legitimate, published signal source — and we're
under-using it. **Add attention and tone-dispersion** (both free from GDELT)
alongside tone. Dispersion (disagreement) is a known volatility/edge proxy.

> [News media sentiment, Chinese markets (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0927538X22001056) ·
> [GDELT & the S&P 500 (GDELT blog)](https://blog.gdeltproject.org/the-benefit-of-narratives-for-prediction-of-the-sp-500-index/) ·
> [News Sentiment & Market Dynamics (MDPI 2025)](https://www.mdpi.com/1911-8074/18/8/412)

## 4. News sentiment at industrial scale (RavenPack — the benchmark)

The commercial state of the art; what "done well" looks like.

- **Information Ratios up to 4.8 (1-day) and 2.6 (1-week).**
- **Insider trades + news sentiment combined: 8.6% / 13.9% annualized, IR
  1.82 / 2.64** (mid-large / small-cap) — combining beats either alone.
- **Alpha decay:** *slower* for **small-caps** (illiquid, slow to price news),
  faster for large-caps; **negative signals decay faster** than positive.
- **Match strategy to decay:** mean-reversion → fast decay, short horizons;
  trend → slow decay, longer horizons.

**What this tells us:** (a) the alpha is **biggest in mid/small-caps** — so run
Bellwether on the **midcap universe (our E3 flag)**, not just large-caps;
(b) **combine** the statement-sentiment sleeve with a second signal (insider/
flows) for a materially higher IR; (c) size the hold to the signal type.

> [RavenPack — News Sentiment Everywhere](https://www.ravenpack.com/research/news-sentiment-everywhere/) ·
> [RavenPack — Insider trading + news sentiment](https://www.ravenpack.com/research/insider-trading-news-sentiment-data/)

## 5. Central-bank communication (Fed/ECB, and RBI for us)

- **Fed/ECB sentiment predicts policy rates** quarters ahead — but **stock
  returns *lead* central-bank sentiment** (markets price it first). Trading CB
  tone for *equity direction* is therefore reflexive and hard.
- **RBI (directly relevant):** a one-unit **dovish** shift in MPC communication →
  **~150 bps Sensex *decline* over 30 days**, significant after ~10 days, building
  gradually. **Banks/financials most sensitive.**

**What this tells us:** the **RBI sleeve is the single most promising India-direct
signal** — a documented, multi-day, sector-specific effect (Nifty Bank). But note
two traps: the effect is **slow (10–30 days, not a 1-day pop)** and the **sign can
be counter-intuitive** (dovish→down in that study, likely a growth-fear read).
**Per-figure holding period + learned sign are mandatory.**

> [Words that Move Markets — RBI (arXiv 2411.04808)](https://arxiv.org/html/2411.04808v1) ·
> [Central Bank Sentiment: Fed & ECB (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4797935)

## 6. India political events (elections, budget)

- **2024 election counting day: +2.03% average abnormal return** on Nifty50.
- Method: **market-model event study, AAR/CAAR over ±15–21 day windows**.
- **Strong sectoral heterogeneity** (materials/consumer/tech most positive).
- But several studies find **abnormal returns *not* statistically significant**
  around the event → **priced in beforehand (semi-strong efficiency)**.

**What this tells us:** big *scheduled* events (elections, Union Budget, MPC) are
largely **anticipated** — the tradeable edge is the **surprise vs expectation**,
not the event's occurrence. And **event-study AAR/CAAR** is the rigorous way to
*attribute* P&L to a figure — we should adopt it in P4 alongside the DSR gate.

> [Pricing Political Risk — India 2024 election (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S3050700626000605) ·
> [Union Budget & Indian market (arXiv 2502.15787)](https://arxiv.org/pdf/2502.15787)

## 7. The insider-echo funds (a live, public benchmark)

- **NANC** (Democrats / "Pelosi") and **KRUZ** (Republicans) ETFs clone disclosed
  congressional trades since Feb 2023. **NANC ~+30% vs SPY ~+24%** since
  inception — periods of out-performance, **but neither consistently beats SPY**;
  the two diverge by sector tilt (NANC tech/growth, KRUZ value/energy).

**What this tells us:** the "trade what insiders *do*" idea is **real enough to be
a product**, but the edge is modest and **regime/sector-driven**, not a free
lunch — and it's **US-only** (fits our Alpaca track, §5b). A sober benchmark for
our disclosed-trades sleeve.

> [NANC vs KRUZ (ETF.com)](https://www.etf.com/sections/etf-basics/nanc-vs-kruz-battle-congress-stock-trackers)

## 8. The modern frontier — LLMs beat FinBERT

- **Lopez-Lira & Tang (2023), "Can ChatGPT Forecast Stock Price Movements?":**
  GPT-4 on news headlines gets **~90% portfolio-day hit rate** for the initial
  reaction, **predicts the subsequent drift** (esp. small stocks + negative news),
  and **outperforms traditional sentiment measures** (including FinBERT). Ability
  **grows with model size**.
- **Two caveats:** strategy returns **decline as LLM adoption rises** (efficiency),
  and **look-ahead bias** is a documented hazard — an LLM may "know" post-cutoff
  facts, inflating backtests.

**What this tells us:** our **SME/LLM layer is a genuine upgrade path** over
FinBERT for scoring statements — but only with **point-in-time discipline** (use
a model whose training cutoff precedes the test window, or score headline-only
with strict as-of dating) and honest evaluation.

> [Can ChatGPT Forecast Stock Price Movements? (arXiv 2304.07619)](https://arxiv.org/abs/2304.07619) ·
> [Detecting Look-ahead Bias in LLM Forecasts (arXiv)](https://arxiv.org/pdf/2512.23847)

---

## 9. How they outperformed us — the transferable techniques

| # | Technique the literature uses | Where it came from |
|---|---|---|
| T1 | **Materiality filter** — trade only the few high-impact statements | Volfefe (146/4000) |
| T2 | **Multi-dimensional sentiment** — tone **+ attention + dispersion** | GDELT China study |
| T3 | **Per-figure holding period** — Trump intraday, RBI 10–30d | Trump vs RBI studies |
| T4 | **Learned direction/sign** — don't assume positive→up | RBI dovish→down |
| T5 | **Tilt to less-liquid (mid/small-cap)** — slower decay = more alpha | RavenPack decay |
| T6 | **Combine signals** — statement sentiment + insider/flows | RavenPack IR 1.8–2.6 |
| T7 | **Surprise vs expectation** for scheduled events | India election/budget efficiency |
| T8 | **Event-study AAR/CAAR** for honest per-figure attribution | India event studies |
| T9 | **LLM scoring** (guarded) over lexical/FinBERT | Lopez-Lira & Tang |
| T10 | **Anti-overfit rigor** (we already do this) | Bollen replication failure |

## 10. What to include / modify in *our* project (mapped to phases)

**Already ahead:** our **DSR gate + walk-forward `[decay]` + mechanical corpus**
(T10) put us ahead of the naive Bollen-style attempts. Keep them.

**Add in P2 (mapping):**
- **T1 materiality gate** — only emit a signal when a statement clears an
  attention/|tone| threshold (skip the 96% that don't matter).
- Extend the entity map with the **surprise (T7)** idea for scheduled events:
  compare a figure's tone to its *own rolling baseline*, trade the deviation.

**Add in P3 (signal):**
- **T2** — pull GDELT **attention (volume)** and **tone-dispersion**, not just
  tone (both already free; collector change is small).
- **T3** — a **per-figure holding period** field in the registry (Trump 1d, RBI
  ~15d), later *learned* from realized decay.
- **T4** — learn each figure's **realized sign** from the corpus rather than
  assuming positive→buy.
- **T9** — an **LLM-scoring backend option** (our SME layer) benchmarked against
  FinBERT, with point-in-time / look-ahead guards.

**Add in P4 (event-backtest):**
- **T8** — report **AAR/CAAR event-study attribution** per figure alongside the
  DSR gate (this becomes the "did Modi actually pay?" answer).
- **T5** — run Bellwether on the **midcap universe** (`ATS_UNIVERSE_INCLUDE_MIDCAP`,
  already built) — the literature says the alpha lives there.
- **T6** — design the sleeve so it can **stack with a second signal** (the
  insider/flows or FII/DII sleeves from the niche-strategy shortlist).

**Re-prioritize the figures:** the evidence says the **RBI sleeve** (documented
multi-day Sensex/bank effect) and **Modi/Budget scheduled-surprise** sleeves are
the most likely to actually pay on NSE — front-load those over the noisier US
figures (which fit the Alpaca/US track for their *direct* names anyway, §5b).

## 11. The honest caveat

Every serious source agrees on two things: **(a)** the edge is **real but small
and decaying** (efficiency competes it away as adoption rises), and **(b)** it is
**trivially easy to fool yourself** (Bollen). So the realistic goal is **not** a
money-printing machine — it's a **small, honestly-measured, decaying edge** that
survives our gate. If a **materiality-filtered, RBI/Modi-focused, midcap,
surprise-based** sleeve clears the deflated-Sharpe + walk-forward bar with
realistic costs, that is a genuine, publishable-quality result. If it doesn't,
we'll have learned it cheaply — which is the whole point.

---

### Sources (consolidated)
Trump/Volfefe: [PLOS One](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0229931),
[ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2214635021001386),
[Volfefe/Wikipedia](https://en.wikipedia.org/wiki/Volfefe_index) ·
Bollen critique: [Econ Journal Watch](https://econjwatch.org/articles/shy-of-the-character-limit-twitter-mood-predicts-the-stock-market-revisited) ·
GDELT: [Chinese markets](https://www.sciencedirect.com/science/article/abs/pii/S0927538X22001056),
[GDELT blog](https://blog.gdeltproject.org/the-benefit-of-narratives-for-prediction-of-the-sp-500-index/) ·
RavenPack: [News Sentiment Everywhere](https://www.ravenpack.com/research/news-sentiment-everywhere/),
[Insider + sentiment](https://www.ravenpack.com/research/insider-trading-news-sentiment-data/) ·
Central banks: [RBI arXiv](https://arxiv.org/html/2411.04808v1),
[Fed/ECB SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4797935) ·
India events: [2024 election](https://www.sciencedirect.com/science/article/pii/S3050700626000605),
[Union Budget](https://arxiv.org/pdf/2502.15787) ·
Insider ETFs: [NANC vs KRUZ](https://www.etf.com/sections/etf-basics/nanc-vs-kruz-battle-congress-stock-trackers) ·
LLMs: [Lopez-Lira & Tang](https://arxiv.org/abs/2304.07619).
