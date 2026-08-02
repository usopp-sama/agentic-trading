# Agent-Based / LLM-Agent Trading — Literature Survey (2026-07-14)

*Where this project's whole paradigm — a firm of LLM "experts" (SMEs) that read
news/fundamentals, debate, and get synthesized by a CIO under risk guardrails,
across a fast/slow/governance three-loop — sits in the published and live-tested
literature. What others built, what they achieved, why most of the reported
success is an illusion, and what we should borrow or guard against.*

> Scope note: this is about the **agentic architecture** (the project as a whole).
> The separate `bellwether_literature_survey.md` covers the narrower
> "follow public figures' statements" sub-strategy.

---

## Executive summary — the 7 things worth knowing

1. **Your architecture is not novel — and that's *good*.** The 2024 **TradingAgents**
   paper describes almost exactly this project: specialised LLM analysts
   (fundamentals / news / sentiment / technical), **Bull vs Bear researcher
   debate**, a Trader that synthesises, and a **Risk Manager** — the same shape as
   your SMEs → CIO → risk-guardrails → three-loop. You independently built a
   state-of-the-art design.
2. **Multi-agent debate genuinely beats a single LLM** at these tasks (better
   integration of heterogeneous data, less lock-in to a wrong first answer) —
   validating the SME-committee + CIO idea over a single model.
3. **The reported returns are real *in backtests* and mostly *illusory*.** The
   dominant, field-defining problem is **LLM look-ahead / data contamination**:
   the model "remembers" post-event news from pre-training, inflating any
   backtest. Concretely, once you test *past* a model's training cutoff,
   **FinMem's total return fell ~72% and QuantAgent's Sharpe ~51%.** Half to
   two-thirds of the "alpha" was leakage.
4. **Almost no LLM-trading study is reproducible.** An audit found only a small
   minority document time-consistent train/test splits, explicit transaction
   costs, or survivorship handling — and **none reached the top reproducibility
   tier**. This is precisely the gap our **deflated-Sharpe + walk-forward + real-fee
   gate** closes. **On rigor, this project is *ahead* of most published work.**
