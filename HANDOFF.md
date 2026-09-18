# Handoff — continuing this discourse-analysis pipeline

This file is meant to be handed directly to a Claude Code agent (or read by a
person) to pick up this project on a new machine — **written for a Windows
machine specifically**, since that's where this will be read next, with
macOS/Linux equivalents noted alongside. It is self-contained: follow it top
to bottom and you'll have a working clone with everything except one
capability (adding brand-new documents without Ollama) fully reproducible —
no external services required for anything already in the repo.

## What this is

A discourse-analysis pipeline supporting a dissertation on "AI for the public
good" as a sociotechnical imaginary in UK government discourse on AI in public
services (GDS/DSIT, January 2024 – July 2026). Read these three files first,
in order:

1. [`PLAN.md`](PLAN.md) — the full methodological design and its constraints
   (three research objectives, SO1/SO2/SO3, everything the pipeline does maps
   to one of them). Read its **"Note on tooling"** section before touching
   anything Round-1-coding-related — see "What changed on 2026-09-18" below
   for why that section matters more than it looks.
2. [`README.md`](README.md) — repo structure, script inventory, the author's
   review checkpoints.
3. [`interpretation.html`](interpretation.html) — open it in a browser. It's
   the interpretation guide: a card per corpus document, how to read every
   deliverable, and an explicit list of assumptions/limitations.

The `AGENT — ` prefix marks the parts of this file addressed directly to you
(a Claude Code agent picking this up), as opposed to background for a human.

## What changed on 2026-09-18 (read this before Step 3)

The corpus grew from 35 to **66 documents** via a new selection file,
`corpus.xlsx` (now tracked in the repo root — `scripts/01_manifest.py` reads
it by default). The 31 new documents went through `add_document.py`'s Phase 7
intake correctly, but their Round 1 coding was originally done by a **Claude
Code agent hand-answering the 11 questions per unit** (labelled
`"model": "claude-code-local"`) because no Ollama instance was available on
the machine doing that intake. That interim pass was **fully discarded** on
2026-09-18 and every one of the 31 documents was re-coded against real
Ollama Cloud models. `coding/round1/*.jsonl` now has **zero**
`claude-code-local` records anywhere — you can verify this yourself:

```powershell
Select-String -Path coding\round1\*.jsonl -Pattern 'claude-code-local'
# (expect no output)
```

