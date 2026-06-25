# LLM provider: billing, resilience, and tuning

The SME experts and the CIO synthesis run on a pluggable LLM client
(`ats/services/agents/llm_client.py`). This doc covers running it reliably for a
month-long unattended paper run on **Google Gemini**, what the resilience layer
does, and the knobs you can turn.

> If no real provider is configured (`ATS_LLM_PROVIDER=mock`) the system still
> runs end-to-end on a deterministic, grounded heuristic — just without natural
> reasoning. Everything below is about running a *real* model.

## 1. How calls map to cost

| Path | Model (`.env`) | Volume | Notes |
| --- | --- | --- | --- |
| Per-symbol SME opinions | `ATS_LLM_MODEL` (`gemini-2.5-flash`) | High (~10 calls per symbol evaluated) | The dominant cost/quota driver. |
| CIO brief / debates / console | `ATS_LLM_CIO_MODEL` (`gemini-2.5-pro`) | Low (on-demand) | CIO aggregation itself is deterministic; the model is used for the daily brief, debates, and the expert console. |

Because SMEs are the high-volume path, that is the lever for both **spend** and
**requests-per-day (RPD)** limits.

## 2. Tier-1 setup (one time)

1. In [Google AI Studio](https://aistudio.google.com/) open **Get API key → set
   up billing** and link a billing account (the project moves from *Free* to
   *Tier 1*). This raises the rate limits substantially (e.g. flash free is
   ~10 RPM / a few hundred RPD; Tier 1 is far higher).
2. Copy the key into `.env` as `ATS_LLM_API_KEY` (it is sent in the
   `x-goog-api-key` header, never in the URL, so it doesn't leak into request
   logs). `.env` is gitignored — keep it that way.
3. Restart the server. Confirm real reasoning is live:

   ```bash
   curl -s http://127.0.0.1:8000/api/health | python3 -m json.tool
   ```

   Look for `"llm": { "real": true, "downgraded": false, ... }`.

## 3. Resilience layer (why a transient 429 no longer kills the session)

Previously a single failed startup probe pinned the whole session to the mock.
Now every real provider is wrapped in a `ResilientLLMClient`:

- **Retry with backoff.** Transient errors (HTTP `429`, `500`, `502`, `503`,
  `504`, and network errors) are retried with capped exponential backoff. A
  `Retry-After` header, if present, is honored.
- **Recoverable fallback.** If the provider is still failing after retries, the
  mock is served for a **cooldown window**, then the real provider is re-probed
  on the next call. A transient rate-limit self-heals without a restart.
- **Live health.** `/api/health.llm` reflects the *current* state (it flips back
  to `real: true` automatically once the provider recovers), not just the
  startup probe.
- **Bad JSON ≠ outage.** A malformed-but-successful response is handled locally
  (one-off mock fallback for that call) and does **not** mark the provider
  unhealthy.

## 4. Tunables (`.env`)

```ini
# Retry/backoff for transient provider errors
ATS_LLM_MAX_RETRIES=3            # attempts beyond the first
ATS_LLM_BACKOFF_BASE_S=2.0       # base seconds; wait = base * 2**attempt
ATS_LLM_RECOVER_COOLDOWN_S=180   # serve mock this long before re-probing

# Optional process-wide rate cap across ALL SME + CIO calls (0 = unlimited)
ATS_LLM_MAX_RPM=0                # set 8 to stay under a free tier's 10 RPM
```

On paid Tier 1, leave `ATS_LLM_MAX_RPM=0`. On the free tier, set it to a value
just under your RPM ceiling (e.g. `8` for a 10 RPM limit) to avoid 429 storms.

## 5. Budget-safe model split

The defaults are quality-first (`flash` SMEs, `pro` CIO). If you hit per-day
request caps or want lower spend, switch the high-volume SME path to the
cheaper, higher-quota lite model and keep CIO on a stronger model for the
(low-volume) briefs:

```ini
ATS_LLM_MODEL=gemini-2.5-flash-lite   # SMEs: cheaper + more headroom
ATS_LLM_CIO_MODEL=gemini-2.5-flash    # CIO: still strong, much cheaper than pro
```

If RPD pressure persists, the durable fix is reducing call volume (caching SME
opinions per symbol/bar) rather than upgrading further.

## 6. Budget alerts

In Google Cloud Billing, set a **budget + threshold alert** (e.g. 50% / 90% /
100% of a small monthly cap like a few dollars) on the billing account so a
runaway loop or a busy news day can't surprise you. Gemini spend for a month of
paper trading on flash/flash-lite is typically very small, but the alert is your
backstop.

## 7. Key rotation

- Rotate by creating a new key in AI Studio, updating `ATS_LLM_API_KEY` in
  `.env`, and restarting. Revoke the old key after confirming `/api/health`
  shows `llm.real: true`.
- Never commit the key. `.env` is gitignored; if a key is ever pasted into a
  tracked file or a log, treat it as compromised and rotate immediately.
- The key only ever travels in the `x-goog-api-key` request header over HTTPS.
