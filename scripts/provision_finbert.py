"""Provision FinBERT weights (perf plan P1.2).

The sentiment scorer prefers FinBERT (finance-tuned transformer) but the server
NEVER downloads it at boot — so on a machine where the weights were never
fetched, it correctly falls back to VADER (lexical) and the logs say
``finbert_unavailable_using_vader``. That is not a bug; it just means FinBERT
was never provisioned here.

Run this ONCE, on a network where the download succeeds, to fetch
``ProsusAI/finbert`` (~440 MB) into the local Hugging Face cache. After it,
restarts load FinBERT offline (no network) and ``/api/health`` +the System page
report ``sentiment: finbert``.

    .venv/Scripts/python -m scripts.provision_finbert

Runtime cost once loaded: ~800 MB RAM. To stay lexical/low-RAM on this laptop,
set ``ATS_NLP_SENTIMENT_MODEL=vader`` instead and skip this.
"""

from __future__ import annotations

import os
import sys

MODEL = "ProsusAI/finbert"


def main() -> int:
    # Route SSL through the OS trust store when available (corporate TLS proxies
    # present a root CA that certifi's bundle does not carry).
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:  # noqa: BLE001 — download may still work without it
        pass

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except Exception as exc:  # noqa: BLE001
        print(f"transformers is not installed ({exc}).")
        print("Install the NLP extra, then re-run: pip install transformers torch")
        return 1

    print(f"Downloading {MODEL} (~440 MB) into the local Hugging Face cache …")
    try:
        AutoTokenizer.from_pretrained(MODEL)
        AutoModelForSequenceClassification.from_pretrained(MODEL)
    except Exception as exc:  # noqa: BLE001
        print(f"Download failed: {exc}")
        print("Check connectivity/proxy; the server keeps using VADER until this succeeds.")
        return 1

    # Verify it now loads fully offline (this is exactly what the server does).
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
        AutoModelForSequenceClassification.from_pretrained(MODEL, local_files_only=True)
    except Exception as exc:  # noqa: BLE001
        print(f"Offline-load verification failed: {exc}")
        return 1

    print("OK: FinBERT is provisioned and loads offline.")
    print("Restart the server — the scorer will use FinBERT (~800 MB RAM).")
    print("/api/health and the System page will show sentiment: finbert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
