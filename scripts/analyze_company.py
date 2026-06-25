#!/usr/bin/env python
"""Deep company analysis (Phase 1+2) — on-demand CLI.

Phase 1: download the public disclosures you point it at (transcript /
results / presentation / shareholding / annual-report URLs from the company's
investor-relations page) into ``var/research/<SYMBOL>/``.
Phase 2: extract structured signal — financial highlights, forward guidance,
risk factors, capex/expansion plans, management commentary.

Examples:
    # See what every NSE/BSE company must publish, and why it matters.
    .venv/bin/python -m scripts.analyze_company --checklist

    # Analyse a local transcript/results PDF (no network needed).
    .venv/bin/python -m scripts.analyze_company --symbol RELIANCE \
        --doc ~/Downloads/RIL_Q1FY26_transcript.pdf

    # Download from an investor-relations URL, then analyse.
    .venv/bin/python -m scripts.analyze_company --symbol TATAPOWER \
        --doc https://www.tatapower.com/.../Q1FY26-transcript.pdf --download
"""

from __future__ import annotations

import argparse
import json
import sys

from ats.services.research import (
    DisclosureFetcher,
    LODR_CHECKLIST,
    analyze_document,
    research_dir,
)
from ats.services.research.disclosures import classify


def _print_checklist() -> None:
    print("What an NSE/BSE-listed company must publish (SEBI LODR):\n")
    for item in LODR_CHECKLIST:
        print(f"  • {item['kind'].value}  [{item['regulation']}]")
        print(f"      cadence: {item['cadence']}")
        print(f"      use:     {item['why']}\n")
    print("Best sources for analysis: the earnings-call TRANSCRIPT and the")
    print("annual report's MD&A. Grab these from the company's Investor")
    print("Relations page or the BSE/NSE corporate-announcements feed.")


def _analyse(symbol: str, docs: list[str], download: bool) -> dict:
    dossier: dict = {"symbol": symbol, "documents": []}
    fetcher = DisclosureFetcher(allow_download=download)
    for doc in docs:
        local = doc
        kind = classify(doc)
        if doc.lower().startswith(("http://", "https://")):
            if not download:
                print(f"  ! {doc} is a URL; re-run with --download to fetch it.", file=sys.stderr)
                continue
            d = fetcher.download(symbol, doc)
            if not d.local_path:
                print(f"  ! failed to download {doc}: {d.meta.get('error')}", file=sys.stderr)
                continue
            local = d.local_path
            kind = d.kind
        try:
            analysis = analyze_document(local)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! could not analyse {local}: {exc}", file=sys.stderr)
            continue
        dossier["documents"].append({"source": local, "kind": kind.value, **analysis})
    return dossier


def main() -> None:
    ap = argparse.ArgumentParser(description="Deep company analysis (Phase 1+2).")
    ap.add_argument("--checklist", action="store_true", help="print the SEBI LODR disclosure checklist and exit")
    ap.add_argument("--symbol", help="NSE symbol, e.g. RELIANCE")
    ap.add_argument("--doc", action="append", default=[], help="path or URL to a disclosure (repeatable)")
    ap.add_argument("--download", action="store_true", help="allow downloading --doc URLs")
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    args = ap.parse_args()

    if args.checklist:
        _print_checklist()
        return
    if not args.symbol or not args.doc:
        ap.error("provide --symbol and at least one --doc (or use --checklist)")

    dossier = _analyse(args.symbol, args.doc, args.download)
    if args.json:
        print(json.dumps(dossier, indent=2, ensure_ascii=False))
        return

    print(f"\n=== Dossier: {dossier['symbol']} ===")
    print(f"(documents saved under {research_dir(dossier['symbol'])})\n")
    for d in dossier["documents"]:
        print(f"── {d['kind']}  ·  {d['source']}")
        print(f"   {d['chars']:,} chars, {d['sentences']} sentences")
        fh = d.get("financial_highlights") or {}
        if fh:
            print("   Financial highlights:")
            for metric, hits in fh.items():
                print(f"     {metric}: {hits[0]}")
        for label, key in (("Guidance", "guidance"), ("Risks", "risks"),
                            ("Capex/expansion", "capex_expansion"),
                            ("Mgmt commentary", "management_commentary")):
            items = d.get(key) or []
            if items:
                print(f"   {label}:")
                for s in items[:3]:
                    print(f"     • {s}")
        print()


if __name__ == "__main__":
    main()
