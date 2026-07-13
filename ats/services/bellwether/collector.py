"""Historical statement collector (Bellwether P1).

For each figure in the registry, pull from GDELT:
  * a daily TONE series + a daily VOLUME series (merged into one frame) — the
    signal the event-backtest (P4) will trade,
  * a sample of dated headlines — for auditing that the matches are on-topic.

Writes a per-figure corpus under ``var/bellwether/corpus/`` and a manifest with
coverage stats + a RICH/THIN/UNAVAILABLE verdict (same bar as the Phase-0 spike).
Best-effort per figure: one figure failing (e.g. a transient 429 after retries)
never aborts the rest.

This is the collection layer only — mapping statements to tickers (P2) and
scoring/backtesting (P3/P4) come later. GDELT's own tone is stored now; our
FinBERT can re-score the headline text in P3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ats.core.config import DATA_DIR
from ats.core.logging import get_logger
from ats.services.bellwether.figures import Figure, get_figures
from ats.services.bellwether.gdelt import GdeltClient

log = get_logger("ats.bellwether.collector")

CORPUS_DIR = Path(DATA_DIR) / "bellwether" / "corpus"


@dataclass
class FigureCorpus:
    figure: str
    market: str
    daily: pd.DataFrame          # index=date, cols=[tone, volume]
    headlines: list[dict]
    verdict: str

    def stats(self) -> dict:
        d = self.daily
        return {
            "figure": self.figure,
            "market": self.market,
            "tone_points": int(len(d)),
            "first_date": d.index.min().isoformat() if len(d) else None,
            "last_date": d.index.max().isoformat() if len(d) else None,
            "mean_tone": round(float(d["tone"].mean()), 3) if len(d) else None,
            "headlines": len(self.headlines),
            "verdict": self.verdict,
        }


def _merge_daily(tone: list[dict], volume: list[dict]) -> pd.DataFrame:
    """(tone series, volume series) -> a date-indexed frame [tone, volume]. Pure."""
    if not tone:
        return pd.DataFrame(columns=["tone", "volume"])
    t = pd.DataFrame(tone).rename(columns={"value": "tone"})
    frame = t.set_index("date")
    if volume:
        v = pd.DataFrame(volume).rename(columns={"value": "volume"}).set_index("date")
        frame = frame.join(v, how="left")
    if "volume" not in frame:
        frame["volume"] = pd.NA
    frame.index = pd.to_datetime(frame.index)
    return frame.sort_index()


def _verdict(daily: pd.DataFrame, start: date, end: date) -> str:
    n = len(daily)
    if n == 0:
        return "UNAVAILABLE"
    span = max(1, (end - start).days)
    coverage = 100.0 * daily.index.normalize().nunique() / span
    if coverage >= 40 and n >= 200:
        return "RICH"
    return "THIN" if n >= 50 else "SPARSE"


def collect_figure(client: GdeltClient, figure: Figure, start: date, end: date,
                   sample: int = 25) -> FigureCorpus:
    """Pull one figure's daily tone/volume + headline sample. Best-effort."""
    try:
        tone = client.timeline_tone(figure.query, start, end)
        volume = client.timeline_volume(figure.query, start, end)
        headlines = client.artlist(figure.query, start, end, maxrecords=sample)
    except Exception as exc:  # noqa: BLE001 - one figure failing must not abort the run
        log.warning("figure_collect_failed", extra={"figure": figure.key, "error": str(exc)})
        tone, volume, headlines = [], [], []
    daily = _merge_daily(tone, volume)
    return FigureCorpus(figure.key, figure.market, daily, headlines, _verdict(daily, start, end))


def collect(keys: list[str] | None = None, years: int = 3, sample: int = 25,
            out_dir: Path | None = None, client: GdeltClient | None = None) -> dict:
    """Collect the corpus for the roster (or ``keys``) and write it to disk.

    Returns a manifest dict (also saved as ``manifest.json``). Per figure writes
    ``{key}_daily.parquet`` (the signal) + ``{key}_headlines.jsonl`` (the audit)."""
    out_dir = out_dir or CORPUS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    client = client or GdeltClient()
    end = date.today()
    start = end - timedelta(days=int(365.25 * years))
    figures = get_figures(keys)

    manifest_rows: list[dict] = []
    for fig in figures:
        corpus = collect_figure(client, fig, start, end, sample=sample)
        if len(corpus.daily):
            corpus.daily.to_parquet(out_dir / f"{fig.key}_daily.parquet")
        (out_dir / f"{fig.key}_headlines.jsonl").write_text(
            "\n".join(json.dumps(h) for h in corpus.headlines), encoding="utf-8")
        manifest_rows.append(corpus.stats())
        s = corpus.stats()
        log.info("figure_collected", extra=s)

    manifest = {
        "generated": end.isoformat(),
        "window": {"start": start.isoformat(), "end": end.isoformat(), "years": years},
        "figures": manifest_rows,
        "rich": [r["figure"] for r in manifest_rows if r["verdict"] == "RICH"],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
