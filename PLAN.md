# Discourse analysis pipeline — "AI for the public good"
### GDS / DSIT, January 2024 – July 2026 · Frozen corpus v1 (35 documents)

This plan operationalises the methodological design of `Research_Alignment_Matrix.docx`
and `Document Analysis v1.xlsx`. Two guiding principles:

1. **The LLM locates and extracts; the author interprets and consolidates** (Saldaña
   2025: provisional coding guided by questions, not by a closed list of codes).
2. **The three specific objectives are the pipeline's hard constraint.** No
   component is built unless it serves SO1, SO2, or SO3. Every output carries an
   objective tag (`so_tags`), and anything that only validates the method (without
   generating findings) is marked as internal QA.

---

## Constraint: the three objectives and which component serves which

> **Aim.** To analyse how the framing of "AI for the public good" functions as a
> sociotechnical imaginary in UK government discourse on AI in public services,
> anchored in the Government Digital Service.

| Objective | Theoretical framework (matrix) | Pipeline components serving it |
|---|---|---|
| **SO1.** Examine the sociotechnical imaginary projected under the rhetoric of "AI for the public good" in GDS texts. | Jasanoff & Kim (imaginaries); Kaplan (narrative/plot); Lears (hegemony) | **Round 1.1** — the author's own interpretive coding in NVIVO: reading each document for the phrase, coding it against the 7 core questions (beneficiary, mechanism, safeguard, responsible, projected future, hero/threat, naturalised order) plus the definitional term-search, on the documents she read closely. **Round 1.2** — LLM-assisted coding extends that same question set across the full 66-document corpus, entirely via Ollama Cloud (`kimi-k3:cloud`, with a `deepseek-v4-flash:cloud` fallback for quota limits — see "Note on tooling" below), then clusters every resulting instance by cosine similarity into a candidate codebook the author names. The chronological comparison of definitions stays the author's own reading of what Round 1.1/1.2 locates (METAPHOR/Lakoff & Johnson analysis was dropped 2026-09-13 — not part of the committed framework). |
| **SO2.** Trace how that imaginary moves from a statement of principles to strategic priorities, policy commitments, and public-facing claims. | Fairclough (intertextuality); Jasanoff & Kim; Lears (naturalisation) | **Round 2.1** — the author's own intertextuality coding in NVIVO (the `r2_intertextuality` node: which documents cite, echo or supersede which). This is assisted by an intertextual network that the author designed and directed Claude Code to build computationally (title-alias reference detection + declared supersession over the full corpus) — the network surfaces candidate links at a scale manual reading alone cannot cover; the author still decides which links matter. MECHANISM, PROJECTED FUTURE and NATURALISED ORDER (from Round 1.2) supply the passage-level evidence for how the framing changes as it moves across genres. |
| **SO3.** Analyse the evolution of the framing across the department's partnership documents with frontier AI companies. | Hajer (discourse coalitions); Lears (naturalisation); Fairclough (agent deletion, nominalisation, modality) | **Round 2.2** — the author's own MoU-family coding in NVIVO (the `MouFam1`–`MouFam8` nodes: benefits, mechanism, safeguards, narratives and trust coded separately per partner company). This is assisted by echo-phrase detection and AGENCY/MODALITY analysis that the author designed and directed Claude Code to run across every MoU family at once — surfacing which n-grams and grammatical patterns (agentless passive vs. first-person government agent) repeat within and across families, which the author then reads for the intra-family and inter-family comparison Hajer's framework calls for. |

**Trimming rule applied.** Everything that does not map was excluded or downgraded:
- **LEGITIMATION (van Leeuwen)** — dropped: it extends the theoretical framework
  beyond what the matrix establishes.
- **Community detection (Leiden) and embedding triangulation** — downgraded to
  **internal QA**: they help verify that groupings are not an artefact, but generate
  no findings of their own and do not appear as results.
- Embedding-based "exploratory discovery" — eliminated as an end in itself;
  embeddings are only used for retrieving the distributive claim (SO1/SO2) and the QA
  above.

---

## Note on rounds vs. phases (read this before the Phase 0-7 walkthrough)

This document tracks two different things, and they are not the same axis:

- **Rounds** are the author's own coding process — what she did, in what order,
  in NVIVO, and what she directed this pipeline to do to assist it. Rounds are
  named the way the author names them in her NVIVO project and codebook.
- **Phases** are this pipeline's engineering steps (0-7) — what script produces
  what file, in what order, so the pipeline itself is reproducible. Phases are
  a *build process*, not a coding methodology; several phases can serve one
  round, and one phase's output can assist more than one round.

The mapping, current as of 2026-09-12:

