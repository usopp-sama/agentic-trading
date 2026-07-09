# `knowledge/` — the committed SME library

This folder holds the **cleaned, curated notes** that the experts read. Unlike
`library/` (raw PDFs/HTML — large, often licensed, git-ignored), everything here
is **version-controlled** so the maintained SME knowledge ships and deploys with
the repo.

## How notes get here

Run the ingester; it parses + cleans + structures raw sources from `library/`
and writes notes here by default:

```bash
python scripts/ingest_knowledge.py            # library/ -> knowledge/
python scripts/ingest_knowledge.py --dry-run  # preview without writing
```

Each note starts with YAML front-matter the knowledge base reads to scope and
rank retrieval:

```yaml
---
family: B            # A | B | C | RISK | all
source: rbi_mpc_2024-04
doc_type: pdf
reliability: 95      # 0-100; higher outranks generic chatter
date: 2024-04
tickers: [NIFTYBEES, BANKBEES]
ingested: 2026-06-21
---
```

You can also hand-author notes here directly (same front-matter) — no ingester
required.

## Loading order

`KnowledgeBase.ingest_all` reads, in order:

1. `ats/services/agents/corpus/` — built-in primers (reliability 90)
2. `knowledge/` — this committed library (reliability 95)
3. `ATS_KNOWLEDGE_DIR` (default `var/knowledge/`) — optional **local-only**
   scratch notes, git-ignored

See `docs/sme_knowledge_base.md` for the full pipeline.
