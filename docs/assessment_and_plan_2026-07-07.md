# Honest Assessment & Plan — 2026-07-07

An independent review of the repo (code, docs, handoff of 2026-06-30) against the stated
goal: **₹10,000/month profit on ₹1,00,000 capital, after operational costs.**

---

## 1. Verdict in three sentences

The engineering is genuinely good — this is a well-architected paper-trading research
platform (~23k lines, 31 test modules, layered safety, real fee model, honest
anti-overfitting tooling). But it is a **laboratory, not a business**: it has never
proven it can make money, it cannot yet place a real order (the Kite adapter is a
deliberate stub), and there is no completed track record in this repo. The biggest
problem is not the code — it is the goal: **₹10k/month on ₹1L is 10% per month
(~214% a year compounded), which is beyond what the best hedge funds in history
sustain.** The plan below is about closing both gaps honestly.

---

## 2. The financial reality (read this first)

You said you're a novice, so here is the math nobody selling trading courses shows you.
*(I'm not a financial advisor; this is factual context for your own decision.)*

**What 10%/month means.** Compounded, ₹1L → ₹3.14L in one year. The best sustained
records ever: Renaissance Medallion ~66%/yr (closed fund, PhD army), Buffett ~20%/yr
over a career, good hedge funds 15–25%/yr. A solid *retail* systematic long-only swing
system on NSE large caps — which is exactly what you built — realistically targets
**10–20% per year**, with 15–25% drawdowns along the way.

**What that yields on ₹1L:**

| Scenario | Annual return | Monthly avg (pre-tax) |
|---|---|---|
| Realistic good outcome | 15%/yr | ~₹1,250 |
| Excellent outcome | 25%/yr | ~₹2,100 |
| Your target | 214%/yr | ₹10,000 |

**Costs eat small accounts.** Kite Connect full data API is ₹500/month (order APIs are
free since March 2025) — that alone is 6%/yr of your capital. Add Gemini API spend
(your own docs record a ₹40 incident from news fan-out), an always-on host, and
brokerage/STT/GST per trade (your `fees.py` models this correctly). At ₹1L scale,
**opex can consume the entire realistic profit.** Then tax: STCG on equity is 20%,
and frequent trading may be assessed as business income.

**The only paths to 10%/month are leverage and options selling** — and SEBI's own
studies show ~91–93% of retail F&O traders lose money, averaging ~₹2L in losses.
Your system is long-only cash equity by design. That design is *correct*; the target
is what's wrong.

**The honest reframe.** ₹10k/month pre-tax at a good-but-realistic 12–15%/yr needs
**₹8–10 lakh of capital**, not ₹1L. So the genuine plan is: prove the system works at
₹1L scale (real money, small), and treat capital growth — from salary, or from the
career value of this project — as the route to the income target. Section 6 covers
what this project can earn you *besides* trading profit, which is likely more.

---

## 3. What you actually have (state of the codebase)

**Working (verified by reading code/tests; run `pytest` locally to confirm green):**
two independent autonomous paper-trading paths (24-strategy quant library + 26-persona
Gemini SME pipeline) converging on one risk gate and one paper book; immutable
guardrails (10% position cap, 35% sector, 3% daily-loss kill switch, rate limits);
realistic Indian fee model; walk-forward backtest gate with deflated Sharpe; sleeve
attribution and SME learning loop; 11-page dashboard; email digests; watchdog;
restart-safe risk state; LLM cost governance. The `.env`, `var/` and run logs are not
in this copy — the June-30 dress rehearsal state lives on the other machine.

**Not working / missing for real deployment:**

1. **No real execution.** `kite_adapter.py` raises `NotImplementedError` by design.
2. **No completed track record.** The month-long paper run was set up on June 30 but
   there are no results here. Nothing is proven.
3. **Data quality.** yfinance is delayed ~15 min and rate-limity; fine for paper swing
   trading, not for anything faster. Going live means Kite Connect data (₹500/mo).
4. **SEBI compliance is now mandatory, not optional.** Since **April 1, 2026**, every
   algo order by a retail trader must carry an exchange-assigned **Algo-ID**,
   registered through your broker, with a **static whitelisted IP**, OAuth + 2FA, and
   daily session logout. Self-built algos must be registered via Zerodha with the
   exchange before they can legally trade. This is a real workstream (see §5 Phase 2).
5. **Housekeeping.** 275 files show CRLF line-ending churn on Windows (set
   `git config core.autocrlf` and add `.gitattributes`); `pyproject` wants
   Python ≥3.11; `library.rar` (122 MB) sits untracked in the tree.

---

## 4. The core risk nobody's code can fix

A clean architecture does not create *edge*. Your strategies are textbook families
(Donchian, RSI-2, momentum, pairs, factor composites) — published for decades, traded
by everyone, and mostly arbitraged thin. The SME/LLM layer is genuinely novel as
engineering, but there is **no evidence anywhere that LLM personas debating news
produce alpha** — and every Gemini call costs money, so the SME path must *outperform
the quant path by more than its own cost* to justify existing. Treat it as an
experiment to be measured, not an asset to be assumed.

The month-long paper run is therefore not a formality — it is **the entire question**.
Everything in Phase 1 below is designed to make its answer trustworthy.

---

## 5. The plan

### Phase 0 — Stabilize and start the clock (this week)

Fix line endings and commit the working tree. Run `pytest` — the suite must be green.
Deploy to an always-on host (the Pi/systemd or Docker path in `deployment_lan.md`;
a laptop that sleeps invalidates the run). Reset the paper book to ₹1L, enable email
digests (the go-live doc says only credentials are missing). **Write down kill
criteria before starting**, e.g.: "If after 3 months the system underperforms
NIFTYBEES buy-and-hold after costs, or max drawdown exceeds 15%, I stop and rethink."
Pre-committing to this is what separates evaluation from self-deception.

### Phase 1 — The honest 3-month paper evaluation (Jul–Oct 2026)

Let it run. Weekly 30-minute review ritual (already documented in
`month_paper_run.md`): check feed health, per-sleeve Sharpe, and the three numbers
that matter — **total return vs NIFTYBEES, max drawdown, and profit factor after
fees**. Keep LLM spend capped (the gating knobs exist; set a hard monthly budget,
₹500–1,000). Track the quant path and SME path *separately* — the handoff already
suggests a per-path toggle; build it, because at the end you must answer: does the
SME layer pay for itself?

**Pass bar:** beats NIFTYBEES after simulated costs over the full period, max DD
< 15%, and behavior you can explain trade-by-trade from the Activity page.
**Most systems fail this bar. If yours does, that is a success of the process** —
you avoided losing real money, and you iterate on strategy selection (the shadow →
paper promotion gate exists for exactly this).

### Phase 2 — Tiny real money, maximum friction (only if Phase 1 passes)

Capital: **₹10–25k, not ₹1L.** Mode: `APPROVAL` (you tap to confirm every order) for
at least a month before even considering `AUTO`. Work items: implement the Kite
adapter properly (order placement, fill reconciliation, partial fills, rejections);
get Kite Connect (data ₹500/mo); complete **SEBI algo registration through Zerodha**
(Algo-ID per strategy, static IP on your always-on host, 2FA/OAuth session rules);
then run 2–3 months measuring **live slippage vs paper assumptions** — the 5 bps
paper slippage is a guess until proven. Expect live results to be worse than paper.

### Phase 3 — Scale with evidence, not hope

Only after ~6 months of combined paper+live evidence: move to the full ₹1L, consider
`AUTO` with the approval fallback, and revisit the income math with real numbers. If
the system genuinely does 15%/yr, the path to ₹10k/month is **adding capital over
time**, not squeezing more risk out of ₹1L.

### Budget through Phase 2 (~6 months)

| Item | ₹/month | Notes |
|---|---|---|
| Always-on host | 0–400 | Pi you own, or a small VPS |
| Gemini API (capped) | 300–1,000 | gating knobs already built |
| Kite Connect data | 0 → 500 | only from Phase 2 |
| **Total opex** | **~₹500–1,900** | keep it under ₹1k in Phase 1 |

---

## 6. What this project is worth beyond trading profit

Being direct: the most probable financial return from this codebase is **career
capital, not trading P&L.** Your own `roadmap.md` already knows this — WorldQuant
Brain (alpha royalties, window open now through Sep 2026), IMC Prosperity, Jane
Street ETC, GSoC/LFX/Outreachy (stipends $1.5k–$7k). A documented, honest,
month-long systematic trading evaluation — *even one that concludes "no edge"* — is
a portfolio piece that quant firms and fintechs respect far more than a lucky
backtest. Do not skip these tracks while the paper run cooks in the background;
they are the highest-expected-value use of the same skills.

Selling the tool itself (SaaS/signals) is **not** a shortcut: under the 2026 SEBI
framework, algo providers must empanel with exchanges via brokers, and selling advice
triggers Investment Adviser regulation. Personal/family use is the legally clean lane.

---

## 7. This week's checklist

1. `git config core.autocrlf input`, add `.gitattributes`, commit the tree.
2. `pytest` green locally; fix anything red.
3. Stand up the always-on host; start the ₹1L paper run with email digests on.
4. Write and commit your kill criteria (`docs/kill_criteria.md`).
5. Set a Gemini spend cap + Google Cloud billing alert.
6. Register for WorldQuant Brain (deadline-bound, free, parallel track).

---

*Sources: [SEBI circular — Safer participation of retail investors in algorithmic
trading (Feb 2025)](https://www.sebi.gov.in/legal/circulars/feb-2025/safer-participation-of-retail-investors-in-algorithmic-trading_91614.html) ·
[SEBI phased rollout to April 2026](https://www.business-standard.com/markets/news/sebi-extends-timeline-to-roll-out-algo-trading-rules-for-retail-investors-125100100278_1.html) ·
[Kite Connect pricing — ₹500/mo data, free order APIs](https://kite.trade/forum/discussion/15015/revising-kite-connect-fees-from-2000-to-500-per-month) ·
[Zerodha free personal APIs](https://zerodha.com/z-connect/updates/free-personal-apis-from-kite-connect)*
