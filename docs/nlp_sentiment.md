# News Sentiment (VADER + FinBERT)

How the NLP service scores news sentiment, how to switch between the lexical
(VADER) and finance-tuned transformer (FinBERT) backends, and how to provision
the FinBERT weights — including on TLS-inspecting corporate networks.

> Code: [ats/services/nlp/sentiment.py](../ats/services/nlp/sentiment.py),
> wired in [ats/services/nlp/service.py](../ats/services/nlp/service.py).
> Provisioning helper: [scripts/fetch_finbert.py](../scripts/fetch_finbert.py).
> Tests: [tests/test_nlp_sentiment.py](../tests/test_nlp_sentiment.py).

---

## 1. Where it fits

The pipeline is `scraper → nlp → agents`. The NLP service subscribes to
`Topic.NEWS`, scores each headline+body, indexes the doc in the RAG vector
store, persists a `SentimentScore` row per ticker (plus a `MARKET`
pseudo-symbol for macro mood), and publishes `Topic.SENTIMENT`. The score
(`[-1, 1]`) feeds the macro/Family-B SMEs and the news-sentiment-momentum
strategy.

---

## 2. The two backends

| Backend | What it is | When used |
| --- | --- | --- |
| **VADER** | Lexical/rule scorer (`vaderSentiment`). Offline, dependency-light, always available. | Default fallback; the only backend on the lean laptop/Pi image. |
| **FinBERT** | `ProsusAI/finbert`, a finance-tuned transformer via `transformers`/`torch`. Understands market phrasing ("misses estimates", "guidance cut") that trips up a generic lexicon. | Preferred when the weights are provisioned (see §4). |

Why FinBERT matters: VADER scores *"the board approved the meeting agenda"* as
**positive** (lexical "approved"), where FinBERT correctly reads it as
**neutral**. For market news that difference is the whole point.

`SentimentModel.name` reports the backend that actually loaded (`"finbert"` or
`"vader"`), and that value is written to each `SentimentScore.model` row so the
provenance of every score is auditable.

---

## 3. Configuration

All settings are `ATS_`-prefixed env vars (see
[ats/core/config.py](../ats/core/config.py)).

| Variable | Default | Purpose |
| --- | --- | --- |
| `ATS_NLP_SENTIMENT_MODEL` | `auto` | `auto` (prefer FinBERT, fall back to VADER) \| `finbert` (force; warn + fall back if it can't load) \| `vader` (pin lexical). |
| `ATS_NLP_FINBERT_MODEL` | `ProsusAI/finbert` | HF model id **or** a local directory holding `config.json` + weights + tokenizer. |
| `ATS_NLP_FINBERT_DOWNLOAD` | `false` | Allow a runtime network download of the weights. Default **off** (see §5). |

Behavior matrix (`auto`):

| FinBERT extras installed? | Weights cached/local? | Active backend |
| --- | --- | --- |
| no | — | VADER |
| yes | no | VADER (instant fallback, no network) |
| yes | yes | **FinBERT** |

---

## 4. Provisioning the FinBERT weights

FinBERT needs `transformers`, `torch`, and the ~438 MB weights. Install the
extras into the project venv (not system Python):

```bash
.venv/bin/python -m pip install "transformers>=4.44,<5" torch truststore
```

> Pin `transformers` to the 4.x line: it uses a `requests`-based
> `huggingface_hub` that respects `certifi`/`truststore`. The 5.x line ships a
> newer httpx downloader with a known retry bug on some setups.

Then fetch the weights **once** with the helper:

```bash
# Into the shared HF cache (~/.cache/huggingface) — then works on any network:
.venv/bin/python scripts/fetch_finbert.py

# ...or into a self-contained local directory:
.venv/bin/python scripts/fetch_finbert.py --dest var/models/finbert
#   then set ATS_NLP_FINBERT_MODEL=/abs/path/to/var/models/finbert
```

Enable it:

```bash
ATS_NLP_SENTIMENT_MODEL=auto      # FinBERT now loads from cache; VADER stays as fallback
```

The script downloads only the PyTorch files (skips the TF/Flax mirrors) and
verifies the weights file is complete (it errors if a proxy truncated it).

---

## 5. Runtime safety: no downloads at startup

The sentiment model is constructed during **server startup**
(`NlpService.__init__`). If that triggered a model *download*, a blocked or slow
network could hang the entire boot indefinitely. So by design:

- `ATS_NLP_FINBERT_DOWNLOAD=false` (default) → FinBERT loads with
  `local_files_only=True`. If the weights aren't cached, the load **fails fast**
  and falls back to VADER. **It never blocks startup on a download.**
- Set `ATS_NLP_FINBERT_DOWNLOAD=true` only as a convenience on a network where
  the one-time fetch works; provisioning via `scripts/fetch_finbert.py` is
  preferred and keeps the server's boot path network-free.

This mirrors the project's offline-first principle: every external dependency
has an in-process fallback, and the server always boots.

---

## 6. Corporate / TLS-inspecting networks

Symptom: small files (config, tokenizer) download, but the 438 MB weights stall
at 0 bytes (Python) or get reset mid-stream (curl), while `curl https://huggingface.co/...`
for a *small* file returns `200`.

Cause: a TLS-inspecting middlebox (e.g. **Cisco AMP/Umbrella**, Zscaler)
presents a root CA that lives in the macOS **System keychain** but not in the
`certifi` bundle Python ships. `curl`/native apps trust it; Python doesn't —
and large CDN transfers are additionally throttled/cut.

Mitigations:

1. **`truststore`** (installed above) routes Python's SSL through the OS trust
   store, matching `curl`. `scripts/fetch_finbert.py` and the live loader inject
   it automatically when present. This fixes the *SSL* failure.
2. If the large file is still **throttled/cut** (a separate problem from SSL),
   run `scripts/fetch_finbert.py` on a **permissive network** (home Wi-Fi /
   hotspot). Once the weights are cached, the server uses them on any network —
   no further download is attempted.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `SentimentScore.model` is `vader` despite `auto` | weights not cached, or extras missing | Run `scripts/fetch_finbert.py`; confirm `transformers`/`torch` in the venv. |
| `CERTIFICATE_VERIFY_FAILED` on download | TLS-inspecting proxy + certifi | `pip install truststore` (auto-injected). |
| Download stalls at 0 bytes / resets | proxy throttling large CDN transfers | Provision on a permissive network (§6). |
| Truncated weights error from the script | transfer cut mid-stream | Re-run; the script verifies the ~438 MB size. |
| `transformers 5.x` download retry bug | newer httpx downloader | `pip install "transformers>=4.44,<5"`. |

Verify the active backend quickly:

```bash
.venv/bin/python -c "from ats.services.nlp.sentiment import build_sentiment_model as b; print(b().name)"
```

---

## 8. Cross-references

- [architecture.md §6 (nlp)](architecture.md) — the NLP service in the wider system.
- [month_paper_run.md](month_paper_run.md) — operating the paper run.
- [requirements.txt](../requirements.txt) — the optional FinBERT extras block.
