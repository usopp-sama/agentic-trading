# Roadmap

Consolidated forward-looking roadmap for the agentic trading project and the
parallel career tracks (paid open-source programs + quant/trading
competitions). Distilled from the "Open source contribution opportunities"
working session and reconciled against the current state of the repo.

Status legend: ✅ shipped · 🔜 next · ⏳ deferred · 📅 scheduled external track ·
🚫 not built yet.

---

## 1. Product roadmap (the trading server)

### 1.1 Shipped (locked decisions now in the codebase)

- ✅ **Live intraday charts** — TradingView **Lightweight Charts v5** candlestick
  view (`ats/server/templates/charts.html`, `ats/server/static/charts.js`).
- ✅ **Pluggable market-data adapter** — `NseLiveSource` (live quotes + 1m/5m/15m
  intraday, no API key, yfinance-backed) wrapped by `ResilientDataSource` with a
  deterministic synthetic fallback (`ats/services/market_data/sources.py`,
  `tests/test_live_adapter.py`). Any source exposing `poll` + `intraday` +
  `quote` drops straight in.
- ✅ **Open-source NSE data first** — covered via the `.NS` yfinance path today;
  `nsefetch` / `niftyterminal` / `indian-stock-market-api` remain candidate
  drop-ins behind the same adapter if a richer live feed is wanted.
- ✅ **Multi-provider LLM client** — `mock` / `ollama` / `openai` / `gemini`
  (currently Gemini) via the unified client builder; config + self-check only.
- ✅ **Free Indian-market news** — RSS + Marketaux collectors (Marketaux
  throttled to the 100/day free tier) → FinBERT/VADER sentiment.
- ✅ **Ops** — multi-page dashboard, LAN access + deployment doc
  ([docs/deployment_lan.md](deployment_lan.md)), daily digest, email alerts,
  Dockerized prod profile.

For the full "what works today" inventory, see the build-status canvas and the
README roadmap mapping.

### 1.2 Next

- 🔜 **ML-based signals with walk-forward validation** — wire learned models into
  the strategy layer, gated by the existing anti-overfitting toolkit
  (`quant/backtest/validation.py`: walk-forward, deflated Sharpe, MC drawdown).
- 🔜 **Fold the experts console into the multi-page dashboard** — unify the SME
  console (living theses, multi-expert debate) into the shared layout.
- 🔜 **Watchlist-relevant news surfacing** — highlight news tied to held / watched
  names on the dashboard.

### 1.3 Deferred (until earned)

- ✅ **Zerodha Kite market data (read-only)** — `KiteLiveSource`
  (`ATS_DATA_SOURCE=kite`): batched live quotes + daily/intraday candles, needs
  only a daily token, degrades to nse_live. `kiteconnect` optional at runtime.
- ⏳ **Zerodha Kite execution adapter** — order path is an intentional stub
  behind `ATS_REAL_MONEY_ENABLED`; open only after the paper track record
  justifies it. `kiteconnect` stays optional in prod requirements.
- ⏳ **Real-money execution path** — same gate; paper-only by design for now.

---

## 2. Quant skills + market-making simulator

- 🚫 **Market-making simulator (roadmap 7.9)** — a simulated order-book / MM loop
  for ETC- and Prosperity-style prep. Not built; this is the main missing piece
  that connects the trading server to the competition track below.
- 🔜 **Foundations** — probability, statistics, linear algebra, time-series, and
  Python/C++ are the prerequisites for the competitions in §4.

---

## 3. Open-source mentorship programs (paid)

Career track A: programs like GSoC that pay for open-source contributions.

| Program | Stipend | Timeline | Notes |
|---|---|---|---|
| Google Summer of Code (GSoC) | ~$1,500–$3,000 | ends ~Sep | The classic |
| MLH Fellowship | Paid stipend | Rolling batches | Open-source track, real projects (React, Rails, …); recruiter-respected |
| **LFX Mentorship** (Linux Foundation) | $3,000–$6,600 | Spring/Summer/Fall | Kubernetes, CNCF, Hyperledger |
| **Outreachy** | ~$7,000 | May / Mar | Focused on underrepresented groups |
| Julia Seasons of Contributions | Varies | Ongoing | Julia ecosystem |
| FOSSASIA Codeheat | Prizes | Oct–Mar | Smaller but active |
| Rails Girls Summer of Code | Stipend | Varies | Ruby/Rails |
| X.Org EVoC | Stipend | Year-round | Graphics / Linux kernel |

**Takeaway:** LFX Mentorship and Outreachy are the strongest GSoC alternatives
by stipend + resume impact; MLH is well-regarded. Stacking 2–3 (GSoC + LFX +
MLH) builds a strong SWE profile.

---

## 4. Quant / trading competitions

Career track B: more math-heavy, more competitive, higher upside (prizes +
direct hiring pipelines).

| Competition | What it is | Indicative window |
|---|---|---|
| **WorldQuant Brain** | Build alphas online; royalties if they go live | 📅 2026-06 → 2026-09 |
| **IMC Prosperity** | Online trading simulation, very popular | 📅 2026-09 → 2026-11 |
| **Two Sigma / Kaggle** | Data-science + finance, time-series / alpha research | 📅 2026-09 → 2027-03 |
| **Jane Street ETC** | Team-based simulated market-making | 📅 2026-12 → 2027-03 |
| Jane Street Puzzles | Monthly math/logic puzzles (janestreet.com/puzzles) | Ongoing |
| Optiver Ready Trader Go | Algorithmic trading challenge | Seasonal |
| Citadel Datathon / Data Open | Data analysis + financial insight | Seasonal |
| JPMC Code for Good | Hackathon → internship pipeline | Seasonal |

### Skills by firm (prep emphasis)
- **Jane Street** — probability, expected value, game theory, mental math, market-making intuition.
- **Two Sigma / Kaggle** — data science, time-series prediction, feature engineering.
- **Citadel / Citadel Securities** — quant research + engineering; strong math + coding.
- **HRT** — low-latency systems, C++, algorithms, competitive programming.
- **Optiver / IMC** — trading intuition under uncertainty, fast decision-making.

### Reading list
- *A Practical Guide to Quantitative Finance Interviews* — Xinfeng Zhou ("Green Book"); go-to for Jane Street / Two Sigma / Citadel.
- *Fifty Challenging Problems in Probability* — Frederick Mosteller.
- Graham (value), Hull (derivatives), López de Prado (ML for finance), Damodaran (valuation); MIT 18.S096.

---

## 5. Recommended sequencing

> **Best of both worlds:** do a GSoC/LFX/MLH program this summer for SWE depth,
> and in parallel start probability + market-microstructure prep to enter the
> quant competitions (IMC Prosperity → Jane Street ETC). Building the
> market-making simulator (§2) is the bridge that lets the trading server double
> as competition prep.
