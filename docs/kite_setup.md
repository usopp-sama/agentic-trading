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
3. Set a **Redirect URL** on the app (e.g. `http://127.0.0.1:8000/` — you only
   need to read the `request_token` it appends to the URL).
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
step:

```powershell
.venv/Scripts/python -m scripts.kite_login
```

It prints a login URL → open it, log in, and you'll be redirected to your
app's Redirect URL with `?request_token=XXXX` in the address bar. Paste that
token back into the prompt; it prints the line to add to `.env`:

```
ATS_KITE_ACCESS_TOKEN=the_generated_token
```

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
