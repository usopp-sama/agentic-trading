# Building the SME Knowledge Base (RAG curriculum)

> How the LLM actually "becomes" a subject-matter expert in this system, what we
> have today, what is missing, and the concrete reading/sourcing list to make
> each SME genuinely expert — fast.

---

## 1. How an SME becomes an expert here (the mechanism)

An SME is **not** a fine-tuned model. It is, at answer time, a composition of four
things assembled in `ats/services/agents/console.py` and `context.py`:

1. **Persona** — a short role + `system_prompt` from
   `ats/services/agents/personas/*.yaml` (e.g. "You understand ETF mandates,
   holdings, tracking error, NAV premium/discount…").
2. **Live grounding** — normalized signals, technicals, news, sentiment for a
   symbol (the `ContextAssembler`).
3. **Retrieved domain knowledge (RAG)** — the top-k most relevant chunks from the
   **knowledge base** (`knowledge_base.py`), scoped to the expert's family.
4. **Memory** — the running conversation thread + durable "directives" the expert
   has been told to remember.

These are stitched into the prompt as untrusted **DATA**, and the LLM (Gemini)
reasons over them. **The retrieved knowledge in step 3 is where expertise comes
from.** A thin knowledge base ⇒ a shallow expert, no matter how good the model is.

### The retrieval path (verified working)
- Corpus + your notes are chunked by markdown heading/paragraph (≤900 chars each),
  embedded into a vector store (today: dependency-free hashed bag-of-words +
  cosine; upgradeable to `chromadb` + `sentence-transformers`).
- Each chunk is tagged with a **family** (`A`/`B`/`C`/`RISK`) or `all` (shared).
- On a question, `KnowledgeBase.retrieve(query, family, k=4)` returns the top
  chunks for that expert's family **plus** the shared pool, and they are injected
  into the prompt with citations (`kb: <heading>`).

### Reliability tiers (how sources are ranked)
Defined in `knowledge_base.py` / `directives.py`:

| Source | Reliability | Where |
|---|---|---|
| Authored directives ("remember…") | 100 | runtime, per expert/symbol |
| Your notes/research/filings | 95 | `var/knowledge/` (the user dir) |
| Shipped primers | 90 | `ats/services/agents/corpus/` |
| Generated instrument profiles | 88 | from the knowledge service |

Higher reliability outranks generic material in retrieval. **Your curated notes
(95) beat the built-in primers (90)** — which is exactly what we want.

---

## 2. Current state and the gap

**What ships today** (`ats/services/agents/corpus/`): 7 one-page primers, ~2,255
words / 48 chunks total:

- `family_a_market_quant.md` → family A
- `family_b_india_macro_primer.md`, `family_b_macro_pillars.md` → family B
- `family_c_instruments.md` → family C
- `risk_governor.md` → RISK
- `general.md`, `nse_market_primer.md` → shared (`all`)

**The operator knowledge dir `var/knowledge/` is empty** (it does not exist yet).
So every expert is currently grounded by ~1 page of generic notes. The mechanism
is real; the depth is not. That is the whole job ahead.

**The roster needing material** (`personas/*.yaml`): ~30 experts —
- **Family A (5, active):** Technical Analyst, Trend Follower, Mean-Reversion,
  Volume Breakout, Quant Value.
- **Family B (16, shadow):** Macro Economist, Monetary Policy, Fiscal Policy,
  Geopolitics, Foreign Relations, Trade & Tariffs, FX, Energy & Commodities,
  Regulatory, Industrial Policy, Agri & Monsoon, Labor & Consumption, Technology
  Disruption, Climate & ESG, Global Risk, Political.
- **Family C (4):** Company Profile (active), ETF Specialist (active), Mutual Fund
  Specialist (shadow), Peer & Supply-Chain Mapper (shadow).
- **RISK (1):** Risk Governor.

---

## 3. How to author knowledge (rules that matter)

**Important:** the goal is **distilled notes**, not raw books. You read the books
and papers below and write (or curate) tight markdown summaries. Do **not** dump
entire PDFs/books — the retriever chunks by paragraph and copyright/noise hurt
quality. Think "expert's cheat-sheet," not "library."

### Directory + naming (naming controls scoping!)
Drop `.md`/`.txt` files into `var/knowledge/` (set by `ATS_KNOWLEDGE_DIR`). The
**filename prefix decides the family**:

```
var/knowledge/
  family_a_momentum.md          # → family A
  family_a_mean_reversion.md     # → family A
  family_b_rbi_monetary.md       # → family B
  family_b_fx_inr.md             # → family B
  family_c_etfs_india.md         # → family C
  risk_position_sizing.md        # → RISK
  glossary.md                    # no prefix → shared by ALL experts
```

Anything **without** a `family_a/b/c` or `risk` prefix is tagged `all` and is
retrieved for every expert — use that only for truly shared material (keep it
small to avoid diluting retrieval).

### Chunking + writing style (so retrieval actually finds it)
- **Use descriptive `##` headings** — each heading starts a new chunk and is
  carried with the body, so the heading should read like a mini-title
  ("Volume z-score and breakout confirmation", not "Notes").
- **Keep each section short** (a paragraph or two; ≤~900 chars is one chunk).
- **Use the vocabulary an asker would use.** Retrieval is keyword-based today, so
  if someone asks about "tracking error," the word "tracking error" should appear
  in the relevant chunk. Add synonyms.
- **One concept per section.** Self-contained beats long prose.
- For **company/instrument-specific** notes (Family C), put the **ticker in the
  heading** (e.g. `## RELIANCE.NS — business segments & moat`) so it matches.

### Upgrade path (do once the corpus grows)
The bag-of-words retriever is fine for a few hundred chunks. Once you have real
volume, install `sentence-transformers` + `chromadb` and set
`ATS_VECTOR_STORE=chroma` for semantic recall (synonyms, paraphrases). Same
interface; no code change. **See §4 for the full library-scale pipeline.**

---

## 4. Scaling to a real library — the ingestion & retrieval pipeline

You are right: you cannot hand the LLM a 1,000-page PDF or a 20 MB `.txt`. Two
hard limits make that impossible — the model's **context window** (a few hundred
KB of text max, and quality degrades long before that) and **cost/latency** (you
pay per token, every call). The answer is the standard production-RAG split:

