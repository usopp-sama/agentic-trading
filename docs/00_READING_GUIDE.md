# 00 · Reading Guide — start here

New to this project (or coming back after a break)? Read the docs in the order
below. Each line says **what the doc is** and **why you'd read it**, so you can
skip around once you know the lay of the land.

> Why a guide instead of renaming every file `01_…`, `02_…`? The docs
> cross-link each other, and the README + code reference them by name — renaming
> ~24 files would break all those links. This guide gives you the same numbered
> reading order without the breakage. (If you'd still prefer physical renames,
> say so and I'll do it carefully, fixing every link.)

Two brand-new companion docs live next to this one:
- **[01_SOURCE_GUIDE.md](01_SOURCE_GUIDE.md)** — a plain-language tour of the
  *code* (what each folder does, how a price becomes a trade). Read it alongside
  step 2 below.

---

## Track A — Understand what this thing is (read first)

1. **[../README.md](../README.md)** — the front door: what the system does, how
   to install and run it, the safety model, and a map of every subsystem. If you
   read only one thing, read this.
2. **[architecture.md](architecture.md)** — the engineering picture: the event
   bus, the orchestrator, and every service, with links into the code. Pair it
   with [01_SOURCE_GUIDE.md](01_SOURCE_GUIDE.md).
3. **[roadmap.md](roadmap.md)** — what's built, what's deferred, and why
   (real-money is intentionally gated off). Good for "is X done yet?".

## Track B — The ideas behind the "brains" (LLM + experts)

4. **[smx.md](smx.md)** — deep dive on the "SMX / SME" idea: how a plain LLM is
   turned into a domain expert. Conceptual, self-contained.
5. **[sme_knowledge_base.md](sme_knowledge_base.md)** — how those experts
   actually *learn* (the RAG curriculum) and what reading feeds them.
6. **[nlp_sentiment.md](nlp_sentiment.md)** — how news headlines become a
   sentiment score (VADER + FinBERT) that the system can trade on.
7. **[llm_provider.md](llm_provider.md)** and
   **[llm_cost_controls.md](llm_cost_controls.md)** — which LLM is called, when,
   and how spend is capped (the ₹/month budget gate you see on the Ops Console).

## Track C — Run it for real (paper trading)

8. **[kite_setup.md](kite_setup.md)** — connect Zerodha (Kite) for real NSE
   market data and the one-click daily login.
9. **[deployment_lan.md](deployment_lan.md)** — serve the dashboard to other
   devices on your home network.
10. **[month_paper_run.md](month_paper_run.md)** — the operator playbook for
    running a month of paper trading (fake money, real prices) unattended.
11. **[plans/monday_dummy_run.md](plans/monday_dummy_run.md)** — the concrete
    "strategies trade a ₹1 lakh paper book" dry-run plan.

## Track D — Where the project has been (history / context)

12. **[handoff_2026-06-30.md](handoff_2026-06-30.md)** — a snapshot handoff of
    the system state (older, but good narrative context).
13. **[assessment_and_plan_2026-07-07.md](assessment_and_plan_2026-07-07.md)** —
    an honest independent review against the stated goal (₹10k/month on ₹1L).
14. **[dashboard_redesign.md](dashboard_redesign.md)** — the "results-first"
    dashboard design thinking.

## Track E — Detailed build plans (`docs/plans/`, deepest, read last)

These are the working specs behind each big chunk of work — read the ones that
match what you're touching:

- **[plans/three_loop_architecture.plan.md](plans/three_loop_architecture.plan.md)**
  — the fast/slow/governance loop design.
- **[plans/quant_analytics_engine.plan.md](plans/quant_analytics_engine.plan.md)**
  — the deterministic analytics engine.
- **[plans/perf_and_ops_console.plan.md](plans/perf_and_ops_console.plan.md)** —
  the performance fixes + the Ops Console (the "engine room" UI).
- **[plans/live_readiness_and_multiuser.plan.md](plans/live_readiness_and_multiuser.plan.md)**
  — live-data readiness, the Ops credits panels, Kite live source, go-live
  hardening (L1–L6), and the multi-user roadmap.
- **[plans/strategy_edge_improvement.plan.md](plans/strategy_edge_improvement.plan.md)**
  — **why the backtest promoted 0 strategies and how we make them better**
  (E1–E7). If you care about the trading edge, read this.
- Older/superseded plans (kept for the record):
  [go_live_readiness.md](plans/go_live_readiness.md),
  [gemini_upgrade_and_resilience_11304d15.plan.md](plans/gemini_upgrade_and_resilience_11304d15.plan.md),
  [results-first_dashboard_redesign_6131c9dc.plan.md](plans/results-first_dashboard_redesign_6131c9dc.plan.md),
  [agentic_trading_server_67829fae.plan.md](plans/agentic_trading_server_67829fae.plan.md),
  [architecture_documentation_46947af0.plan.md](plans/architecture_documentation_46947af0.plan.md),
  [month-long_paper_run_59c0fb01.plan.md](plans/month-long_paper_run_59c0fb01.plan.md).

---

## The 10-minute version

If you just want the gist: read the **README**, skim **architecture.md** with
**[01_SOURCE_GUIDE.md](01_SOURCE_GUIDE.md)** open beside it, then read the top of
**[plans/strategy_edge_improvement.plan.md](plans/strategy_edge_improvement.plan.md)**
to understand where the trading edge stands today.
