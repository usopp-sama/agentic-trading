# NSE Market Structure Primer

This shared primer grounds every expert in how the Indian cash-equity market
actually works. It is reference material, not trading advice.

## Trading sessions and hours (IST)
- Pre-open session: 09:00-09:15 (order collection 09:00-09:08, matching 09:08-09:12).
- Continuous (normal) session: 09:15-15:30.
- Closing session / post-close: 15:40-16:00 at the day's close price.
- Equities settle on a T+1 rolling basis (India moved fully to T+1 in 2023).
- The market is closed on weekends and on NSE-published trading holidays. A one-off
  evening "Muhurat" session runs on Diwali.

## Key indices
- NIFTY 50 (ticker ^NSEI): 50 large-cap blue chips, the headline benchmark.
- NIFTY Bank (^NSEBANK): the most-traded sectoral index, banking heavyweights.
- NIFTY 100 / NIFTY 500: broader large- and multi-cap baskets.
- India VIX: implied-volatility gauge derived from NIFTY option prices; spikes in
  stress, mean-reverts in calm regimes.

## Circuit limits and halts
- Individual stocks have price bands (2%, 5%, 10%, or 20%) that cap a single day's move.
- Index-level circuit breakers halt the whole market at 10%, 15%, and 20% moves, with
  halt durations that lengthen later in the day.
- A stock at its band ("upper/lower circuit") may be hard to exit; treat band proximity
  as a liquidity risk.

## Transaction costs (cash delivery, indicative)
- Brokerage: often zero for delivery at discount brokers; intraday capped per order.
- STT (Securities Transaction Tax): ~0.1% on both buy and sell for delivery.
- Exchange transaction charges, SEBI turnover fee, GST on (brokerage + txn charges),
  and stamp duty on the buy side.
- Net round-trip friction for delivery is small but non-zero; intraday and F&O differ.
  Always evaluate edge net of these costs.

## Liquidity and tradability
- NIFTY 100 names are generally liquid; small/mid-caps can have wide spreads and gaps.
- Avoid sizing into names where your order is large versus average daily volume.
- Corporate actions (splits, bonuses, dividends, rights) adjust prices; use adjusted
  series for signals and watch ex-dates.

## Derivatives context
- Index and single-stock F&O exist with defined lot sizes; weekly and monthly expiries.
- Option premiums embed an implied-volatility view; selling premium harvests the
  variance risk premium but carries tail risk (defined-risk structures cap it).
