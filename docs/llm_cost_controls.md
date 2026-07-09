# LLM cost controls — when we call Gemini, and how we keep it cheap

This is the authoritative map of **every event that spends Gemini tokens**, what
runs **locally for free**, and the **knobs** that throttle autonomous spend.

## 1. What triggers a Gemini call

LLM calls happen in exactly three places in the code:

- `ats/services/agents/runtime.py` → `SmeRuntime.run/opine` → `generate_opinion`
  (one call **per persona**)
- `ats/services/agents/console.py` → `ExpertConsole` → `chat` / `opine`
- `ats/server/results_api.py` → Today brief / explain → `build_llm_client("cio").chat`

Everything else just *feeds* those. The trigger graph:

| # | Trigger | Path | Cost | Gated? |
|---|---------|------|------|--------|
| 1 | **Fresh news sentiment** | scraper → `NEWS` → nlp (local score) → `SENTIMENT` → `agents._on_sentiment` → `run_symbol` per ticker | **`tickers × symbol_personas` calls** + 1 macro refresh | ✅ now gated (hours + universe + cooldown + cap) |
| 2 | **Volume spike** | market_data → `VOLUME_SPIKE` → `agents._on_spike` → `run_symbol` | `symbol_personas` calls | ✅ now gated (same levers) |
| 3 | **Periodic macro sweep** | scheduler → `agents._scheduled_macro_sweep` → `refresh_macro` | `market_personas` calls | ✅ already session-gated |
| 4 | **Experts console** (you) | `/api/experts/*` → console | per question | manual — always allowed |
| 5 | **Today brief / explain** (you) | `/api/today/*` → CIO chat | per click | manual — always allowed |
| 6 | **Startup health probe** | `select_llm_clients` → `health_check` | **1 tiny ping** | n/a (already single ping) |

> The "26 personas pinging to check online" worry was about **#6**, but the
> health probe is and always was a **single** `OK` request. The real burst is
> **#1/#2** — every news item used to fan out an SME pass across the roster for
> every ticker it named, 24/7. That is what the gating below fixes.

### The fan-out math (why #1 hurt)
One macro headline naming 8 tickers, with ~16 symbol-scope personas, was
`8 × 16 = 128` Gemini calls — and it fired even at 3 a.m. on a Sunday, because
news arrives around the clock. Multiply by restarts and you get the ₹40.

## 2. What is already 100% local (no Gemini)

| Work | Where | Engine |
|------|-------|--------|
| News fetching | `scraper/` | RSS + Marketaux HTTP (no LLM) |
| News sentiment | `nlp/sentiment.py` | **VADER / FinBERT** on-device |
| Ticker extraction | `nlp` ticker mapper | local dictionary |
| RAG indexing/search | `nlp/vectorstore.py` | local embeddings |
| Strategy signals | `strategies/`, `quant/` | pure math (pandas/numpy) |
| Regime detection | `regime/` | math |
| Risk checks / sizing | `risk/`, `execution/` | rules |
| Fundamentals | `fundamentals/` | math over fetched ratios |
| Deep-analysis docs | `research/` | pdfplumber + heuristics |

**Gemini is only used to *synthesize a judgement* (SME opinion, CIO brief).**
That already matches your goal — "only use Gemini for smart decisions." The
problem was never *what* we used it for, only *how often*. The knobs in §3 fix
the frequency; no decision-making was moved off Gemini.

## 3. The knobs (all in `.env`, defaults in `ats/core/config.py`)

| Setting | Default | Effect |
|---------|---------|--------|
| `ATS_LLM_EVAL_MARKET_HOURS_ONLY` | `true` | No autonomous spend outside NSE session (+45 min grace). News still scored locally; SMEs read the backlog at open. |
| `ATS_LLM_EVAL_UNIVERSE_ONLY` | `true` | Only run SMEs for watchlist names; off-universe tickers in news are ignored. |
| `ATS_LLM_SYMBOL_COOLDOWN_S` | `900` | A symbol re-evaluates at most once per 15 min, so a news burst on one name = one pass. |
| `ATS_LLM_MAX_SYMBOLS_PER_EVENT` | `3` | A multi-ticker headline fans out to at most the 3 most-mentioned names. |
| `ATS_LLM_MAX_PROMPT_CHARS` | `24000` | An oversized opinion prompt is **skipped** (mock answers) and logged, instead of auto-spending a large request. Your "approval for big calls" — lightweight form. |

