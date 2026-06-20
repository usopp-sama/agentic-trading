"""Bootstrap SME track records from real historical performance.

This is the honest version of "training the SMEs". The market/quant SMEs are
grounded in deterministic signals (trend, mean-reversion, volume breakout), so
we can measure how those signals would actually have done on real price
history and seed each SME's track record (hit-rate, Brier, vote weight,
promote/demote status) accordingly.

The result: when the live server starts, these SMEs already carry an
evidence-based vote weight instead of a cold-start 1.0, and the same Phase-8
learning loop keeps updating them from live fills going forward.

Run:
    python scripts/train_smes.py                 # 2y history, real data
    python scripts/train_smes.py --period 5y     # more history
    python scripts/train_smes.py --horizon 5     # bars ahead to score against
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ats.core.db import init_db, session_scope  # noqa: E402
from ats.core.logging import configure_logging, get_logger
from ats.core.models import Instrument, SmeTrackRecord
from ats.core.schemas import Stance
from ats.services.bootstrap import seed_all
from ats.services.learning.scoring import promotion_decision, update_record
from ats.services.strategies.library import default_strategies
from quant.data.fetch import fetch_prices_batch, synthetic_prices

log = get_logger("ats.train")

# Each strategy's historical edge calibrates one or more grounded SMEs.
STRATEGY_TO_SME = {
    "sma_crossover": ["trend_follower", "technical_analyst"],
    "mean_reversion": ["mean_reversion_analyst"],
    "volume_breakout": ["volume_breakout_analyst"],
}


def _sign(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


def _direction(stance: Stance) -> int:
    return {Stance.BUY: 1, Stance.SELL: -1}.get(stance, 0)


def walk_forward(strategy, df, horizon: int, step: int) -> list[tuple[bool, float, float]]:
    """Replay a strategy bar-by-bar; return (correct, conviction, signed_return)."""
    out: list[tuple[bool, float, float]] = []
    closes = df["close"].to_numpy()
    n = len(df)
    start = max(strategy.min_bars, 2)
    for t in range(start, n - horizon, step):
        sig = strategy.evaluate("X", df.iloc[: t + 1])
        if sig is None:
            continue
        d = _direction(sig.stance)
        if d == 0 or sig.conviction <= 0:
            continue
        fwd = (closes[t + horizon] - closes[t]) / closes[t]
        if fwd == 0:
            continue
        correct = _sign(d) == _sign(fwd)
        out.append((correct, float(sig.conviction), d * float(fwd)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default="2y")
    ap.add_argument("--horizon", type=int, default=5, help="bars ahead to score against")
    ap.add_argument("--step", type=int, default=2, help="stride between samples (reduce overlap)")
    ap.add_argument("--offline", action="store_true", help="use synthetic data (no network)")
    args = ap.parse_args()

    configure_logging("INFO")
    init_db()
    seed_all()

    with session_scope() as s:
        symbols = [
            r.symbol for r in s.query(Instrument).filter(
                Instrument.active.is_(True), Instrument.instrument_type != "INDEX"
            ).all()
        ]
    print(f"Training on {len(symbols)} instruments | period={args.period} horizon={args.horizon}")

    if args.offline:
        frames = {sym: synthetic_prices(n=500, seed=abs(hash(sym)) % 10000) for sym in symbols}
    else:
        frames = fetch_prices_batch(symbols, period=args.period)
        missing = [s for s in symbols if s not in frames]
        if missing:
            print(f"  ({len(missing)} symbols had no live data, skipped)")
    print(f"Loaded history for {len(frames)} instruments\n")

    strategies = {st.id: st for st in default_strategies()}
    # Accumulate per-SME running stats across all symbols + mapped strategies.
    acc: dict[str, dict] = {}

    def record_for(sme: str) -> dict:
        return acc.setdefault(sme, {"n": 0, "wins": 0, "brier": 0.25, "pnl_contrib": 0.0,
                                    "hit_rate": 0.0, "vote_weight": 1.0})

    for strat_id, strategy in strategies.items():
        smes = STRATEGY_TO_SME.get(strat_id, [])
        if not smes:
            continue
        for sym, df in frames.items():
            if df is None or len(df) < strategy.min_bars + args.horizon + 2:
                continue
            for correct, conviction, signed_ret in walk_forward(strategy, df, args.horizon, args.step):
                for sme in smes:
                    r = record_for(sme)
                    upd = update_record(
                        n=r["n"], wins=r["wins"], brier_sum=r["brier"],
                        pnl_contrib=r["pnl_contrib"], correct=correct,
                        conviction=conviction, contribution_return=signed_ret,
                    )
                    r.update(upd)

    # Persist as track records with promotion status.
    print(f"{'SME':24s} {'n':>5s} {'hit':>6s} {'brier':>6s} {'vote':>6s}  status")
    print("-" * 60)
    with session_scope() as s:
        for sme, r in sorted(acc.items(), key=lambda kv: kv[1]["vote_weight"], reverse=True):
            status, promoted = promotion_decision(r["n"], r["hit_rate"], "shadow")
            tr = s.get(SmeTrackRecord, sme) or SmeTrackRecord(sme=sme)
            tr.n = r["n"]; tr.wins = r["wins"]; tr.hit_rate = r["hit_rate"]
            tr.brier = r["brier"]; tr.pnl_contrib = r["pnl_contrib"]
            tr.vote_weight = r["vote_weight"]; tr.status = status; tr.promoted_weight = promoted
            s.merge(tr)
            print(f"{sme:24s} {r['n']:5d} {r['hit_rate']:6.2f} {r['brier']:6.2f} "
                  f"{r['vote_weight']:6.2f}  {status}")
    print("\nTrack records seeded. The live server will now start these SMEs with "
          "evidence-based weights and keep learning from real fills.")


if __name__ == "__main__":
    main()
