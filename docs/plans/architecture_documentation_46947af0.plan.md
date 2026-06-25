---
name: Architecture Documentation
overview: Write a single comprehensive architecture document (docs/architecture.md) that explains how every component of the agentic trading server is structured and how they play together, grounded in the actual code, existing docs, and the git history.
todos:
  - id: draft-doc
    content: Write docs/architecture.md sections 1-15 with verified file/line citations and mermaid diagrams
    status: completed
  - id: diagrams
    content: Build corrected top-level architecture diagram + per-layer data-flow diagrams (data/intel, strategies, agents/CIO, risk/execution, dashboard)
    status: completed
  - id: topic-matrix
    content: Compile the canonical event-topic subscribe/publish matrix and the quant-import table
    status: completed
  - id: crosslink
    content: Cross-link existing docs (smx, sme_knowledge_base, dashboard_redesign, month_paper_run, deployment_lan) and note stale README details
    status: completed
isProject: false
---

# Architecture Documentation

## Goal
Create one authoritative `docs/architecture.md` describing the **current** architecture: the modular-monolith structure, the event-driven pipeline, every service, the shared core/state, the web/dashboard layer, the `quant/` toolkit, and the safety/learning loops — with how components interact (events, oracles, orchestrator registry). Cite real files/line ranges.

## Source material (already gathered)
- Code: `ats/core/`, `ats/server/`, `ats/services/*`, `quant/` (verified via exploration of all four subsystems).
- Existing docs to fold in / cross-link: [README.md](README.md), [docs/smx.md](docs/smx.md), [docs/sme_knowledge_base.md](docs/sme_knowledge_base.md), [docs/dashboard_redesign.md](docs/dashboard_redesign.md), [docs/month_paper_run.md](docs/month_paper_run.md), [docs/deployment_lan.md](docs/deployment_lan.md).
- Git history (28 commits) used to frame the build order / evolution narrative.

## Document structure (sections)
1. **System overview** — what it is (always-on agentic NSE trading server), modular monolith, paper-first/safety-first, offline-first with in-process fallbacks.
2. **Architecture at a glance** — corrected top-level mermaid diagram including all wired services (`market_data`, `regime`, `fundamentals`, `options_data`, `scraper`, `nlp`, `strategies`, `knowledge`, `agents`, `risk`, `execution`, `vol_premium`, `telegram`, `watchdog`, `learning`, `metrics`, `rules`, `dashboard`).
3. **Core infrastructure** (`ats/core/`) — config (pydantic-settings, `ATS_` env), JSON logging + secret redaction, SQLAlchemy db + models, Pydantic schemas/contracts, the event bus (`InMemoryEventBus`/`RedisStreamBus`, `Topic`), runtime KV + hash-chained audit (`state.py`).
4. **Orchestration & lifecycle** — `app.py` lifespan, `bootstrap.seed_all`, `wiring.py` service list, `Orchestrator` (bus + APScheduler + name registry), fault-isolated registration, scheduler cadences.
5. **The event pipeline** — canonical topics table and a stage-by-stage subscribe/publish matrix (who consumes/produces each topic), the BAR "clock", plus the **oracle pattern** (synchronous `orchestrator.get(name)` calls alongside the bus).
6. **Data & intelligence layer** — `market_data` (pluggable sources, NSE calendar, volume-spike detection, feed-health alerts, `option_chain`), `scraper` (RSS/Marketaux, dedup, ticker map), `nlp` (VADER/FinBERT, ticker mapper, shared vector store), `fundamentals`, `options_data` (IV premium), `regime`, `knowledge` (instrument profiles).
7. **Strategy layer** — `base` contracts, per-symbol vs universe families (`library*.py`), virtual `sleeves`, regime tilt (dampen-only), capital `allocation` (inverse-vol → ERC → tilt), shadow/paper/paused lifecycle + backtest promotion gate.
8. **The SME agent layer** — personas (26: 5 A / 16 B / 4 C / 1 RISK; active vs shadow), `ContextAssembler` + read-only tools, RAG `KnowledgeBase` (corpus + `var/knowledge` + profiles, reliability tiers, ingestion pipeline), self-evolving `directives`, `SmeRuntime`, `CIO` aggregation (track-record-weighted voting + macro tilt), the interactive `console` + `experts_api` (threads, theses, debate). Cross-link smx.md and sme_knowledge_base.md.
9. **Risk, execution & safety** — risk guardrails (immutable) + Kelly-capped allocator + adaptive-rule clamp → `exec.decision`; execution autonomy switch (OFF/PAPER/APPROVAL/AUTO), real-money gate, fee model, paper broker, approval flow, daily P&L, restart-safe state; `rules` engine (lifecycle + meta-limits); `watchdog` dead-man switch; `telegram` one-tap approvals; isolated `vol_premium` options sleeve. Summarize the multi-layer safety model.
10. **Learning loop** — fill attribution → forward-return scoring (hit-rate/Brier/vote-weight) → promotion/demotion feeding back into agent vote weights; `metrics` exports.
11. **Web & dashboard layer** — FastAPI app, control API (`api.py`), results API (`results_api.py`), experts API, `auth` token gate, WebSocket `hub`, `dashboard` service bridge (event→WS + 5s snapshot), the 7 current pages and the bus→hub→browser flow.
12. **The `quant/` toolkit** — standalone, look-ahead-safe library (data/analysis/backtest/risk/options/projects) and the table of which services import which parts.
13. **Storage & deployment topology** — SQLite↔Postgres/Timescale, memory↔Redis bus, memory↔Chroma vector store; Docker/compose/systemd; localhost-only posture.
14. **Evolution (from git history)** — short narrative: initial monolith + dashboard → quant toolkit/strategy library → regime/allocation/sleeves → India data layer → autonomy (watchdog/telegram/vol-premium) → SME experts + RAG + console → dashboard redesign → paper-run hardening + knowledge curriculum.
15. **Cross-references** — links to the other docs so this becomes the index.

## Conventions
- Lead with mermaid diagrams (top-level + per-layer data-flow), then prose + compact tables.
- Cite real paths with line ranges; use markdown links for file mentions.
- Correct the stale README details (dashboard pages, service list, persona count) in the new doc; optionally note a follow-up to refresh README's Architecture/Dashboard sections (out of scope unless requested).

## Deliverable
- New file: `docs/architecture.md` (no code changes).