> **The library is not the index.** Raw sources live on disk; a pipeline turns
> them into many small, enriched, searchable **chunks**. At question time we
> retrieve only the handful of chunks that actually matter and put *those* in the
> prompt. The model reads ~2–4k tokens of hyper-relevant material, not the book.

```
 RAW LIBRARY                 INGESTION (offline, once per source)            INDEX
 books/PDFs/HTML  ──▶ 1.parse ─▶ 2.clean ─▶ 3.chunk ─▶ 4.augment ─▶ 5.embed ─▶ 6.index (vector+keyword)
 filings/reports                                                                   │
                                                                                   ▼
 question ──▶ 7.build query ─▶ 8.hybrid ─▶ 9.filter ─▶ 10.rerank ─▶ 11.diversify ─▶ 12.fit-to-budget ─▶ PROMPT ─▶ LLM
                                          RETRIEVAL (every query)
```

### 4.1 The ingestion pipeline (run once per source, offline)

1. **Parse** — convert heterogeneous files to clean text/markdown, *preserving
   structure* (headings, lists, tables):
   - Text PDFs: `pypdf` / `pdfplumber`; scanned PDFs: OCR via `ocrmypdf`/`tesseract`.
   - HTML: `trafilatura` or `readability-lxml` (strips nav/ads).
   - DOCX: `python-docx`. Tables (financials!): extract to markdown tables or
     `key: value` lines so numbers keep their labels.
2. **Clean / normalize** — the quality step most people skip:
   - Strip boilerplate: page headers/footers, page numbers, repeated disclaimers,
     watermarks, table-of-contents, cover pages.
   - Fix PDF artifacts: de-hyphenate line-wrapped words, join broken sentences,
     normalize Unicode and whitespace, drop garbage/OCR-noise pages.
   - De-duplicate repeated paragraphs; keep facts, drop filler.
3. **Structure-aware chunking** — *not* fixed 900-char cuts. Best practice:
   - Split first on document structure (chapter/section/heading), then into
     **token windows of ~256–512 tokens with ~10–15% overlap** so ideas aren't
     severed mid-thought.
   - Never split a table/list across chunks.
   - Prepend a **breadcrumb** (doc title › chapter › section) to each chunk so it
     is self-describing out of context.
