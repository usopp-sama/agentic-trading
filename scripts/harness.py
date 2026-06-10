"""Async end-to-end harness.

Boots the orchestrator (not via HTTP), drives a few cycles of the live
services, and prints a summary. This grows into the full end-to-end demo as
phases land. Runs fully offline (synthetic data + mock LLM).

Usage: python scripts/harness.py
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ats.core.db import init_db  # noqa: E402
from ats.core.events import Topic  # noqa: E402
from ats.core.logging import configure_logging  # noqa: E402
from ats.services.bootstrap import seed_all  # noqa: E402
from ats.server.wiring import build_orchestrator  # noqa: E402


def banner(title: str) -> None:
    print("\n" + "=" * 64 + f"\n{title}\n" + "=" * 64)


async def main() -> None:
    configure_logging("WARNING")  # keep harness output readable
    init_db()
    seed_all()

    orch = build_orchestrator()

    counts: Counter[str] = Counter()
    for topic in (Topic.BAR, Topic.VOLUME_SPIKE, Topic.NEWS, Topic.SENTIMENT,
                  Topic.SIGNAL, Topic.OPINION, Topic.PROPOSAL, Topic.DECISION,
                  Topic.ORDER, Topic.FILL):
        async def _h(evt, _t=topic):
            counts[_t] += 1
        orch.bus.subscribe(topic, _h)

    await orch.start()

    banner("Phase 1: Market Data")
    md = orch.get("market_data")
    print(f"Watchlist size : {len(md.watchlist())}")

    # Drive several market scan cycles (each appends a synthetic bar + detects spikes).
    for _ in range(8):
        await md.poll_all()
        await asyncio.sleep(0.05)  # let the bus dispatch

    sample = md.watchlist()[2] if len(md.watchlist()) > 2 else md.watchlist()[0]
    hist = md.get_history(sample)
    print(f"Sample symbol  : {sample}")
    print(f"History bars   : {len(hist)}")
    print(f"Last price     : {md.latest_price(sample):.2f}")
    print(f"BAR events     : {counts[Topic.BAR]}")
    print(f"VOLUME_SPIKE   : {counts[Topic.VOLUME_SPIKE]}")

    banner("Phase 2: Paper Broker + Portfolio")
    execution = orch.get("execution")
    if execution is not None:
        wl = [s for s in md.watchlist() if not s.startswith("^")]
        buy1, buy2 = wl[0], wl[1]
        print("BUY 10:", await execution.submit_market_order(buy1, "BUY", 10))
        print("BUY 5 :", await execution.submit_market_order(buy2, "BUY", 5))
        print("SELL 4:", await execution.submit_market_order(buy1, "SELL", 4))
        await asyncio.sleep(0.05)
        execution.record_equity()
        snap = execution.get_snapshot()
        print(f"Cash           : {snap['cash']:.2f}")
        print(f"Holdings value : {snap['holdings_value']:.2f}")
        print(f"Equity         : {snap['equity']:.2f}")
        print(f"Realized PnL   : {snap['realized_pnl']:.2f}")
        print(f"Positions      : {snap['positions']}")
        print(f"FILL events    : {counts[Topic.FILL]}")

    banner("Phase 3: Strategy Engine")
    strat = orch.get("strategies")
    if strat is not None:
        all_latest = strat.all_latest()
        actionable = [
            s for sigs in all_latest.values() for s in sigs
            if s.stance.value != "neutral"
        ]
        print(f"SIGNAL events  : {counts[Topic.SIGNAL]}")
        print(f"Symbols w/ sig : {len(all_latest)}")
        print(f"Actionable now : {len(actionable)}")
        for s in actionable[:5]:
            print(f"  - {s.strategy:16s} {s.symbol:14s} {s.stance.value:6s} conv={s.conviction:.2f} {s.features}")

    banner("Phase 4: News + NLP + RAG")
    scraper = orch.get("scraper")
    nlp = orch.get("nlp")
    if scraper is not None and nlp is not None:
        for _ in range(4):
            await scraper.collect_once()
            await asyncio.sleep(0.05)
        print(f"NEWS events    : {counts[Topic.NEWS]}")
        print(f"SENTIMENT evts : {counts[Topic.SENTIMENT]}")
        print(f"Vector docs    : {len(nlp.store)}")
        # Find a symbol that has sentiment and show it + a RAG hit.
        for sym in md.watchlist():
            rs = nlp.recent_sentiment(sym)
            if rs["count"] > 0:
                print(f"Sentiment {sym}: mean={rs['mean_score']:+.3f} label={rs['label']} n={rs['count']}")
                hits = nlp.search_symbol(sym, k=2)
                for h in hits[:2]:
                    print(f"  RAG: {h['text'][:70]}")
                break

    banner("Phase 5a/5b: SME Roster + CIO")
    agents = orch.get("agents")
    if agents is not None:
        from ats.services.agents.registry import families
        roster = agents.personas()
        print(f"Roster size    : {len(roster)}  families={families(roster)}")
        tilt = await agents.refresh_macro()
        print(f"Macro tilt     : {tilt:+.3f} (Family B shadow -> ~0 until promoted)")
        wl = [s for s in md.watchlist() if not s.startswith("^")]
        for sym in wl[:2]:
            ops, proposal = await agents.run_symbol(sym)
            active = [o for o in ops if agents._by_id.get(o.sme, {}).get("weight", 0) > 0 and agents._by_id.get(o.sme, {}).get("family") != "RISK"]
            print(f"\n{sym}: {len(ops)} opinions ({len(active)} voting) -> PROPOSAL {proposal.action} "
                  f"w={proposal.target_weight:+.3f} conv={proposal.conviction:.2f}")
            for op in active:
                print(f"  {op.sme:24s} {op.stance.value:11s} conv={op.conviction:.2f}")
            print(f"  CIO: {proposal.rationale}")
        print(f"\nOPINION events : {counts[Topic.OPINION]}")
        print(f"PROPOSAL events: {counts[Topic.PROPOSAL]}")

    banner("Phase 6: Risk Manager + Allocator")
    risk = orch.get("risk")
    if risk is not None and agents is not None:
        wl = [s for s in md.watchlist() if not s.startswith("^")]
        for sym in wl[:10]:
            await agents.run_symbol(sym)  # -> PROPOSAL -> risk -> DECISION -> FILL
        await asyncio.sleep(0.2)
        print(f"DECISION events: {counts[Topic.DECISION]}")
        print(f"FILL events    : {counts[Topic.FILL]}")
        # Guardrail demo: an oversized 90% target must be clamped to the cap.
        demo = await risk.evaluate_proposal(
            {"symbol": wl[0], "action": "BUY", "target_weight": 0.9, "conviction": 1.0,
             "rationale": "guardrail test", "contributors": {}}
        )
        print(f"Oversized order: {demo}")
        snap = orch.get('execution').get_snapshot()
        print(f"Equity now     : {snap['equity']:.2f}  positions={len(snap['positions'])}")

    banner("Phase 5c: Instrument Knowledge Base")
    knowledge = orch.get("knowledge")
    if knowledge is not None:
        profs = knowledge.all_profiles()
        print(f"Profiles       : {len(profs)}")
        prof = knowledge.get_profile("RELIANCE.NS")
        print(f"RELIANCE themes: {prof.get('themes')}")
        print(f"  thematic_fit : {prof.get('thematic_fit')}")
        for theme in ("green energy transition", "AI adoption", "safe haven inflation hedge"):
            route = knowledge.route_view_to_vehicle(theme)
            print(f"Route '{theme}' -> {route}")

    banner("Phase 7: Autonomy Switch + Approvals")
    execution = orch.get("execution")
    from ats.core import state as _state
    if execution is not None and risk is not None:
        sym = [s for s in md.watchlist() if not s.startswith("^")][3]

        _state.set_mode("OFF")
        off = await execution.execute_decision({"symbol": sym, "action": "BUY", "qty": 2})
        print(f"OFF blocks     : {off}")

        _state.set_mode("APPROVAL")
        await risk.evaluate_proposal({"symbol": sym, "action": "BUY", "target_weight": 0.05,
                                      "conviction": 0.8, "rationale": "approval demo", "contributors": {}})
        await asyncio.sleep(0.1)
        pending = execution.list_pending_approvals()
        print(f"Pending appr.  : {len(pending)} -> {pending[:1]}")
        if pending:
            did = pending[0]["decision_id"]
            filled = await execution.approve_decision(did)
            print(f"After approve  : status={filled.get('status')} qty={filled.get('qty')} (paper; gate closed)")

        _state.set_mode("AUTO")
        auto = await risk.evaluate_proposal({"symbol": sym, "action": "BUY", "target_weight": 0.03,
                                             "conviction": 0.6, "rationale": "auto demo", "contributors": {}})
        await asyncio.sleep(0.1)
        print(f"AUTO routes    : {auto.get('status')} (real_money_active={_state.real_money_active()})")
        _state.set_mode("PAPER")

    banner("Phase 8: Learning + PnL Attribution")
    learning = orch.get("learning")
    if learning is not None:
        for _ in range(6):  # let prices move so forward returns resolve
            await md.poll_all()
            await asyncio.sleep(0.02)
        res = learning.evaluate(force=True)
        print(f"Attributions evaluated: {res['evaluated']}")
        print("SME leaderboard (by vote weight):")
        for r in learning.leaderboard(limit=8):
            print(f"  {r['sme']:24s} n={r['n']:3d} hit={r['hit_rate']:.2f} "
                  f"brier={r['brier']:.2f} vote={r['vote_weight']:.2f} status={r['status']}")

    banner("Phase 9: Self-Governing Rule Engine")
    rules = orch.get("rules")
    if rules is not None:
        book = rules.rulebook()
        guard = [r for r in book if r["type"] == "guardrail"]
        adapt = [r for r in book if r["type"] == "adaptive"]
        print(f"Guardrails (immutable): {len(guard)}  Adaptive: {len(adapt)}")
        # Agent proposes a legal, conservative rule -> validate -> activate.
        prop = rules.propose_rule(
            "skip_oversold_knife",
            {"metric": "rsi", "op": "lt", "value": 15, "action": "block"},
            "Avoid catching a falling knife on extreme oversold.",
            evidence={"backtest": "synthetic", "edge": 0.02}, author="agent",
        )
        print(f"Agent proposal : {prop}")
        print(f"  validate     : {rules.validate_rule('skip_oversold_knife')}")
        print(f"  activate     : {rules.activate_rule('skip_oversold_knife')}")
        # Meta-limit: an attempt to LOOSEN a guardrail must be rejected.
        bad = rules.propose_rule(
            "loosen_caps", {"metric": "position_pct", "op": "le", "value": 0.5, "action": "block"},
            "try to raise position cap", evidence={}, author="agent",
        )
        print(f"Illegal proposal rejected: {bad}")
        print(f"Audit chain intact: {__import__('ats.core.state', fromlist=['verify_audit_chain']).verify_audit_chain()}")

    await orch.stop()
    print("\nHARNESS OK")


if __name__ == "__main__":
    asyncio.run(main())
