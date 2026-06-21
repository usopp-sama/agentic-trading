"""Single-command walk-forward backtest gate across every strategy.

Replays all per-symbol and universe strategies over a price panel, scores each
with annualized Sharpe + the deflated Sharpe ratio (multiple-testing aware) +
Monte Carlo drawdowns, and reports which shadow strategies clear the promotion
bar. With ``--apply`` it flips the cleared strategies from ``shadow`` to
``paper`` in the DB (so they start taking capital); without it the run is a
read-only dry run.

Run:
    python scripts/run_backtests.py --offline           # synthetic, dry run
    python scripts/run_backtests.py --period 3y          # real yfinance history
    python scripts/run_backtests.py --apply              # promote cleared shadows
    python scripts/run_backtests.py --dsr 0.95 --min-obs 60
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from ats.core.config import get_settings  # noqa: E402
from ats.core.db import init_db, session_scope  # noqa: E402
from ats.core.logging import configure_logging, get_logger  # noqa: E402
from ats.core.models import Instrument, Strategy as StrategyRow  # noqa: E402
from ats.services.bootstrap import seed_all  # noqa: E402
from ats.services.fundamentals.providers import build_fundamentals_provider  # noqa: E402
from ats.services.strategies.backtest import run_gate  # noqa: E402
from ats.services.strategies.library import (  # noqa: E402
    default_strategies,
    default_universe_strategies,
)
from quant.data.fetch import fetch_prices_batch, synthetic_prices  # noqa: E402

log = get_logger("ats.backtest_gate")


def _build_fundamentals(symbols: list[str]) -> dict[str, dict]:
    """Snapshot fundamentals for the factor sleeves' value/quality/size legs."""
    provider = build_fundamentals_provider()
    out: dict[str, dict] = {}
    for sym in symbols:
        try:
            snap = provider.fetch(sym)
        except Exception:  # noqa: BLE001
            snap = None
        if snap is not None:
            out[sym] = snap.as_dict()
    return out


def _wire_fundamentals(universe_strategies, fundamentals: dict[str, dict]) -> None:
    for strat in universe_strategies:
        setter = getattr(strat, "set_fundamentals", None)
        if setter is not None:
            setter(lambda f=fundamentals: f)


def _load_panel(offline: bool, period: str, limit: int) -> dict[str, pd.DataFrame]:
    with session_scope() as s:
        symbols = [r.symbol for r in s.query(Instrument).filter(
            Instrument.active.is_(True)).all()]
    if offline:
        # Deterministic per-symbol GBM so the run is reproducible offline.
        return {
            sym: synthetic_prices(n=limit, seed=abs(hash(sym)) % 10_000,
                                  annual_drift=0.10, annual_vol=0.22)
            for sym in symbols
        }
    frames = fetch_prices_batch(symbols, period=period)
    missing = [s for s in symbols if s not in frames]
    if missing:
        print(f"  ({len(missing)} symbols had no live data, skipped)")
    return frames


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="synthetic data (no network)")
    ap.add_argument("--period", default="3y", help="yfinance history window")
    ap.add_argument("--limit", type=int, default=750, help="bars for the synthetic panel")
    ap.add_argument("--dsr", type=float, default=None, help="deflated-Sharpe bar (default 0.90)")
    ap.add_argument("--min-obs", type=int, default=30, help="min active observations")
    ap.add_argument("--step", type=int, default=1, help="per-symbol replay stride")
    ap.add_argument("--universe-step", type=int, default=5, help="universe replay stride")
    ap.add_argument("--apply", action="store_true", help="promote cleared shadows to paper")
    args = ap.parse_args()

    configure_logging("INFO")
    init_db()
    seed_all()
    settings = get_settings()
    dsr = args.dsr if args.dsr is not None else 0.90

    panel = _load_panel(args.offline, args.period, args.limit)
    print(f"Loaded history for {len(panel)} instruments "
          f"(source={'synthetic' if args.offline else 'yfinance'})\n")

    universe_strategies = default_universe_strategies()
    _wire_fundamentals(universe_strategies, _build_fundamentals(list(panel.keys())))
    report = run_gate(
        panel,
        per_symbol_strategies=default_strategies(),
        universe_strategies=universe_strategies,
        dsr_threshold=dsr, min_obs=args.min_obs, fee_bps=5.0,
        step=args.step, universe_step=args.universe_step,
    )
    print(report.summary())

    # Persist the run for the research record.
    out_dir = Path(settings.metrics_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [vars(r) for r in report.results]
    pd.DataFrame(rows).to_parquet(out_dir / f"backtest_gate_{date.today().isoformat()}.parquet",
                                  index=False)
    (out_dir / "backtest_gate_latest.json").write_text(
        json.dumps({"day": date.today().isoformat(), "dsr_threshold": dsr,
                    "results": rows}, indent=2))

    promote = set(report.promote_ids())
    print(f"\n{len(promote)} strategy(ies) cleared the gate: {sorted(promote)}")
    if not args.apply:
        print("Dry run (no DB changes). Re-run with --apply to promote shadow->paper.")
        return

    changed = []
    with session_scope() as s:
        for sid in promote:
            row = s.get(StrategyRow, sid)
            if row is not None and row.status == "shadow":
                row.status = "paper"
                changed.append(sid)
    print(f"Promoted shadow->paper: {sorted(changed)}")
    log.info("backtest_gate_applied", extra={"promoted": changed, "dsr_threshold": dsr})


if __name__ == "__main__":
    main()
