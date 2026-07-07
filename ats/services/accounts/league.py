"""The strategy league: segregated solo accounts + the benchmark account.

Every roster strategy trades its own signals in its own simulated bank
account (``solo_<id>``) through its own BrokerSim connection — no consensus,
no LLM, its own money. A ``benchmark`` account buys and holds NIFTYBEES from
day 1. The /league dashboard page compares them all: this is how "which
strategies earn their keep?" gets answered with evidence instead of defaults.

Solo discipline (the laws of physics every account obeys):
- long-only, cash-limited (BrokerSim + AccountLedger enforce overdrafts away)
- per-position cap: ``max_position_pct`` of the account's OWN equity
- per-order value cap (``max_trade_value``)
- daily-loss entry block: equity down ``daily_loss_limit_pct`` from the day's
  open → no new entries for that account until the next day (exits still pass)
- global kill switch respected; indices/commodity feeds never tradeable

The league is an experiment harness, not the main book: its accounts are
isolated by construction (per-account ledger + positions), so a runaway solo
strategy can lose at most its own Rs 1L of paper money.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from ats.core import state
from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.events import Topic
from ats.core.logging import get_logger
from ats.core.models import Fill, Instrument, Order, PnlDaily, Position
from ats.core.schemas import Stance
from ats.services.accounts.ledger import AccountLedger
from ats.services.execution.broker_sim import BrokerSim
from ats.services.execution.portfolio import snapshot
from ats.services.risk.guardrails import is_tradeable

log = get_logger("ats.league")

BENCHMARK_ACCOUNT = "benchmark"
# The main combined paper book, shown in the league for comparison. Until the
# SME/consensus paths are split into separate accounts (WS-3), this is the
# blended three-loop + SME book.
MAIN_ACCOUNT = "paper"


def solo_account(strategy_id: str) -> str:
    return f"solo_{strategy_id}"[:24]


def league_roster(settings=None) -> dict[str, str]:
    """strategy_id -> account name for the configured league roster."""
    settings = settings or get_settings()
    raw = (settings.league_strategies or "auto").strip()
    if raw.lower() == "auto":
        from ats.services.reference import STRATEGIES

        ids = [sid for sid, _n, _t, status in STRATEGIES
               if status == "paper" and sid != "vol_premium"]
    else:
        ids = [x.strip() for x in raw.split(",") if x.strip()]
    return {sid: solo_account(sid) for sid in ids}


class LeagueService:
    name = "league"

    def __init__(self) -> None:
        self._md = None
        self._broker: BrokerSim | None = None
        self._roster: dict[str, str] = {}   # strategy_id -> account
        self._itypes: dict[str, str] = {}
        self._entry_blocked: dict[str, str] = {}  # account -> ISO day blocked

    # --- lifecycle -----------------------------------------------------------
    async def start(self, ctx) -> None:
        settings = get_settings()
        if not settings.league_enabled:
            log.info("league_disabled")
            return
        self._md = ctx.orchestrator.get("market_data")
        self._broker = BrokerSim(price_fn=self.price_of)
        self._roster = league_roster(settings)
        with session_scope() as s:
            rows = s.execute(select(Instrument)).scalars().all()
            self._itypes = {r.symbol: r.instrument_type for r in rows}

        self._fund_accounts(settings)

        ctx.bus.subscribe(Topic.SIGNAL, self._on_signal)
        ctx.bus.subscribe(Topic.BAR, self._on_bar)
        ctx.scheduler.add_job(
            self.record_equity, "interval",
            seconds=max(60, settings.league_snapshot_interval_s),
            id="league_equity", max_instances=1, coalesce=True,
        )
        log.info(
            "league_started",
            extra={"accounts": len(self._roster) + 1,
                   "strategies": sorted(self._roster)},
        )

    def _fund_accounts(self, settings) -> None:
        """Fund each league account once with the same starting capital."""
        for account in [*self._roster.values(), BENCHMARK_ACCOUNT]:
            flag_key = f"league:funded:{account}"
            if state.get_kv(flag_key).get("funded"):
                continue
            AccountLedger(account).deposit(
                settings.league_capital, note="league initial funding"
            )
            state.set_kv(flag_key, {"funded": True,
                                    "amount": settings.league_capital})
            log.info("league_account_funded",
                     extra={"account": account, "amount": settings.league_capital})

    # --- price oracle ----------------------------------------------------------
    def price_of(self, symbol: str) -> float | None:
        if self._md is not None:
            px = self._md.latest_price(symbol)
            if px is not None:
                return px
        from ats.services.market_data.store import load_history

        hist = load_history(symbol, limit=1)
        if not hist.empty:
            return float(hist["close"].iloc[-1])
        return None

    # --- benchmark: buy-and-hold NIFTYBEES from day 1 ----------------------------
    async def _on_bar(self, evt) -> None:
        settings = get_settings()
        if evt.payload.get("symbol") != settings.league_benchmark_symbol:
            return
        if state.get_kv("league:benchmark_seeded").get("done"):
            return
        self._seed_benchmark(settings)

    def _seed_benchmark(self, settings) -> dict:
        symbol = settings.league_benchmark_symbol
        price = self.price_of(symbol)
        if not price or price <= 0 or self._broker is None:
            return {"status": "no_price"}
        available = self._broker.margins(BENCHMARK_ACCOUNT)["available"]
        # Leave room for the reserve fee buffer + charges so the order fills.
        qty = int((available / 1.006) // price)
        if qty <= 0:
            return {"status": "no_cash"}
        res = self._broker.place_order(BENCHMARK_ACCOUNT, symbol, "BUY", qty)
        if res.get("status") == "FILLED":
            state.set_kv("league:benchmark_seeded",
                         {"done": True, "qty": qty, "price": res["fill_price"]})
            log.info("benchmark_seeded", extra={"qty": qty, "price": res["fill_price"]})
        return res

    # --- solo trading -------------------------------------------------------------
    async def _on_signal(self, evt) -> None:
        self.handle_signal(evt.payload)

    def handle_signal(self, payload: dict) -> dict:
        """One strategy's signal drives (only) its own solo account."""
        if self._broker is None:
            return {"status": "not_started"}
        strategy = payload.get("strategy")
        symbol = payload.get("symbol")
        account = self._roster.get(strategy or "")
        if not account or not symbol:
            return {"status": "not_in_league"}
        if symbol.startswith("^") or not is_tradeable(self._itypes.get(symbol)):
            return {"status": "not_tradeable"}
        if state.is_killed():
            return {"status": "killed"}

        try:
            direction = Stance(payload.get("stance", "neutral")).direction
        except ValueError:
            direction = 0
        conviction = float(payload.get("conviction", 0.0) or 0.0)

        held = {p["symbol"]: p["qty"] for p in self._broker.positions(account)}

        if direction < 0 and held.get(symbol, 0) > 0:
            # Exits always pass — risk-reducing by definition.
            res = self._broker.place_order(account, symbol, "SELL", held[symbol])
            log.info("league_exit", extra={"account": account, "symbol": symbol,
                                           "status": res.get("status")})
            return res

        if direction <= 0 or held.get(symbol, 0) > 0:
            return {"status": "no_action"}

        # New entry: per-account guardrails, scaled to this account's equity.
        settings = get_settings()
        if self._daily_loss_blocked(account, settings):
            return {"status": "entry_blocked_daily_loss"}
        price = self.price_of(symbol)
        if not price or price <= 0:
            return {"status": "no_price"}
        snap = snapshot(account, self.price_of)
        cap_value = settings.max_position_pct * snap["equity"]
        available = self._broker.margins(account)["available"]
        budget = min(
            cap_value * max(0.25, min(1.0, conviction)),
            available / 1.006,  # room for the reserve fee buffer
            settings.max_trade_value,
        )
        qty = int(budget // price)
        if qty <= 0:
            return {"status": "too_small"}
        res = self._broker.place_order(account, symbol, "BUY", qty)
        log.info("league_entry", extra={"account": account, "symbol": symbol,
                                        "qty": qty, "status": res.get("status")})
        return res

    def _daily_loss_blocked(self, account: str, settings) -> bool:
        """Per-account daily-loss guardrail: entries blocked for the rest of
        the day once equity drops the configured fraction from the day's open.
        Exits are never blocked."""
        today = date.today().isoformat()
        if self._entry_blocked.get(account) == today:
            return True
        key = f"league:day_open:{account}"
        stored = state.get_kv(key)
        equity = snapshot(account, self.price_of)["equity"]
        if stored.get("day") != today:
            state.set_kv(key, {"day": today, "equity": equity})
            return False
        day_open = float(stored.get("equity", 0.0))
        if day_open > 0 and equity <= day_open * (1.0 - settings.daily_loss_limit_pct):
            self._entry_blocked[account] = today
            log.warning("league_daily_loss_block",
                        extra={"account": account, "day_open": day_open,
                               "equity": equity})
            return True
        return False

    # --- equity snapshots (PnlDaily per account) -----------------------------------
    def record_equity(self) -> dict:
        settings = get_settings()
        out: dict[str, float] = {}
        today = date.today()
        for account in self.accounts():
            snap = snapshot(account, self.price_of)
            equity = snap["equity"]
            peak_key = f"league:peak:{account}"
            peak = max(float(state.get_kv(peak_key, {"peak": 0.0}).get("peak", 0.0)),
                       equity)
            state.set_kv(peak_key, {"peak": peak})
            drawdown = (equity / peak - 1.0) if peak > 0 else 0.0
            _trades, fees = self._trade_stats(account)
            net = round(equity - settings.league_capital, 2)
            with session_scope() as s:
                row = s.execute(
                    select(PnlDaily).where(
                        PnlDaily.account == account, PnlDaily.day == today
                    )
                ).scalar_one_or_none()
                if row is None:
                    row = PnlDaily(account=account, day=today)
                    s.add(row)
                row.equity = equity
                row.net = net
                row.fees = round(fees, 2)
                row.gross = round(net + fees, 2)
                row.drawdown = round(drawdown, 4)
            out[account] = equity
        return out

    # --- read side (the /league page) ------------------------------------------------
    def accounts(self) -> list[str]:
        return [*sorted(self._roster.values()), BENCHMARK_ACCOUNT]

    def league_table(self) -> dict:
        """Comparable stats per account: the league standings."""
        settings = get_settings()
        by_account = {acct: sid for sid, acct in self._roster.items()}
        rows: list[dict] = []
        entries = [
            (MAIN_ACCOUNT, "main (combined book)", settings.paper_starting_capital),
            (BENCHMARK_ACCOUNT, "benchmark (NIFTYBEES buy & hold)",
             settings.league_capital),
        ] + [
            (acct, by_account[acct], settings.league_capital)
            for acct in sorted(self._roster.values())
        ]
        for account, label, capital in entries:
            snap = snapshot(account, self.price_of)
            equity = snap["equity"]
            series = self._equity_series(account)
            trades, fees = self._trade_stats(account)
            rows.append({
                "account": account,
                "label": label,
                "capital": capital,
                "equity": round(equity, 2),
                "return_pct": round(100.0 * (equity / capital - 1.0), 2)
                if capital else 0.0,
                "sharpe": _sharpe(series),
                "max_dd_pct": _max_drawdown_pct(series),
                "trades": trades,
                "fees": round(fees, 2),
                "positions": len(snap["positions"]),
                "realized_pnl": snap["realized_pnl"],
                "unrealized_pnl": snap["unrealized_pnl"],
            })
        # Standings: benchmark stays visible wherever it lands.
        rows.sort(key=lambda r: -r["return_pct"])
        return {
            "table": rows,
            "curves": self.equity_curves(),
            "capital": settings.league_capital,
        }

    def equity_curves(self) -> dict[str, list[dict]]:
        """Per-account daily equity normalized to 100 at inception."""
        out: dict[str, list[dict]] = {}
        with session_scope() as s:
            rows = s.execute(
                select(PnlDaily)
                .where(PnlDaily.account.in_([MAIN_ACCOUNT, *self.accounts()]))
                .order_by(PnlDaily.day)
            ).scalars().all()
        for r in rows:
            series = out.setdefault(r.account, [])
            base = series[0]["equity"] if series else r.equity
            norm = 100.0 * r.equity / base if base else 100.0
            series.append({"day": r.day.isoformat(), "equity": r.equity,
                           "norm": round(norm, 2)})
        return out

    def account_detail(self, account: str) -> dict:
        """One account's book: positions, passbook, and recent orders."""
        snap = snapshot(account, self.price_of)
        ledger = AccountLedger(account)
        with session_scope() as s:
            orders = s.execute(
                select(Order, Fill)
                .outerjoin(Fill, Fill.order_id == Order.id)
                .where(Order.account == account)
                .order_by(Order.id.desc())
                .limit(100)
            ).all()
            order_rows = [
                {
                    "id": o.id, "ts": o.ts.isoformat(), "symbol": o.symbol,
                    "side": o.side, "qty": o.qty, "status": o.status,
                    "fill_price": f.price if f else None,
                    "fees": f.fees if f else None,
                }
                for o, f in orders
            ]
        by_account = {acct: sid for sid, acct in self._roster.items()}
        return {
            "account": account,
            "strategy": by_account.get(account),
            "balance": ledger.balance().as_dict(),
            "snapshot": snap,
            "passbook": ledger.statement(limit=200),
            "orders": order_rows,
        }

    # --- internals ---------------------------------------------------------------
    @staticmethod
    def _equity_series(account: str) -> list[float]:
        with session_scope() as s:
            rows = s.execute(
                select(PnlDaily.equity)
                .where(PnlDaily.account == account)
                .order_by(PnlDaily.day)
            ).scalars().all()
        return [float(x) for x in rows]

    @staticmethod
    def _trade_stats(account: str) -> tuple[int, float]:
        with session_scope() as s:
            n, fees = s.execute(
                select(func.count(Fill.id), func.coalesce(func.sum(Fill.fees), 0.0))
                .join(Order, Fill.order_id == Order.id)
                .where(Order.account == account)
            ).one()
        return int(n or 0), float(fees or 0.0)

    @staticmethod
    def realized_by_account(account: str) -> float:
        with session_scope() as s:
            total = s.execute(
                select(func.coalesce(func.sum(Position.realized_pnl), 0.0))
                .where(Position.account == account)
            ).scalar_one()
        return float(total or 0.0)


def _sharpe(equity: list[float]) -> float | None:
    """Annualized Sharpe from a daily equity series (needs >= 4 points)."""
    if len(equity) < 4:
        return None
    rets = [equity[i] / equity[i - 1] - 1.0 for i in range(1, len(equity))
            if equity[i - 1] > 0]
    if len(rets) < 3:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    std = var ** 0.5
    if std == 0:
        return None
    return round(mean / std * (252 ** 0.5), 2)


def _max_drawdown_pct(equity: list[float]) -> float | None:
    if len(equity) < 2:
        return None
    peak = equity[0]
    worst = 0.0
    for x in equity:
        peak = max(peak, x)
        if peak > 0:
            worst = min(worst, x / peak - 1.0)
    return round(100.0 * worst, 2)
