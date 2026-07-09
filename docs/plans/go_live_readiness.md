# Go-live readiness plan

This is the standing plan for the work requested before going live (the
"email + dashboard numbers + order log + deep analysis" prompt), plus the two
follow-ups (Gemini resilience, LLM/Logs tabs). It records **what's done, how to
verify it, and what's left**. Most of it is already built — the only true
blocker is filling in email credentials.

Legend: ✅ done · 🟡 needs your input · ⏳ optional / later

---

## Plan inventory (where the plans live)

In-project (`docs/plans/`):
- `agentic_trading_server_67829fae.plan.md` — the master build plan
- `month-long_paper_run_59c0fb01.plan.md` — the unattended paper-run plan
- `results-first_dashboard_redesign_6131c9dc.plan.md` — dashboard IA
- `architecture_documentation_46947af0.plan.md` — docs plan
- `gemini_upgrade_and_resilience_11304d15.plan.md` — **just copied in** from `~/.cursor/plans/`
- `go_live_readiness.md` — this file

On the device but **not** project-related (left in `~/.cursor/plans/`): netgraph,
ldpc_5g_nr, freebsd_mpls, yomu_ipad, notion_life_os, whatsapp-to-ai, fix_ubuntu.
These are other projects — not copied in.

---

## 1. Email alerts & digests 🟡 (only credentials remain)

**Built:** event-driven email on `Topic.ALERT` (`ats/services/email/service.py`,
`transport.py`), the `notify()` funnel prefers email, and a 2–3/day digest
scheduler (intraday status emails + the authoritative close digest) in
`ats/services/execution/service.py` (`push_intraday_digest`). Sudden-move alerts
go out via the mover detector.

**What's left (you):** the `.env` email block is still commented out, so it's
log-only right now. To turn it on:
1. Gmail → turn on 2-Step Verification, then create an **App Password**
   (myaccount.google.com/apppasswords, type "Mail").
2. In `.env`, uncomment and fill the `ATS_EMAIL_*` block (use the 16-char app
   password, not your Gmail password):
   ```ini
   ATS_EMAIL_SMTP_HOST=smtp.gmail.com
   ATS_EMAIL_SMTP_PORT=587
   ATS_EMAIL_SMTP_USER=you@gmail.com
   ATS_EMAIL_SMTP_PASSWORD=your-16-char-app-password
   ATS_EMAIL_FROM=ATS Bot <you@gmail.com>
   ATS_EMAIL_TO=you@gmail.com
   ATS_EMAIL_USE_TLS=true
   ATS_DIGEST_INTRADAY_HOURS=[10,13]
   ```
3. Restart the server. **Verify:** you should receive the next scheduled
   intraday digest; or trigger an alert to confirm delivery.

---

## 2. Real dashboard numbers (no more random P&L) ✅

**Was:** corrupted/duplicated test fills made investments & P&L look random.
**Fixed:** `scripts/reset_paper_book.py` resets the paper book to clean starting
capital (with a timestamped `ats.db` backup), and a **dedupe-fill guard** in the
execution service prevents a `decision_id` from being filled twice.

**Verify:** dashboard equity/P&L reconcile with the trade blotter. If numbers
ever look off again: stop the server, run
`.venv/bin/python scripts/reset_paper_book.py` (backs up first), restart.

---

## 3. Order log with the "why" ✅

**Built:** `/api/activity` joins `Fill → Order → Decision → SmeOpinion → Signal`
to produce, per order: the CIO rationale, the **experts** who weighed in (stance,
conviction, rationale, risks), the **strategy signals** that fired (with their
features = "what the strategy thought"), and the **risk rules** applied.

**Verify:** open **Activity** → each order expands into its full reasoning.

---

## 4. Always-on log tab + "what's going on now" + email summary ✅

**Built:**
- **Activity** tab (`/activity`) — the order log above, always available.
- A live "what's going on right now" summary (`ats/services/dashboard/summary.py`,
  `/api/summary`) shown on Activity and embedded in the email digests.
