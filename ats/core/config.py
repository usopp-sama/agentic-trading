"""Central configuration.

Loaded from environment / a local ``.env`` file via pydantic-settings. Secrets
never live in code (see the no-hardcoded-credentials policy); they come from
the environment and are redacted from logs by ``ats.core.logging``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "var"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATS_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Environment ---
    env: str = "dev"
    debug: bool = True

    # --- Storage (SQLite by default; swap to Postgres/TimescaleDB via URL) ---
    db_url: str = f"sqlite:///{DATA_DIR / 'ats.db'}"

    # --- Event bus ("memory" for single-process; "redis" for multi-service) ---
    event_bus: str = "memory"
    redis_url: str = "redis://localhost:6379/0"

    # --- Vector store ("memory" fallback; "chroma" if installed) ---
    vector_store: str = "memory"

    # --- Expert knowledge base (RAG grounding for SMEs) ---
    # Built-in domain primers ship per family; drop your own .md/.txt notes,
    # research, or filings here to extend any expert's reading.
    knowledge_dir: str = str(DATA_DIR / "knowledge")
    knowledge_retrieval_k: int = 4
    # Multi-expert debate (Phase 5): rounds of critique before the CIO blends.
    debate_rounds: int = 1
    expert_memory_messages: int = 20  # per-thread chat history kept for context

    # --- LLM (provider: "mock" | "ollama" | "openai") ---
    # "mock" is a deterministic, grounded heuristic so the whole system runs
    # with no API key. You manage real providers/keys.
    llm_provider: str = "mock"
    llm_model: str = "mock-1"
    llm_base_url: str = "http://localhost:11434"  # ollama default
    llm_api_key: str = Field(default="", repr=False)
    llm_cio_model: str = "mock-1"  # stronger model for synthesis (tiered routing)
    llm_temperature: float = 0.1
    llm_timeout_s: float = 60.0

    # --- Trading mode + the real-money gate -------------------------------
    # mode: OFF | PAPER | APPROVAL | AUTO. v1 default PAPER.
    trading_mode: str = "PAPER"
    # Master safety gate. Real orders are IMPOSSIBLE while this is False,
    # regardless of mode. Must be flipped explicitly after validation.
    real_money_enabled: bool = False
    base_currency: str = "INR"
    paper_starting_capital: float = 1_000_000.0  # Rs 10 lakh paper book

    # --- Market data ("yfinance" | "synthetic" | "kite") ---
    # Defaults to real (delayed) NSE data via yfinance; falls back to synthetic
    # per-symbol only if a live fetch fails, so it still boots offline.
    data_source: str = "yfinance"
    bar_interval: str = "1d"
    # Pause live-source polling outside NSE hours (synthetic is exempt).
    respect_market_hours: bool = True

    # --- Fundamentals ("synthetic" | "yfinance"; "auto" follows data_source) ---
    fundamentals_source: str = "auto"
    fundamentals_refresh_hours: int = 24

    # --- Options chain (NIFTY IV monitor; "synthetic" | "nse"; "auto") ---
    option_chain_source: str = "auto"
    option_chain_symbol: str = "NIFTY"
    option_chain_interval_s: int = 1800

    # --- Hard risk guardrails (apply in ALL live modes) ---
    max_position_pct: float = 0.10       # max 10% of capital in one name
    max_sector_pct: float = 0.35         # max 35% in one sector
    max_gross_exposure_pct: float = 1.00 # no leverage in v1
    daily_loss_limit_pct: float = 0.03   # 3% daily loss -> kill
    max_orders_per_min: int = 30
    max_trade_value: float = 50_000.0    # absolute per-order cap

    # --- Regime detection (roadmap Part 7.12) ---
    regime_reference_symbol: str = "^NSEI"  # index the regime is read from
    regime_crisis_scale: float = 0.5     # cut new-exposure sizing in crisis vol

    # --- Strategy sleeves: virtual P&L attribution + decay detection ---
    sleeve_decay_sharpe: float = 0.0     # alert when rolling Sharpe drops below
    sleeve_decay_min_days: int = 60      # ...after at least this many marked days
    # Capital allocation across sleeves: auto | inverse_vol | erc | erc_tilt.
    # auto = inverse-vol until 2+ sleeves have ~2 months of history, then
    # correlation-aware risk parity with a bounded performance tilt.
    sleeve_allocation_method: str = "auto"

    # --- External data API keys (free-tier v1 stack; optional) ---
    marketaux_api_key: str = Field(default="", repr=False)
    alphavantage_api_key: str = Field(default="", repr=False)
    fmp_api_key: str = Field(default="", repr=False)
    fred_api_key: str = Field(default="", repr=False)
    telegram_bot_token: str = Field(default="", repr=False)
    telegram_chat_id: str = Field(default="", repr=False)

    # --- Broker (Zerodha Kite) - deferred until real money is enabled ---
    kite_api_key: str = Field(default="", repr=False)
    kite_api_secret: str = Field(default="", repr=False)
    kite_access_token: str = Field(default="", repr=False)

    # --- Scheduler cadences (seconds) ---
    market_scan_interval_s: int = 60
    news_poll_interval_s: int = 300
    agent_cycle_interval_s: int = 120

    # --- Watchdog (dead-man's switch; roadmap Part 10) ---
    watchdog_interval_s: int = 60
    watchdog_stale_after_s: int = 600     # bar silence tolerated before unhealthy
    watchdog_auto_kill: bool = True       # engage kill switch on sustained failure
    watchdog_kill_after_failures: int = 3 # consecutive unhealthy checks

    # --- Telegram approvals ---
    telegram_poll_interval_s: int = 5

    # --- Vol-premium sleeve (roadmap 7.7; paper-only, defined-risk) ---
    vol_premium_enabled: bool = True
    vol_entry_iv_premium: float = 0.04    # enter when ATM IV - realized >= 4 pts
    vol_profit_target: float = 0.5        # close at 50% of credit captured
    vol_stop_mult: float = 2.0            # close if debit reaches 2x credit
    vol_otm_pct: float = 0.05             # short strikes ~5% OTM each side
    vol_wing_steps: int = 4               # wings this many strike steps further
    vol_max_lots: int = 1
    vol_sleeve_capital: float = 100_000.0 # ~10% of the Rs 10 lakh paper book
    nifty_strike_step: float = 50.0
    nifty_lot_size: int = 75

    @property
    def is_real_money_active(self) -> bool:
        """Real orders may flow only when the gate is open AND mode is live."""
        return self.real_money_enabled and self.trading_mode in {"APPROVAL", "AUTO"}


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