**Why this matters for you:** the interim pass silently produced a false
positive finding (a DEFINITIONAL instance that a real model did not
reproduce — see `PLAN.md`'s "Note on tooling" and its retraction under "What
surprised us"). Hand-coding as a substitute for the evaluated model pipeline
is exactly the failure mode this repo's `model` provenance field exists to
catch. **Do not repeat it.** If you are ever asked to add or re-code
documents and Ollama is not reachable, the correct move is to say so and stop
— not to answer the questions yourself under a placeholder model name. See
Step 3 below for what to do instead.

## AGENT — Step 0: check prerequisites, install whatever's missing

Don't assume `git`, Python, or Ollama are already installed — check first,
and install silently if they're missing rather than asking the user to do it
manually.

**Windows (PowerShell):**
```powershell
git --version; py -3 --version; ollama --version
```
If any is missing:
```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.13 -e
# Ollama for Windows (no WSL needed — it runs as a native background service):
winget install --id Ollama.Ollama -e
```
Restart the terminal after `winget install` so `PATH` updates take effect
before re-checking versions.

**macOS:**
```bash
git --version && python3 --version && ollama --version
```
```bash
xcode-select --install        # provides git; user may need to click through a GUI prompt
brew install python3          # only if brew is available and python3 is still missing
brew install ollama           # or download from https://ollama.com/download
```

**Debian/Ubuntu Linux:**
```bash
sudo apt-get update && sudo apt-get install -y git python3 python3-venv python3-pip
curl -fsSL https://ollama.com/install.sh | sh
```

No GitHub account and no `gh` CLI are needed — the repository is public, so a
plain `git clone` over HTTPS works with no authentication. Don't install or
configure `gh` unless the user separately asks for something that needs it.

After confirming `git`, Python, and `ollama` all work, continue to Step 1.

## AGENT — Step 1: clone and set up

**Windows (PowerShell):**
```powershell
git clone https://github.com/fridaruh/uk-ai-public-good-discourse.git
cd uk-ai-public-good-discourse
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull embeddinggemma
ollama pull kimi-k3:cloud             # needs an Ollama Cloud session for anything beyond DOC_PROFILE-free local use
ollama pull deepseek-v4-flash:cloud   # fallback once kimi-k3:cloud hits its session usage quota
```

**macOS / Linux:**
```bash
git clone https://github.com/fridaruh/uk-ai-public-good-discourse.git
cd uk-ai-public-good-discourse
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ollama pull embeddinggemma
ollama pull kimi-k3:cloud
ollama pull deepseek-v4-flash:cloud
```

**Do not reuse a `.venv` committed to or copied from another machine** — it
is a symlink farm / launcher tied to that machine's OS and Python install
(a macOS `.venv` has a `bin/` directory with shell shebangs; a Windows one
has `Scripts/` with `.exe` launchers). `.venv/` is gitignored precisely so
each machine builds its own. If you find a `.venv` already present that
doesn't match the current OS (e.g. `.venv/bin/` missing but `.venv/Lib/`
present on a machine that isn't Windows), delete it and rebuild:
```powershell
Remove-Item -Recurse -Force .venv
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Every command in this file and in the other docs is written as
`.venv/bin/python scripts/<script>.py` (the macOS/Linux form). On Windows,
substitute `.venv\Scripts\python.exe scripts\<script>.py` — same script, same
arguments, just the interpreter path and separators change. All scripts open
files with `encoding="utf-8"` explicitly, so this works identically
regardless of the OS's default locale (this used to silently corrupt
non-ASCII text — curly quotes, en-dashes — on Windows' `cp1252` default
before that fix; it's why every `open(...)` call in `scripts/` you might
write yourself should also pass `encoding="utf-8"`).

## AGENT — Step 2: what's already done and fully reproducible offline

Everything through Phase 6 of `PLAN.md` is complete and committed, for all
**66 documents**:

- `data/text/` — structured transcription of all 66 corpus documents (title /
  section heading / body / quotation blocks). The original PDFs/HTML are not
  in the repo (by design, to keep it light); `data/raw/*.meta.json` has the
  source URL + hash for documents fetched via the batch fetch scripts, and
  `data/raw/archive_urls.json` has an archive.org snapshot for each. (Note:
  documents added via `add_document.py`'s Phase 7 intake do not currently get
  a `.meta.json` written — a known gap in that script, not something you need
  to fix unless asked.)
- `data/embeddings/` — the persisted embeddinggemma vectors (one per document
  section + the lexicon's semantic probes, corpus-wide), so segmentation/
  retrieval results can be verified without re-embedding anything.
- `coding/round1/*.jsonl` — the full LLM coding output: 1,001 unit×question
  pairs, 4,078 records, 99.2% verbatim-quote fidelity, **every record from a
  real Ollama Cloud model** (`kimi-k3:cloud` or `deepseek-v4-flash:cloud` —
  no `claude-code-local` anywhere as of 2026-09-18). Every record carries its
  `model`, `prompt_version` and `run_id`.
- `analysis/` — the intertextual network + map, the three NVivo-style
  queries, echo-phrases, the thematic network, NVivo exports, internal QA —
  all regenerated from the data above, corpus-wide.
- `coding/guidebook_draft.yaml` + `analysis/guidebook_summary.html` — Phase 5
  candidate sub-codes (open `guidebook_summary.html` in a browser: it's an
  interactive review page — type final names per cluster, export a starting
  YAML). This is the author's next open task, not yours unless asked.

None of this needs regenerating. If you want to regenerate it anyway (e.g.
after editing a script), everything downstream of `coding/round1/` is pure
Python — run `.venv/bin/python scripts/10_finalize.py`, no Ollama involved —
then, if you also touched the guidebook or any `.md` deliverable,
`.venv/bin/python scripts/15_guidebook_summary.py` and
`.venv/bin/python scripts/16_render_markdown.py`.

The **only** things in this pipeline that need Ollama are (a) coding
brand-new documents (Round 1), and (b) re-embedding if `data/embeddings/`
ever needs to be regenerated from scratch. You now have Ollama installed
(Step 0/1), so — unlike the previous version of this file — **you should use
it**, not work around it.

## AGENT — Step 3: adding a new document

### 3a. Admission + intake (pure Python, works as-is)

```
.venv/bin/python scripts/add_document.py "<url>" --dry-run
```

This prints the admission checklist (time window, speaker-vs-publisher,
functional boundary of the digital centre, blog criterion,
producer-vs-scrutineer, written-vs-spoken — see `PLAN.md` Phase 7). Show the
checklist to the user and get their go-ahead before continuing — nothing
should enter the corpus without a human confirming the checklist. Once
confirmed:

```
.venv/bin/python scripts/add_document.py "<url>" --yes [--family Anthropic|Cohere|OpenAI|DeepMind|ElevenLabs|NVIDIA|Cisco|Synthesia] [--genre STRAT|MOU|PRGOV|PRCO|BLOG|WMS|REG]
```

This fetches the document, extracts it into the same block schema as the rest
of the corpus, appends a row to `data/manifest.csv` (`corpus_version`
bumped), and writes its coding units to `coding/units.jsonl`. All of this is
plain Python + `requests`/`BeautifulSoup`/`pymupdf` — no LLM involved yet. It
prints a `coding pending: <command>` line at the end — that command is
exactly Step 3b.

### 3b. Coding the new document's units — use Ollama, always

```
.venv/bin/python scripts/05_code.py --doc <doc_id>
```

This is the same script and the same real model (`kimi-k3:cloud`, per
`coding/model_eval/decision.md`'s Phase 3 evaluation) that coded every other
document in the corpus. It handles verbatim-quote verification, retries, and
resume-on-quota-limit automatically — you do not need to re-implement any of
that.

**If this command fails because Ollama is unreachable or the model can't be
pulled:** stop and tell the user. Do not answer the 11 questions yourself and
write `coding/round1/<doc_id>.jsonl` by hand under any model label,
`claude-code-local` or otherwise — see "What changed on 2026-09-18" above for
exactly what went wrong the last time this happened and what it cost to fix.
The one legitimate exception is if the user *explicitly* asks you to
hand-code as a stopgap knowing the tradeoff; if so, label it clearly, tell
them it is not equivalent to a real model run, and flag it prominently in
your report back (Step 3d) so it isn't mistaken for finished Round 1 coding
later.

**If the session usage quota is hit mid-run** (`429` errors, `kimi-k3:cloud`
specifically), re-run the same command with
`--model deepseek-v4-flash:cloud` to finish the remaining pairs — `05_code.py`
resumes automatically and only spends calls on what's still missing. This is
exactly what happened for the 2026-09-18 re-code of the 31 new documents (90
of 440 unit×question pairs succeeded on `kimi-k3:cloud` before the quota
hit; `deepseek-v4-flash:cloud` finished the remaining 350) and is the
expected, normal way to complete a large coding run on the free tier.

Also run the document-level profile, which `05_code.py` already does as part
of the same invocation (it processes `DOC_PROFILE` for any doc missing one
before the unit-level loop) — you do not need a separate command for it.

### 3c. Regenerate everything downstream

```
.venv/bin/python scripts/10_finalize.py
.venv/bin/python scripts/15_guidebook_summary.py
.venv/bin/python scripts/16_render_markdown.py
```

Pure Python, no network calls needed — this re-consolidates the guidebook
draft, rebuilds the intertextual network and map, the queries, the thematic
network, the NVivo exports, the QA report, the hub (`index.html`), the
interactive guidebook review page, and the themed `.html` renders of every
`.md` deliverable. Check `10_finalize.py`'s summary table for any step that
reports `failed` and investigate before considering the intake done.

### 3d. Tell the human what happened

Report: the new `doc_id`, how many units/records were coded, how many
`applies: true` instances per question, the exact model(s) used
(`kimi-k3:cloud` / `deepseek-v4-flash:cloud`, per-record — never say "coded"
without naming the model), and explicitly flag any question where the model's
confidence was low or the passage was ambiguous so the author can review
those first. Point them at `analysis/guidebook_summary.html` and
`coding/validation/` — new records are exactly the kind of thing that should
go into a spot-check, not be trusted blindly.

## Ground rules that hold everywhere in this project

- **Never fabricate a `verbatim_quote`.** This is the single most
  load-bearing rule in the whole pipeline (it's literally what the Phase 3
  model evaluation in `coding/model_eval/decision.md` was optimizing for).
  A hallucinated quote is worse than an admitted "nothing found here."
- **Round 1 coding is Ollama's job, not yours.** See "What changed on
  2026-09-18" and Step 3b — this is the one rule this file exists to
  reinforce after it was violated once already.
- **The LLM locates and extracts; the author interprets.** Sub-code naming,
  the final metaphor domain assignment, and any qualitative reading of what a
  pattern "means" are the author's calls, not yours to settle.
- **Corpus admission needs a human's go-ahead.** Never skip the checklist
  step in `add_document.py` or add a document `--yes` without the user
  having seen and approved the checklist first.
- Everything in this repo is in **English**, and no output should refer to
  "Frida" — use "the author."
