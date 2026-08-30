# Handoff — continuing this discourse-analysis pipeline

This file is meant to be handed directly to a Claude Code agent (or read by a
person) to pick up this project on a new machine. It is self-contained: follow
it top to bottom and you'll have a working clone with everything except one
capability (adding brand-new documents) fully reproducible — no external
services required for anything already in the repo.

## What this is

A discourse-analysis pipeline supporting a dissertation on "AI for the public
good" as a sociotechnical imaginary in UK government discourse on AI in public
services (GDS/DSIT, January 2024 – July 2026). Read these two files first,
in order:

1. [`PLAN.md`](PLAN.md) — the full methodological design and its constraints
   (three research objectives, SO1/SO2/SO3, everything the pipeline does maps
   to one of them).
2. [`README.md`](README.md) — repo structure, script inventory, the author's
   review checkpoints.
3. [`interpretation.html`](interpretation.html) — open it in a browser. It's
   the interpretation guide: a card per corpus document, how to read every
   deliverable, and an explicit list of assumptions/limitations.

The `AGENT — ` prefix marks the parts of this file addressed directly to you
(a Claude Code agent picking this up), as opposed to background for a human.

## AGENT — Step 0: check prerequisites, install whatever's missing

Don't assume `git` or Python are already installed — check first, and install
silently if they're missing rather than asking the user to do it manually.

```bash
git --version && python3 --version
```

If either command is missing, install based on the OS:

**macOS** — prefer Homebrew if it's already there (`brew --version`); if not,
installing Homebrew itself is a bigger, more invasive step, so check for
Xcode Command Line Tools first, since that alone provides `git`:
```bash
xcode-select --install        # provides git; user may need to click through a GUI prompt
# if python3 is still missing after that:
brew install python3          # only if brew is available; otherwise point the user to python.org
```

**Debian/Ubuntu Linux**:
```bash
sudo apt-get update && sudo apt-get install -y git python3 python3-venv python3-pip
```

**Fedora/RHEL**:
```bash
sudo dnf install -y git python3 python3-pip
```

**Windows** (if you're running in WSL, use the Linux instructions above for
the WSL environment; if running natively):
```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.13 -e
```

No GitHub account and no `gh` CLI are needed — the repository is public, so a
plain `git clone` over HTTPS works with no authentication. Don't install or
configure `gh` unless the user separately asks for something that needs it
(e.g. opening issues); it's not required for anything in this handoff.

After confirming `git` and `python3` both work, continue to Step 1.

## AGENT — Step 1: clone and set up

