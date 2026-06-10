"""Agentic Trading Server (ATS).

An always-on, server-oriented agentic trading system that runs on top of the
``quant`` analytics toolkit. See the plan in
``.cursor/plans/agentic_trading_server_*.plan.md``.

Design stance: offline-first and paper-first. Everything runs locally with no
external API keys (SQLite, in-process event bus, a deterministic mock LLM,
lexicon sentiment). Production swaps (Postgres/TimescaleDB, Redis, Zerodha
Kite, a hosted LLM) sit behind interfaces and are enabled purely via config.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
