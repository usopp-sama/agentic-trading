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

    # --- Logging (stdout always; optional rotating file for unattended runs) ---
    log_to_file: bool = True
    log_dir: str = str(DATA_DIR / "logs")
    log_max_bytes: int = 10_000_000   # ~10 MB per file
    log_backup_count: int = 10        # keep 10 rotations (~100 MB ceiling)
    # Daily digest push (IST 24h clock) shortly after the 15:30 close + settle.
    digest_hour: int = 15
    digest_minute: int = 45
    # Extra intraday "what's going on now" digests (IST hours). With the close
    # digest above this gives 2-3 status emails a day. Set to [] to disable.
    # Override via env: ATS_DIGEST_INTRADAY_HOURS=[10,13]
    digest_intraday_hours: list[int] = [10, 13]

    # --- Learning attribution + research metrics ---
    # Forward-return horizon used to score an SME's directional call. An
    # attribution is only resolved once this many calendar days have elapsed
    # since the fill (in-flight attributions live in the DB, so they survive
    # restarts). Set to 0 to score on the next evaluation tick (legacy behavior).
    learning_horizon_days: int = 5
    # Daily export of per-strategy and per-SME metrics to var/metrics/*.parquet
    # plus an append-only research log of active params + rolling performance.
    metrics_export_enabled: bool = True
    metrics_dir: str = str(DATA_DIR / "metrics")
    metrics_export_hour: int = 16
    metrics_export_minute: int = 0

    # --- Web server (dashboard) ---
    # host: "127.0.0.1" = this machine only (default, safest).
    #       "0.0.0.0"   = reachable from other devices on your LAN.
    # Never expose this directly to the public internet without auth + a
    # reverse proxy / VPN (see docs/deployment_lan.md).
    host: str = "127.0.0.1"
    port: int = 8000
    # Optional shared-secret gate for LAN access. Empty = no auth (LAN-only).
    # When set, the dashboard requires ?token=... once (stored in a cookie).
    dashboard_token: str = Field(default="", repr=False)

    # --- Storage (SQLite by default; swap to Postgres/TimescaleDB via URL) ---
    db_url: str = f"sqlite:///{DATA_DIR / 'ats.db'}"

    # --- Event bus ("memory" for single-process; "redis" for multi-service) ---
    event_bus: str = "memory"
    redis_url: str = "redis://localhost:6379/0"

    # --- Vector store ("memory" fallback; "chroma" if installed) ---
    vector_store: str = "memory"

    # --- News sentiment model ("auto" | "finbert" | "vader") ---
    # "auto" prefers the finance-tuned FinBERT transformer and falls back to the
    # lexical VADER scorer when transformers/torch are not installed, so the
    # offline laptop/Pi target still works with zero extra deps. "finbert" forces
    # the transformer (and warns + falls back if it cannot load); "vader" pins
    # the lexical scorer. Install the FinBERT extras to actually enable it
    # (see requirements.txt): pip install "transformers>=4.44" torch
    nlp_sentiment_model: str = "auto"
    # HF model id, or a local directory holding config.json + weights + tokenizer.
    nlp_finbert_model: str = "ProsusAI/finbert"
    # Allow a runtime network download of the FinBERT weights. Default False: the
    # model loads from local cache only and never blocks server startup on a
    # download (which can hang behind a TLS-inspecting proxy). Provision weights
    # once out-of-band, then flip this true only on a network where the fetch
    # works — or point nlp_finbert_model at a local directory.
    nlp_finbert_download: bool = False

    # --- Expert knowledge base (RAG grounding for SMEs) ---
    # Built-in domain primers ship per family; drop your own .md/.txt notes,
    # research, or filings here to extend any expert's reading.
    knowledge_dir: str = str(DATA_DIR / "knowledge")
    knowledge_retrieval_k: int = 4
    # Multi-expert debate (Phase 5): rounds of critique before the CIO blends.
    debate_rounds: int = 1
    expert_memory_messages: int = 20  # per-thread chat history kept for context

    # --- LLM (provider: "mock" | "ollama" | "openai" | "gemini") ---
    # "mock" is a deterministic, grounded heuristic so the whole system runs
    # with no API key. You manage real providers/keys.
    # For Gemini (Google AI Studio): set provider="gemini",
    # base_url="https://generativelanguage.googleapis.com",
    # model="gemini-2.5-flash" (or -pro), and put the key in ATS_LLM_API_KEY.
    llm_provider: str = "mock"
    llm_model: str = "mock-1"
    llm_base_url: str = "http://localhost:11434"  # ollama default
    llm_api_key: str = Field(default="", repr=False)
    llm_cio_model: str = "mock-1"  # stronger model for synthesis (tiered routing)
    llm_temperature: float = 0.1
    llm_timeout_s: float = 60.0
    # Ollama context window (num_ctx). Ollama defaults to 4096 tokens, which
    # silently truncates the retrieved-knowledge + DATA envelope we pass for
    # RAG grounding. Raise for better grounding; note the KV cache grows with
    # this, so keep it modest on memory-constrained hosts (e.g. a 16 GB box).
    # 0 = leave Ollama's own default untouched.
    llm_num_ctx: int = 8192

    # --- LLM resilience (unattended month-long runs) ----------------------
    # Retry transient provider errors (HTTP 429 rate-limit, 500/502/503/504)
    # with capped exponential backoff (honoring Retry-After) before giving up.
    llm_max_retries: int = 3
    llm_backoff_base_s: float = 2.0
    # After a real-provider failure, serve the deterministic mock for this long
    # before re-probing the real provider — so a transient 429 self-heals
    # without a restart instead of latching to the mock for the whole session.
    llm_recover_cooldown_s: float = 180.0
    # Optional client-side cap on real-provider calls per minute (0 = unlimited).
    # On the paid tier leave this off; set e.g. 8 to stay under a free tier's
    # 10 RPM. Applies process-wide across all SME + CIO calls.
    llm_max_rpm: int = 0

    # --- LLM cost governance (keep Gemini spend predictable) --------------
    # The ONLY events that spend Gemini tokens are autonomous SME/macro
    # evaluations (fresh news sentiment, volume spikes, the periodic macro
    # sweep) plus the user-driven Experts console and Today brief. These knobs
    # throttle the *autonomous* path only; anything you click stays available.
    #
    # Only let news/spikes spend tokens during the NSE session (+grace window).
    # News is still fetched and scored locally 24/7 -- the SMEs read the
    # accumulated sentiment when the market re-opens, so nothing is lost.
    llm_eval_market_hours_only: bool = True
    # Only run SMEs for symbols in the active watchlist/universe; ignore news
    # that merely names tickers we do not trade.
    llm_eval_universe_only: bool = True
    # Minimum seconds between autonomous SME re-runs for the SAME symbol. A
    # burst of headlines on one name then costs a single evaluation rather than
    # one full roster pass per item.
    llm_symbol_cooldown_s: float = 900.0
    # Cap how many distinct symbols one news/spike event may fan out to (the
    # most-mentioned win). Stops a 10-ticker macro headline from firing the
    # whole roster across every name.
    llm_max_symbols_per_event: int = 3
    # Hard ceiling on characters sent to the model in a single autonomous
    # opinion call. Above this the call is treated as "too big to auto-spend":
    # the deterministic mock answers instead and the skip is logged for your
    # review, rather than silently burning a large-token request. 0 = no cap.
    llm_max_prompt_chars: int = 24000

    # --- Trading mode + the real-money gate -------------------------------
    # mode: OFF | PAPER | APPROVAL | AUTO. v1 default PAPER.
    trading_mode: str = "PAPER"
    # Master safety gate. Real orders are IMPOSSIBLE while this is False,
    # regardless of mode. Must be flipped explicitly after validation.
    real_money_enabled: bool = False
    base_currency: str = "INR"
    paper_starting_capital: float = 1_000_000.0  # Rs 10 lakh paper book

    # --- Market data ("yfinance" | "synthetic" | "nse_live" | "kite") ---
    # Defaults to real (delayed) NSE data via yfinance; falls back to synthetic
    # per-symbol only if a live fetch fails, so it still boots offline.
    # "nse_live" adds free intraday candles + live quotes (yfinance-backed, no
    # key) for the Charts page; Kite drops into the same adapter later.
    data_source: str = "yfinance"
    bar_interval: str = "1d"
    # Default intraday interval the Charts page opens with, and how often the
    # live source refreshes its intraday cache (seconds).
    intraday_interval: str = "5m"
    intraday_refresh_s: int = 60
    # Pause live-source polling outside NSE hours (synthetic is exempt).
    respect_market_hours: bool = True
    # Feed integrity: when a live source is configured and we are in-session,
    # the feed is "degraded" if fewer than this fraction of symbols are on the
    # real feed (the rest fell back to synthetic). Degradation halts NEW entries.
    feed_min_live_ratio: float = 0.5
    feed_halt_entries_on_degrade: bool = True

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

    # --- Strategy auto-trade: let the quant strategies drive paper orders ---
    # When enabled, StrategyTraderService turns a consensus of the `paper`-status
    # strategy signals into proposals that flow through the SAME Risk -> Execution
    # path the LLM pipeline uses (sizing, guardrails, long-only clamp all apply).
    # No LLM/Gemini spend on this path. Signals only fire during the polling
    # window, so trades are naturally market-hours bound.
    strategy_autotrade_enabled: bool = True
    # Net strategy score = (Σ bullish conviction − Σ bearish conviction) / voters.
    # Open a new position when net ≥ buy_threshold AND ≥ min_agree strategies agree.
    strategy_trade_buy_threshold: float = 0.12
    # Flatten a held name when its net strategy score falls to/below this.
    strategy_trade_exit_threshold: float = 0.0
    strategy_trade_min_agree: int = 1
    # Per-symbol cooldown between strategy-driven orders (anti-churn), seconds.
    strategy_trade_cooldown_s: int = 300

    # --- Strategy league: segregated solo accounts + benchmark (plan §9) ---
    # Every roster strategy gets its own simulated bank account + broker
    # connection (solo_<id>) funded with the same capital, plus a buy-and-hold
    # NIFTYBEES `benchmark` account — the bar everyone must clear. The /league
    # page compares them. Solo trading is signal-driven (no consensus, no LLM)
    # and runs the same immutable per-account guardrails scaled to its equity.
    league_enabled: bool = True
    league_capital: float = 100_000.0  # Rs 1L each, so PnL% is comparable
    # "auto" = all paper-status equity strategies (vol_premium excluded — it
    # runs its own options book). Or a comma-separated list of strategy ids,
    # which may include shadow strategies (their solo book trades real paper
    # money in the league even while their consensus voice stays shadow).
    league_strategies: str = "auto"
    league_benchmark_symbol: str = "NIFTYBEES.NS"
    league_snapshot_interval_s: int = 300

    # --- External data API keys (free-tier v1 stack; optional) ---
    marketaux_api_key: str = Field(default="", repr=False)
    alphavantage_api_key: str = Field(default="", repr=False)
    fmp_api_key: str = Field(default="", repr=False)
    fred_api_key: str = Field(default="", repr=False)
    telegram_bot_token: str = Field(default="", repr=False)
    telegram_chat_id: str = Field(default="", repr=False)

    # --- Email notifications (SMTP) ---
    # The preferred alert/digest channel. When host + from + to are set the
    # notify() funnel and EmailService deliver alerts, the daily digest, and
    # approval requests over SMTP (STARTTLS by default). Password is a secret,
    # so it comes from the environment and is redacted from logs.
    email_smtp_host: str = ""
    email_smtp_port: int = 587            # 587 = STARTTLS, 465 = implicit TLS
    email_smtp_user: str = Field(default="", repr=False)
    email_smtp_password: str = Field(default="", repr=False)
    email_from: str = ""                  # e.g. "ATS Bot <you@gmail.com>"
    email_to: str = ""                    # comma-separated recipients
    email_use_tls: bool = True            # STARTTLS on 587; ignored on 465 (implicit)
    email_subject_prefix: str = "[ATS]"
    email_timeout_s: int = 15

    # --- Broker (Zerodha Kite) - deferred until real money is enabled ---
    kite_api_key: str = Field(default="", repr=False)
    kite_api_secret: str = Field(default="", repr=False)
    kite_access_token: str = Field(default="", repr=False)

    # --- Scheduler cadences (seconds) ---
    market_scan_interval_s: int = 60
    news_poll_interval_s: int = 300
    agent_cycle_interval_s: int = 120
    # Marketaux free tier allows only 100 requests/day. News polls every
    # ``news_poll_interval_s`` (~288/day at 300s), which would blow the quota,
    # so Marketaux is throttled to at most one call per this many seconds
    # (1200s = ~72/day, comfortably under the cap). RSS feeds still run every
    # poll. Raise the cap by lowering this only if you have a paid plan.
    marketaux_min_interval_s: int = 1200

    # --- Watchdog (dead-man's switch; roadmap Part 10) ---
    watchdog_interval_s: int = 60
    # Bar silence tolerated before unhealthy. 15 min absorbs yfinance delay /
    # rate-limit hiccups during a real session without false-tripping.
    watchdog_stale_after_s: int = 900
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

    # --- Strategy library tunables (the "variables" to fine-tune over the run) ---
    # These drive the shadow strategies added for the month-long paper test so
    # lookbacks/thresholds are config, not code edits. All start as shadow
    # (signals logged, no capital) until the backtest gate promotes them.
    # Cross-sectional / dual momentum
    xs_mom_formation: int = 252
    xs_mom_skip: int = 21
    xs_mom_decile: float = 0.2
    xs_mom_rebalance_days: int = 21
    dual_mom_lookback: int = 252
    dual_mom_top_n: int = 5
    # 52-week high
    high52_buy_near: float = 0.95
    high52_sell_near: float = 0.75
    # MACD + ADX trend
    macd_adx_min: float = 20.0
    # Short-term reversal
    st_reversal_lookback: int = 5
    st_reversal_decile: float = 0.2
    # OU / Keltner reversion
    ou_keltner_ema: int = 20
    ou_keltner_atr: int = 10
    ou_keltner_z_entry: float = 1.0
    ou_keltner_z_exit: float = 0.3
    # Single-factor sleeves
    factor_sleeve_top_n: int = 8
    factor_sleeve_rebalance_days: int = 90
    # Cointegration pairs
    coint_formation: int = 252
    coint_z_window: int = 60
    coint_entry_z: float = 2.0
    coint_exit_z: float = 0.5
    coint_reselect_days: int = 21
    # Post-earnings drift (price-proxy)
    pead_gap_z: float = 2.5
    pead_drift_days: int = 10
    # News-sentiment momentum
    news_sent_buy: float = 0.25
    news_sent_sell: float = -0.25
    news_sent_min_count: int = 3
    # Turn-of-month seasonality
    tom_days_before: int = 1
    tom_days_after: int = 3
    # Volatility-target overlay
    vol_target_annual: float = 0.15
    vol_target_max: float = 0.60

    @property
    def is_real_money_active(self) -> bool:
        """Real orders may flow only when the gate is open AND mode is live."""
        return self.real_money_enabled and self.trading_mode in {"APPROVAL", "AUTO"}


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