4. **Augment / enrich** — this is what makes retrieval *smart* (see §4.3):
   - **Metadata** per chunk: `source`, `author`, `date`, `family`, `ticker(s)`,
     `sector`, `doc_type`, `reliability`, `page/section`, `url`. Enables filtered
     search ("only RBI", "only 2024+", "only family B", "only SILVERBEES").
   - **Derived text** to boost recall: an LLM-written **one-line summary**, a
     short list of **"questions this chunk answers,"** and extracted
     **entities/keywords** (tickers, schemes, people).
   - **Contextual header**: a one-sentence "this passage is from X, about Y"
     prepended *before embedding* (Anthropic's "contextual retrieval" — large
     accuracy gains for finance docs full of pronouns and tables).
5. **Embed** — turn enriched chunks into vectors with a local, free model
   (`BAAI/bge-small-en-v1.5` or `all-MiniLM-L6-v2` via `sentence-transformers`) so
   it runs offline on the laptop. Embed the *enriched* text, not the raw chunk.
6. **Index** — persist vectors in `chromadb` (per-family collection or one
   collection with a `family` metadata filter), **and** keep a sparse keyword
   index (BM25) for hybrid search.

### 4.2 The retrieval pipeline (runs on every question)

7. **Build the query** — blend the question + the persona's lens + the symbol +
   recent headlines (the `ContextAssembler` already does a version of this).
8. **Hybrid search** — run **dense** (embeddings, for meaning/synonyms) **and**
   **sparse** (BM25, for exact tickers/acronyms like "SILVERBEES", "MPC", "REER")
   and merge. Hybrid beats either alone, especially for finance jargon.
9. **Metadata filter** — restrict to the expert's `family` + shared, optionally a
   `ticker`, a `date` window (macro is time-sensitive!), and `reliability ≥ N`.
10. **Rerank** — run a **cross-encoder reranker** (e.g. `bge-reranker-base`) over
    the top ~30 candidates and keep the best k. This is the biggest precision win
    after embeddings: it reads query+chunk *together* instead of comparing vectors.
11. **Diversify (MMR)** — drop near-duplicate chunks so the k slots cover
    different facets, not five paraphrases of one paragraph.
12. **Fit-to-budget + compress** — pack the top chunks until a token budget
    (~2–4k), newest/most-reliable first, attach citations. Optional **contextual
    compression**: extractively trim each chunk to only the sentences relevant to
    the query before the final prompt — more signal per token.

### 4.3 Augmentation techniques that matter most (in priority order)

- **Contextual chunk headers** — cheap, large recall gain. Do this first.
- **Synthetic "questions this answers"** — embed the questions too; user/pipeline
  questions then match question-to-question, which is far more reliable.
- **Multi-vector / parent-document retrieval** — embed *small* precise chunks but
  return the *larger* parent section to the LLM (search precision + read context).
- **Query expansion / HyDE** — expand a terse query with synonyms, or have the LLM
  draft a hypothetical answer and search with *that* (great for vague questions).
- **Recency decay** — down-weight stale macro chunks by `date`; keep evergreen
  concept notes (definitions) flat.

### 4.4 How this maps onto our code today

