#!/usr/bin/env python3
"""Phase 6E -- NVivo exports: attribute classification sheet + coded passages.

Two direct-import-format outputs, written into analysis/nvivo/:

(a) classification_sheet.csv -- one row per document in data/manifest.csv,
    first column is the document/unit name (doc_id, matching the source name
    used everywhere else in this project, e.g. data/text/<doc_id>.json),
    followed by the NVivo classification-sheet attribute columns: Genre,
    Speaker, Side, Family, GDSTier, Stage, TermStatus, Year. Independent of
    Round 1 coding -- always corpus-complete (all 35 manifest rows, including
    the CONTEXT_ document).

(b) coded_passages.csv -- one row per successful Round 1 instance (question
    applies, no "error" field, a verbatim quote was extracted) across the
    corpus, from whichever documents Round 1 has reached so far: doc_id,
    unit_id, question, sub_answer, verbatim_quote, quote_verified, model,
    run_id. sub_answer is `answer_summary`, the single human-readable string
    the coding pipeline already produces for every question type. Includes
    ALL successful records regardless of coverage; carries a leading
    "# STATUS: PARTIAL ..." comment row when Round 1 has not completed.

Idempotent: re-run any time coding/round1/*.jsonl has more successful
records; both files are fully regenerated each run.

Usage:
    .venv/bin/python scripts/12_nvivo_export.py
"""
import csv
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "manifest.csv")
RUN_META = os.path.join(ROOT, "coding", "round1", "run_meta.json")
OUT_DIR = os.path.join(ROOT, "analysis", "nvivo")
OUT_CLASSIFICATION = os.path.join(OUT_DIR, "classification_sheet.csv")
OUT_PASSAGES = os.path.join(OUT_DIR, "coded_passages.csv")

SKIP_FILES = {"doc_profiles.jsonl", "definitional_instances.jsonl"}


def load_manifest():
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_classification_sheet(rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_CLASSIFICATION, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["doc_id", "Genre", "Speaker", "Side", "Family",
                          "GDSTier", "Stage", "TermStatus", "Year"])
        for r in rows:
            year = (r.get("date") or "")[:4]
            writer.writerow([
                r["doc_id"], r.get("genre", ""), r.get("speaker", ""),
                r.get("side", ""), r.get("family", ""), r.get("gds_tier", ""),
                r.get("stage", ""), r.get("term_status", ""), year,
            ])
    print(f"classification_sheet.csv: {len(rows)} documents -> {OUT_CLASSIFICATION}")


def load_run_meta():
    if not os.path.exists(RUN_META):
        return None, None, None
    meta = json.load(open(RUN_META, encoding="utf-8"))
    runs = meta.get("runs", [])
    if not runs:
        return None, None, None
    run = runs[-1]
    return run.get("pct_calls_succeeded"), run.get("n_docs_with_at_least_one_success"), run.get("n_docs_total")


def load_coded_passages():
    passages = []
    n_attempted = 0
    n_ok = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "coding/round1/*.jsonl"))):
        base = os.path.basename(path)
        if base in SKIP_FILES or base.startswith("CONTEXT_"):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                n_attempted += 1
                if "error" in d:
                    continue
                n_ok += 1
                if not d.get("applies") or not d.get("verbatim_quote"):
                    continue
                passages.append({
                    "doc_id": d.get("doc_id", ""),
                    "unit_id": d.get("unit_id", ""),
                    "question": d.get("question", ""),
                    "sub_answer": d.get("answer_summary", "") or "",
                    "verbatim_quote": d.get("verbatim_quote", "") or "",
                    "quote_verified": d.get("quote_verified", ""),
                    "model": d.get("model", ""),
                    "run_id": d.get("run_id", ""),
                })
    return passages, n_attempted, n_ok


def write_coded_passages(passages, n_attempted, n_ok):
    pct_calls, n_docs_ok, n_docs_total = load_run_meta()
    is_partial = pct_calls is None or pct_calls < 99.5
    docs_covered = len({p["doc_id"] for p in passages})

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PASSAGES, "w", newline="", encoding="utf-8") as f:
        if is_partial:
            pct_txt = f"{pct_calls:.1f}%" if pct_calls is not None else "unknown"
            f.write(
                "# STATUS: PARTIAL -- regenerate after Round 1 completes. "
                f"Coverage: {docs_covered} documents contributed at least one coded passage "
                f"({len(passages)} passages from {n_ok}/{n_attempted} unit-question pairs attempted "
                f"so far across all questions; latest Round 1 run at {pct_txt} of calls -- see "
                "coding/round1/run_meta.json). This file contains ALL successful records to date, "
                "but is NOT corpus-wide; re-run scripts/12_nvivo_export.py once Round 1 completes.\n"
            )
        writer = csv.writer(f)
        writer.writerow(["doc_id", "unit_id", "question", "sub_answer",
                          "verbatim_quote", "quote_verified", "model", "run_id"])
        for p in passages:
            writer.writerow([p["doc_id"], p["unit_id"], p["question"], p["sub_answer"],
                              p["verbatim_quote"], p["quote_verified"], p["model"], p["run_id"]])

    print(f"coded_passages.csv: {len(passages)} passages from {docs_covered} documents "
          f"({n_ok}/{n_attempted} unit-question pairs succeeded so far) -> {OUT_PASSAGES}")
    if is_partial:
        pct_txt = f"{pct_calls:.1f}%" if pct_calls is not None else "unknown"
        print(f"STATUS: PARTIAL -- latest Round 1 run at {pct_txt} of calls. "
              "Re-run after Round 1 completes.")
    else:
        print("STATUS: COMPLETE")


def main():
    manifest_rows = load_manifest()
    write_classification_sheet(manifest_rows)

    passages, n_attempted, n_ok = load_coded_passages()
    write_coded_passages(passages, n_attempted, n_ok)


if __name__ == "__main__":
    main()
