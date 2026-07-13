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
    ("TMPV.NS", "Tata Motors PV", "Auto", "EQ"),
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
    ("LIQUIDBEES.NS", "Nippon Liquid ETF", "Liquid ETF", "ETF"),
    # Underlying references for ETF NAV arbitrage. COMMODITY instruments are
    # price feeds only — the risk layer vetoes any order for them.
    ("SI=F", "COMEX Silver Futures", "Commodity Futures", "COMMODITY"),
    ("GC=F", "COMEX Gold Futures", "Commodity Futures", "COMMODITY"),
]


# E3: a curated, liquid subset of the NIFTY Midcap universe (not the exact 150 —
# membership drifts; this is a diverse, stable-symbol starter set). Adds the
# cross-sectional *dispersion* the momentum/factor sleeves need. Gated behind
# ATS_UNIVERSE_INCLUDE_MIDCAP so the large-cap-only book stays the reference.
# A wrong/renamed symbol simply contributes no data (skipped), never a crash.
MIDCAP_UNIVERSE: list[tuple[str, str, str, str]] = [
    # Banking & Financials
    ("BANKBARODA.NS", "Bank of Baroda", "Banking & Financials", "EQ"),
    ("PNB.NS", "Punjab National Bank", "Banking & Financials", "EQ"),
    ("IDFCFIRSTB.NS", "IDFC First Bank", "Banking & Financials", "EQ"),
    ("FEDERALBNK.NS", "Federal Bank", "Banking & Financials", "EQ"),
    ("CHOLAFIN.NS", "Cholamandalam Investment", "Banking & Financials", "EQ"),
    ("MUTHOOTFIN.NS", "Muthoot Finance", "Banking & Financials", "EQ"),
    ("SBICARD.NS", "SBI Cards", "Banking & Financials", "EQ"),
    ("LICHSGFIN.NS", "LIC Housing Finance", "Banking & Financials", "EQ"),
    # IT / Tech
    ("PERSISTENT.NS", "Persistent Systems", "IT", "EQ"),
    ("COFORGE.NS", "Coforge", "IT", "EQ"),
    ("MPHASIS.NS", "Mphasis", "IT", "EQ"),
    ("OFSS.NS", "Oracle Financial Services", "IT", "EQ"),
    # Auto & ancillaries
    ("TVSMOTOR.NS", "TVS Motor", "Auto", "EQ"),
    ("ASHOKLEY.NS", "Ashok Leyland", "Auto", "EQ"),
    ("BHARATFORG.NS", "Bharat Forge", "Auto", "EQ"),
    ("BALKRISIND.NS", "Balkrishna Industries", "Auto", "EQ"),
    ("MRF.NS", "MRF", "Auto", "EQ"),
    # Pharma & Healthcare
    ("LUPIN.NS", "Lupin", "Pharma", "EQ"),
    ("AUROPHARMA.NS", "Aurobindo Pharma", "Pharma", "EQ"),
    ("TORNTPHARM.NS", "Torrent Pharma", "Pharma", "EQ"),
    ("ALKEM.NS", "Alkem Laboratories", "Pharma", "EQ"),
    ("ZYDUSLIFE.NS", "Zydus Lifesciences", "Pharma", "EQ"),
    ("MAXHEALTH.NS", "Max Healthcare", "Healthcare", "EQ"),
    ("FORTIS.NS", "Fortis Healthcare", "Healthcare", "EQ"),
    # Metals & Mining
    ("SAIL.NS", "Steel Authority of India", "Metals", "EQ"),
    ("NMDC.NS", "NMDC", "Metals", "EQ"),
    ("JINDALSTEL.NS", "Jindal Steel & Power", "Metals", "EQ"),
    ("NATIONALUM.NS", "National Aluminium", "Metals", "EQ"),
    ("HINDZINC.NS", "Hindustan Zinc", "Metals", "EQ"),
    # Cement & Infra
    ("AMBUJACEM.NS", "Ambuja Cements", "Cement", "EQ"),
    ("ACC.NS", "ACC", "Cement", "EQ"),
    ("DALBHARAT.NS", "Dalmia Bharat", "Cement", "EQ"),
    # Power & Energy
    ("TATAPOWER.NS", "Tata Power", "Power", "EQ"),
    ("GAIL.NS", "GAIL India", "Energy", "EQ"),
    ("PETRONET.NS", "Petronet LNG", "Energy", "EQ"),
    ("IGL.NS", "Indraprastha Gas", "Energy", "EQ"),
    ("TORNTPOWER.NS", "Torrent Power", "Power", "EQ"),
    # Consumer & Retail
    ("GODREJCP.NS", "Godrej Consumer", "FMCG", "EQ"),
    ("DABUR.NS", "Dabur India", "FMCG", "EQ"),
    ("MARICO.NS", "Marico", "FMCG", "EQ"),
    ("COLPAL.NS", "Colgate-Palmolive India", "FMCG", "EQ"),
    ("VBL.NS", "Varun Beverages", "FMCG", "EQ"),
    ("TRENT.NS", "Trent", "Retail", "EQ"),
    ("JUBLFOOD.NS", "Jubilant FoodWorks", "Retail", "EQ"),
    # Chemicals
    ("PIDILITIND.NS", "Pidilite Industries", "Chemicals", "EQ"),
    ("SRF.NS", "SRF", "Chemicals", "EQ"),
    ("DEEPAKNTR.NS", "Deepak Nitrite", "Chemicals", "EQ"),
    # Capital goods / Industrials
    ("BEL.NS", "Bharat Electronics", "Defence", "EQ"),
    ("HAL.NS", "Hindustan Aeronautics", "Defence", "EQ"),
    ("CUMMINSIND.NS", "Cummins India", "Industrials", "EQ"),
    ("POLYCAB.NS", "Polycab India", "Industrials", "EQ"),
    ("HAVELLS.NS", "Havells India", "Consumer Durables", "EQ"),
    ("VOLTAS.NS", "Voltas", "Consumer Durables", "EQ"),
    ("DIXON.NS", "Dixon Technologies", "Consumer Durables", "EQ"),
    # Realty & travel
    ("GODREJPROP.NS", "Godrej Properties", "Realty", "EQ"),
    ("OBEROIRLTY.NS", "Oberoi Realty", "Realty", "EQ"),
    ("INDHOTEL.NS", "Indian Hotels", "Consumer Services", "EQ"),
    ("IRCTC.NS", "IRCTC", "Consumer Services", "EQ"),
]


