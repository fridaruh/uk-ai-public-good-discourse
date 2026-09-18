# Review of the author's NVIVO coding — separating Round 1 from Round 2/3

**Source reviewed:** `NVIVO CODING R1.docx` (the author's analytic memos, one entry per
corpus document, corpus v1's 35 documents + `Dx` duplicate pass on document 36) and
`Research_Alignment_Matrix.docx` (the theoretical/methodological framework these memos
answer to).

**Why this review exists.** The author flagged that the NVIVO export is titled "R1" but
its content is not purely Round 1: some documents carry an explicit `ROUND 02 ->` header;
many more carry Round-2/3-level analytical content — intertextual links, cross-speaker
comparison, family-completion reasoning — folded into an entry that is still labelled
`ROUND 01`. This file makes that separation explicit, per document, and flags where Round 1
itself looks incomplete on the author's own account ("did not code much," "will have to
read in detail").

**This is a locate-and-classify pass, not a re-coding.** Nothing below overrides the
author's own analytic judgment; it sorts her existing notes against the definitions in
`PLAN.md` / `Research_Alignment_Matrix.docx` so she can see, at a glance, which of her own
observations are already Round 2/3-level synthesis she doesn't need to redo, and which
documents still need a Round 1 pass before their zero-counts can be trusted.

## Classification used

| Round | What it is (per PLAN.md / the Matrix) | What it looks like in the NVIVO memos |
|---|---|---|
| **Round 1** | Per-passage answers to the 7 core questions (BENEFICIARY, MECHANISM, SAFEGUARD, RESPONSIBILITY, PROJECTED_FUTURE, ACTANTS, NATURALISED_ORDER) + the narrative/AGENCY/METAPHOR observations, located within **one document's own text**. Table 2's document-level questions (function, force, structural position, voice) are also Round 1 — they describe the document itself, not its relation to others. | "Who is named as beneficiary? → members of the public and the economy"; a verbatim quote; "What I did: read the section, coded." |
| **Round 2** | Grouping/consolidating Round 1 answers **across documents**: intertextual links (this document cites/echoes that one), family-level or speaker-level comparison, timing/sequence arguments, admission/relevance judgment calls. This is exactly what `06_consolidate.py` + `06_network_v0.py` + the guidebook do computationally — Round 2 in this project is explicitly **assisted** by that pipeline, not purely manual. | "SIX DAYS AFTER THE BLUEPRINT, WHICH USES THE TERM"; "the only MoU that explicitly names GDS"; "That's intertextuality in Fairclough's sense." |
| **Round 3** (or beyond-corpus) | Connections to the theory chapter / literature review, or methodological process notes about how the coding itself should proceed. Not corpus coding at all — thesis-writing scaffolding that happens to live in the same memo. | "gets my attention since it's something I read about in the literature review"; "might be better to do quantitative approaches using Claude code." |

None of this is a criticism of mixing them — grounded theory (Saldaña 2025, cited in
`PLAN.md`) expects noticing to happen before formal categories exist. The point is only to
stop the R1/R2 labels from misleading anyone (including future-you) about what still needs
a first pass versus what is already synthesis.

## Per-document classification

| Doc (# in NVIVO memo) | Round 1 in the memo | Round 2/3 already embedded | Flag |
|---|---|---|---|
| D1 AI Playbook | 4 of 7 core Qs answered explicitly (beneficiary/mechanism/safeguard/responsibility); 3 narrative Qs listed but not answered in this memo | Explicit `ROUND 02 ->` block: Table 2 questions (function/force/structural position/voice) + a forward methodological note ("how would Gramsci interrogate this... using gen AI") | Narrative Qs (future/hero/order) not visibly answered — check they exist elsewhere in the live NVIVO project, not just this export |
| D2 Playbook launch blog | Read/coded, no per-question breakdown in memo | A pattern-recognition claim ("I can recognize from a pattern of what they name/list") — borderline R2, thin evidence trail | Core Qs not itemised here |
| D3 Blueprint | Six-point plan = MECHANISM answer | Direct quote from the Roadmap establishing Blueprint→Roadmap intertextuality; explicit `R2:` tag for a forward re-read of Section 3 | R2 material already substantial and well-evidenced |
| D4 Roadmap launch blog | Read/coded, quotes only | — | Core Qs not itemised here |
| D5 Roadmap | Beneficiary categories (citizens/business/workers); 2 subpillars = MECHANISM | "will consider that for when I do round 2 of coding" — explicit forward reference | Document was split into an expanded version for later coding; make sure both halves get a full R1 pass |
| D6 Roadmap WMS | Term-used quote only | — | Core Qs not itemised here |
| D7 Top British AI Expertise | Term-used quote | Anthropic's own use of the phrase compared to government's (discourse-coalition observation) | "Ready for scans for R2" — author's own R1/R2 boundary marker |
| D8 AI Opportunities Action Plan | **Thin** — "did not code much... will have to read in detail" | Causal link drawn from Recommendation 33 to the MoU programme (a real R2/R3-level claim, stated as a hypothesis: "I would think that...") | **R1 incomplete on the author's own account** — the most-cited document in the corpus (44 in-edges) has the thinnest Round 1 coding |
| D9 Action Plan gov response | "No evident codes here" | Notes the AI Opportunities Unit's creation (context, not coding) | **R1 incomplete** |
| D10 Action Plan One Year On | "Only one code found" | — | **R1 incomplete**; author flags needing to "draw a line and justify" the term-sections-only approach |
| D11 Generative AI Framework | Term-used quote ("supports the public good") | Withdrawal/supersession relationship to the Playbook (R2-level, and the one supersession edge already coded into `intertextual_v0.json`) | — |
| D12 Pro-innovation AI regulation response | Forewords + keyword search on "public" | Explicit self-identification: "That's intertextuality in Fairclough's [sense]" | Author already naming her own R2 move correctly |
| D13 PM "turbocharge AI" blueprint | Beneficiary = "working people" | **Heavy R2/R3**: Labour-language correlation, 5-govt-vs-22-industry voice count, MoU-timing-relative-to-quotes analysis, naming-sequence argument (digital centre named 8 days before Blueprint) | The clearest example of R2/R3 analysis filed under "ROUND 01" — this entry alone justifies the author's "R1 label but R1+R2 content" observation |
| D14 Blueprint WMS | Term-used quote, AGENCY-shaped observation ("FIRST-PERSON PLURAL, GOVERNMENT AS AGENT") | — | AGENCY tag is R1-level (passage-internal), correctly scoped despite looking analytical |
| D15 State of Digital Gov Review | "2 codes emerged but not relevant" | — | **R1 thin** |
| D16 Same name, new ambitions | Read/coded whole document | Timing argument ("SIX DAYS AFTER THE BLUEPRINT"); a `COMMENT` asking to "add dates to all to analyze timeline evolution" (methodological, R3-adjacent) | The dated-timeline request is exactly what `date` already does in `manifest.csv` — already satisfied by the pipeline |
| D17 AI Exemplars blog | Term-used quote, portfolio-approach context | — | — |
| D18 Anthropic MoU | "A few codes" | Forward reference to a later document (GOV.UK assistant "built with GDS engineers") | — |
| D19 Anthropic signs MOU (Anthropic voice) | "2 things" | — | **R1 thin** |
| D20 Anthropic GOV.UK partnership | Term-used quotes ("public benefit") | Admission-relevance reasoning ("NOT AN ANNOUNCEMENT blog, still we will keep") | This is Phase 0/7 admission judgment, not coding — a fourth category worth naming separately if the memo is reorganised |
| D21 Cohere MoU | "Almost no codes emerged" | Family-comparison flag: "the only MoU that explicitly names GDS" | **R1 thin**, but the R2 flag here is exactly what feeds `gds_tier = T2` |
| D22 Cohere Canada/UK (Cohere voice) | "No term used" | Explicit statement that MoU/announcement genres "might be better... using Claude code" — i.e., the author naming the need for this pipeline's assistance in real time | Direct textual evidence for "R2/R3 assisted by this code" |
| D23 OpenAI MoU | "No term" | — | **R1 thin** |
| D24 OpenAI expand UK office | "No term" | — | **R1 thin** |
| D25 OpenAI strategic partnership | "Few codes" | — | **R1 thin** |
| D26 Next chapter sovereign AI (MoJ) | Metaphor note | Cross-speaker trust-framing comparison (government vs. OpenAI's use of "trust") | Comparison is genuinely R2 — a good AGENCY/NATURALISED_ORDER candidate once formalised |
| D27 Stargate UK | "Not really any codes" | Admission-boundary reasoning ("recommend moving to context") | **R1 thin**; another Phase-0/7-flavoured note, not coding |
| D28 DeepMind MoU | Section structure noted (Table 2-level, R1) | — | — |
| D29 DeepMind national renewal (govside) | Term found twice | **AGENCY cross-document comparison**: "we harness" (govt, 1st-person-plural) vs. the MoU's agentless passive "AI will be harnessed" — a genuinely strong finding | This is exactly the kind of R2 pattern `agency_by_genre.csv` is built to surface at scale |
| D30 DeepMind deepening AISI | — | Intra-family split-release comparison (vs. D31); a literature-review connection note (Chain-of-Thought monitoring) — the latter is **R3**, not corpus coding | — |
| D31 DeepMind strengthening partnership | Term used once, full quotes | — | — |
| D32 ElevenLabs MoU | Near-miss quotes | Relevance judgment on Service Standard 5 citation | — |
| D33/D34 ElevenLabs (research / bring voice AI) | Both minimal | Cross-document duplicate-quote flag (same minister quote in both) | — |
| D35 Tackling AI security risks | Term absent (verified read) | **Heaviest R2/R3 in the set**: explicit family-completion verification against D23/D28's government releases; a citizens-as-protected vs. citizens-as-served semantic-role finding; AISI renaming/remit-narrowing note | This entry is functionally a mini Round-2 memo on its own — strong candidate for a `NATURALISED_ORDER`/`ACTANTS` sub-code once named |
| D36/Dx Data and AI Ethics Framework | Update history (4 new principles) | **Definitional intertextuality**: connects "deliver public good" (2025) back to the Roadmap's "societal wellbeing and public good" (2025) heading | Independently converges with the pipeline's own finding — see below |

## Where the author's manual reading already agrees with the pipeline

Three convergences worth knowing about, because they cross-validate each other without
either side having seen the other's output:

1. **D36/Dx's "deliver public good" note** is the same passage the automated DEFINITIONAL
   question flagged as one of only **4 explicit (glossed) definitions in 66 documents** —
   see `interpretation.html`'s "Term defined vs. term used" section. The author found this
   by close reading; the pipeline found it by running the same question mechanically over
   every unit. Same answer, two independent methods.
2. **D29's AGENCY observation** ("we harness" vs. the MoU's agentless passive) is precisely
   the pattern `11_agency_query.py` / `agency_by_genre.csv` was built to detect at scale
   (411 AGENCY records corpus-wide). The author's single hand-found instance is a good
   spot-check case for validating that CSV once it's reviewed.
3. **D13's discourse-coalition analysis** (voice counts, timing relative to MoU signings) is
   exactly SO3's design intent (Hajer 1995, discourse coalitions) — already the sharpest
   manual analysis in the set, and a template for what the echo-phrase/agency data could
   support for the other MoU families if extended the same way.

## What this means for "Round 1 is what I did in NVIVO"

Fourteen of the 35 entries (D8, D9, D10, D15, D19, D21, D22, D23, D24, D25, D27, D30, D32,
D33/34) are flagged above as having thin or no per-question Round 1 coding — mostly on
documents where the term is absent and the author's own notes already say she scanned
rather than close-read. This is not necessarily a problem: several of those documents
(MoUs, press releases with no term) are exactly the zero-count cases the design expects
(`term_status = absent` is itself a finding, not a gap) — but it does mean any claim drawn
from those documents' *narrative* questions (future/hero/threat/order), as opposed to their
term-presence status, should be treated as author-flagged-incomplete until she does a full
read, not as a completed Round 1 pass.

The documents with the richest embedded Round 2/3 content (D3, D7, D8, D12, D13, D16, D18,
D21, D22, D26, D29, D30, D35, D36) are, not coincidentally, mostly the documents that sit at
family or genre boundaries — exactly where intertextual/comparative noticing happens
naturally while reading. That content is valuable and should not be re-done; it should be
pulled into the guidebook naming pass (Phase 5) and the network's edge evidence
(`intertextual_v0.json`) rather than left stranded in a memo titled "R1."
