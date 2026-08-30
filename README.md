# AI for the public good — corpus and analysis pipeline
### Discourse analysis · GDS/DSIT, United Kingdom · January 2024 – July 2026

Pipeline supporting the author's dissertation on "AI for the public good" as a
sociotechnical imaginary in UK government discourse on AI in public services,
anchored in the Government Digital Service.

**Guiding principle: the LLM locates and extracts; the author interprets and
consolidates.** No interpretive result is final until validated (see checkpoints).

- **Full design and constraints (SO1/SO2/SO3):** [PLAN.md](PLAN.md)
- **Interpretation guide for each deliverable and its assumptions:** [interpretation.html](interpretation.html)
- **Consolidated hub (corpus + deliverables + document intake):** [index.html](index.html)

## Quick start

```bash
# local hub with incremental document intake ("Add document" form)
.venv/bin/python scripts/serve_site.py
# → http://localhost:8765
```

Requirements: Python 3.14 (venv in `.venv/`, already provisioned), [Ollama](https://ollama.com)
running on `localhost:11434` with an active Ollama Cloud session (LLM model) and
`embeddinggemma` local (embeddings).

## Structure

```
data/manifest.csv        frozen corpus v1 (35 docs) + attributes; append-only (v2+ = new intakes)
data/raw/                downloaded originals + metadata per doc (outside git; snapshots on archive.org)
data/text/                structured text per doc (blocks: title/pillar/heading/body/quotation)
coding/lexicon_v1.yaml   term variants (nominal / variant / distributive) — versioned
coding/units.jsonl       53 coding units (retrieval: lexicon | semantic | full_short_doc)
coding/prompts/          prompts for the 11 questions + document profile, versioned
coding/model_eval/       Ollama model evaluation and documented decision
coding/round1/           raw Round 1 output (JSONL per doc, with run metadata)
coding/validation/       sample for the author's double coding + agreement
coding/guidebook_draft.yaml  candidate sub-code clusters (DRAFT until the author names them)
analysis/networks/       intertextual network v0 (JSON with evidence) + interactive map
analysis/queries/        term counts, queries (zero-count, GDS-tier), echoes by family
analysis/metaphors_report.md  most frequent metaphors with suggested source/target (to validate)
```

## Scripts (in pipeline order)

| Script | Phase | What it does |
|---|---|---|
| `01_manifest.py` | 0 | Selection Excel → `data/manifest.csv` |
| `02a/02b_fetch_*.py` | 1 | Download and structured extraction (gov / companies) |
| `02c_archive_snapshots.py` | 1 | Snapshots on web.archive.org |
| `03_qa_merge.py` | 1 | Extraction QA + metadata merge into the manifest |
| `04_segment.py` | 2 | Coding units + term/variants + semantic retrieval |
| `05_code.py` | 4 | Round 1 with Ollama (11 questions × unit; `--doc` for a single one) |
| `06_consolidate.py` | 5 | Response grouping → guidebook draft |
| `06_network_v0.py` | 6 | Explicit-reference network (title alias + MoU rule) |
| `07_echo.py` / `07b_queries.py` | 6 | Echo-phrases by MoU family + queries (3 charts) |
| `09_round1_watchdog.py` | 4 | Resumes Round 1 in bursts until the Ollama Cloud quota allows completion |
| `10_thematic_network.py` | 6 | Bipartite document↔sub-code network (from the guidebook draft) |
| `11_agency_query.py` | 6 | Agency × genre query (NVivo plan query 2) from Round 1 AGENCY records |
| `12_nvivo_export.py` | 6 | NVivo classification sheet + coded passages CSVs |
| `13_qa_communities.py` | QA | Leiden communities vs families/speakers (ARI) — internal, not results |
| `10_finalize.py` | — | Re-runs the whole analysis chain in order (use after Round 1 completes) |
| `08_build_site.py` | — | Regenerates `index.html` from the data |
| `add_document.py` | 7 | Incremental intake: admission checklist → fetch → recompute |
| `serve_site.py` | — | Hub on localhost:8765 with the intake form |

Everything runs with `.venv/bin/python scripts/<script>.py`.

## Author checkpoints (non-delegable human decisions)

1. Variant lexicon (`coding/lexicon_v1.yaml`) — approve/extend.
2. `gds_tier` — the current assignment is automatic and provisional (column
   `gds_tier_source`).
3. Validation sample (`coding/validation/sample_for_author.csv`) — double coding
   and agreement report before signing off on Round 1.
4. Guidebook (`coding/guidebook_draft.yaml`) — name/merge/reject sub-codes.
5. Metaphors (`analysis/metaphors_report.md`) — validate suggested source/target
   domains.
6. Document intake (Phase 7) — confirm the admission checklist for each new URL.

## Decisions on record

- Corpus v1 = 35 documents (the decided range in the Excel file contains an empty
  row; cutoff at row 38, the "EITHER BRING" marker). The `CONTEXT_` document (AI
  Opportunities Action Plan) **enters the corpus** with `Speaker=External_adviser`
  (decision 2026-08-29).
- LEGITIMATION (van Leeuwen) dropped: exceeds the matrix's theoretical framework.
- `data/raw/` outside git; persistence via local copies + archive.org (33/35).
- METAPHOR anchored in Lakoff & Johnson (1980) + MIP; the domains the pipeline
  produces are suggestions.
