"""Shared test fixtures + environment isolation.

Tests must not depend on a developer's local ``.env`` (which may point the LLM
at a real Ollama/OpenAI endpoint for the live paper run). We force the
deterministic mock provider and the offline synthetic feed here, before any
``ats`` module reads settings, so the suite is hermetic and never makes network
calls. Environment variables take precedence over the ``.env`` file in
pydantic-settings, so this reliably overrides it.
"""

from __future__ import annotations

import os

os.environ.setdefault("ATS_LLM_PROVIDER", "mock")
os.environ.setdefault("ATS_LLM_MODEL", "mock-1")
os.environ.setdefault("ATS_LLM_CIO_MODEL", "mock-1")
os.environ.setdefault("ATS_DATA_SOURCE", "synthetic")
os.environ.setdefault("ATS_RESPECT_MARKET_HOURS", "false")
os.environ.setdefault("ATS_LOG_TO_FILE", "false")

# If settings were already cached (import order), drop the cache so the forced
# environment above takes effect.
try:  # pragma: no cover - defensive
    from ats.core.config import get_settings

    get_settings.cache_clear()
except Exception:  # noqa: BLE001
    pass
