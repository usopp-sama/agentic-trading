# Month-Long Paper Run — Operator Playbook

How to run the agentic trading server unattended for a month of **NSE paper
trading** (fake money, real prices), keep it healthy, and review/fine-tune it
weekly. This is the operational companion to the hardening + strategy-library
work; for network/hosting see [deployment_lan.md](deployment_lan.md).

> Paper only. `ATS_REAL_MONEY_ENABLED=false` and `ATS_TRADING_MODE=PAPER` must
> stay set for the whole run. No order ever reaches a real broker in this mode —
> the paper broker simulates fills with Zerodha-style fees and 5 bps slippage.

---

## 1. One-time setup

### 1.1 Environment (`.env` at the repo root)

```bash
ATS_ENV=dev
ATS_DEBUG=false

# Paper trading on live NSE prices
ATS_TRADING_MODE=PAPER
ATS_REAL_MONEY_ENABLED=false
ATS_DATA_SOURCE=nse_live          # yfinance-backed live candles; falls back gracefully
ATS_RESPECT_MARKET_HOURS=true
ATS_PAPER_STARTING_CAPITAL=1000000

# Real SME reasoning (pick ONE backend)
ATS_LLM_PROVIDER=ollama            # local; run `ollama serve` + `ollama pull llama3.1`
ATS_LLM_MODEL=llama3.1
ATS_LLM_BASE_URL=http://localhost:11434
# --- or a hosted OpenAI-compatible API ---
# ATS_LLM_PROVIDER=openai
# ATS_LLM_BASE_URL=https://api.your-provider.com/v1
# ATS_LLM_API_KEY=...              # never commit this

# LAN access (optional)
ATS_HOST=0.0.0.0
ATS_PORT=8000
ATS_DASHBOARD_TOKEN=choose-a-long-random-string
```

The startup self-check logs whether the LLM endpoint actually answered
(`llm_selfcheck_*`). If a real provider is configured but unreachable, the
session transparently downgrades to the deterministic mock so the run never
hangs — fix the endpoint and restart to get real reasoning back.

### 1.2 Seed knowledge + bootstrap the SME track records

```bash
# Activate the venv first:  source .venv/bin/activate
python scripts/train_smes.py --offline        # cold-start SME weights from history
#   (drop --offline to calibrate on real yfinance history)
```

Domain primers under `ats/services/agents/corpus/` are ingested automatically so
SME grounding (RAG) is non-empty from the first request.

### 1.4 (Optional) Enable FinBERT news sentiment

News sentiment defaults to lexical VADER. To use the finance-tuned FinBERT
transformer instead, install the extras and provision the weights **once**:

```bash
.venv/bin/python -m pip install "transformers>=4.44,<5" torch truststore
.venv/bin/python scripts/fetch_finbert.py        # ~438 MB, one-time
# then set in .env:  ATS_NLP_SENTIMENT_MODEL=auto
```

The server never downloads the model at startup (it loads from cache only and
falls back to VADER instantly if absent), so this step is safe to skip or defer.
Behind a TLS-inspecting proxy (e.g. Cisco AMP) the download may stall — run it on
a permissive network; cached weights then work everywhere. Full details and
troubleshooting in [nlp_sentiment.md](nlp_sentiment.md).

### 1.3 Pre-flight checks

```bash
python -m pytest -q                            # full suite must be green
python scripts/run_backtests.py --offline      # dry-run the strategy gate
```

The strategy library ships ~24 strategies. The 15 new ones start as
**`shadow`** (signals logged, **no capital**) and only become `paper` after they
clear the backtest gate (§6.3).

---

## 2. Start / stop

### Foreground (first run, to watch logs)

```bash
python -m ats.server          # binds ATS_HOST:ATS_PORT; Ctrl-C to stop
```

### Always-on service

Use the service unit appropriate to the host (full configs in
[deployment_lan.md §5](deployment_lan.md)):

- **Linux (systemd):** `sudo systemctl enable --now ats` ; logs `journalctl -u ats -f`
- **macOS (launchd):** `launchctl load ~/Library/LaunchAgents/com.ats.server.plist`
- **Docker (any OS):** `docker compose -f deploy/docker-compose.lan.yml up -d --build`

The server is **restart-safe**: peak-equity/drawdown (the daily-loss kill
switch), open option spreads, and in-flight learning attributions all persist to
the DB/KvState, so a mid-month restart resumes without resetting risk state.

### Kill switch

A hard stop that blocks all new entries (positions are held, not liquidated):

```bash
curl -X POST http://localhost:8000/api/kill -H 'Content-Type: application/json' -d '{"engage": true}'   # engage
curl -X POST http://localhost:8000/api/kill -H 'Content-Type: application/json' -d '{"engage": false}'  # release
```

It also engages automatically on a 3% daily loss or sustained feed failure. The
dashboard exposes the same control as a button.

---

## 3. Daily health checks (≈2 minutes)

