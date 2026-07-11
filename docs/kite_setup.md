# Kite (Zerodha) setup — historical data + backtesting

yfinance is unreliable on some networks (Yahoo throttles with `401`s), which
makes backtests slow and patchy. Zerodha **Kite Connect** gives clean,
authenticated NSE history. This is **read-only** data — it does *not* enable
live trading (that stays behind the real-money gate, untouched).

## 1. One-time: get API credentials

1. Create a Kite Connect app at **https://developers.kite.trade/** → you get an
   **API key** and **API secret**.
2. Subscribe to Kite Connect and enable the **Historical Data** add-on (the
   `historical_data` endpoint requires it).
3. Set the app's **Redirect URL** to exactly:

   ```
   http://127.0.0.1:8000/kite/callback
   ```

   This is a real route in the running dashboard — Zerodha sends the browser
   back there with `?request_token=…`, and the dashboard exchanges it for the
   access token automatically. (No port clash: it's the same server catching a
   browser redirect, not a second service.) If the dashboard runs on a
   different host/port, match it here.
4. Install the client:

   ```powershell
   pip install kiteconnect
   ```

5. Put the key/secret in `.env`:

   ```
   ATS_KITE_API_KEY=your_api_key
   ATS_KITE_API_SECRET=your_api_secret
   ```

## 2. Daily: get an access token

Kite access tokens expire every morning (~6 AM IST), so this is a once-a-day
step. Two ways:

**A) One click from the dashboard (recommended).** With the server running,
open the **Ops Console** (`/ops`) → the **Kite** card → **Login with Zerodha**.
Log in; Zerodha redirects to `/kite/callback`, the dashboard exchanges the
`request_token`, and stores the access token at runtime (in the DB) — so it
works immediately *and* the backtest process picks it up. The card flips to
`token active`. Nothing to copy-paste. (The success page also shows the
`ATS_KITE_ACCESS_TOKEN=…` line if you'd like to add it to `.env` so it survives
a restart.)

**B) Command line.** If you're not running the server:

```powershell
.venv/Scripts/python -m scripts.kite_login
```

It prints a login URL → log in → paste the `request_token` from the redirect
URL back into the prompt; it prints `ATS_KITE_ACCESS_TOKEN=…` to add to `.env`.

## 3. Backtest every strategy on Kite history

```powershell
# All strategies, walk-forward, over the last year of authenticated NSE data:
.venv/Scripts/python scripts/run_backtests.py --kite --period 1y

# Longer window:
.venv/Scripts/python scripts/run_backtests.py --kite --period 3y

# Promote the shadow strategies that clear the gate to 'paper':
.venv/Scripts/python scripts/run_backtests.py --kite --period 1y --apply
```

The harness replays each per-symbol and universe strategy over the price panel,
scores it with annualized Sharpe + the **deflated Sharpe ratio** (multiple-
testing aware) + Monte-Carlo drawdowns, and reports which shadow sleeves clear
the promotion bar. `--apply` flips the winners from `shadow` to `paper` in the
DB so they start taking (paper) capital. Without `--apply` it's a read-only dry
run.

> **Reading the turmoil year:** a strategy that clears the deflated-Sharpe bar
> over the last 12 months has survived a genuinely adversarial tape (wars,
> rate shocks). Trend/momentum sleeves tend to do well in trending stress;
> mean-reversion suffers in gaps. The report shows each sleeve's Sharpe so you
> can see who held up.

## Live trading is still off

This only wires **historical data**. Order placement still routes through the
`KiteAdapter`, which hard-refuses unless `ATS_REAL_MONEY_ENABLED=true` **and**
the compliance checklist is done. Reading candles never touches that path.
