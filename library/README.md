# `library/` — raw knowledge sources

Drop raw documents here, then run the ingester to turn them into clean,
retrieval-ready notes under `knowledge/` (which **is** committed to git):

```bash
# install parsers once (only on the machine that ingests):
pip install pypdf trafilatura python-docx

# clean everything in this folder into knowledge/
python scripts/ingest_knowledge.py
```

The **contents** of this folder are git-ignored (only this README is tracked) —
raw PDFs/reports are often large or licensed, so they stay local. The *cleaned*
output in `knowledge/` is what gets committed and deployed.

## Layout — sub-folders set the expert family

Put each source under the family it belongs to; the ingester reads the family
from the sub-folder name:

```
library/
  family_a/   -> A     (e.g. equity / fundamentals)
  family_b/   -> B     (e.g. macro: RBI, inflation, rates)
  family_c/   -> C     (e.g. ETFs / commodities / instrument docs)
  risk/       -> RISK  (risk, position sizing, drawdown control)
  <loose files at the top level default to "all" / shared)
```

Supported types: `.pdf`, `.html`/`.htm`, `.docx`, `.txt`, `.md`.

## Examples

```bash
# a macro report, tagged for two index ETFs
python scripts/ingest_knowledge.py --src library/family_b/rbi_mpc_2024-04.pdf \
    --family B --tickers NIFTYBEES,BANKBEES

# preview the whole library without writing anything
python scripts/ingest_knowledge.py --dry-run
```

Each generated note in `knowledge/` starts with a YAML front-matter block
(`family`, `source`, `doc_type`, `date`, `reliability`, `tickers`) that the
knowledge base reads to scope and rank retrieval. See
`docs/sme_knowledge_base.md` for the full pipeline.