| Round | What it is | Who does it | Which phase(s) it uses |
|---|---|---|---|
| **1.1** | The author's interpretive coding in NVIVO: reading documents closely, coding the 7 core questions (beneficiary, mechanism, safeguard, responsible, projected future, hero/threat, naturalised order) plus the definitional term-search, and noting emerging codes as they surface. | Author, manually, in NVIVO. Predates and grounds this repo. | No phase — this is outside the pipeline. Reviewed in `coding/nvivo_r1_r2_review.md`; recorded in the author's `Codebook - Dissertation.docx` NVIVO export. |
| **1.2** | LLM-assisted coding: the same question set, extended across the *entire* 66-document corpus by an LLM, then every resulting instance clustered by cosine similarity into a candidate codebook. This is what lets Round 1.1's scheme scale from the documents the author read closely to the full corpus. | LLM does the locating/extracting/clustering; the author names and validates the resulting clusters (`analysis/guidebook_summary.html`). | Phases 2 (segmentation), 3 (model evaluation), 4 (full-corpus coding), 5 (clustering). |
| **2.1** | Intertextuality coding: which documents cite, echo, or supersede which (the author's `r2_intertextuality` NVIVO node — 35 files, 58 references). | Author, manually, in NVIVO — **assisted** by a network the author designed and directed this pipeline to compute. | Part of Phase 6 (the intertextual network specifically). |
| **2.2** | MoU-family coding: benefits, mechanism, safeguards, narratives and trust, coded separately for each of the 8 partner companies (the author's `MouFam1`-`MouFam8` NVIVO nodes). | Author, manually, in NVIVO — **assisted** by echo-phrase and agency/modality analysis the author designed and directed this pipeline to compute across every family at once. | Part of Phase 6 (echo-phrases + `agency_by_genre.csv` specifically). |

There is no "Round 3" — MoU-family coding is Round 2.2, not a separate round, per
the author's 2026-09-12 clarification. "Phase 3" (model evaluation) is a
pipeline engineering step, not a coding round; it belongs inside Round 1.2 above,
not on its own.

**On "Incremental intake (ongoing)"** (Phase 7, tracked separately from the
rounds): this is the mechanism (`add_document.py`) for adding documents to the
corpus *after* v1 was frozen — the checklist → fetch → extract → segment →
append flow that brought the corpus from 35 to 66 documents on 2026-09-10. It
stays open-ended ("ongoing") because nothing about the design assumes the
corpus is finished — the author can run it again whenever a new document
needs to enter. It is not itself a coding round; every document it admits
still needs to go through Round 1.2 (and, if relevant, 2.1/2.2) like any other
document. The decision open to the author is simply whether to treat the
corpus as closed now (no more intake expected) or keep it open for documents
published after 2026-09-10 — the mechanism works either way; nothing in the
pipeline needs to change based on that choice.

---

## Decisions already made

| Decision | Value |
|---|---|
| Corpus v1 | Only rows with a decision made in `Official_Document Selection` (before the "EITHER BRING COHERE..." row). Pending blocks A/B do NOT enter v1. |
| Text source | `Link for document` column → full document. `Exact phrase` only as cross-verification where it exists. |
| LLM | Ollama Cloud. 2–3 models are evaluated on a sample and the best one is chosen (Phase 3). |
| Codes | The 7 parent codes from Table 3 + the nodes from the `method` sheet. New codes: only aligned ones (see Codes section); the author decides which ones go in before the run. |
| Extensibility | Incremental document intake using the corpus admission rules as a filter (see Phase 7). |

---

## Project structure

```
Tafoya/
├── PLAN.md                       ← this document
├── data/
│   ├── manifest.csv              ← frozen corpus v1, append-only
│   ├── raw/                      ← downloaded PDFs/HTML + archive.org snapshot
│   └── text/                     ← structured JSON per document (hierarchical sections)
├── coding/
│   ├── prompts/                  ← one prompt per question, versioned; each declares its so_tags
│   ├── model_eval/                ← model comparison + documented decision
│   ├── round1/                   ← raw LLM output, JSONL per document
│   ├── validation/               ← hand-coded sample + agreement report
│   └── guidebook.yaml            ← Round 2: consolidated sub-codes (edited by the author)
├── analysis/
│   ├── networks/                 ← GraphML + interactive HTML visualization
│   ├── queries/                  ← the three queries from the NVivo plan (CSV + charts)
│   ├── qa/                       ← internal validations (not results)
│   └── nvivo/                    ← exports ready for import into NVivo
└── scripts/
    ├── 01_manifest.py … 07_analyze.py
    └── add_document.py           ← incremental intake with admission checklist
```

---

## Phase 0 — Freeze the corpus (manifest)

**Input:** `Official_Document Selection` sheet. **Output:** `data/manifest.csv` with:
`doc_id` (NVivo name `YYYY-MM-DD_GENRE_ACTOR_Slug`), `date`, `genre`
(STRAT/MOU/PRGOV/PRCO/BLOG/WMS/REG), `speaker` (cleaned value, column U), `side`,
`family` (Anthropic/Cohere/OpenAI/DeepMind/ElevenLabs/None), `gds_tier` (T1/T2/T3),
`stage` (1/2), `term_status` (present/variant/absent), `url`, `archive_url`,
`corpus_version` (=1), `is_context` (bool).

Decisions made (2026-08-29): the `CONTEXT_..._AIOpportunitiesActionPlan` row
**enters the corpus** coded with `Speaker = External_adviser`; new archive.org
snapshots are created for the whole corpus; local git repository with `data/raw/` in
`.gitignore` (originals on disk + archive.org).

Checks (reported to the author, not resolved silently):
- **Count**: confirm that the decided rows add up to 37; discrepancies are listed.
- `term_status = CHECK` (docs 7, 10): remain flagged; Phase 2 resolves them using the
  full text and the author confirms.
- Broken links or withdrawn documents → `archive_url`.

## Phase 1 — Download and archiving

Download from `url`; fallback to web.archive.org where the document changed or was
withdrawn (already happened with the Generative AI Framework); **new archive.org
snapshot for anything that doesn't have one** — protection against link rot during
the dissertation.

Text extraction **preserving structure** (PyMuPDF for PDFs with heading hierarchy;
DOM parsing for gov.uk/blogs with h1–h4, blockquotes and attributed quotations).
Each block carries `structural_position` (title / pillar_name / section_heading /
body / quotation) — the "Phrase position" attribute from Table 4 depends on this,
and the structural position is itself a finding declared in the matrix.

## Phase 2 — Segmentation and term detection *(SO1, SO2)*

Faithful to the declared method: *full scan → detailed coding of the section that
contains the term.*

1. Versioned **variant lexicon** (approved by the author): nominal ("public good",
   "the public good", "AI for public good") and distributive/competing ("public
   benefit", "public interest", "benefits reach every citizen", "delivers for all",
   "improve people's lives", "working people", "taxpayer") — mirroring the
   `PublicGood_Nominal` / `PublicBenefit_Distributive` nodes and the 8 beneficiary
   nodes. Stemming off (NVivo rule: don't catch "goods").
2. Sections-with-term → detailed coding queue. Documents without the term →
   semantic retrieval (paragraph embeddings) of the distributive claim, so that the
   zero-count comes accompanied by "and instead X is said" (SO1/SO2). Passages
   retrieved by embedding are flagged `retrieval=semantic` (auditable).
3. Embeddings via Ollama (`nomic-embed-text` or `mxbai-embed-large`; decided in
   Phase 3). Persistent index for incremental reuse. **Sole analytical use of
   embeddings**; any other use is QA.
4. Automatic update of `term_status` in the manifest (resolves the `CHECK` cases).

## Phase 3 — Model evaluation (Ollama Cloud)

1. Stratified sample: ~5 documents (1 long STRAT, 1 MoU, 1 PRCO, 1 BLOG, 1 WMS)
   → ~25–40 passages.
2. Candidates: 2–3 large models from the Ollama Cloud catalogue current at run time.
3. Same prompt, temperature 0, forced JSON, the 7 questions per passage.
4. Decision metrics:
   - **Extractive fidelity**: every returned quote exists verbatim in the passage
     (automatic verification — the best hallucination detector for this task).
   - Valid-JSON rate and correct "not applicable" rate.
   - **Agreement with the author** on the sample (or inter-model agreement + the
     author's adjudication on disagreements).
5. Output: `coding/model_eval/decision.md` — model, exact version, metrics; text
   nearly ready to drop into the methods chapter.

> The documents are public: running on Ollama Cloud poses no confidentiality issue;
> provider, model and date are logged all the same.

## Phase 4 — LLM-assisted coding, full corpus (Round 1.2, part 1)

- **One prompt per question**, each with: the exact wording from Table 3, its
  theoretical source in one line, its `so_tags` per the matrix (BENEFICIARY →
  SO1/SO2/SO3; MECHANISM → SO1/SO2; SAFEGUARD → SO1/SO3; RESPONSIBILITY → SO1/SO3;
  PROJECTED FUTURE → SO1/SO2; ACTANTS → SO1/SO3; NATURALISED ORDER → SO1/SO2), the
  passage and minimal document context.
- Output per passage/question: `{doc_id, passage_id, question, so_tags,
  answer_summary, verbatim_quote, applies, confidence, model, prompt_version,
  run_id, timestamp}`.
- Separate **definitional extractor** (SO1): statements where the document says what
  the phrase means or requires → `definitional_instances.jsonl` with structural
  position. The pipeline only aligns the instances chronologically; reading what
  each definition retains, drops, adds or replaces is the author's analysis (as the
  matrix sets out).
- Post-check: every `verbatim_quote` is validated against the source text; those
  that don't match are flagged and retried or discarded.

**Validation (for the methods chapter):** 15–20% of passages, stratified by genre
and family, double-coded (the author + LLM); per-question agreement; disagreements
feed at most one round of prompt iteration, then are frozen.

## Phase 5 — Clustering by cosine similarity (Round 1.2, part 2)

- `06_consolidate.py` groups the responses per question by semantic similarity and
  presents each cluster with its quotes — raw material for **the author to name the
  sub-codes** in `guidebook.yaml` (name, definition, inclusion/exclusion rule,
  exemplar passage). The 8 beneficiary nodes already defined in the `method` sheet
  enter the guidebook as-is as BENEFICIARY sub-codes.
- Automatic cluster→sub-code assignment pass; the author reviews the edge cases.

## Phase 6 — Analysis: only outputs mapped to objectives

**A. Intertextual network** *(SO2 — Fairclough)*: nodes = documents with manifest
attributes; edges directed by (i) family, (ii) explicit references in the text
(titles of other corpus documents, gov.uk links between them), (iii) declared
supersession. Reading: the path declaration → priority → commitment → public claim.

**B. Echo-phrases** *(SO3 — Hajer)*: shared n-grams (≥6 words) between government
text and company text within each MoU family, with who published first — material
evidence of interdiscursive borrowing/coalition. Intra-family and cross-family
comparison by counterparty, as the matrix requires.

**C. Thematic network** *(SO1/SO2)*: bipartite document↔sub-code, projected onto a
weighted document–document graph by shared codes, faceted by Period, Speaker,
Family and TermStatus.

**D. The three NVivo plan queries** *(replicated as-is)*: zero count × Genre
(SO1/SO2); agency × Genre — agentless passive vs. first-person government agent
(SO3); PublicGood_Nominal × GDSTier — the query that kills the obvious objection
(SO3). CSV + chart for each.

**E. NVivo exports**: coded passages + attribute classification sheet, in
direct-import format.

**F. Metaphor report** *(SO1)*: the corpus's most frequent metaphorical
expressions, and for each **a suggested source domain and target domain** with its
proposed `TARGET IS SOURCE` formula, tentative L&J type and evidence passages —
presented as a proposal for the author to validate, correct or rename the mappings
(the final domain assignment is her interpretive decision, not the pipeline's).

**G. Visualization**: self-contained interactive HTML; nodes colourable by
Period/Speaker/Family/TermStatus, edges by type (family, reference, echo), temporal
slider Jan-2024 → Jul-2026 with the July 2024 cutoff marked.

Main view ("authorship and families map", per the author's visual reference
2026-08-29): **node colour = authoring actor** (GDS / DSIT / DSIT+GDS / CDDO / PMO /
External_adviser / each company — companies share a palette range, distinguishable
from one another); **spatial grouping = family** (the 8 MoU families as bounded
clusters with hull/label, the GDS/DSIT strategy trunk at the centre); **node size =
in-degree** (how many times other corpus documents reference it — proxy for
authority); **edge thickness = reference frequency**; arrow direction = who cites
whom; line type distinguishes explicit reference / family / supersession / echo.
Per-node tooltip: doc_id, date, genre, term_status.
*Schedule preview*: this view is generated in a preliminary version at the close of
Phase 1 (requires only texts + manifest: extraction of explicit references), and is
enriched in Phase 6 with echo-phrases and shared codes.

**Internal QA (not results)**: Leiden comparison vs. families/groupings and
semantic similarity matrix — live in `analysis/qa/`, cited only if the author
decides to use them as a robustness check in the methods section.

## Phase 7 — Incremental document intake

`add_document.py <url> [--family X --genre Y ...]`:
1. **Admission checklist first** — the rules from the `method` sheet applied as an
   explicit filter: Rule 1 (supersession/window), Rule 3 (speaker, not publisher),
   Rule 4 (functional boundary of the digital centre), Rule 5 (blog criterion),
   producer-vs-scrutineer (parliamentary scrutiny/audit is context, not corpus)
   and written-vs-spoken (Hansard excluded). The script presents the evaluated
   checklist and **the author approves admission**; nothing enters automatically.
2. New row in the manifest with the next `corpus_version` — v1 stays intact: the
   dissertation's analysis can always be regenerated by filtering
   `corpus_version == 1`.
3. Phases 1–4 only on the new document, with **prompts, model and guidebook
   frozen** at the current version.
4. Responses without an existing sub-code → `candidate_code`, accumulated for the
   author's review; new codes never arise without a human decision.
5. Phase 6 is regenerated in full (it is idempotent from the JSONL files).

Each run logs `run_id`, model, prompt version and guidebook version: any number in
the dissertation is traceable to an exact run.

---

## Codes and attributes

**Taken as-is:** the 7 parent codes from Table 3, `PublicGood_Nominal`,
`PublicBenefit_Distributive`, the 8 beneficiary nodes, and the Table 4 attributes
(Period, Authorship, Side, Partnership family, Phrase position, Definitional
status) + Genre, GDSTier, Stage, TermStatus from the NVivo plan.

**Proposed additions — only those that fit within the matrix's framework** (the
author decides before the run):

1. **AGENCY** *(SO3; extensible to the full corpus)* — Fairclough 2003, already
   declared in the matrix for SO3: `explicit_agent / agentless_passive /
   nominalisation`. Its corpus-wide application is sanctioned by query 2 of the
   NVivo plan itself (agency × Genre).
2. **MODALITY** *(SO3)* — Fairclough, explicit in the matrix: `deontic`
   (must/should/commit) vs. `epistemic/predictive` (will/could/expected). Crosses
   with the "force" question from Table 2: distinguishes commitment from prophecy.
3. **NARRATIVE_ARC** *(SO1; per-document attribute)* — Kaplan 2020 (beginnings,
   middles, ends), already implicit in the memos ("ARC POSITION 1"); formalising
   it makes it queryable.
4. **THREAT_TYPE** *(SO1/SO3; sub-dimension of ACTANTS)* — Kaplan:
   `technological_risk / geopolitical_lag / bureaucratic_status_quo /
   public_distrust`. The migration of the threat over the period is a likely
   finding (doc 1's memo already detects it: "AI is the risk").
5. ~~**METAPHOR**~~ *(dropped, 2026-09-13)* — was proposed as Lakoff & Johnson
   1980 + MIP/MIPVU (Pragglejaz 2007; Steen et al. 2010), per-instance source
   domain → target domain → `TARGET IS SOURCE` formula → L&J type → what it
   illuminates/hides. **The author confirmed this is not part of her committed
   analytical framework** — it was the only proposed addition that would have
   added citations to the theory chapter, and she is not incorporating L&J/MIP
   into it. `coding/round1/*.jsonl`'s METAPHOR records and
   `analysis/metaphors_report.md` (419 candidate expressions) still exist as
   raw pipeline output from when this was still a live candidate, but are not
   presented as a finding anywhere (`analysis/guidebook_summary.html` no
   longer surfaces them; see `dissertation_outputs/analytical_tools_table.md`).
6. **ECHO** *(SO3)* — computationally generated in Phase 6B (Hajer); not
   hand-coded.
7. **AUDIENCE** *(SO2; per-document attribute)* — `parliament / practitioners /
   general_public / industry`; already recorded as prose in the function memo
   (Table 2); as a closed value it enables the crossing "before which audience does
   the term appear, and before which does it disappear?", which is the heart of
   SO2.

**Dropped by the alignment constraint:** LEGITIMATION (van Leeuwen 2007) —
extended the theoretical framework beyond what the matrix establishes, without
being needed for any SO.

---

## Execution order and human checkpoints

| Step | Round | Does | Serves | Author checkpoint |
|---|---|---|---|---|
| — | 1.1 | Author's interpretive coding in NVIVO | SO1/SO2/SO3 | Manual — predates the pipeline |
| 0 | — | Manifest from the Excel file | base | Confirm count of 37 and flagged cases |
| 1 | — | Download + archiving + structured text | base | Review broken-links report |
| 2 | 1.2 | Segmentation + term/variants + embeddings | SO1/SO2 | Confirm `CHECK` cases; approve lexicon |
| 3 | 1.2 | Model evaluation | base | Code the sample; approve model |
| — | — | — | — | **Decide which proposed codes go in** |
| 4 | 1.2 | Full-corpus LLM-assisted coding | SO1/SO2/SO3 | 15–20% validation + agreement report |
| 5 | 1.2 | Clustering by cosine similarity | SO1/SO2/SO3 | **Name sub-codes (guidebook)** |
| 6a | 2.1 | Intertextual network (assists `r2_intertextuality`) | SO2 | Analytical reading — interpretation begins here |
| 6b | 2.2 | Echo-phrases + agency/modality (assists `MouFam1-8`) | SO3 | Intra/inter-family comparative reading |
| 6c | — | Other outputs: queries, metaphors, NVivo exports | SO1/SO2/SO3 | Validate metaphor domains |
| 7 | — | Incremental intake | per doc | Approve admission (checklist) and `candidate_codes` |

Stack: Python (project venv), PyMuPDF, requests/BeautifulSoup, Ollama API (cloud
for LLM; embeddings local or cloud), networkx + python-igraph, self-contained HTML
visualization. Intermediate data in flat files (CSV/JSONL/YAML), version-controllable.

---

Label language: coding labels standardised to English on 2026-08-29; prompts_v1.yaml
already emits Spanish label values for AGENCY/MODALITY/ACTANTS — mapped at
consolidation.

---

## Phase 7 — Incremental intake, round 1 (2026-09-10)

Corpus v1 (35 documents, frozen) was extended by 31 new documents in one intake
session, run against the author's own `corpus.xlsx` selection sheet (the
successor to `Official_Document Selection`). Two tiers, both approved by the
author before fetching:

- **Tier A (15 entries, admitted on the author's own "family completion" /
  "baseline zero" reasoning):** the `AI Opportunities Action Plan` promoted out
  of `CONTEXT_` status into a full corpus member (per the 2026-08-29 decision
  below); five parliamentary written statements closing gaps in the Action
  Plan / regulation-response lineages; three brand-new MoU-partner
  families — **Cisco**, **NVIDIA** (two MoUs), **Synthesia** — with their
  companion government/company announcements; the OpenAI–Ministry of Justice
  data-hosting announcement; and the GDS **Data and AI Ethics Framework**,
  which turned out to carry the corpus's most explicit (if still glossed
  rather than freestanding) definitional instance — see the Appendix below.
- **Tier B (17 departmental/local-government blog posts** from CDDO,
  Technology in Government, Data in Government, GDS and Inside GOV.UK,
  surfaced by an earlier AI-assisted `site:blog.gov.uk` sweep and marked
  `NOT REVIEWED` in the author's spreadsheet): evaluated against `add_document.py`'s
  automated checklist (Rules 1, 3–5, producer-vs-scrutineer, written-vs-spoken)
  — zero hard failures; the only recurring flag was that the checklist's blog
  recognizer only whitelists `gds.blog.gov.uk` by name, not the other three
  official government blog subdomains, which is a script limitation rather
  than an admission problem (all four are the same institutional family
  already present in the corpus — CDDO is an existing v1 speaker). The author
  approved admission of all 17 on that basis.

**Corpus after this intake: 66 documents, 8 partner-company families**
(Anthropic, Cisco, Cohere, Google DeepMind, ElevenLabs, NVIDIA, OpenAI,
Synthesia — corrects the Appendix matrix's "9 Companies" line below, which
also names Meta; Meta is mentioned in passing in one press release
(`2026-01-27_PRGOV_DSIT_TopBritishAIExpertise`, a skills partnership) but has
no MoU or dedicated document in the corpus, so it is not counted as a
partnership family here). `data/manifest.csv` stays append-only: v1 filtered
by `corpus_version == 1` still reproduces the frozen 35-document analysis
exactly; the 31 additions carry `corpus_version` 7 and 16–37 (each admission
bumps the counter by one, so the numbering is not contiguous with the batch
boundary — this is `add_document.py`'s existing per-document versioning
behaviour, not an error).

**Coding of the 31 new documents** could not use Ollama on 2026-09-10 (none
available on the machine performing this intake), so it ran as an interim
`claude-code-local` pass; that pass was fully superseded on 2026-09-18 by a
real Ollama re-code of all 31 documents (`kimi-k3:cloud` + `deepseek-v4-flash:cloud`
fallback) from a machine with Ollama Cloud access — see "Note on tooling"
below for the full account, including a definitional-status finding that
changed once the real model, not the interim one, coded the passage.

**A cross-platform bug fixed during this intake:** every script that reads or
writes UTF-8 text without an explicit `encoding=` argument (`add_document.py`,
`06_network_v0.py`, `04_segment.py`, `08_build_site.py`, `03_qa_merge.py`,
`01_manifest.py`, `02b_fetch_companies.py`, `09_round1_watchdog.py`,
`14_export_embeddings.py`, `15_guidebook_summary.py`, `16_render_markdown.py`)
silently defaulted to the OS locale encoding. On macOS/Linux that default is
UTF-8, so the bug was invisible; on Windows it is `cp1252`, which corrupted or
crashed on non-ASCII characters (curly quotes, en-dashes) the moment a new
document was admitted. All affected calls now pass `encoding="utf-8"`
explicitly. `scripts/06_consolidate.py` additionally now checks Ollama's
reachability **once**, up front, and — if unreachable — skips clustering
entirely rather than overwriting `guidebook_draft.yaml` with an empty result;
`metaphors_report.md` regenerates regardless, since it needs no embeddings.

## Note on tooling: the claude-code-local interim pass, and its 2026-09-18 reconciliation

`coding/round1/*.jsonl` records every Round 1 call with a `model` field —
that provenance is what caught and let us fix the issue described below.

1. **Corpus v1 (35 documents): `kimi-k3:cloud` via Ollama Cloud.** Chosen in
   Phase 3 on extractive-fidelity and agreement grounds — see
   `coding/model_eval/decision.md`.
2. **The 2026-09-10 intake (31 documents), interim pass: `claude-code-local`.**
   No Ollama instance was available on the machine performing the intake, so
   a Claude Code agent read each unit's text directly and answered the same
   11 questions from `prompts_v1.yaml` in place of a real model call, with
   the same mechanical `quote in unit_text` verification `05_code.py` runs on
   Ollama output. This was **never put through Phase 3's model comparison**
   and does not carry the same evidentiary weight as an actual LLM run,
   however careful the read — an agent choosing what counts as an "instance"
   is a different process from a model doing so under a fixed decoding
   procedure, and the whole point of Phase 3 was to pick and document one
   such procedure. 434 records were written this way and briefly stood in
   for real Round 1 coding of the intake.
3. **2026-09-18: the interim pass was fully superseded.** All 31 documents
   were re-coded from a machine with Ollama Cloud access — `kimi-k3:cloud`
   first (the Phase 3 winner), falling back to `deepseek-v4-flash:cloud` for
   the ~80% of calls that hit the session usage quota (the same fallback
   corpus v1 itself used, per the "Model switch addendum" in the commit
   history). Every `claude-code-local` record was discarded, not merged or
   reconciled by hand; `coding/round1/*.jsonl` now contains **zero**
   `claude-code-local` records anywhere in the corpus, so
   `grep '"model": "claude-code-local"'` returns nothing. **This changed a
   substantive finding, not just the provenance label**: the interim pass
   had found a DEFINITIONAL instance in `2025-12-18_STRAT_GDS_DataAIEthicsFramework`
   (the basis for the "single most direct definitional gloss in the whole
   corpus" claim below, under "What surprised us"); `deepseek-v4-flash:cloud`
   coded all 7 of that document's units as DEFINITIONAL `applies: false`.
   That claim is retracted — see the updated Table 4 and the corrected
   "What surprised us" note. The other two intake documents that had DOC_PROFILE
   or unit-level records survive the re-code with materially the same content
   (re-verify against `coding/round1/*.jsonl` before citing any per-document
   number from before 2026-09-18).
4. **The admission checklist itself (`add_document.py`) is pure Python** — no
   model of any kind evaluates Rules 1/3/4/5; it is regex and domain-list
   matching, run identically regardless of who or what is driving the intake.
5. **The METAPHOR question's suggested source/target domain and L&J type**
   remains the author's call, not the model's, for both the corpus v1 run and
   the 2026-09-18 re-code (see Phase 6F below).

The upshot: as of 2026-09-18, **every Round 1 record in the corpus was
produced by an Ollama Cloud model** (`kimi-k3:cloud` or
`deepseek-v4-flash:cloud`), with full per-record traceability. A reader who
wants to isolate the original Phase-3-evaluated model's output alone can
still `grep '"model": "kimi-k3:cloud"'`.

## Discussion — what was tried, what worked, what didn't (methods reflection)

**What worked as designed.** The append-only manifest with `corpus_version`
did exactly its intended job during a same-day 66-document expansion: nothing
about the frozen 35-document analysis needed touching, and the whole
incremental-intake machinery (checklist → fetch → extract → segment → append)
ran unattended for 31 documents without a single admission decision being
made silently. `quote_verified` caught every typography mismatch (curly vs.
straight apostrophes, a stray space before a period, bullet lines joined by
`\n` rather than a space) as a hard failure rather than a wrong-but-plausible
quote slipping through — the fidelity mechanism worked precisely because it
is mechanical and does not trust either coder's transcription.

**What surprised us.** (1) The definitional-status finding was sharper than
either the design or the author's own manual notes anticipated: only 3 of the
now 23 documents that use the phrase or a named variant offer anything
resembling a definition, and even the automated Round 1 coding — running on a
looser bar than "explicit definition" — could not find more than that. The
phrase behaves almost entirely as a citation of itself, not a concept anyone
commits to elaborating. (2) **Retracted 2026-09-18.** An earlier version of
this note claimed the GDS *Data and AI Ethics Framework*, added in this
intake as a routine "family completion" candidate, was the single most
direct definitional gloss in the whole corpus. That claim came from the
`claude-code-local` interim pass; once the document was re-coded by a real
Ollama model (`deepseek-v4-flash:cloud`), none of its 7 units coded as an
explicit DEFINITIONAL instance (see Table 4 and "Note on tooling"). The
reminder stands the other way round: an ad hoc agent read, however careful,
is not a substitute for the evaluated model pipeline, which is exactly why
Phase 3 exists and why this repo insists on per-record model provenance.
(3) The blog
checklist's institutional-voice recognizer (`Rule 5`) was written narrowly
enough (only `gds.blog.gov.uk`) that it flagged 12 of the 17 Tier B blogs as
"not-determinable" even though none of them raised a real admission concern
once read — a script-vs-substance gap worth knowing about before trusting a
"no flags" result at face value on a future intake.

**What didn't work / had to be worked around.** (1) `scripts/06_consolidate.py`
requires Ollama for guidebook clustering with no offline fallback in the
original design; the first attempt at re-running it on this machine silently
overwrote 3,516 lines of the author's existing (Ollama-computed) clusters
with an empty skeleton, which was caught only because `git status` showed the
diff before it was compounded by further runs — restored from git, and the
script now checks Ollama's reachability once and refuses to touch
`guidebook_draft.yaml` at all if it is unreachable, rather than writing a
partial result. (2) `add_document.py`'s single-document design assumes a
short-document fallback under 9,000 characters; two zero-count, term-absent
documents in this intake (an NVIDIA press release, an Inside GOV.UK blog)
exceeded that without triggering section-based segmentation either, and were
left with zero coding units until a manual full-text unit was added for each
— a real gap in the incremental-intake script for long, headingless
documents, not something that needs the author's judgment call to fix, but
worth patching before the next intake. (3) Every file-encoding bug above was
invisible on the machine the pipeline was designed and run on (macOS
default UTF-8) and would have surfaced as silent corruption rather than a
crash for several of the affected scripts had the corrupted bytes happened to
fall inside cp1252's mapped range instead of outside it — worth a
cross-platform smoke test before this repo is handed to any other
Windows-based collaborator. (4) `add_document.py`'s heuristics for `family` and `date` are
both too permissive/too fragile respectively for a batch of 31: `guess_family()` substring-matches
company names anywhere in the first 4,000 characters, which wrongly tagged 4 documents with a
company family from a passing mention (e.g. a blog naming "Anthropic models" as GOV.UK Chat's
backend, an omnibus press release's joint statement with four labs) rather than an actual
partnership; and `guess_date()`'s fallback to "today" when it cannot parse a publication date
from the page silently back-dated 7 documents to 2026-09-09/10 in the manifest even though
their `doc_id` (assigned by hand from the source) carried the correct date. Both were caught
only by eyeballing the rendered corpus table in `index.html` after the fact, not by any
automated check — worth adding a manifest-vs-doc_id date-prefix consistency check to the intake
script before the next round.

## Appendix. Research Alignment Matrix — filled with what was actually used

Regenerated per the author's request (2026-09-03): the same shape as the
original single-page matrix (Saldaña 2025, after Auerbach & Silverstein), now
completed against the pipeline as it actually ran rather than as it was
planned. Corpus figures below are corpus-wide (all 66 documents, both coding
runs) unless marked "v1 only."

### Table 1. Research aim → objective → framework → methods → data → analysis (as run)

| Research Objective | Methods actually used | Data actually used | Analysis actually produced |
|---|---|---|---|
| **SO1.** Sociotechnical imaginary in GDS texts. | 91 coding units (53 lexicon-triggered, 33 full/short-document, 3 semantic-retrieval, 2 manually added for oversized zero-count documents) scored against the 11 `prompts_v1.yaml` questions + DOC_PROFILE, one prompt-run per document; 4,078 Round 1 records, all Ollama Cloud-produced (3,790 `applies: true`, 3,758 with `quote_verified: true` — 99.2%). | 66 documents: 9 STRAT, 9 MOU, 12 PRCO, 7 PRGOV, 21 BLOG, 7 WMS, 1 REG; `term_status` 16 present / 7 variant / 43 absent. | Definitional-status finding (re-run 2026-09-18 against the full Ollama re-code): of the 23 documents carrying the phrase or a named variant, only 3 (13%) contain an explicit DEFINITIONAL instance, and each of those glosses the term via a criterion or mechanism rather than defining it as a standing concept (Table 4 below has the full breakdown). `metaphors_report.md`: 592 distinct metaphorical expressions ranked by frequency, each with a suggested source/target domain — author validation pending. |
| **SO2.** Declared principle → strategic priority → policy commitment → public claim. | `06_network_v0.py` (title-alias reference detection + declared supersession) + `07_echo.py` (≥6-word shared n-grams by MoU family) run against the full 66-document text; `07b_queries.py` for the zero-count × Genre and PublicGood_Nominal × GDSTier crossings. | Full 66-document corpus; `gds_tier` still `auto_provisional` for all rows (10 T1/8 T2/17 T3 in v1, 15/23/28 corpus-wide) — unreviewed, so the GDSTier query is not yet reportable. | Intertextual network: 66 nodes, 107 edges (93 reference, 13 echo, 1 declared supersession — the AI Playbook superseding the CDDO Generative AI Framework). `zero_count_by_genre.csv` / `nominal_by_gdstier.csv` / `queries.html` regenerated corpus-wide. |
| **SO3.** Evolution across the partnership documents with frontier AI companies. | AGENCY/MODALITY coding (558 and 557 records respectively) + `11_agency_query.py`'s agency × Genre crossing; echo-phrase detection within and across MoU families. | **8 partnership families**, not the 5 in the original design: Anthropic (3 docs, unchanged from v1), OpenAI (6), Google DeepMind (4), Cohere (2, unchanged from v1), ElevenLabs (3), **NVIDIA (3, new)**, **Cisco (2, new)**, **Synthesia (1, new)**. | `agency_by_genre.csv`: 558 AGENCY instances from 62/66 documents (564/564 unit-question pairs succeeded). Echo-phrase edges: 13 document pairs. Cross-family comparison (safety-security framing, "hardworking people" vs. universalist "benefit humanity" registers) still an author-level reading, not automated. |

### Table 3. Coding question map — Sub-codes (Round 1, inductive)

Sub-code clusters below come from `coding/guidebook_draft.yaml`, computed by
cosine similarity of `answer_summary` (`embeddinggemma`, corpus-wide, all
2,981 records across both coding runs). **Re-clustered 2026-09-11**: the
2026-09-10 intake's 434 `claude-code-local` records had been held back
because Ollama was unreachable on the intake machine (see "What didn't
work" above); the author supplied an Ollama Cloud API key on 2026-09-11,
which was used to run Ollama locally (`embeddinggemma` pulled and served on
`localhost:11434`) and re-run `06_consolidate.py` against the full corpus —
this table now reflects all 66 documents, not v1 alone. Names are the
auto-generated `candidate_name` heuristic label, **not** author-approved
code names.

| Coding question | NVivo code | Instances (corpus-wide) | Clusters | Largest candidate sub-codes (unnamed, DRAFT) |
|---|---|---|---|---|
| Who is named as beneficiary? | BENEFICIARY | 370 | 24 | `the_public`, `innovators`, `the_next_generation`, `humanity`, `young_people`, `Beneficiary_PublicGood` |
| Through what mechanism does benefit arise? | MECHANISM | 270 | 155 | `economic_growth`, `scientific_discovery_innovation`, `upskilling_productivity`, `personal_opportunities`, `faster_innovation_speed_to_market`, `innovation_via_openness` — highly granular; needs author-led merging before it is usable as a codebook |
| What safeguards are attached? | SAFEGUARD | 253 | 16 | `documentation_and_record_keeping_for_aud`, `human_involvement_in_public_sector_tasks`, `cost_monitoring_finops_oversight`, `alignment_with_human_values_and_intentio`, `possible_pause_of_model_development_unde` |
| To whom is responsibility for delivery assigned? | RESPONSIBILITY | 102 | 65 | `we_gds`, `you_unnamed`, `regulators`, `a_new_steering_committee_with_government`, `a_new_digital_centre_of_government_withi`, `the_cabinet_their_departments_tasked_per` |
| What future does the passage project? | PROJECTED FUTURE | 290 | 142 | `a_future_in_which_innovation_in_generati`, `the_lives_of_the_british_people_are_impr`, `the_state_is_technologically_transformed`, `generative_ai_systems_whose_performance_`, `the_uk_will_revolutionise_its_economy_an` |
| Who is cast as hero, threat or obstacle? | ACTANTS | 255 | 32 | `ai`, `the_private_sector`, `matt_clifford`, `elevenlabs`, `llms_outdated_and_non_knowledge_base_nat`, `pet_and_pseudonymisation` |
| What social order does the passage naturalise? | NATURALISED ORDER | 236 | 161 | `the_government_is_the_natural_guarantor_`, `the_uk_s_role_as_global_leader_in_ai_saf`, `workers_are_expected_to_adapt_themselves`, `central_government_gds_is_the_natural_le`, `a_fixed_hierarchy_in_which_humans_design` |

The very high cluster counts for MECHANISM (155), PROJECTED_FUTURE (142) and
NATURALISED_ORDER (161) relative to their instance counts are themselves a
finding worth the author's attention before naming: at a ~0.75 cosine
threshold, `answer_summary` texts for these three questions are not merging
much at all, which either means the underlying passages are genuinely that
heterogeneous, or that the threshold/embedding choice is too strict for this
kind of free-text answer. Both AGENCY and MODALITY are excluded from
consolidation by design (`CORE_QUESTIONS` in `06_consolidate.py`) since they
are closed-vocabulary codes, not open clusters to name.

### Table 4. Attribute register — filled

| Attribute | Values | Information (corpus-wide, 66 docs) |
|---|---|---|
| Period | 2024 / 2025 / 2026 | Derived from `date`; the corpus now runs to 2026-07 documents on both ends of the window (earliest: 2024-01-18 CDDO framework; latest: 2026-07-02 TechInGov blog). |
| Authorship | Unit / Department / Joint / Company | `speaker`: GDS, DSIT, DSIT_and_GDS, CDDO, PMO, External_adviser, DSIT_and_<Company>, <Company> — 42 documents carry `family = None` (the trunk + all departmental/local-government blogs), 24 sit within one of the 8 partnership families. |
| Side | Public / Joint / Private | 50 Public, 10 Private, 5 Private (partnership — MoU text), 1 "Public, led by external actor" (the AI Opportunities Action Plan). |
| Partnership family | Anthropic / Cohere / OpenAI / Google DeepMind / ElevenLabs / **NVIDIA / Cisco / Synthesia** | 3 Anthropic, 6 OpenAI, 4 DeepMind, 2 Cohere, 3 ElevenLabs, 3 NVIDIA, 2 Cisco, 1 Synthesia (24 total; unchanged from v1 for Anthropic/Cohere/OpenAI/DeepMind/ElevenLabs). |
| Phrase position | Title / pillar name / section heading / body text / quotation / not present | Not yet tabulated as a standalone attribute-register column; recoverable per-instance from `structural_position` on the block each `verbatim_quote` falls in — an author-level cross-tab, not run here to avoid pre-empting the reading. |
| **Definitional status** | Explicit definition / use without elaboration / not present | **Explicit definition: 3 documents, 3 instances** (`2025-01-21_WMS_DSIT_BlueprintMinisterialStatement` — "public benefit" gloss; `2025-02-10_STRAT_GDS_AIPlaybookUKGovernment` — conceptual "societal wellbeing… means" definition; `2025-12-11_PRGOV_DSIT_NationalRenewalDeepMind`) — **unchanged from corpus v1**; re-verified 2026-09-18 against the full Ollama re-code (see "Note on tooling"). Note this **corrects an earlier claim**: the interim `claude-code-local` pass had also flagged `2025-12-18_STRAT_GDS_DataAIEthicsFramework` as a 4th definitional document, which drove the "single most direct definitional gloss in the whole corpus" note under "What surprised us" below; `deepseek-v4-flash:cloud` coded all 7 of that document's units `applies: false` for DEFINITIONAL, so that claim — and anything in `dissertation_outputs/umbrella_term_definitional_analysis.md` that relies on it — needs the author's re-check. Two dominant surface **forms** of the umbrella term itself: "societal wellbeing and public good" (Playbook only) and "harness the power of AI for (the) public good" (8 documents, Jan 2025 – Jan 2026, always followed by a list of entailments) — see `dissertation_outputs/umbrella_term_definitional_analysis.md` for the full 3-way breakdown (defined / used / listed-entailments) the author requested 2026-09-13. **Use without elaboration: 19 documents.** **Not present: 43 documents.** |

### Things to run w/ Claude — status

- ~~Round 2 and 3 of coding~~ — Round 1 now covers all 66 documents (two
  coding runs, see "Note on tooling" above); Round 2 consolidation
  (`guidebook_draft.yaml`) was re-run 2026-09-11 against the full corpus
  once the author supplied an Ollama Cloud API key (see Table 3 above) —
  **naming the sub-codes is still entirely the author's open task**, this
  only reran the clustering step, not the naming.
- **Identify all AI terms defined in the corpus** — done for "AI for the
  public good" / "public benefit" and close variants specifically (Table 4
  above); a broader sweep for *any* defined AI term (e.g. "AI", "frontier
  AI", "agentic AI", "sovereign AI") was not attempted and remains open.

### Addendum, 2026-09-11 — Ollama Cloud re-clustering

The guidebook gap flagged above ("What didn't work," item 1; Table 3's
original note) is closed: the author supplied an Ollama Cloud API key,
which was used to install Ollama locally, pull `embeddinggemma` (621 MB,
runs locally — cloud auth was not actually required for this specific
model, only for the account-gated pull), and re-run `06_consolidate.py`
against all 2,981 Round 1 records. Effect: cluster counts roughly doubled
for several questions (e.g. RESPONSIBILITY 36→59 clusters, NATURALISED_ORDER
105→137) simply from more instances entering the same 0.75-threshold
clustering, not from any change in method. `analysis/networks/thematic_network.json`
was regenerated immediately after: sub-code coverage moved from 35/66 to
**66/66 documents**, and the network grew from 365 to 1,953 edges over 467
sub-codes. The Ollama server and API key were used only for this one
recomputation and were not left running or stored anywhere in the repo.

### Addendum, 2026-09-18 — the `claude-code-local` interim pass fully replaced with Ollama

Per "Note on tooling" above: all 434 `claude-code-local` records from the
2026-09-10 intake were discarded and the 31 documents re-coded end to end
with `05_code.py` against Ollama Cloud (`kimi-k3:cloud`, falling back to
`deepseek-v4-flash:cloud` once the session quota was hit mid-run — the same
pattern as corpus v1's own model-switch history). `coding/round1/*.jsonl`
now has zero `claude-code-local` records; every one of the 1,001 unit ×
question pairs (91 units × 11 questions) across all 66 documents succeeded
with a real Ollama call, producing 4,078 records (3,790 `applies: true`,
3,758 `quote_verified: true` — 99.2%). The entire downstream chain was
re-run against this corrected corpus (`10_finalize.py`, plus
`14_export_embeddings.py`, `15_guidebook_summary.py` and
`16_render_markdown.py`): `guidebook_draft.yaml` (Table 3 above),
`metaphors_report.md` (592 distinct expressions), the intertextual network
(66 nodes, 107 edges), `agency_by_genre.csv` (558 AGENCY instances from
62/66 documents, 564/564 unit-question pairs succeeded), the NVivo exports, the thematic
network (66 document nodes, 534 sub-codes, 1,893 edges, 66/66 coverage), and
the Leiden communities QA. One finding did not survive the correction: see
the retraction under "What surprised us" and the updated Table 4 — the
`claude-code-local` pass's DEFINITIONAL hit on the *Data and AI Ethics
Framework* was not reproduced by the real model. No other per-document
claim elsewhere in this file was individually re-verified against the
2026-09-18 numbers; treat any specific number attributed to the 31-document
intake from before this date as superseded by `coding/round1/*.jsonl` and
the regenerated `analysis/` outputs.