### 3.1 The health endpoint

```bash
curl -s http://localhost:8000/api/health | python -m json.tool
```

Confirm each field daily:

| Field | Healthy value | If not |
|-------|---------------|--------|
| `status` | `ok` | `degraded` → read the sub-objects below |
| `db_ok` | `true` | DB unreachable — check disk/permissions |
| `kill_switch` | `false` | something tripped it; see logs before resuming |
| `mode` | `PAPER` | must never be a live mode this month |
| `last_bar_age_s` | < ~900 during a session | feed stalled (see watchdog/feed) |
| `market_data.degraded` | `false` in-session | too many symbols on synthetic fallback |
| `market_data.ratio` | ≥ `feed_min_live_ratio` (0.5) | live feed thin; new BUYs are halted |
| `llm.real` | `true` | provider unreachable → SMEs on mock; restart after fixing |
| `watchdog` | healthy | dead-man's switch unhappy |

Outside market hours a low `ratio` / stale `last_bar_age_s` is expected and not
an alert.

### 3.2 The end-of-day digest

A digest is pushed via the notify channel shortly after the 15:30 IST close
(`ATS_DIGEST_HOUR`/`MINUTE`, default 15:45) summarizing P&L and activity. Skim it
for surprises (an outsized loss, an unexpected kill-switch event).

**Email alerts (recommended channel).** The notify funnel emails alerts, the
daily digest, and approval requests over SMTP when configured; the `EmailService`
additionally forwards bus alerts (strategy decay, feed degrade/recover). Set:

```bash
ATS_EMAIL_SMTP_HOST=smtp.gmail.com   # 587 STARTTLS (default) or 465 implicit TLS
ATS_EMAIL_SMTP_USER=you@gmail.com
ATS_EMAIL_SMTP_PASSWORD=your-app-password   # create an App Password (2FA on); never your login
ATS_EMAIL_FROM="ATS Bot <you@gmail.com>"
ATS_EMAIL_TO=you@gmail.com            # comma-separated for multiple recipients
```

All three of host/from/to must be set to enable; otherwise pushes log-only.
Transport is TLS-verified, the password is never logged, and a send failure
never interrupts trading (it logs and the digest/alert still hits the dashboard).

### 3.3 Logs

Rotating JSON logs live under `var/logs/` (10 MB × 10). Quick scan:

```bash
grep -E '"level": "(WARNING|ERROR)"' var/logs/*.log | tail -50
```

Watch for `feed_degraded`, `strategy_decay`, `sme_status_change`,
`learning_horizon_changed`.

---

## 4. What runs automatically

| Job | Cadence | Purpose |
|-----|---------|---------|
| Market-data poll | `ATS_MARKET_SCAN_INTERVAL_S` (60s) | bars → strategies + SMEs |
| News scrape + NLP | continuous | sentiment feeds macro SMEs + the news-sentiment sleeve |
| Learning eval | ~4 min | scores attributions whose **5-day horizon** elapsed |
| Daily digest | 15:45 IST | end-of-day summary push |
| Metrics export | 16:00 IST | `var/metrics/*.parquet` + research log |
| Fundamentals refresh | 24 h | value/quality/size factor inputs |

---

## 5. Backup / restore of `var/ats.db`

The SQLite file is the single source of truth (orders, fills, P&L, sleeves, SME
track records). Back it up daily.

### Backup (consistent snapshot even while running)

```bash
BACKUP_PASSPHRASE='a-long-secret' ./scripts/backup.sh
# writes backups/ats_sqlite_<UTC>.db.gz[.enc], prunes > RETENTION_DAYS (7)
```

Schedule it via cron on the server laptop:

```cron
0 2 * * * BACKUP_PASSPHRASE='a-long-secret' /home/youruser/gsoc/scripts/backup.sh >> /home/youruser/gsoc/var/backup.log 2>&1
```

### Restore

```bash
# 1) stop the server (systemctl stop ats / launchctl unload / compose down)
# 2) decrypt (only if encrypted) + decompress into place
openssl enc -d -aes-256-cbc -pbkdf2 -in backups/ats_sqlite_<UTC>.db.gz.enc \
  -out /tmp/ats.db.gz -pass env:BACKUP_PASSPHRASE
gunzip -c /tmp/ats.db.gz > var/ats.db
# 3) restart the server
```

Keep at least one backup **off** the server laptop (cloud drive / another disk).

---

## 6. Weekly review ritual (≈30 minutes)

### 6.1 Read the week's metrics

Per-strategy and per-SME snapshots are columnar Parquet under `var/metrics/`:

```python
import pandas as pd, glob
strat = pd.concat(pd.read_parquet(f) for f in glob.glob("var/metrics/strategies_*.parquet"))
smes  = pd.concat(pd.read_parquet(f) for f in glob.glob("var/metrics/smes_*.parquet"))
# Rank sleeves by rolling Sharpe; eyeball drawdowns and holdings.
print(strat.sort_values("sleeve_sharpe", ascending=False).tail(20))
print(smes.sort_values(["hit_rate", "n"], ascending=False).head(20))
```