Implementation: `ats/services/agents/gating.py` (pure, unit-tested) wired into
`AgentService._on_spike` / `_on_sentiment`; the size guard is in
`HttpLLMClient.generate_opinion`.

### Rough impact
A weekend of macro news that previously fired hundreds of calls now fires
**zero** (market closed). During the session, the same name with 5 fresh
headlines fires **one** pass instead of five. Multi-ticker headlines are capped.
Expect autonomous call volume down ~80–95% with no loss of decision quality
(deferred, not dropped).

## 4. The two repos you found

- **linshenkx/prompt-optimizer** — a standalone web/desktop/Docker app + MCP
  server for *hand-tuning* prompts at dev time. It is a TypeScript/Vue product,
  not a Python library to embed, and calling its MCP `optimize-*` tools at
  runtime would *add* an LLM call (the opposite of our goal). **Recommended use:**
  run our SME/CIO system prompts through it once, offline, and commit the
  improved templates. Not a runtime dependency.
- **JuliusBrussee/caveman** — an agent *skill* that makes a chat agent reply
  tersely to cut **output** tokens. Our SME calls already return compact JSON
  (output is already minimal), so caveman's win mostly applies to the free-form
  CIO brief/console. We can adopt the *principle* (a "be terse" instruction)
  there without installing anything. Our dominant cost is **input** tokens and
  **call count**, which §3 addresses directly.

**Verdict:** neither is worth a runtime integration; the call-volume + input
controls above are the high-ROI levers. prompt-optimizer is a useful one-time
dev tool for sharpening templates.

## 5. News grouping / targeted SME work — SHIPPED

Two layers, both local (no LLM), both unit-tested:

**Symbol layer** (`gating.rank_symbols`): incoming news tickers are de-duped,
ranked most-mentioned-first, universe-filtered, and capped — so symbol-scope SME
work targets the names we actually trade, not the whole list on everything.

**Theme layer** (`news_routing.py`): each headline is classified into coarse
macro **themes** by a local keyword map, then routed to only the relevant
macro (Family B) experts instead of all 16.

| Theme | Sample keywords | Experts run |
|-------|-----------------|-------------|
| monetary | rbi, repo, inflation, cpi, mpc | monetary_policy (+core) |
| fiscal | budget, fiscal deficit, gst, divestment | fiscal_policy |
| geopolitics | war, border, sanction, missile | geopolitics, global_risk |
| foreign_relations | fii, fpi, foreign investor | foreign_relations, fx_analyst |
| trade | tariff, export, import duty, wto | trade_tariffs, fx_analyst |
| fx | rupee, inr, dollar, forex | fx_analyst, foreign_relations |
| energy | crude, brent, opec, gas, coal | energy_analyst, climate_esg |
| commodity | gold, silver, copper, steel, metal | energy_analyst, industrial_policy |
| regulatory | sebi, regulator, circular, norms | regulatory_analyst |
| industrial | pli, capex, manufacturing, iip | industrial_policy |
| agri | monsoon, kharif, crop, rural demand | agri_monsoon |
| labor | jobs, wages, layoff, consumption | labor_consumption |
| tech | semiconductor, chip, AI, software | technology_disruption |
| climate | climate, carbon, esg, renewable | climate_esg, energy_analyst |
| politics | election, parliament, minister, reform | political_analyst |
| global | fed, us rates, recession, china | global_risk, macro_economist |

- **Always-on core:** `macro_economist`, `global_risk` read on every macro
  trigger so the broad regime tilt is never lost.
- **Unclassifiable headline:** runs only the 2 core experts — not all 16.
- **Periodic macro sweep** (clock-driven, in-session) still runs the full roster
  for a complete read; only the *news-driven* path is theme-routed.

Net effect: a crude-oil headline now wakes ~3 experts (energy + climate + core)
instead of 16 — on top of the market-hours/cooldown/cap gates from §3.

Design decisions (confirmed): the "large call" guard stays **skip-and-log**
(no blocking/approval queue); the taxonomy above was auto-derived from the
Family B persona roles for review — edit `THEME_KEYWORDS` / `PERSONA_THEMES` in
`news_routing.py` to tune.
