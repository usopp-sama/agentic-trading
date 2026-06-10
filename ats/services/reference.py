"""Reference/seed data: the v1 universe, strategy registry, baseline rules.

Universe = large-cap NSE names across sectors + key indices + SILVERBEES (ETF)
+ a commodity proxy. Symbols use the yfinance convention (``.NS`` suffix,
``^`` for indices) so the yfinance data source works directly; the synthetic
source ignores the suffix.
"""

from __future__ import annotations

# (symbol, display name, sector, instrument_type)
UNIVERSE: list[tuple[str, str, str, str]] = [
    # Indices
    ("^NSEI", "Nifty 50", "Index", "INDEX"),
    ("^NSEBANK", "Nifty Bank", "Index", "INDEX"),
    # Banking & Financials
    ("HDFCBANK.NS", "HDFC Bank", "Banking & Financials", "EQ"),
    ("ICICIBANK.NS", "ICICI Bank", "Banking & Financials", "EQ"),
    ("SBIN.NS", "State Bank of India", "Banking & Financials", "EQ"),
    ("KOTAKBANK.NS", "Kotak Mahindra Bank", "Banking & Financials", "EQ"),
    ("AXISBANK.NS", "Axis Bank", "Banking & Financials", "EQ"),
    ("BAJFINANCE.NS", "Bajaj Finance", "Banking & Financials", "EQ"),
    ("HDFCLIFE.NS", "HDFC Life", "Banking & Financials", "EQ"),
    # IT
    ("TCS.NS", "Tata Consultancy Services", "IT", "EQ"),
    ("INFY.NS", "Infosys", "IT", "EQ"),
    ("WIPRO.NS", "Wipro", "IT", "EQ"),
    ("HCLTECH.NS", "HCL Technologies", "IT", "EQ"),
    ("TECHM.NS", "Tech Mahindra", "IT", "EQ"),
    # Energy & Power
    ("RELIANCE.NS", "Reliance Industries", "Energy", "EQ"),
    ("ONGC.NS", "ONGC", "Energy", "EQ"),
    ("NTPC.NS", "NTPC", "Power", "EQ"),
    ("POWERGRID.NS", "Power Grid", "Power", "EQ"),
    ("BPCL.NS", "BPCL", "Energy", "EQ"),
    ("IOC.NS", "Indian Oil", "Energy", "EQ"),
    # FMCG
    ("HINDUNILVR.NS", "Hindustan Unilever", "FMCG", "EQ"),
    ("ITC.NS", "ITC", "FMCG", "EQ"),
    ("NESTLEIND.NS", "Nestle India", "FMCG", "EQ"),
    ("BRITANNIA.NS", "Britannia", "FMCG", "EQ"),
    ("TATACONSUM.NS", "Tata Consumer", "FMCG", "EQ"),
    # Auto
    ("MARUTI.NS", "Maruti Suzuki", "Auto", "EQ"),
    ("TATAMOTORS.NS", "Tata Motors", "Auto", "EQ"),
    ("M&M.NS", "Mahindra & Mahindra", "Auto", "EQ"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto", "Auto", "EQ"),
    ("EICHERMOT.NS", "Eicher Motors", "Auto", "EQ"),
    # Pharma & Healthcare
    ("SUNPHARMA.NS", "Sun Pharma", "Pharma", "EQ"),
    ("DRREDDY.NS", "Dr Reddy's", "Pharma", "EQ"),
    ("CIPLA.NS", "Cipla", "Pharma", "EQ"),
    ("DIVISLAB.NS", "Divi's Labs", "Pharma", "EQ"),
    ("APOLLOHOSP.NS", "Apollo Hospitals", "Healthcare", "EQ"),
    # Metals & Mining
    ("TATASTEEL.NS", "Tata Steel", "Metals", "EQ"),
    ("JSWSTEEL.NS", "JSW Steel", "Metals", "EQ"),
    ("HINDALCO.NS", "Hindalco", "Metals", "EQ"),
    ("COALINDIA.NS", "Coal India", "Metals", "EQ"),
    ("VEDL.NS", "Vedanta", "Metals", "EQ"),
    # Cement & Infra
    ("ULTRACEMCO.NS", "UltraTech Cement", "Cement", "EQ"),
    ("GRASIM.NS", "Grasim", "Cement", "EQ"),
    ("LT.NS", "Larsen & Toubro", "Infrastructure", "EQ"),
    # Telecom
    ("BHARTIARTL.NS", "Bharti Airtel", "Telecom", "EQ"),
    # Consumer & Retail
    ("TITAN.NS", "Titan", "Consumer Durables", "EQ"),
    ("ASIANPAINT.NS", "Asian Paints", "Consumer Durables", "EQ"),
    ("DMART.NS", "Avenue Supermarts", "Retail", "EQ"),
    # Realty
    ("DLF.NS", "DLF", "Realty", "EQ"),
    # ETFs / Commodities (your silver interest)
    ("SILVERBEES.NS", "Nippon Silver ETF", "Commodity ETF", "ETF"),
    ("GOLDBEES.NS", "Nippon Gold ETF", "Commodity ETF", "ETF"),
    ("NIFTYBEES.NS", "Nippon Nifty ETF", "Index ETF", "ETF"),
]


# Strategy registry: (id, name, type, status)
STRATEGIES: list[tuple[str, str, str, str]] = [
    ("sma_crossover", "SMA 20/50 Crossover", "trend", "paper"),
    ("mean_reversion", "Bollinger Mean Reversion", "mean_reversion", "paper"),
    ("volume_breakout", "Volume Breakout", "momentum", "shadow"),
    ("donchian_trend", "Donchian 55/20 Trend Following", "trend", "paper"),
    ("rsi2_reversion", "RSI(2) Pullback in Uptrend", "mean_reversion", "paper"),
    ("ts_momentum", "12-1 Time-Series Momentum", "momentum", "paper"),
    ("pairs_zscore", "Pairs Z-Score (stat arb)", "stat_arb", "paper"),
]


# Baseline IMMUTABLE guardrail rules (human-set; the agent cannot change these).
# Stored so they are visible/auditable; enforced in code by the risk manager.
GUARDRAILS: list[dict] = [
    {
        "id": "max_position_pct",
        "scope": "global",
        "rule_type": "guardrail",
        "description": "No single position may exceed the configured percent of capital.",
        "expression": {"metric": "position_pct", "op": "<=", "value": 0.10},
    },
    {
        "id": "max_sector_pct",
        "scope": "global",
        "rule_type": "guardrail",
        "description": "No single sector may exceed the configured percent of capital.",
        "expression": {"metric": "sector_pct", "op": "<=", "value": 0.35},
    },
    {
        "id": "daily_loss_limit",
        "scope": "global",
        "rule_type": "guardrail",
        "description": "Engage kill switch if daily loss exceeds the limit.",
        "expression": {"metric": "daily_loss_pct", "op": "<=", "value": 0.03},
    },
    {
        "id": "no_leverage",
        "scope": "global",
        "rule_type": "guardrail",
        "description": "Gross exposure may not exceed 100 percent (no leverage in v1).",
        "expression": {"metric": "gross_exposure_pct", "op": "<=", "value": 1.00},
    },
    {
        "id": "max_trade_value",
        "scope": "global",
        "rule_type": "guardrail",
        "description": "Absolute per-order notional cap.",
        "expression": {"metric": "trade_value", "op": "<=", "value": 50000.0},
    },
]