`var/metrics/research_log.jsonl` ties each day's numbers to the **exact params**
that produced them — the reproducibility anchor for A/B comparisons.

### 6.2 Triage decay

Any `strategy_decay` warning in the logs means a sleeve's rolling Sharpe fell
below tolerance. Decide: keep, pause, or re-parameterize (§7). To pause a sleeve
(stop it trading while keeping its track record), set its status to `paused` in
the DB:

```bash
sqlite3 var/ats.db "UPDATE strategies SET status='paused' WHERE id='<strategy_id>';"
```

The strategy service re-reads status on the next start; restart to apply.

### 6.3 Run the promotion gate

```bash
python scripts/run_backtests.py --period 3y            # dry run, review the table
python scripts/run_backtests.py --period 3y --apply    # promote cleared shadows
```

A shadow strategy is promoted to `paper` only if it clears all of:

- **raw Sharpe > 0**,
- **deflated Sharpe ≥ 0.90** (Bailey & López de Prado — discounts the result for
  having searched across ~24 strategies, killing lucky flukes), and
- **≥ `--min-obs` active observations**.

Monte Carlo block-bootstrap drawdowns (`dd95`) are reported so you can size the
tail risk before promoting. Results are saved to
`var/metrics/backtest_gate_<date>.parquet`.

### 6.4 Note SME movements

`sme_status_change` log lines (shadow→paper / demotions) show the learning loop
re-weighting who gets influence, scored on the configurable forward-return
horizon (`ATS_LEARNING_HORIZON_DAYS`, default 5).

---

## 7. Fine-tuning the variables

Every strategy lookback/threshold is **config, not code** (see the
strategy-library block in `ats/core/config.py`), so tuning is an `.env` edit +
restart. Examples:

```bash
ATS_OU_KELTNER_Z_ENTRY=1.25        # require a deeper stretch to fade
ATS_MACD_ADX_MIN=25                # only trade clearly-trending tape
ATS_COINT_ENTRY_Z=2.5              # stricter pairs entry
ATS_FACTOR_SLEEVE_TOP_N=10         # wider factor baskets
ATS_LEARNING_HORIZON_DAYS=10       # judge SME calls on a 2-week horizon
ATS_SLEEVE_ALLOCATION_METHOD=erc_tilt
```

Change one axis at a time, restart, and let the metrics export + research log
record the before/after for the weekly comparison.

---

## 8. Known limitations (acceptable for a paper month)

- **yfinance is delayed**, not exchange-real-time. Fine for a daily-bar swing
  paper test; the watchdog tolerates the delay (`stale_after_s=900`). The Kite
  adapter slot is left clean for a later real-time upgrade.
- **Long-only paper book.** Short legs of factor/pairs/stat-arb strategies are
  recorded as signals but only the long leg trades; noted in the metrics.
- **PEAD uses a price/volume gap proxy** for the earnings event (no SUE feed
  wired in yet) — documented in the strategy docstring.

---

## Academic references

The strategy library is grounded in published research (full citations in each
strategy's docstring):

- Moskowitz, Ooi & Pedersen (2012) — time-series momentum. <https://www.sciencedirect.com/science/article/pii/S0304405X11002613>
- Jegadeesh & Titman (1993) — cross-sectional momentum. <https://www.bauer.uh.edu/rsusmel/phd/jegadeesh-titman93.pdf>
- George & Hwang (2004) — 52-week-high momentum. <https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2004.00695.x>
- Antonacci (2014) — dual momentum.
- Lehmann (1990); Jegadeesh (1990) — short-term reversal.
- Gatev, Goetzmann & Rouwenhorst (2006) — pairs trading. <http://stat.wharton.upenn.edu/~steele/Courses/434/434Context/PairsTrading/PairsTradingGGR.pdf>
- Engle & Granger (1987) — cointegration.
- Fama & French (1992/1993) — value.
- Asness, Frazzini & Pedersen (2019) — Quality Minus Junk.
- Frazzini & Pedersen (2014) — Betting Against Beta / low-vol. <https://pages.stern.nyu.edu/~lpederse/papers/BettingAgainstBeta.pdf>
- Banz (1981) — size.
- Bernard & Thomas (1989) — post-earnings-announcement drift. <https://www.jstor.org/stable/2491062>
- Tetlock (2007) — media sentiment.
- Ariel (1987) — turn-of-the-month seasonality.
- Moreira & Muir (2017) — volatility-managed portfolios.
- Carr & Wu (2009) — variance risk premium (short-vol / iron condor). <https://engineering.nyu.edu/sites/default/files/2019-01/CarrReviewofFinStudiesMarch2009-a.pdf>
- Bailey & López de Prado (2014) — the deflated Sharpe ratio (the promotion gate's anti-overfit statistic).
```