def active_universe(include_midcap: bool | None = None) -> list[tuple[str, str, str, str]]:
    """The instrument universe to seed. Large-cap core always; the curated
    NIFTY Midcap set appended when ``ATS_UNIVERSE_INCLUDE_MIDCAP`` is on (E3).
    ``include_midcap`` overrides the config (used by tests)."""
    if include_midcap is None:
        from ats.core.config import get_settings

        include_midcap = get_settings().universe_include_midcap
    return UNIVERSE + MIDCAP_UNIVERSE if include_midcap else list(UNIVERSE)


# Strategy registry: (id, name, type, status)
STRATEGIES: list[tuple[str, str, str, str]] = [
    # The core ballast (plan §2): regime-aware ETF allocation. Paper from
    # day 1 by design — it is the medium loop's primary earner, not an alpha
    # experiment awaiting a gate.
    ("core_allocation", "Core Allocation (regime-aware ETF ballast)", "allocation", "paper"),
    ("sma_crossover", "SMA 20/50 Crossover", "trend", "paper"),
    ("mean_reversion", "Bollinger Mean Reversion", "mean_reversion", "paper"),
    ("volume_breakout", "Volume Breakout", "momentum", "shadow"),
    ("donchian_trend", "Donchian 55/20 Trend Following", "trend", "paper"),
    ("rsi2_reversion", "RSI(2) Pullback in Uptrend", "mean_reversion", "paper"),
    ("ts_momentum", "12-1 Time-Series Momentum", "momentum", "paper"),
    ("pairs_zscore", "Pairs Z-Score (stat arb)", "stat_arb", "paper"),
    ("factor_composite", "Momentum + Low-Vol Factor Composite", "factor", "paper"),
    ("nav_premium", "ETF NAV Premium/Discount Arbitrage", "arbitrage", "paper"),
    # Phase-2 strategy-library expansion. All start as "shadow": signals are
    # logged and a virtual track record accrues, but no capital is allocated
    # until the walk-forward backtest gate promotes them to "paper".
    ("xs_momentum", "Cross-Sectional 12-1 Momentum", "momentum", "shadow"),
    ("high_52w", "52-Week-High Momentum", "momentum", "shadow"),
    ("dual_momentum", "Dual (Absolute + Relative) Momentum", "momentum", "shadow"),
    ("macd_adx_trend", "MACD Trend + ADX Filter", "trend", "shadow"),
    ("st_reversal", "Short-Term (1-Week) Reversal", "mean_reversion", "shadow"),
    ("ou_keltner", "Keltner Z-Score Mean Reversion", "mean_reversion", "shadow"),
    ("value_factor", "Value (FF) Factor Sleeve", "factor", "shadow"),
    ("quality_qmj", "Quality (QMJ) Factor Sleeve", "factor", "shadow"),
    ("size_factor", "Size (Banz) Factor Sleeve", "factor", "shadow"),
    ("low_vol_bab", "Low-Volatility / Betting-Against-Beta", "factor", "shadow"),
    ("coint_pairs", "Cointegration Pairs (Engle-Granger)", "stat_arb", "shadow"),
    ("pead_drift", "Post-Earnings-Announcement Drift", "momentum", "shadow"),
    ("news_sentiment", "News-Sentiment Momentum", "momentum", "shadow"),
    ("turn_of_month", "Turn-of-Month Seasonality", "other", "shadow"),
    ("vol_target", "Volatility-Managed Exposure Overlay", "other", "shadow"),
    ("vol_premium", "Iron Condor — Variance Risk Premium", "vol", "paper"),
    # QA-8: analytics-engine confluence sleeve (shadow until the gate promotes it).
    ("tech_confluence", "Confluence: composite summary + level support", "trend", "shadow"),
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