```bash
git clone https://github.com/fridaruh/uk-ai-public-good-discourse.git
cd uk-ai-public-good-discourse
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

That's it for setup. No API keys, no accounts, no Ollama needed for anything
that already exists in the repo — read on for why.

## AGENT — Step 2: what's already done and fully reproducible offline

Everything through Phase 6 of `PLAN.md` is complete and committed:

- `data/text/` — structured transcription of all 35 corpus documents (title /
  section heading / body / quotation blocks). The original PDFs/HTML are not
  in the repo (by design, to keep it light) but `data/raw/*.meta.json` has
  the source URL + hash for every one, and `data/raw/archive_urls.json` has
  an archive.org snapshot for each.
- `data/embeddings/` — the persisted embeddinggemma vectors (one per document
  section + the lexicon's semantic probes), so segmentation/retrieval results
  can be verified without re-embedding anything.
- `coding/round1/*.jsonl` — the full LLM coding output: 583 unit×question
  pairs, 2547 records, 98.8% verbatim-quote fidelity. Every record carries
  its `model`, `prompt_version` and `run_id`.
- `analysis/` — the intertextual network + map, the three NVivo-style
  queries, echo-phrases, the thematic network, NVivo exports, internal QA —
  all regenerated from the data above.
- `coding/guidebook_draft.yaml` + `analysis/guidebook_summary.html` — Phase 5
  candidate sub-codes (open `guidebook_summary.html` in a browser: it's an
  interactive review page — type final names per cluster, export a starting
  YAML). This is the author's next open task, not yours unless asked.

None of this needs regenerating. If you want to regenerate it anyway (e.g.
after editing a script), everything downstream of the raw data is pure
Python — run `.venv/bin/python scripts/10_finalize.py`, no Ollama involved.

The **only** thing in this pipeline that originally used Ollama (a local LLM
runtime) is coding brand-new documents added after this handoff. You will not
have Ollama available. Step 3 tells you what to do instead.

## AGENT — Step 3: adding a new document (no Ollama — you do the coding yourself)

When asked to add a document to the corpus, do NOT try to install or call
Ollama. Instead:

### 3a. Admission + intake (pure Python, works as-is)

```bash
.venv/bin/python scripts/add_document.py "<url>" --dry-run
```

This prints the admission checklist (time window, speaker-vs-publisher,
functional boundary of the digital centre, blog criterion,
producer-vs-scrutineer, written-vs-spoken — see `PLAN.md` Phase 7). Show the
checklist to the user and get their go-ahead before continuing — nothing
should enter the corpus without a human confirming the checklist. Once
confirmed:

```bash
.venv/bin/python scripts/add_document.py "<url>" --yes [--family Anthropic|Cohere|OpenAI|DeepMind|ElevenLabs] [--genre STRAT|MOU|PRGOV|PRCO|BLOG|WMS|REG]
```

This fetches the document, extracts it into the same block schema as the rest
of the corpus, appends a row to `data/manifest.csv` (`corpus_version` bumped),
and writes its coding units to `coding/units.jsonl`. All of this is plain
Python + `requests`/`BeautifulSoup`/`pymupdf` — no LLM involved yet.

### 3b. Coding the new document's units — this is where you replace Ollama

Read `coding/units.jsonl`, find the units for the new `doc_id` (their
`unit_id` starts with `<doc_id>::`). For **each unit**, and for **each of the
11 questions** in `coding/prompts/prompts_v1.yaml`, you personally answer the
question — the same way the prompt asks an LLM to: read the question's
`prompt` text in that YAML file (it tells you exactly what to extract and
what JSON shape to reason in), read the unit's `text`, and decide.

**The governing rule, unchanged from the whole pipeline: you locate and
extract, you do not interpret beyond what's asked.** If nothing in the
passage answers the question, that's a legitimate answer (`applies: false`) —
do not invent content to fill a record. Every `verbatim_quote` you write MUST
be an exact, character-for-character substring of the unit's `text` — copy it,
never paraphrase it, and verify the substring match yourself (in Python:
`quote in unit_text`) before writing `quote_verified`.

Append one JSON line per record to `coding/round1/<doc_id>.jsonl` (create the
file). This is the **exact schema** already used by every existing record —
match it precisely so downstream scripts (consolidation, exports, QA) keep
working unchanged:

```json
{
  "doc_id": "2026-08-30_BLOG_GDS_ExampleNewPost",
  "unit_id": "2026-08-30_BLOG_GDS_ExampleNewPost::s00",
  "heading": "the section heading text, or the doc title for a full-doc unit",
  "question": "BENEFICIARY",
  "so_tags": ["SO1", "SO2", "SO3"],
  "model": "claude-code-local",
  "prompt_version": 1,
  "run_id": "<a uuid4 you generate once per session, reused across all records from this run>",
  "timestamp": "2026-08-30T12:00:00+00:00",
  "applies": true,
  "confidence": 0.9,
  "answer_summary": "beneficiary=citizens; noun_used=citizens",
  "verbatim_quote": "the exact quoted sentence from the passage",
  "quote_verified": true,
  "instance_data": "{\"beneficiary\": \"citizens\", \"verbatim_quote\": \"the exact quoted sentence from the passage\", \"noun_used\": \"citizens\"}"
}
```

Notes on the fields:
- `so_tags` — copy from that question's entry in `prompts_v1.yaml` (`so_tags:` key).
- `model` — always literally `"claude-code-local"` for anything you code
  yourself. This is how the corpus stays honest about provenance: every
  record's origin (which Ollama model, or a human, or you) is traceable and
  filterable forever. Never write an Ollama model name for a record you produced.
- `answer_summary` — one string, `key=value; key2=value2` for every field in
  your JSON answer except `verbatim_quote` (that's what
  `scripts/05_code.py`'s `summarize_instance()` does — replicate it exactly
  so the CSV exports and the guidebook clustering keep reading it correctly).
- `instance_data` — the raw JSON object you produced for that instance,
  serialized as a string (matches the `Return JSON: {...}` shape in the
  question's prompt).
- If a question genuinely produces **multiple instances** in one passage
  (the prompt's schema is `instances: [...]`), write one record per instance,
  all sharing the same `doc_id`/`unit_id`/`question`/`run_id`.
- If nothing applies: one record with `applies: false`, `confidence`, and
  `answer_summary`/`verbatim_quote`/`quote_verified`/`instance_data` all `null`.
- The `METAPHOR` question additionally asks you to suggest a source domain,
  target domain, the `TARGET IS SOURCE` formula, a Lakoff & Johnson type, and
  what the mapping highlights/hides — same rule applies: these are your
  suggestions for the author to validate, not settled interpretation. Look at
  a few existing entries in `analysis/metaphors_report.md` to match the tone
  and grain expected.

Also produce one **document-level profile** record (the `DOC_PROFILE` prompt
under `doc_level` in `prompts_v1.yaml`, run once against the full document
text) and append it as a new line to `coding/round1/doc_profiles.jsonl`.

### 3c. Regenerate everything downstream

```bash
.venv/bin/python scripts/10_finalize.py
```

Pure Python, no network calls needed except none at all here — this
re-consolidates the guidebook draft, rebuilds the intertextual network and
map, the queries, the thematic network, the NVivo exports, the QA report, and
the hub (`index.html`). Check its summary table for any step that reports
`failed` and investigate before considering the intake done.

### 3d. Tell the human what happened

Report: the new `doc_id`, how many units/records you coded, how many
`applies: true` instances you found per question, and explicitly flag any
question where you were unsure (low confidence, ambiguous passage) so the
author can review those first. Point them at
`analysis/guidebook_summary.html` and `coding/validation/` — new records you
add are exactly the kind of thing that should go into a spot-check, not be
trusted blindly just because you produced them carefully.

## Ground rules that hold everywhere in this project

- **Never fabricate a `verbatim_quote`.** This is the single most
  load-bearing rule in the whole pipeline (it's literally what the Phase 3
  model evaluation in `coding/model_eval/decision.md` was optimizing for).
  A hallucinated quote is worse than an admitted "nothing found here."
- **The LLM (or you) locates and extracts; the author interprets.** Sub-code
  naming, the final metaphor domain assignment, and any qualitative reading
  of what a pattern "means" are the author's calls, not yours to settle.
- **Corpus admission needs a human's go-ahead.** Never skip the checklist
  step in `add_document.py` or add a document `--yes` without the user
  having seen and approved the checklist first.
- Everything in this repo is in **English**, and no output should refer to
  "Frida" — use "the author."
