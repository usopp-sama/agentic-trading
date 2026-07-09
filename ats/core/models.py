"""SQLAlchemy ORM models for the core data model.

Uses SQLite by default for zero-setup local dev; the same models run on
Postgres/TimescaleDB by changing ``ATS_DB_URL``. Time-series tables
(``ohlcv``) map cleanly onto TimescaleDB hypertables later.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Instrument(Base):
    __tablename__ = "instruments"
    symbol: Mapped[str] = mapped_column(String(64), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(16), default="NSE")
    name: Mapped[str] = mapped_column(String(256), default="")
    sector: Mapped[str] = mapped_column(String(64), default="Unknown")
    instrument_type: Mapped[str] = mapped_column(String(16), default="EQ")  # EQ/ETF/INDEX/COMMODITY
    kite_token: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    tick_size: Mapped[float] = mapped_column(Float, default=0.05)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Ohlcv(Base):
    __tablename__ = "ohlcv"
    __table_args__ = (UniqueConstraint("symbol", "ts", "interval", name="uq_ohlcv"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    interval: Mapped[str] = mapped_column(String(8), default="1d")
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)


class NewsItem(Base):
    __tablename__ = "news_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=_utcnow)
    source: Mapped[str] = mapped_column(String(128), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    tickers: Mapped[list] = mapped_column(JSON, default=list)
    event_type: Mapped[str] = mapped_column(String(48), default="general")
    raw_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=_utcnow)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    news_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str] = mapped_column(String(48), default="vader")
    label: Mapped[str] = mapped_column(String(16), default="neutral")
    score: Mapped[float] = mapped_column(Float, default=0.0)  # -1..1


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=_utcnow)
    strategy: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    stance: Mapped[str] = mapped_column(String(16), default="neutral")
    conviction: Mapped[float] = mapped_column(Float, default=0.0)
    features: Mapped[dict] = mapped_column(JSON, default=dict)


class SmeOpinion(Base):
    __tablename__ = "sme_opinions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=_utcnow)
    sme: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    stance: Mapped[str] = mapped_column(String(16), default="neutral")
    conviction: Mapped[float] = mapped_column(Float, default=0.0)
    horizon: Mapped[str] = mapped_column(String(16), default="swing")
    rationale: Mapped[str] = mapped_column(Text, default="")
    key_risks: Mapped[list] = mapped_column(JSON, default=list)
    suggested_size: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class LlmCall(Base):
    """One real LLM provider call (prompt + response), for the dashboard's
    LLM history. Persisted so the question log survives restarts; old rows are
    trimmed by the recorder to keep the SQLite file bounded."""

    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=_utcnow)
    kind: Mapped[str] = mapped_column(String(16), default="opinion", index=True)  # opinion|chat|health
    provider: Mapped[str] = mapped_column(String(24), default="")
    model: Mapped[str] = mapped_column(String(64), default="", index=True)
    persona: Mapped[str] = mapped_column(String(64), default="", index=True)
    symbol: Mapped[str] = mapped_column(String(64), default="", index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    response: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    error: Mapped[str] = mapped_column(Text, default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=_utcnow)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(8))  # BUY/SELL/HOLD
    target_qty: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(16), default="PAPER")
    rationale: Mapped[str] = mapped_column(Text, default="")
    contributors: Mapped[dict] = mapped_column(JSON, default=dict)
    rules_applied: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="proposed", index=True)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[int | None] = mapped_column(ForeignKey("decisions.id"), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=_utcnow)
    account: Mapped[str] = mapped_column(String(24), default="paper", index=True)
    broker: Mapped[str] = mapped_column(String(24), default="paper")
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(4))  # BUY/SELL
    qty: Mapped[int] = mapped_column(Integer)
    order_type: Mapped[str] = mapped_column(String(12), default="MARKET")
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="NEW", index=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Fill(Base):
    __tablename__ = "fills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    qty: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, default=0.0)


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("account", "symbol", name="uq_position"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account: Mapped[str] = mapped_column(String(24), default="paper", index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    qty: Mapped[int] = mapped_column(Integer, default=0)
    avg_price: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)


class PnlDaily(Base):
    __tablename__ = "pnl_daily"
    __table_args__ = (UniqueConstraint("account", "day", name="uq_pnl_daily"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account: Mapped[str] = mapped_column(String(24), default="paper", index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    gross: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    net: Mapped[float] = mapped_column(Float, default=0.0)
    equity: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown: Mapped[float] = mapped_column(Float, default=0.0)


class LedgerEntry(Base):
    """One journaled money movement on a simulated bank account.

    The 'passbook': every deposit, withdrawal, reservation (order staged),
    release (order cancelled/rejected) and settlement (fill) is one row, with
    the running balance after the entry. Append-only; never updated.
    """

    __tablename__ = "ledger_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=_utcnow)
    account: Mapped[str] = mapped_column(String(24), index=True)
    # DEPOSIT / WITHDRAW / RESERVE / RELEASE / SETTLE_DEBIT / SETTLE_CREDIT
    kind: Mapped[str] = mapped_column(String(16), index=True)
    amount: Mapped[float] = mapped_column(Float)  # signed effect on cash (0 for RESERVE/RELEASE)
    reserved_delta: Mapped[float] = mapped_column(Float, default=0.0)  # signed effect on holds
    ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # order/decision ref
    note: Mapped[str] = mapped_column(String(256), default="")
    cash_after: Mapped[float] = mapped_column(Float)
    reserved_after: Mapped[float] = mapped_column(Float)


class Strategy(Base):
    __tablename__ = "strategies"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    type: Mapped[str] = mapped_column(String(32), default="quant")
    status: Mapped[str] = mapped_column(String(16), default="shadow")  # shadow/paper/live/paused
    allocation_pct: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class Fundamental(Base):
    """Latest fundamental ratios per instrument (Indian market, NSE symbols).

    One row per (symbol, as_of) refresh. Ratios feed the value/quality
    factors, the screener, and agent context. ``None`` means the source
    did not report the field — consumers must treat missing as missing,
    never as zero.
    """

    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("symbol", "as_of", name="uq_fundamental"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb: Mapped[float | None] = mapped_column(Float, nullable=True)
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(24), default="synthetic")


class SleevePnl(Base):
    """Daily virtual P&L per strategy sleeve (attribution + decay detection).

    Tracks what each strategy WOULD have earned trading its own signals
    in an equal-weight virtual book, independent of what the blended real
    book did. This is how per-strategy performance is attributed and how
    decaying strategies are caught (roadmap Parts 8.2/8.5).
    """

    __tablename__ = "sleeve_pnl"
    __table_args__ = (UniqueConstraint("strategy", "day", name="uq_sleeve_pnl"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    ret: Mapped[float] = mapped_column(Float, default=0.0)     # daily return
    equity: Mapped[float] = mapped_column(Float, default=1.0)  # cumulative growth of 1.0
    holdings: Mapped[int] = mapped_column(Integer, default=0)  # names held at close


class SmeTrackRecord(Base):
    __tablename__ = "sme_track_record"
    sme: Mapped[str] = mapped_column(String(64), primary_key=True)
    n: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    hit_rate: Mapped[float] = mapped_column(Float, default=0.0)
    brier: Mapped[float] = mapped_column(Float, default=0.25)
    pnl_contrib: Mapped[float] = mapped_column(Float, default=0.0)
    vote_weight: Mapped[float] = mapped_column(Float, default=1.0)
    promoted_weight: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="shadow")


class Attribution(Base):
    """Links a fill back to the SMEs/contributors that drove the decision."""

    __tablename__ = "attributions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    decision_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(4))
    entry_price: Mapped[float] = mapped_column(Float)
    contributors: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    forward_return: Mapped[float] = mapped_column(Float, default=0.0)


class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), default="global")
    rule_type: Mapped[str] = mapped_column(String(16), default="adaptive")  # guardrail/adaptive
    expression: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    version: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    change: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    author: Mapped[str] = mapped_column(String(32), default="agent")  # agent/human
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), index=True)
    channel: Mapped[str] = mapped_column(String(24), default="dashboard")
    requested_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    responded_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    actor: Mapped[str] = mapped_column(String(64), default="")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    action: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(64), default="")
    prev_hash: Mapped[str] = mapped_column(String(64), default="")


class ExpertThread(Base):
    """A conversation with a single expert (an SME id, or 'cio').

    Threads give the interactive console memory: each turn is persisted and the
    most recent turns are replayed to the model so the expert remembers the
    discussion. Optionally pinned to a symbol so grounding is auto-assembled.
    """

    __tablename__ = "expert_threads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class ExpertMessage(Base):
    __tablename__ = "expert_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("expert_threads.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    role: Mapped[str] = mapped_column(String(16), default="user")  # user/assistant
    content: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # citations, grounding, model


class PositionThesis(Base):
    """A living investment thesis for an (expert, symbol).

    Unlike an immutable opinion row, a thesis is revisited as new evidence
    arrives: the expert can reaffirm, upgrade, downgrade, or exit, and each
    change is recorded as a linked revision. This is what lets an expert
    "alter past decisions" with an auditable trail.
    """

    __tablename__ = "position_theses"
    __table_args__ = (UniqueConstraint("expert", "symbol", name="uq_thesis"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    stance: Mapped[str] = mapped_column(String(16), default="neutral")
    conviction: Mapped[float] = mapped_column(Float, default=0.0)
    thesis: Mapped[str] = mapped_column(Text, default="")       # the current view
    invalidation: Mapped[str] = mapped_column(Text, default="")  # what would flip it
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)  # open/closed
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)


class ThesisRevision(Base):
    __tablename__ = "thesis_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thesis_id: Mapped[int] = mapped_column(ForeignKey("position_theses.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    prev_stance: Mapped[str] = mapped_column(String(16), default="neutral")
    new_stance: Mapped[str] = mapped_column(String(16), default="neutral")
    prev_conviction: Mapped[float] = mapped_column(Float, default=0.0)
    new_conviction: Mapped[float] = mapped_column(Float, default=0.0)
    action: Mapped[str] = mapped_column(String(16), default="reaffirm")  # reaffirm/upgrade/downgrade/flip/exit
    trigger: Mapped[str] = mapped_column(Text, default="")  # what new info prompted this
    rationale: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(32), default="expert")  # expert/human


class KnowledgeDirective(Base):
    """A self-evolving, expert-authored knowledge rule (SMX-style directive).

    Distinct from ``Rule`` (which governs RISK/sizing behaviour): a directive is
    *context only* — durable domain guidance an expert learns and writes back
    ("remember/learn/forget"), retrieved into future reasoning so the expert
    gets sharper over time. Directives NEVER change risk limits or order sizing;
    that path stays behind the immutable guardrails + human approval.

    Indexed into the vector store at reliability 100 so authored rules outrank
    generic prose during retrieval. Organised L0-L4 (foundational -> edge case).
    """

    __tablename__ = "knowledge_directives"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stable_id: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    expert: Mapped[str] = mapped_column(String(64), default="", index=True)  # owning family/sme or 'human'
    scope: Mapped[str] = mapped_column(String(16), default="global")  # global/symbol/sector
    symbol: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    family: Mapped[str | None] = mapped_column(String(16), nullable=True)  # A/B/C/RISK or None=all
    level: Mapped[str] = mapped_column(String(4), default="L2")  # L0..L4
    title: Mapped[str] = mapped_column(String(256), default="")
    rule: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(48), default="operational")
    reliability: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)  # active/retired
    author: Mapped[str] = mapped_column(String(32), default="human")  # expert/human
    source_thread: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class Hypothesis(Base):
    """One research hypothesis in the slow-loop registry (plan §3.1).

    The backbone of the research factory: every trading idea — agent-proposed
    or human — lives here with its proposer, evidence, exact rule, and gate
    result. Nothing trades that did not walk this lifecycle:

        PROPOSED → SPECIFIED → BACKTESTED → REJECTED | SHADOW → PAPER → LIVE

    Agents are scored by hypothesis survival rate, not per-trade attribution.
    """

    __tablename__ = "hypotheses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    updated_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    title: Mapped[str] = mapped_column(String(256))
    agent: Mapped[str] = mapped_column(String(64), index=True)  # proposer (role id or "human")
    thesis: Mapped[str] = mapped_column(Text, default="")       # the idea, plain words
    evidence: Mapped[str] = mapped_column(Text, default="")     # sources/citations
    rule: Mapped[str] = mapped_column(Text, default="")         # exact backtestable spec
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    universe: Mapped[list] = mapped_column(JSON, default=list)
    stage: Mapped[str] = mapped_column(String(16), default="PROPOSED", index=True)
    backtest: Mapped[dict] = mapped_column(JSON, default=dict)  # walk-forward gate result
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class HypothesisEvent(Base):
    """Audit trail of hypothesis stage transitions (who moved it, and why)."""

    __tablename__ = "hypothesis_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hypothesis_id: Mapped[int] = mapped_column(ForeignKey("hypotheses.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    from_stage: Mapped[str] = mapped_column(String(16), default="")
    to_stage: Mapped[str] = mapped_column(String(16), default="")
    actor: Mapped[str] = mapped_column(String(64), default="system")
    note: Mapped[str] = mapped_column(Text, default="")


class ResearchNote(Base):
    """Output of a scheduled research-role pass (macro/fundamentals/risk/…).

    Commentary and flags only — notes never touch orders. The strategy
    researcher's outputs land in ``hypotheses`` instead.
    """

    __tablename__ = "research_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    role: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # risk_flags, parse info, model


class AllocationRecommendation(Base):
    """A monthly committee allocation recommendation awaiting human approval.

    Tilts are bounded (±10% by config) and only nudge sleeve weights after
    explicit approval on the dashboard; guardrails are never touched.
    """

    __tablename__ = "allocation_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    tilts: Mapped[dict] = mapped_column(JSON, default=dict)  # strategy_id -> tilt
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    actor: Mapped[str] = mapped_column(String(64), default="")
    responded_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FlowDaily(Base):
    """One day of public flow data per symbol (delivery % + bulk deals).

    Inputs to the pump-signature veto (hypothesis #1) and, later, the
    institutional-flow hypothesis (#2). Collected nightly from free NSE
    archives; missing days simply stay absent (the signature degrades to
    delivery-unconfirmed rather than guessing).
    """

    __tablename__ = "flows_daily"
    __table_args__ = (UniqueConstraint("symbol", "day", name="uq_flow_daily"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    delivery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    bulk_buy_qty: Mapped[float] = mapped_column(Float, default=0.0)
    bulk_sell_qty: Mapped[float] = mapped_column(Float, default=0.0)
    deals: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="nse")


class FinancialStatements(Base):
    """Parsed financial-statement lines per instrument (annual or quarterly).

    The data unlock for Piotroski/Altman/DCF (``quant.analysis.quality`` and
    the fair-value surface). One row per (symbol, period, as_of). Every metric
    is nullable — a source that doesn't report a line leaves it ``None`` and
    the consumer treats missing as missing (a missing Piotroski input is a
    *failed* check, never a free point). Fed by the yfinance provider or a
    manual/paid CSV export through the same ``source`` field.
    """

    __tablename__ = "financial_statements"
    __table_args__ = (
        UniqueConstraint("symbol", "period", "as_of", name="uq_financial_stmt"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    period: Mapped[str] = mapped_column(String(16), default="annual")  # annual/quarterly
    as_of: Mapped[date] = mapped_column(Date, index=True)
    # income statement
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    ebit: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True)  # decimal
    tax_rate: Mapped[float | None] = mapped_column(Float, nullable=True)      # decimal
    # cash flow
    cfo: Mapped[float | None] = mapped_column(Float, nullable=True)           # operating CF
    capex: Mapped[float | None] = mapped_column(Float, nullable=True)         # positive magnitude
    dna: Mapped[float | None] = mapped_column(Float, nullable=True)           # depr & amort
    dividends_paid: Mapped[float | None] = mapped_column(Float, nullable=True)
    # balance sheet
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_liabilities: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_liabilities: Mapped[float | None] = mapped_column(Float, nullable=True)
    retained_earnings: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    shares_outstanding: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(24), default="yfinance")


class KvState(Base):
    """Small key/value table for runtime state (kill switch, mode, etc.)."""

    __tablename__ = "kv_state"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
