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
| **SO1.** Examine the sociotechnical imaginary projected under the rhetoric of "AI for the public good" in GDS texts. | Jasanoff & Kim (imaginaries); Kaplan (narrative/plot); Lears (hegemony) | Coding of the 7 questions (all apply to SO1); definitional extractor; chronological comparison of definitions; METAPHOR; NARRATIVE_ARC; THREAT_TYPE |
| **SO2.** Trace how that imaginary moves from a statement of principles to strategic priorities, policy commitments, and public-facing claims. | Fairclough (intertextuality); Jasanoff & Kim; Lears (naturalisation) | Intertextual network (families + references + supersession); MECHANISM, PROJECTED FUTURE, NATURALISED ORDER questions; Period and AUDIENCE attributes; zero-count × Genre queries; semantic retrieval of the distributive claim; visualization's temporal slider |
| **SO3.** Analyse the evolution of the framing across the department's partnership documents with frontier AI companies. | Hajer (discourse coalitions); Lears (naturalisation); Fairclough (agent deletion, nominalisation, modality) | Echo-phrases by MoU family; AGENCY and MODALITY; intra-family and inter-family comparison; SAFEGUARD, RESPONSIBILITY, ACTANTS questions; shared metaphorical source domains government↔company; GDS-control × GDSTier query |

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

## Phase 4 — Round 1 coding (LLM)

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

## Phase 5 — Round 2 consolidation (the author, with support)

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
from one another); **spatial grouping = family** (the 5 MoU families as bounded
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
5. **METAPHOR** *(SO1, feeds NATURALISED ORDER for SO1/SO2)* — Lakoff & Johnson
   1980; MIP/MIPVU procedure (Pragglejaz 2007; Steen et al. 2010); optional bridge
   with Fairclough: Charteris-Black 2004. Per instance: verbatim expression →
   source domain → target domain → `TARGET IS SOURCE` formula (e.g. "turbocharge"
   → THE GOVERNMENT IS A MACHINE; "frontier AI" → AI DEVELOPMENT IS TERRITORIAL
   EXPLORATION; "harness" → AI IS A FORCE TO BE TAMED) → L&J type (structural /
   orientational / ontological / personification) → **what it illuminates / what
   it hides**. The "hides" field is the lexical mechanism of naturalisation
   (Lears) and feeds directly into question 7. Aggregates enabled, all within the
   SOs: source domains by speaker (SO1), shared government↔company domains by
   family (SO3, complements ECHO), temporal migration of domains (SO2). *The only
   addition that adds citations to the framework: requires incorporating L&J
   (+ MIP) into the theory chapter.*
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

| Step | Does | Serves | Author checkpoint |
|---|---|---|---|
| 0 | Manifest from the Excel file | base | Confirm count of 37 and flagged cases |
| 1 | Download + archiving + structured text | base | Review broken-links report |
| 2 | Segmentation + term/variants + embeddings | SO1/SO2 | Confirm `CHECK` cases; approve lexicon |
| 3 | Model evaluation | base | Code the sample; approve model |
| — | — | — | **Decide which proposed codes go in** |
| 4 | Round 1 coding | SO1/SO2/SO3 | 15–20% validation + agreement report |
| 5 | Clustering for consolidation | SO1/SO2/SO3 | **Name sub-codes (guidebook)** |
| 6 | Networks, queries, exports, viz | SO1/SO2/SO3 | Analytical reading — interpretation begins here |
| 7 | Incremental intake | per doc | Approve admission (checklist) and `candidate_codes` |

Stack: Python (project venv), PyMuPDF, requests/BeautifulSoup, Ollama API (cloud
for LLM; embeddings local or cloud), networkx + python-igraph, self-contained HTML
visualization. Intermediate data in flat files (CSV/JSONL/YAML), version-controllable.

---

Label language: coding labels standardised to English on 2026-08-29; prompts_v1.yaml
already emits Spanish label values for AGENCY/MODALITY/ACTANTS — mapped at
consolidation.