5. **Live, LLM agents mostly underperform buy-and-hold** — and specifically
   **fail in downturns** (they're long-biased). Across 11 public AI-trading
   contests, only **2 had a profitable *median*** model. "Being great at financial
   Q&A does not translate to trading."
6. **The other "agent" tradition — deep RL (FinRL)** — shows big backtest Sharpes
   (2.1–2.4) but is notoriously fragile: seed-sensitive, overfits, and exploits
   simulator unrealism. Its hard-won lessons (realistic costs, retraining,
   *fallback to simple baselines*) apply to us too.
7. **The honest position:** this project is **architecturally SOTA and unusually
   rigorous** — but the agentic layer's edge is **currently unmeasurable by
   backtest** (contamination). The deterministic strategies and the point-in-time
   Bellwether track are the honestly-measurable core; **the LLM committee should
   be judged on *forward paper* performance, not backtests.**

---

## 1. The landscape — three traditions of "agents that trade"

**(a) Classic Agent-Based Models (ABM), 30+ years.** Agent-based computational
economics (Tesfatsion). **Zero-intelligence agents** (Gode & Sunder, 1993) submit
random bids/offers yet reproduce real market *stylised facts* — realistic spreads,
fat tails, long-range dependence (Farmer et al.). Point: these are **market
*simulators*** to understand dynamics, **not profit-seeking traders**. Useful
context — "agent-based" historically meant simulation, not a trading firm — but a
different goal from ours.

**(b) LLM multi-agent trading systems (2023–2026) — *this project's family*.**
The modern wave; covered in §2–§3.

**(c) Deep-RL trading (FinRL).** A single policy-agent learns to trade via reward.
Strong backtests, severe fragility; covered in §5.

> [Agent-Based Computational Economics (Tesfatsion)](https://faculty.sites.iastate.edu/tesfatsi/archive/tesfatsi/afinance.htm) ·
> [Parameterised-Response Zero-Intelligence Traders](https://arxiv.org/pdf/2103.11341)

## 2. The direct mirror — TradingAgents ≈ this project

**TradingAgents** (Xiao et al., arXiv 2412.20138, Dec 2024) builds a virtual
trading *firm* of LLM agents:

| TradingAgents role | This project's equivalent |
|---|---|
| Fundamentals / News / Sentiment / Technical **analysts** | the **SME experts** (per-domain) |
| **Bull vs Bear researcher debate** | the **debate rounds** (`debate_rounds`) |
| **Trader** synthesising the debate | the **CIO** synthesis |
| **Risk Manager** monitoring exposure | the **risk guardrails / kill switch** |
| multi-asset, multi-modal inputs | news + fundamentals + technicals + flows |

Its thesis — *"separating responsibilities reduces single-model bias and improves
robustness"* — is the exact rationale for the SME/CIO split. It reports gains in
cumulative return, Sharpe, and max-drawdown over baselines (on a **Jan–Mar 2024**
window — note the short, recent, single-regime period; see §4).

**Takeaway:** the project's shape is validated by the leading paper in the space.
The design instinct was right.

> [TradingAgents (arXiv 2412.20138)](https://arxiv.org/abs/2412.20138) ·
> [project site](https://tradingagents-ai.github.io/)

## 3. Adjacent building blocks — memory, character, contest

- **FinMem** (arXiv 2311.13743, ICLR 2024): a single LLM agent with **Profiling**
  (character/risk persona), **layered Memory** (short/mid/long, human-cognition-like,
  adjustable "cognitive span"), and **Decision-making**; self-evolves knowledge and
  mitigates hallucination. → mirrors our **SME personas + RAG knowledge base**;
  suggests adding **layered memory + reflection**.
- **FinAgent**: layered memorisation + multimodal + technical tools; strong
  backtests, less hallucination.
- **ContestTrade / internal-contest** designs: agents compete; the best signal
  wins — a selection mechanism beyond debate.
- **Multi-agent debate (general):** multiple LLM instances propose→debate→revise
  over rounds, improving factual accuracy and reasoning and **reducing lock-in to
  a wrong first answer**; single LLMs struggle to weight heterogeneous modalities,
  which specialists + fusion handle better. → **direct evidence the committee > one
  model.**

> [FinMem (arXiv 2311.13743)](https://arxiv.org/abs/2311.13743) ·
> [FinMem code](https://github.com/pipiku915/finmem-llm-stocktrading)

## 4. What they achieved — and why to discount it

**Reported (backtest) results are strong:** TradingAgents beats baselines on
return/Sharpe/drawdown; FinMem/FinAgent "boost cumulative returns"; FinRL-Podracer
reports **cumulative 149–362%, annual 56–112%, Sharpe 2.1–2.4**.

**Discount them heavily, for three reasons the literature itself documents:**

1. **Short, recent, single-regime test windows** (e.g. TradingAgents' Jan–Mar
   2024) — a hedge-fund-perspective review insists on **≥ one full bull+bear cycle**.
2. **Data contamination / look-ahead (the big one) — see §5.**
3. **Backtest overfitting** — tuning until the backtest looks good (endemic in RL
   and LLM-agent papers alike).

> [LLMs for Stock Forecasting — Hedge-Fund review (arXiv 2605.05211)](https://arxiv.org/abs/2605.05211)

## 5. The critical literature — *the most important section*

This is where our project's ethos (honest evaluation) meets the field's biggest
open problem.

- **LLM look-ahead is a new kind of leakage with no classical analogue.** Even
  when the *code* passes only contemporaneous inputs, the **model weights /
  post-training data / retrieval corpus** can contain post-event news, summaries,
  and reviews — the model leaks the future through *semantic memory*.
- **Measured impact is enormous:** comparing agents **inside vs outside their
  pre-training cutoff**, **FinMem's total return dropped ~71.85%** and
  **QuantAgent's Sharpe ~51.48%** once the window crossed the cutoff. Most of the
  "edge" was contamination.
- **"The Alpha Illusion":** reported alpha from LLM trading agents **should not be
  treated as deployment evidence.**
- **Reproducibility audit:** only a small minority of studies document
  time-consistent splits / explicit costs / survivorship; **none reach the top
  tier.** Execution assumptions (signal-close vs next tradable price, future
  universe constituents, omitted costs) routinely overturn the apparent edge.
- **Temporal contamination:** news timestamps record **publication**, not
  **availability**, time; without embargo enforcement, backtests inflate.
- **A fix exists:** *look-ahead-freedom as temporal non-interference* — a
  **verifiable correctness property** for backtesting/agentic pipelines.

**Live/real-world results are sobering:** on live multi-market benchmarks
(StockBench, AI-Trader, "When Agents Trade"), most LLM agents show **poor returns
and weak risk management**, and **all underperform a passive baseline in
downturns** (long-bias). Across 11 public AI-trading contests, **only 2 had a
profitable median** model. Crowded AI trades have already caused correlated hedge-
fund losses.

> [The Alpha Illusion (arXiv 2605.16895)](https://arxiv.org/html/2605.16895) ·
> [Look-Ahead-Freedom / Temporal Non-Interference (arXiv 2607.04958)](https://arxiv.org/html/2607.04958v1) ·
> [Reliable Evaluation of LLM Financial Multi-Agent Systems (arXiv 2603.27539)](https://arxiv.org/pdf/2603.27539) ·
> [StockBench](https://stockbench.github.io/) ·
> [Wall Street's AI traders underperform (ZeroHedge)](https://www.zerohedge.com/markets/wall-street-keeps-testing-ai-traders-most-are-still-underperforming)

## 6. Deep-RL's transferable lessons (FinRL)

Even though we're not RL, the RL-trading community learned these the hard way and
they apply to *any* agentic trader:

- **Low signal-to-noise + survivorship bias + backtest overfitting** dominate.
- **Simulator-reality gap:** agents exploit whatever unrealism you allow (mid-price
  fills, infinite liquidity). → our **realistic Indian fees + slippage** matter.
- **Non-stationarity:** markets change; **retrain, monitor drift, and keep a
  fallback to a simple-rules baseline.**
- **Seed/hyperparameter fragility:** Sharpe swings across seeds → **run multiple
  seeds; distrust a single lucky run** (our DSR/plateau checks are the analogue).

> [FinRL-Meta (NeurIPS 2022)](https://proceedings.neurips.cc/paper_files/paper/2022/file/0bf54b80686d2c4dc0808c2e98d430f7-Paper-Datasets_and_Benchmarks.pdf)

## 7. How *this project* compares

**Where we're aligned with SOTA or ahead:**
- **Architecture = TradingAgents-class** (analyst SMEs + Bull/Bear-style debate +
  CIO + risk). Validated design. ✅
- **Evaluation rigor beyond most published work:** deflated-Sharpe (multiple-testing
  aware), **walk-forward `[decay]`**, plateau/curve-fit check, **realistic Indian
  fees**, mechanical corpus. The audit literature says *none* of the LLM-trading
  papers reach this tier — **we already do, for the deterministic strategies.** ✅
- **Paper-only, cost-governed** (LLM budget) — matches "don't treat reported alpha
  as deployment evidence" + the "cost-awareness" eval taxonomy. ✅
- **Regime-aware ballast** (`core_allocation`) partly addresses the bear-market
  failure mode. ✅

**Where we're exposed (the real risks, straight from the literature):**
1. **LLM contamination applies squarely to our SME/CIO layer.** When Gemini reasons
   about a stock on a past date, it may "know" what happened next → **any backtest
   of the agentic decisions is inflated and, honestly, not trustworthy.** This is
   *the* reason the deterministic + point-in-time-event tracks carry the measurable
   weight.
2. **The agentic layer's edge is currently *unmeasured*.** Our DSR gate scores
   *strategies*; it does **not** score the LLM committee (non-reproducible +
   contaminated). We don't actually know if the SMEs add alpha.
3. **Long-bias / downturn fragility** — untested for our committee.
4. **Crowding/decay** as LLM trading adoption rises.

## 8. What to include / modify (concrete, mapped to the system)

**On evaluation (highest priority — this is our differentiator):**
- **E-A: Enforce point-in-time / embargo on every agent input.** Stamp each SME
  input with an *as-of* date; never feed data past the decision date; adopt the
  **"temporal non-interference"** property (arXiv 2607.04958) as a testable
  invariant for any agentic backtest. Log the as-of date on every LLM call.
- **E-B: Judge the agentic layer on *forward paper* performance, not backtests.**
  The learning/attribution loop already scores SME calls forward — lean on it;
  treat backtests of LLM decisions as *directional only*, never as evidence.
- **E-C: Ablation — does the committee beat one agent, and does debate beat no
  debate?** The eval taxonomy stresses **coordination-primacy + cost-awareness**:
  measure whether the multi-agent structure earns its token cost vs a single SME
  and vs `core_allocation`/buy-and-hold baselines.

**On robustness:**
- **E-D: Full-cycle evaluation** over ≥1 bull+bear regime (extend/verify the 3y
  window spans a real drawdown).
- **E-E: Explicit simple-rules fallback** when the agents disagree or a regime flips
  (RL's hardest-won lesson) — `core_allocation` is a good default.
- **E-F: Bear-market stress** — check the committee doesn't collapse to long-only
  beta in a downturn.

**On architecture (optional upgrades from the papers):**
- **E-G: FinMem-style layered memory + reflection** on top of the existing personas
  + RAG (short/mid/long memory with self-critique).
- **E-H: Explicit Bull/Bear adversarial researchers** before the CIO (TradingAgents/
  ContestTrade) — sharpen the debate into a contest, then select.

**On strategy:**
- **E-I: Lean into the *less-crowded* niche.** Global LLM-trading is crowding US
  large-caps; our **NSE + India-specific-signal** focus is a genuine
  differentiator (less arbitraged, less crowded) — a defensible edge the survey
  literature implies but rarely occupies.

## 9. The honest headline

You built a **TradingAgents-class multi-agent system** — the right, state-of-the-art
shape — and wrapped it in **evaluation rigor that exceeds most of the published
field.** That is a real achievement. But the field's defining unsolved problem —
**LLM look-ahead / data contamination** — lands squarely on the agentic layer, which
means **its edge cannot currently be trusted from any backtest** (FinMem lost ~72%
of its return once the leak was closed; assume ours would too). So the *measurable*
value lives in the **deterministic strategies** and the **point-in-time Bellwether**
track, judged by the DSR gate; the **LLM committee is the ambitious layer, and the
only honest verdict on it is *forward paper performance*** — which the attribution
loop is already positioned to give. The winning move is not to believe a pretty
backtest of the agents, but to **run them forward, cheaply, in a less-crowded market,
and let the honest gate decide.**

---

### Sources (consolidated)
Multi-agent LLM: [TradingAgents](https://arxiv.org/abs/2412.20138),
[FinMem](https://arxiv.org/abs/2311.13743),
[LLM Financial Multi-Agent evaluation taxonomy](https://arxiv.org/pdf/2603.27539) ·
Critical / leakage: [The Alpha Illusion](https://arxiv.org/html/2605.16895),
[Temporal Non-Interference](https://arxiv.org/html/2607.04958v1),
[LLM stock-forecasting hedge-fund review](https://arxiv.org/abs/2605.05211) ·
Live results: [StockBench](https://stockbench.github.io/),
[AI traders underperform (ZeroHedge)](https://www.zerohedge.com/markets/wall-street-keeps-testing-ai-traders-most-are-still-underperforming) ·
RL: [FinRL-Meta (NeurIPS)](https://proceedings.neurips.cc/paper_files/paper/2022/file/0bf54b80686d2c4dc0808c2e98d430f7-Paper-Datasets_and_Benchmarks.pdf) ·
ABM: [Agent-Based Computational Economics](https://faculty.sites.iastate.edu/tesfatsi/archive/tesfatsi/afinance.htm).