- The 2–3/day email digest scheduler (see #1) carries that summary; sudden moves
  are emailed as alerts.
- **New this session:** an **LLM** tab (every Gemini question + answer) and a
  **Logs** tab (live tail of the app log). See the resilience plan + below.

---

## 5. Deep-analysis tool ✅ (research done; here's how to proceed)

**Research — what an NSE/BSE company publishes (SEBI LODR):** captured in code as
`LODR_CHECKLIST` (`ats/services/research/disclosures.py`). The high-value docs:

| Document | Reg | Cadence | Why it matters |
| --- | --- | --- | --- |
| Quarterly results | 33 | Quarterly, ≤45d (Q4 ≤60d) | Hard numbers: revenue, PAT, EBITDA, margins, segments, YoY/QoQ |
| **Earnings-call transcript** | 30 | ≤5 working days after the call | **Richest source** — management plans, guidance, analyst Q&A |
| Investor presentation | 30 | Before the call | Strategy, segment outlook, capex, demand commentary |
| Shareholding pattern | 31 | Quarterly, ≤21d | Promoter/FII/DII flows; promoter pledging = red flag |
| Annual report | 34 | Annual | MD&A (strategy + risks), BRSR (ESG), auditor's report |
| Governance report | 27 | Quarterly | Board/committee quality signals |
| Event disclosure | 30 | ≤24h | Catalysts: M&A, dividends, KMP changes, large orders |

**Built:** `ats/services/research/disclosures.py` (fetch + auto-classify by
filename/URL, proxy-resilient via `truststore`) and `extractors.py` (PDF→text via
`pdfplumber`/`pypdf`, then heuristic extraction of financial highlights, guidance,
risks, capex, management commentary). CLI: `scripts/analyze_company.py`.

**How to proceed (you):**
1. See the checklist: `.venv/bin/python scripts/analyze_company.py --checklist`
2. Analyze a company from its investor-relations URLs or local PDFs:
   ```bash
   .venv/bin/python scripts/analyze_company.py --symbol RELIANCE \
     --doc <transcript_url_or_path> --doc <results_url_or_path> --download --json
   ```
   (Best inputs: the **earnings-call transcript** + latest **quarterly results**.)

**Next upgrades (⏳):** auto-discovery from BSE/NSE announcement feeds (currently
operator-provided URLs because those feeds are anti-bot/proxy-blocked); feed the
extracted highlights into an SME persona as grounded RAG context; optional
`pip install pdfplumber` for best PDF extraction.

---

## 6. Gemini upgrade & resilience ✅ (this session)

Full detail in `docs/plans/gemini_upgrade_and_resilience_11304d15.plan.md` and
`docs/llm_provider.md`. Summary: Tier-1 key in use; both SME & CIO on
`gemini-2.5-flash`; retry/backoff (honors `Retry-After`), **recoverable** mock
fallback with auto re-probe (no more session-long downgrade), optional rate cap,
and live `/api/health.llm` status. Blocking LLM calls now run off the event loop
so the dashboard stays responsive.

> Note: Gemini has been throwing transient `503`s today; the resilience layer
> rides them out and auto-recovers — no action needed.

---

## 7. LLM & Logs tabs ✅ (this session)

- **LLM** (`/llm`): history of every real Gemini call — prompt, response, model,
  persona/symbol, latency, tokens, OK/error. Persisted to `llm_calls` (survives
  restarts, auto-trimmed). Filter by type/status; auto-refresh.
- **Logs** (`/logs`): live tail of `var/logs/ats.log` with level filter + search.

---

## Remaining before go-live (the short list)

- 🟡 **Email**: fill the `.env` `ATS_EMAIL_*` block + restart, confirm a digest
  arrives. (Item #1 — the only real blocker.)
- 🟡 **Smoke a market day**: during NSE hours, confirm Activity logs real orders
  with reasoning, the LLM tab fills with opinion calls, and equity/P&L reconcile.
- ⏳ **Budget alert**: set a Google Cloud billing budget alert (see
  `docs/llm_provider.md`).
- ⏳ **Deep-analysis**: optionally `pip install pdfplumber`; run a first company
  end-to-end and decide whether to wire highlights into an SME persona.
- ⏳ **Auto-discovery** of disclosures from BSE/NSE feeds (nice-to-have).