`knowledge_base.py` already implements a *basic* version of stages 3, 5 and a
simple 7–9: naive paragraph chunking, hashed bag-of-words embedding, top-k with a
family filter and reliability tiers. The upgrade keeps the **same `retrieve()`
interface** (so `console.py`/`context.py` don't change) and swaps the internals:

- Add an **ingestion script** `scripts/ingest_knowledge.py` for stages 1–4 that
  reads raw files from `library/`, cleans + structure-chunks + enriches them, and
  either writes clean `var/knowledge/*.md` **or** upserts straight into chroma.
- Swap stage 5–6 to `sentence-transformers` + `chromadb` (`ATS_VECTOR_STORE=chroma`).
- Add **hybrid + rerank + budget** (stages 8–12) inside `KnowledgeBase.retrieve`.
- Teach the ingester to read **YAML front-matter** (below) so chunks carry rich
  metadata, not just the filename-prefix family tag.

### 4.5 Directory layout & metadata convention

```
library/                         # RAW sources — gitignored, NEVER fed to the LLM
  family_b/rbi/monetary_policy_report_2024-04.pdf
  family_c/etf/silverbees_sid.pdf
knowledge/                       # CLEANED, chunked notes — COMMITTED (reliability 95)
  family_b_rbi_monetary.md       # hand-written OR generated by the ingester
var/knowledge/                   # optional LOCAL-only scratch notes — gitignored
var/index/chroma/                # persistent vector index — gitignored
scripts/ingest_knowledge.py      # parse → clean → chunk → enrich → write/index
```

The split is deliberate: raw `library/` sources stay local (bulky/licensed), the
*cleaned* `knowledge/` notes are version-controlled so the maintained SME library
ships and deploys with the repo, and `var/knowledge/` is an optional throwaway
override (`ATS_KNOWLEDGE_DIR`) for machine-local experiments.

Give generated/authored notes **YAML front-matter** so the ingester can tag every
chunk (a small parser addition to `knowledge_base.py` enables this):

```markdown
---
family: B
source: RBI Monetary Policy Report, Apr 2024
doc_type: central_bank_report
date: 2024-04-05
reliability: 96
tickers: []
---

## Stance and rationale of the April 2024 MPC
...
```

### 4.6 Phased rollout (offline-friendly, laptop-safe)

1. **Phase 1 (today):** keep authoring distilled markdown notes — works now, zero
   new deps. Covers Tier-1 experts.
2. **Phase 2 (shipped):** `scripts/ingest_knowledge.py` parses + cleans +
   structure-chunks + writes YAML front-matter, so you can drop PDFs/reports into
   `library/` and auto-generate clean notes in the committed `knowledge/` dir. The
   knowledge base now reads that front-matter (`family`, `reliability`, `tickers`,
   `date`, `doc_type`, `source`) to scope and rank retrieval. Optional parser deps
   (install only on the ingest machine): `pypdf` (PDF), `trafilatura` (HTML),
   `python-docx` (DOCX) — see `requirements.txt` and `library/README.md`. Usage:

   ```bash
   pip install pypdf trafilatura python-docx     # one time, ingest machine only
   # drop sources under library/family_b/, library/risk/, ...
   python scripts/ingest_knowledge.py            # cleans library/ -> knowledge/
   python scripts/ingest_knowledge.py --dry-run  # preview without writing
   ```
3. **Phase 3:** switch the vector store to `chromadb` + `sentence-transformers`
   embeddings for semantic recall.
4. **Phase 4:** add cross-encoder **reranking** + **hybrid (BM25)** + token-budget
   assembly + contextual headers.
5. **Phase 5:** evaluation + feedback loop (§4.7).

### 4.7 Evaluation & feedback (so it actually improves)

- Build a small **eval set**: ~30–50 `question → expected-fact/citation` pairs per
  family. Measure **retrieval hit-rate** whenever you change chunking, embeddings,
  or reranking — otherwise "improvements" are guesses.
- Log **which chunks were cited** and tie it to the SME's existing **track record**
  (`SmeTrackRecord`): chunks that lead to good calls can be up-weighted; noisy
  sources demoted in `reliability`.
- **Re-ingest on update** and version the index; macro/regulatory sources change.

### 4.8 Copyright & cleanliness note

For **public filings/official reports** (RBI, SEBI, NSE, Economic Survey) full
ingestion is fine. For **copyrighted books/papers**, store *your own distilled
notes*, not the full text — better for retrieval (less noise) and legally clean.

---

## 5. Priority order (to be useful ASAP)

Don't try to feed all 30 experts at once. Sequence by what's actually voting:

1. **Tier 1 — the active experts (this week).** Family A (5) + Family C ETF &
   Company Profile (2) + Risk Governor (1). These have real grounding now and
   their answers are user-facing in the console.
2. **Tier 2 — the macro pillars you can source from primary data (next).** Monetary
   (RBI), Fiscal (Budget/Economic Survey), FX, Energy, Trade — all have free,
   authoritative Indian data you can distill quickly.
3. **Tier 3 — the rest of Family B + remaining Family C.** These are `shadow`
   (weight 0) until the learning loop promotes them, so they can wait.

**Fastest high-quality win:** the Indian primary sources in §7 (RBI, SEBI, NSE,
MOSPI, Economic Survey) are free, authoritative (reliability 95 as your notes),
and directly relevant. Start there; books/papers add depth on top.

---

## 6. Curriculum — books & papers per family

> Read these to *write the notes*. Canonical references; pick a few per expert.

### Family A — Market / Quant (Technical, Trend, Mean-Reversion, Volume, Value)

**Books**
- John Murphy — *Technical Analysis of the Financial Markets*
- David Aronson — *Evidence-Based Technical Analysis* (rigor; avoid curve-fitting)
- Perry Kaufman — *Trading Systems and Methods*
- Wesley Gray & Jack Vogel — *Quantitative Momentum*
- Wesley Gray & Tobias Carlisle — *Quantitative Value*
- Marcos López de Prado — *Advances in Financial Machine Learning* (backtest hygiene)
- Andrew Lo & A.C. MacKinlay — *A Non-Random Walk Down Wall Street*

**Papers**
- Jegadeesh & Titman (1993) — *Returns to Buying Winners and Selling Losers* (momentum)
- De Bondt & Thaler (1985) — *Does the Stock Market Overreact?* (mean reversion)
- Asness, Moskowitz & Pedersen (2013) — *Value and Momentum Everywhere*
- Fama & French (1993, 2015) — three- and five-factor models
- Moskowitz, Ooi & Pedersen (2012) — *Time Series Momentum*
- AQR — *A Century of Evidence on Trend-Following Investing*

**Note topics to write:** trend/momentum definitions and signals, overbought/
oversold and RSI/Bollinger, volume z-score & breakout confirmation, fakeout
filters, mean-reversion entry/exit discipline, margin-of-safety/fair-value proxy,
and **backtest pitfalls** (look-ahead, survivorship, overfitting).

### Family B — Macro / Thematic pillars (India-centric)

**Foundational books**
- Blanchard *Macroeconomics* or Mankiw *Macroeconomics* (core)
- Vijay Joshi — *India's Long Road: The Search for Prosperity*
- Montek Singh Ahluwalia — *Backstage: The Story Behind India's High Growth Years*
- Kindleberger & Aliber — *Manias, Panics, and Crashes*
- George Soros — *The Alchemy of Finance* (reflexivity, regimes)

**Per-analyst sourcing (distill the notes from these):**
- **Macro Economist:** Economic Survey of India (annual), RBI *Report on Currency
  and Finance*, business-cycle/GDP nowcasting basics.
- **Monetary Policy:** RBI MPC statements & minutes, RBI Monetary Policy Report,
  the Flexible Inflation Targeting framework (Urjit Patel Committee report, 2014).
- **Fiscal Policy:** Union Budget documents, FRBM Act, fiscal-deficit/borrowing
  dynamics; NK Singh FRBM Review Committee report.
- **FX Analyst:** RBI BoP & FX-reserves data; interest-rate parity, REER; effects
  of INR/USD on importers vs exporters. (Ref: Sarno & Taylor, *The Economics of
  Exchange Rates*.)
- **Energy & Commodities:** Energy Institute *Statistical Review of World Energy*,
  IEA *Oil Market Report*; India's crude import dependence and sector pass-through.
- **Trade & Tariffs:** WTO basics, DGCIS/Ministry of Commerce export-import data,
  DGFT foreign-trade policy.
- **Industrial Policy:** PLI scheme documents, *Make in India*, Index of
  Industrial Production (IIP), capex-cycle indicators.
- **Agri & Monsoon:** IMD monsoon forecasts, Ministry of Agriculture data, rural
  demand/MSP, *Situation Assessment of Agricultural Households*.
- **Labor & Consumption:** PLFS (Periodic Labour Force Survey), CMIE data, RBI
  Consumer Confidence Survey, private-consumption trends.
- **Regulatory:** SEBI circulars + SEBI Annual Report; sector regulators (TRAI,
  IRDAI, CERC) as relevant.
- **Geopolitics / Foreign Relations:** FII/FPI flow data (NSDL/CDSL), risk-on/
  risk-off framing; Kissinger *World Order* for structure.
- **Global Risk:** US FOMC statements, US Treasury curve, VIX, DXY; BIS Annual
  Economic Report. (Ref: Geithner, *Stress Test*.)
- **Technology Disruption:** Christensen, *The Innovator's Dilemma*; sector
  adoption/AI capex notes.
- **Climate & ESG:** SEBI BRSR (Business Responsibility & Sustainability Reporting)
  framework, TCFD recommendations, stranded-asset risk.
- **Political:** Election Commission data, policy-continuity framing, state vs
  union dynamics affecting sectors.

### Family C — Instruments (Company, ETF, Mutual Fund, Supply-Chain)

**Books**
- Pat Dorsey — *The Five Rules for Successful Stock Investing* (economic moats)
- Philip Fisher — *Common Stocks and Uncommon Profits*
- Aswath Damodaran — *The Little Book of Valuation* (and his free online material)
- John Bogle — *The Little Book of Common Sense Investing* (index/ETF logic)

**Primary sources to distill**
- **Company Profile:** company annual reports / investor presentations,
  screener.in, sector value chains; write one note per held name (ticker in heading).
- **ETF Specialist:** NSE/BSE ETF lists, AMFI data, scheme information documents
  (SID), tracking-error & NAV premium/discount mechanics, liquidity/iNAV.
- **Mutual Fund Specialist:** SEBI Mutual Fund Categorization circular (Oct 2017),
  AMFI category data, expense ratios, style (value/growth), holdings overlap.
- **Peer & Supply-Chain Mapper:** industry value-chain maps, supplier/customer
  relationships, second-order beneficiaries of a theme.

### RISK — Risk Governor

**Books / refs**
- John Hull — *Risk Management and Financial Institutions* (VaR, stress testing)
- Grinold & Kahn — *Active Portfolio Management* (risk budgeting, IR)
- Peter Bernstein — *Against the Gods* (history of risk)
- Nassim Taleb — *The Black Swan* / *Fooled by Randomness* (tail risk)
- Position sizing: Kelly criterion (and fractional-Kelly), volatility targeting,
  drawdown control, concentration/sector limits (mirror the system's guardrails).

---

## 7. Indian primary data sources (free, authoritative — start here)

These are the highest-leverage inputs: free, trustworthy, and directly relevant to
an NSE/INR book. Distill them into `family_*` notes (and later wire as live feeds).

- **RBI** — Database on Indian Economy (DBIE), Monthly Bulletin, MPC statements,
  Monetary Policy Report, Financial Stability Report.
- **SEBI** — circulars, master circulars, Annual Report (regulation changes).
- **NSE / BSE** — index methodology, F&O data, ETF lists, sector indices.
- **MOSPI** — GDP, IIP, CPI/WPI.
- **Ministry of Finance** — Economic Survey (annual), Union Budget.
- **AMFI** — mutual fund AUM, category and scheme data.
- **NSDL / CDSL** — FPI/FII flow statistics.
- **IMD** — monsoon onset/forecast.
- **DGCIS / Ministry of Commerce** — trade (export/import) data.
- **PIB / sector ministries** — PLI and policy announcements.

---

## 8. A worked example knowledge file

`var/knowledge/family_c_etfs_india.md`:

```markdown
# Indian ETFs — how to read and pick them

## Tracking error: what it is and why it matters
Tracking error is the std-dev of an ETF's return minus its index return. Causes:
expense ratio, cash drag, sampling, securities-lending, rebalancing. For a passive
view, prefer low tracking error; a persistent gap means the ETF is not delivering
the index exposure you wanted.

## NAV premium / discount and iNAV
Market price can drift from NAV. A persistent premium = demand outstripping
creation; a discount = the reverse. Large, persistent gaps signal liquidity stress
or stale NAV — investigate before trading. Use iNAV (indicative NAV) intraday.

## Liquidity: on-screen volume vs creation/redemption
Thin on-screen volume is not the whole story — APs can create/redeem units, so
true liquidity tracks the underlying basket. Still, wide bid/ask spreads raise the
real cost of entry/exit for retail-size orders.

## SILVERBEES.NS — silver ETF mandate
Nippon India Silver ETF. Expresses a view on silver (safe-haven / inflation hedge /
industrial-demand cycle). Watch tracking error vs silver spot, NAV premium, and
import-duty / currency effects on the INR price.
```

Each `##` becomes a retrievable chunk; the ticker-in-heading line is found when
someone asks about `SILVERBEES`.

---

## 9. Suggested next steps

1. Create `var/knowledge/` and add Tier-1 notes (Family A + ETF/Company + Risk).
2. Lean on §7 Indian primary sources for fast, authoritative content.
3. Build the ingestion pipeline (§4) when you start adding PDFs/reports at volume:
   `scripts/ingest_knowledge.py` first, then `chromadb` + embeddings, then rerank.
4. Stand up the eval set (§4.7) early so retrieval changes are measured, not guessed.
5. Use the console's "remember …" on any expert to capture durable rules
   (reliability 100) as you learn what works.
