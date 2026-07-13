#!/usr/bin/env python
"""Bellwether Phase 0 - GDELT data-feasibility spike.

The whole "market-mover news" strategy (docs/plans/market_mover_news_strategy.plan.md)
hinges on ONE question we must answer before writing any trading code:

    Can we get a COMPLETE, correctly-DATED, 3-year stream of public statements /
    news mentioning market-moving figures - mechanically, for free?

This script probes the free **GDELT 2.0 DOC API** (no key) for a handful of
figures and reports whether the corpus is rich and dated enough to backtest on:

  * mode=timelinetone  -> a daily time series of article VOLUME + average TONE
    for the query over the whole window (this is the "is it dated + does it span
    3 years + does it carry sentiment" proof).
  * mode=artlist       -> a small sample of real dated headlines (so you can eyeball
    that the matches are on-topic and the timestamps are real).

It saves per-figure JSON + a summary to var/bellwether/gdelt_spike/ and prints a
plain verdict per figure (rich / thin / unavailable). Nothing here trades or
touches the book - it is pure data reconnaissance.

Tone note: GDELT's tone is a coarse cross-check; the real pipeline scores tone
with our own FinBERT (see the plan). This spike only needs to prove the *dated
corpus* exists.

Usage:
    python scripts/gdelt_spike.py                 # default 5 figures, 3 years
    python scripts/gdelt_spike.py --years 3 --figures modi,gadkari,trump
    python scripts/gdelt_spike.py --sample 15     # more sample headlines
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
_OUT_DIR = _REPO_ROOT / "var" / "bellwether" / "gdelt_spike"

# The spike roster: a couple of India-direct figures (the cleanest signal), a
# couple of global movers, and one macro body. Query strings use quotes so GDELT
# matches the phrase. English-language filter keeps it tractable.
FIGURES: dict[str, str] = {
    "modi": '"Narendra Modi"',
    "gadkari": '"Nitin Gadkari"',
    "rbi": '"Reserve Bank of India"',
    "trump": '"Donald Trump"',
    "musk": '"Elon Musk"',
}


def _gdelt(params: dict) -> dict | None:
    """One GDELT DOC API call -> parsed JSON, or None on any failure."""
    import httpx

    q = {"format": "json", "sourcelang": "english", **params}
    try:
        resp = httpx.get(_GDELT_DOC, params=q, timeout=40.0,
                         headers={"User-Agent": "bellwether-spike/0.1"})
        resp.raise_for_status()
        # GDELT sometimes returns an HTML error page with a 200 - guard the parse.
        ctype = resp.headers.get("content-type", "")
        if "json" not in ctype and not resp.text.lstrip().startswith("{"):
            return {"_error": f"non-JSON response ({ctype}): {resp.text[:120]}"}
        return resp.json()
    except Exception as exc:  # noqa: BLE001 - reconnaissance, never raise
        return {"_error": str(exc)}


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


def probe_figure(name: str, query: str, start: datetime, end: datetime,
                 sample: int, delay: float) -> dict:
    """Pull the tone timeline + a headline sample for one figure. ``delay`` is
    the pause between calls — GDELT's free DOC API rate-limits by IP (HTTP 429)
    if you fire calls back-to-back, so keep this at a few seconds."""
    win = {"query": query, "startdatetime": _fmt(start), "enddatetime": _fmt(end)}

    tone = _gdelt({**win, "mode": "timelinetone", "timelinesmooth": "0"})
    time.sleep(delay)  # be polite to the free API (avoid 429)
    arts = _gdelt({**win, "mode": "artlist", "maxrecords": str(sample),
                   "sort": "datedesc"})
    time.sleep(delay)

    # --- parse the tone timeline into (date, tone) points ---
    points: list[dict] = []
    tone_err = tone.get("_error") if isinstance(tone, dict) else "no data"
    if isinstance(tone, dict) and "timeline" in tone:
        series = tone.get("timeline") or []
        data = series[0].get("data", []) if series else []
        for d in data:
            try:
                points.append({"date": d["date"][:8], "tone": float(d["value"])})
            except Exception:  # noqa: BLE001
                continue
        tone_err = None

    # --- parse the article sample ---
    articles: list[dict] = []
    if isinstance(arts, dict):
        for a in (arts.get("articles") or [])[:sample]:
            articles.append({
                "seendate": a.get("seendate", ""),
                "title": (a.get("title", "") or "")[:160],
                "domain": a.get("domain", ""),
                "country": a.get("sourcecountry", ""),
                "url": a.get("url", ""),
            })

    tones = [p["tone"] for p in points]
    covered_days = len({p["date"] for p in points})
    span_days = max(1, (end - start).days)
    return {
        "figure": name,
        "query": query,
        "tone_points": len(points),
        "covered_days": covered_days,
        "coverage_pct": round(100.0 * covered_days / span_days, 1),
        "mean_tone": round(sum(tones) / len(tones), 3) if tones else None,
        "first_date": points[0]["date"] if points else None,
        "last_date": points[-1]["date"] if points else None,
        "sample": articles,
        "error": tone_err,
    }


def _verdict(r: dict) -> str:
    if r["error"] or r["tone_points"] == 0:
        return "UNAVAILABLE"
    # ~daily coverage over 3y is rich; sparse is thin.
    if r["coverage_pct"] >= 40 and r["tone_points"] >= 200:
        return "RICH"
    if r["tone_points"] >= 50:
        return "THIN"
    return "SPARSE"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", type=int, default=3, help="lookback window (years)")
    ap.add_argument("--figures", default=None,
                    help="comma-separated subset of: " + ",".join(FIGURES))
    ap.add_argument("--sample", type=int, default=10, help="headline samples per figure")
    ap.add_argument("--delay", type=float, default=5.0,
                    help="seconds between GDELT calls (raise if you hit HTTP 429)")
    args = ap.parse_args()

    wanted = FIGURES
    if args.figures:
        keys = {k.strip() for k in args.figures.split(",") if k.strip()}
        wanted = {k: v for k, v in FIGURES.items() if k in keys}
        if not wanted:
            print(f"No known figures in {args.figures!r}. Known: {', '.join(FIGURES)}")
            return

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=int(365.25 * args.years))
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"GDELT spike: {len(wanted)} figures over {args.years}y "
          f"({start.date()} -> {end.date()}). Probing the free DOC API...\n")

    results = []
    for name, query in wanted.items():
        r = probe_figure(name, query, start, end, args.sample, args.delay)
        r["verdict"] = _verdict(r)
        results.append(r)
        (_OUT_DIR / f"{name}.json").write_text(json.dumps(r, indent=2))
        print(f"[{r['verdict']:11}] {name:9} {query:24} "
              f"{r['tone_points']:>5} dated tone-points, "
              f"{r['coverage_pct']:>5}% of days, mean tone "
              f"{r['mean_tone'] if r['mean_tone'] is not None else 'n/a'}"
              + (f"  ERROR: {r['error']}" if r["error"] else ""))
        if r["sample"]:
            top = r["sample"][0]
            print(f"              e.g. {top['seendate']} [{top['country']}] {top['title']}")

    (_OUT_DIR / "summary.json").write_text(json.dumps(
        {"generated": end.isoformat(), "years": args.years, "results": results}, indent=2))

    rich = [r["figure"] for r in results if r["verdict"] == "RICH"]
    print("\n" + "=" * 78)
    print("VERDICT")
    print("-" * 78)
    if rich:
        print(f"  GDELT returned a rich, dated, tone-carrying corpus for: {', '.join(rich)}.")
        print("  -> Phase 0 PASSES for these figures; proceed to P1 (build the collector).")
    else:
        rate_limited = any("429" in (r["error"] or "") for r in results)
        dns = any("getaddrinfo" in (r["error"] or "") or "handshake" in (r["error"] or "")
                  for r in results)
        print("  No figure came back rich.")
        if rate_limited:
            print("  -> HTTP 429 seen: GDELT rate-limited us. Re-run with a larger --delay (e.g. 10).")
        if dns:
            print("  -> DNS/TLS failures: this host has no outbound internet. Run on an open network.")
        print("  Re-run on an open network before committing to the 3-year backtest; if GDELT")
        print("  stays thin even then, pivot to the live-forward version (collect from today).")
    print(f"\n  Per-figure JSON + samples saved to {_OUT_DIR}")


if __name__ == "__main__":
    main()
