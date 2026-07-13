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
    """Snapshot fundamentals for the factor sleeves' value/quality/size legs.

    Circuit-breaks after 3 consecutive vendor failures (a blocked/rate-limited
    Yahoo used to burn ~10s x 50 symbols of 401 retries per run) and falls back
    to the latest persisted ``Fundamental`` rows instead."""
    provider = build_fundamentals_provider()
    out: dict[str, dict] = {}
    consecutive = 0
    for sym in symbols:
        try:
            snap = provider.fetch(sym)
        except Exception:  # noqa: BLE001
            snap = None
        if snap is not None:
            out[sym] = snap.as_dict()
            consecutive = 0
        else:
            consecutive += 1
            if consecutive >= 3:
                print("  (fundamentals vendor unreachable - using stored ratios)")
                break

    # DB fallback for anything the vendor didn't supply this run.
    missing = [s for s in symbols if s not in out]
    if missing:
        from sqlalchemy import select

        from ats.core.db import session_scope
        from ats.core.models import Fundamental

        with session_scope() as s:
            for sym in missing:
                row = s.execute(
                    select(Fundamental).where(Fundamental.symbol == sym)
                    .order_by(Fundamental.as_of.desc()).limit(1)
                ).scalar_one_or_none()
                if row is not None:
                    out[sym] = {
                        "symbol": row.symbol, "pe": row.pe, "pb": row.pb,
                        "roe": row.roe, "debt_to_equity": row.debt_to_equity,
                        "profit_margin": row.profit_margin,
                        "dividend_yield": row.dividend_yield,
                        "market_cap": row.market_cap,
                    }
    return out


def _wire_fundamentals(universe_strategies, fundamentals: dict[str, dict]) -> None:
    for strat in universe_strategies:
        setter = getattr(strat, "set_fundamentals", None)
        if setter is not None:
            setter(lambda f=fundamentals: f)


def _years_from_period(period: str) -> int:
    try:
        return max(1, int("".join(c for c in period if c.isdigit()) or "1"))
    except ValueError:
        return 1


def _load_panel(offline: bool, period: str, limit: int, kite: bool = False) -> dict[str, pd.DataFrame]:
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
    if kite:
        # Authenticated NSE candles — reliable where yfinance is throttled.
        from ats.services.market_data.kite_history import (
            KiteNotReady, fetch_prices_batch_kite,
        )
        try:
            frames = fetch_prices_batch_kite(symbols, years=_years_from_period(period))
        except KiteNotReady as exc:
            print(f"  Kite not ready: {exc}")
            return {}
    else:
        frames = fetch_prices_batch(symbols, period=period)
    missing = [s for s in symbols if s not in frames]
    if missing:
        print(f"  ({len(missing)} symbols had no live data, skipped)")
    return frames


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="synthetic data (no network)")
    ap.add_argument("--kite", action="store_true", help="authenticated Kite NSE history (needs creds + token)")
    ap.add_argument("--period", default="3y", help="history window (e.g. 1y, 3y)")
    ap.add_argument("--limit", type=int, default=750, help="bars for the synthetic panel")
    ap.add_argument("--dsr", type=float, default=None, help="deflated-Sharpe bar (default 0.90)")
    ap.add_argument("--min-obs", type=int, default=30, help="min active observations")
    ap.add_argument("--step", type=int, default=1, help="per-symbol replay stride")
    ap.add_argument("--universe-step", type=int, default=5, help="universe replay stride")
    ap.add_argument("--walk-forward", action="store_true",
                    help="also report held-out out-of-sample Sharpe (E2) to flag decayed edges")
    ap.add_argument("--only", default=None,
                    help="comma-separated strategy ids to test in isolation, e.g. "
                         "'st_reversal,core_allocation' (iterate on E5 without the full 26-way run)")
    ap.add_argument("--n-trials", type=int, default=None,
                    help="pin the DSR multiple-testing penalty (default: #strategies in this run). "
                         "Use --n-trials 26 with --only to keep DSR comparable to the full-gate baseline")
    ap.add_argument("--apply", action="store_true", help="promote cleared shadows to paper")
    args = ap.parse_args()

    configure_logging("INFO")
    init_db()
    seed_all()
    settings = get_settings()
    dsr = args.dsr if args.dsr is not None else 0.90

    panel = _load_panel(args.offline, args.period, args.limit, kite=args.kite)
    src = "synthetic" if args.offline else "kite" if args.kite else "yfinance"
    print(f"Loaded history for {len(panel)} instruments (source={src})\n")

    # Live progress -> terminal AND a run log file, so the run is never a
    # silently-frozen terminal and you can read afterwards how each strategy did.
    run_log = Path(settings.metrics_dir)
    run_log.mkdir(parents=True, exist_ok=True)
    log_path = run_log / f"backtest_run_{date.today().isoformat()}.log"
    log_fh = log_path.open("w", encoding="utf-8")

    def emit_line(text: str) -> None:
        print(text, flush=True)              # terminal
        log_fh.write(text + "\n"); log_fh.flush()  # file

    def on_progress(ev: dict) -> None:
        if ev["phase"] == "start":
            emit_line(f"[{ev['i']:>2}/{ev['total']}] testing {ev['strategy']} ...")
        elif ev["phase"] == "done" and ev.get("result") is not None:
            emit_line("        " + ev["result"].plain_english())

    emit_line(f"Backtesting {len(panel)} instruments (source={src}, period={args.period}); "
              f"DSR bar {dsr}. This walks every strategy over the whole window - hang tight.\n")

    per_symbol_strategies = default_strategies()
    universe_strategies = default_universe_strategies()
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        per_symbol_strategies = [s for s in per_symbol_strategies if s.id in wanted]
        universe_strategies = [s for s in universe_strategies if s.id in wanted]
        found = {s.id for s in per_symbol_strategies} | {s.id for s in universe_strategies}
        missing = wanted - found
        if missing:
            emit_line(f"  (--only: unknown strategy id(s) skipped: {', '.join(sorted(missing))})")
        emit_line(f"  (--only: testing {len(found)} strateg(ies): {', '.join(sorted(found))}; "
                  f"DSR n_trials={args.n_trials or len(found)})")
    _wire_fundamentals(universe_strategies, _build_fundamentals(list(panel.keys())))
    report = run_gate(
        panel,
        per_symbol_strategies=per_symbol_strategies,
        universe_strategies=universe_strategies,
        dsr_threshold=dsr, min_obs=args.min_obs,   # costs: realistic Indian per-side model
        step=args.step, universe_step=args.universe_step,
        progress=on_progress, walk_forward=args.walk_forward,
        n_trials=args.n_trials,
    )
    summary = report.summary()
    print("\n" + summary)
    log_fh.write("\n" + summary + "\n"); log_fh.flush()
    log_fh.close()
    print(f"\n(Full run log saved to {log_path})")

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
