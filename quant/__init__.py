"""Quant Finance toolkit.

A learning-oriented but production-minded toolkit for market analysis:
data ingestion, technical/fundamental analysis, screening, backtesting,
and risk-based position sizing.

Modules
-------
- ``quant.data``      : fetching market data and persisting it locally
- ``quant.analysis``  : technical indicators, valuation, screening, regime
- ``quant.backtest``  : a simple vectorized signal backtester
- ``quant.risk``      : position sizing (Kelly, fixed-fractional)
- ``quant.options``   : Black-Scholes pricing, Greeks, implied vol, CRR tree
- ``quant.projects``  : end-to-end mini projects (e.g. ETF NAV analysis)
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
