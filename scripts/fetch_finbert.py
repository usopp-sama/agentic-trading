"""One-time provisioning of the FinBERT news-sentiment weights.

The live NLP service (``ats/services/nlp``) prefers the finance-tuned FinBERT
transformer but, by design, NEVER downloads it at runtime — it loads from the
local cache only, so a blocked/slow download can't hang server startup. This
script is that out-of-band download step: run it once on a network that allows
the ~438 MB fetch, then the server picks FinBERT up automatically.

It downloads only the files the PyTorch pipeline needs (config, tokenizer,
vocab, ``pytorch_model.bin``) and skips the TensorFlow/Flax weight mirrors the
repo also ships, roughly halving the transfer.

Usage
-----
    # Into the shared Hugging Face cache (~/.cache/huggingface) — works on any
    # network afterwards via a cache hit:
    python scripts/fetch_finbert.py

    # Into a self-contained local directory you point the server at:
    python scripts/fetch_finbert.py --dest var/models/finbert
    #   then set: ATS_NLP_FINBERT_MODEL=/abs/path/to/var/models/finbert

After provisioning, enable FinBERT with:
    ATS_NLP_SENTIMENT_MODEL=auto      # prefer FinBERT, fall back to VADER

Corporate / TLS-inspecting networks
-----------------------------------
If the large-file download stalls or is reset (a TLS-inspecting proxy such as
Cisco AMP/Umbrella can throttle big CDN transfers), run this on a permissive
network (home Wi-Fi / hotspot) — the cached weights then work everywhere. The
``truststore`` package (optional) is injected when present so Python trusts the
OS keychain CAs, matching ``curl``/native apps. See ``docs/nlp_sentiment.md``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Only the PyTorch pipeline's files — skip tf_model.h5 / flax_model.msgpack.
_ALLOW = [
    "config.json",
    "vocab.txt",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "pytorch_model.bin",
    "model.safetensors",
]
_MIN_WEIGHTS_BYTES = 400_000_000  # ProsusAI/finbert weights are ~438 MB


def _inject_truststore() -> bool:
    try:
        import truststore

        truststore.inject_into_ssl()
        return True
    except Exception:  # noqa: BLE001 - best effort; download may still work
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="ProsusAI/finbert", help="HF model id")
    ap.add_argument(
        "--dest",
        default=None,
        help="local directory to download into (default: shared HF cache)",
    )
    args = ap.parse_args()

    used_truststore = _inject_truststore()
    print(f"truststore (OS trust store): {'on' if used_truststore else 'not installed'}")

    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: huggingface_hub unavailable ({exc}).")
        print('Install the FinBERT extras first: pip install "transformers>=4.44,<5" torch')
        return 1

    kwargs: dict = {"repo_id": args.model, "allow_patterns": _ALLOW}
    if args.dest:
        dest = Path(args.dest).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        kwargs["local_dir"] = str(dest)

    print(f"Downloading {args.model} (PyTorch files only)...")
    try:
        path = snapshot_download(**kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR: download failed ({type(exc).__name__}: {str(exc)[:200]}).")
        print(
            "If you are behind a TLS-inspecting proxy (e.g. Cisco AMP), retry on a "
            "permissive network; the cached weights then work everywhere."
        )
        return 1

    # Sanity-check the weights are complete (a throttled proxy can truncate them).
    root = Path(path)
    weights = next(
        (root / n for n in ("pytorch_model.bin", "model.safetensors") if (root / n).exists()),
        None,
    )
    if weights is None:
        print(f"\nERROR: no weights file under {root} — download incomplete.")
        return 1
    size = weights.stat().st_size
    if size < _MIN_WEIGHTS_BYTES:
        print(
            f"\nERROR: {weights.name} is only {size / 1e6:.1f} MB (expected ~438 MB) "
            "— the transfer was truncated. Re-run on a permissive network."
        )
        return 1

    print(f"\nOK: FinBERT provisioned at {root} ({size / 1e6:.0f} MB weights).")
    if args.dest:
        print(f"Set:  ATS_NLP_FINBERT_MODEL={root}")
    print("Set:  ATS_NLP_SENTIMENT_MODEL=auto   # FinBERT now loads from cache")
    return 0


if __name__ == "__main__":
    sys.exit(main())
