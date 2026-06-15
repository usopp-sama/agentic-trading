# Market & Quant primer (Family A)

## Trend following
A trend is the tendency of price to persist in one direction. Trend followers
buy strength and sell weakness, accepting many small losses in exchange for a
few large wins. Classic confirmation: price above a long moving average (e.g.
200-day SMA) and a faster average above a slower one (e.g. 20 over 50). The
edge is behavioural — investors underreact to news, so moves extend. Trends
fail in choppy, range-bound regimes; that is when trend sleeves bleed.

## Momentum
Cross-sectional momentum buys the strongest names and shorts the weakest over a
lookback (commonly 12 months, skipping the most recent month to avoid
short-term reversal). Time-series momentum trades each asset on its own past
return. Momentum is one of the most robust anomalies across markets and
decades, but it suffers sharp "momentum crashes" when a falling market snaps
back violently.

## Mean reversion
Prices oscillate around a fair value; extremes tend to revert. Tools: RSI
(oversold below ~30, overbought above ~70), Bollinger %b (position within bands),
distance from a moving average. The danger is fading a genuine trend — a cheap
stock can get cheaper. A long-term trend filter (only buy dips that are above
the 200-day average) keeps mean reversion from catching falling knives.

## Volume and breakouts
Volume confirms conviction. A breakout to new highs on heavy volume is more
trustworthy than one on thin volume (often a fakeout). A volume z-score (today's
volume vs its 20-day mean in standard deviations) flags unusual participation.

## Volatility
ATR (average true range) measures typical daily range and is used to size
positions and set stops in price-agnostic terms. Higher volatility means
smaller position sizes for the same risk budget.

## Valuation (quant value)
Cheapness is relative: a stock's P/E or P/B versus its sector and history.
Negative earnings make P/E meaningless. Value works over long horizons and can
underperform for years; pair it with quality (high ROE, low debt) to avoid value
traps.

## Reading signals here
Signals are normalized to [-1, +1]: positive is bullish, magnitude is strength.
Conviction is your confidence the signal is real, not the size of the expected
move. Always name the dominant driver and the main risk.
