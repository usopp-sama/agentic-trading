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

    # --- Hard risk guardrails (apply in ALL live modes) ---
    max_position_pct: float = 0.10       # max 10% of capital in one name
    max_sector_pct: float = 0.35         # max 35% in one sector
    max_gross_exposure_pct: float = 1.00 # no leverage in v1
    daily_loss_limit_pct: float = 0.03   # 3% daily loss -> kill
    max_orders_per_min: int = 30
    max_trade_value: float = 50_000.0    # absolute per-order cap

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

    @property
    def is_real_money_active(self) -> bool:
        """Real orders may flow only when the gate is open AND mode is live."""
        return self.real_money_enabled and self.trading_mode in {"APPROVAL", "AUTO"}


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
