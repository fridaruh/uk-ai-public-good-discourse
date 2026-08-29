#!/usr/bin/env python
"""Fase 4 -- Codificacion Ronda 1 (LLM).

Corre las 11 preguntas de coding/prompts/prompts_v1.yaml sobre las 53 unidades
de coding/units.jsonl, y DOC_PROFILE sobre el texto completo de cada uno de
los 35 documentos. Usa el modelo ganador de la Fase 3 (coding/model_eval/decision.md).

Uso:
    .venv/bin/python scripts/05_code.py                  # corrida completa
    .venv/bin/python scripts/05_code.py --doc <doc_id>    # solo un documento
    .venv/bin/python scripts/05_code.py --questions core  # solo las 7 preguntas nucleo
    .venv/bin/python scripts/05_code.py --model <name>    # forzar modelo

Salidas:
    coding/round1/<doc_id>.jsonl              -- registros pregunta x instancia
    coding/round1/doc_profiles.jsonl           -- un registro DOC_PROFILE por doc
    coding/round1/definitional_instances.jsonl -- applies=true de DEFINITIONAL, orden cronologico
    coding/round1/run_meta.json                -- metadatos de la corrida
    coding/validation/sample_for_frida.csv     -- muestra 15-20% para doble codificacion
      (solo se regenera en corrida completa, no con --doc)
"""
import argparse
import csv
import json
import os
import random
import re
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLLAMA_URL = "http://localhost:11434/api/generate"
TIMEOUT = 180
RETRIES = 2
CONCURRENCY = 4
PROMPT_VERSION = 1
MAX_DOC_CHARS = 12000

CORE_QUESTIONS = [
    "BENEFICIARY", "MECHANISM", "SAFEGUARD", "RESPONSIBILITY",
    "PROJECTED_FUTURE", "ACTANTS", "NATURALISED_ORDER",
]

CORRECTIVE_SUFFIX = (
    "\n\nIMPORTANT CORRECTION: at least one \"verbatim_quote\" in your previous "
    "answer was NOT an exact substring of the passage above. Re-read the passage "
    "and copy each verbatim_quote EXACTLY, character for character, from the "
    "passage text. Return the corrected JSON now, same schema."
)


def default_model():
    """Read the winning model from coding/model_eval/decision.md."""
    path = os.path.join(ROOT, "coding/model_eval/decision.md")
    if os.path.exists(path):
        text = open(path, encoding="utf-8").read()
        m = re.search(r"Modelo ganador:\s*`([^`]+)`", text)
        if m:
            return m.group(1)
    return "gpt-oss:120b-cloud"


def load_manifest():
    manifest = {}
    with open(os.path.join(ROOT, "data/manifest.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            manifest[row["doc_id"]] = row
    return manifest


def load_doc_json(doc_id):
    path = os.path.join(ROOT, "data/text", doc_id + ".json")
    return json.load(open(path, encoding="utf-8"))


def doc_title(doc_id, doc_json_cache):
    d = doc_json_cache[doc_id]
    for b in d["blocks"]:
        if b["structural_position"] == "title":
            return b["text"].strip()
    return doc_id


def full_doc_text(doc_id, doc_json_cache, max_chars=MAX_DOC_CHARS):
    d = doc_json_cache[doc_id]
    parts = []
    for b in d["blocks"]:
        parts.append(b["text"])
    text = "\n".join(parts)
    return text[:max_chars]


def build_doc_context(doc_id, manifest, doc_json_cache):
    row = manifest.get(doc_id, {})
    title = doc_title(doc_id, doc_json_cache)
    return f"{title} | {row.get('date','?')} | {row.get('genre','?')} | {row.get('speaker','?')} | {row.get('family','None')}"


def load_units():
    units = []
    with open(os.path.join(ROOT, "coding/units.jsonl"), encoding="utf-8") as f:
        for line in f:
            units.append(json.loads(line))
    return units


def load_prompts():
    with open(os.path.join(ROOT, "coding/prompts/prompts_v1.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def call_ollama(model, prompt, retries=RETRIES):
    last_err = None
    for _ in range(retries + 1):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0},
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                last_err = data["error"]
                continue
            return data.get("response", ""), None
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            time.sleep(1)
    return "", last_err


def summarize_instance(inst):
    """Compact human-readable summary of one instance dict, minus verbatim_quote."""
    parts = []
    for k, v in inst.items():
        if k in ("verbatim_quote",):
            continue
        parts.append(f"{k}={v}")
    return "; ".join(parts)


def code_unit_question(model, run_id, unit, qname, qdef, header):
    passage = unit["text"]
    full_prompt = header + "\n" + qdef["prompt"]
    raw, err = call_ollama(model, full_prompt)
    timestamp = datetime.now(timezone.utc).isoformat()
    base = {
        "doc_id": unit["doc_id"],
        "unit_id": unit["unit_id"],
        "heading": unit.get("heading"),
        "question": qname,
        "so_tags": qdef.get("so_tags", []),
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "run_id": run_id,
        "timestamp": timestamp,
    }
    if err:
        return [dict(base, applies=None, error=err, raw_response=raw)]

    try:
        parsed = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        return [dict(base, applies=None, error=f"json_parse_error: {e}", raw_response=raw)]

    applies = parsed.get("applies") if isinstance(parsed, dict) else None
    confidence = parsed.get("confidence") if isinstance(parsed, dict) else None
    instances = parsed.get("instances", []) if isinstance(parsed, dict) else []

    if not applies or not instances:
        return [dict(base, applies=bool(applies), confidence=confidence,
                      answer_summary=None, verbatim_quote=None, quote_verified=None,
                      instance_data=None)]

    # check verbatim quotes; retry whole call once if any fail
    def check(insts):
        return [(inst.get("verbatim_quote") or "") in passage for inst in insts]

    oks = check(instances)
    if not all(oks):
        raw2, err2 = call_ollama(model, full_prompt + CORRECTIVE_SUFFIX)
        if not err2:
            try:
                parsed2 = json.loads(raw2)
                instances2 = parsed2.get("instances", []) if isinstance(parsed2, dict) else []
                if instances2:
                    instances = instances2
                    applies = parsed2.get("applies", applies)
                    confidence = parsed2.get("confidence", confidence)
                    oks = check(instances)
            except Exception:  # noqa: BLE001
                pass

    records = []
    for inst, ok in zip(instances, oks):
        records.append(dict(
            base,
            applies=True,
            confidence=confidence,
            answer_summary=summarize_instance(inst),
            verbatim_quote=inst.get("verbatim_quote"),
            quote_verified=ok,
            instance_data=json.dumps(inst, ensure_ascii=False),
        ))
    return records


def code_doc_profile(model, run_id, doc_id, header):
    timestamp = datetime.now(timezone.utc).isoformat()
    prompt = header + "\n" + DOC_PROFILE_PROMPT
    raw, err = call_ollama(model, prompt)
    base = {
        "doc_id": doc_id, "model": model, "prompt_version": PROMPT_VERSION,
        "run_id": run_id, "timestamp": timestamp,
    }
    if err:
        return dict(base, error=err, raw_response=raw)
    try:
        parsed = json.loads(raw)
        return dict(base, error=None, **parsed)
    except Exception as e:  # noqa: BLE001
        return dict(base, error=f"json_parse_error: {e}", raw_response=raw)


def stratified_sample(units, manifest, target_n=10, seed=42):
    rng = random.Random(seed)
    by_genre = defaultdict(list)
    for u in units:
        genre = manifest[u["doc_id"]]["genre"]
        by_genre[genre].append(u)

    total = len(units)
    quotas = {}
    for genre, us in by_genre.items():
        quotas[genre] = max(1, round(len(us) / total * target_n))

    # adjust to hit target_n exactly, trimming/adding from largest groups
    diff = sum(quotas.values()) - target_n
    genres_by_size = sorted(by_genre, key=lambda g: -len(by_genre[g]))
    i = 0
    while diff > 0:
        g = genres_by_size[i % len(genres_by_size)]
        if quotas[g] > 1:
            quotas[g] -= 1
            diff -= 1
        i += 1
        if i > 100:
            break
    i = 0
    while diff < 0:
        g = genres_by_size[i % len(genres_by_size)]
        if quotas[g] < len(by_genre[g]):
            quotas[g] += 1
            diff += 1
        i += 1
        if i > 100:
            break

    sample = []
    for genre, us in by_genre.items():
        # prefer family diversity: shuffle deterministically, then sort by family
        # so consecutive picks favor different families
        us_sorted = sorted(us, key=lambda u: (manifest[u["doc_id"]]["family"], u["unit_id"]))
        rng.shuffle(us_sorted)
        seen_families = set()
        prioritized = []
        rest = []
        for u in us_sorted:
            fam = manifest[u["doc_id"]]["family"]
            if fam not in seen_families:
                prioritized.append(u)
                seen_families.add(fam)
            else:
                rest.append(u)
        ordered = prioritized + rest
        sample.extend(ordered[:quotas[genre]])
    return sample


def write_validation_sample(units, manifest, doc_json_cache, results_by_unit_question):
    path = os.path.join(ROOT, "coding/validation/sample_for_frida.csv")
    sample = stratified_sample(units, manifest, target_n=10)
    sample_ids = {u["unit_id"] for u in sample}

    fieldnames = ["unit_id", "doc_id", "genre", "family", "heading", "text"]
    for q in CORE_QUESTIONS:
        fieldnames.append(f"FRIDA_{q}")
        fieldnames.append(f"LLM_{q}")

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for u in sample:
            row = {
                "unit_id": u["unit_id"],
                "doc_id": u["doc_id"],
                "genre": manifest[u["doc_id"]]["genre"],
                "family": manifest[u["doc_id"]]["family"],
                "heading": u.get("heading"),
                "text": u["text"][:1200],
            }
            for q in CORE_QUESTIONS:
                row[f"FRIDA_{q}"] = ""
                recs = results_by_unit_question.get((u["unit_id"], q), [])
                if not recs:
                    summary = "n/a"
                elif recs[0].get("applies") is False or recs[0].get("applies") is None:
                    summary = "no aplica" if recs[0].get("applies") is False else f"ERROR: {recs[0].get('error')}"
                else:
                    summary = " || ".join(r.get("answer_summary", "") or "" for r in recs)
                row[f"LLM_{q}"] = summary
            w.writerow(row)
    print(f"Wrote {path} ({len(sample)} units, ~{100*len(sample)/len(units):.0f}% of {len(units)})")
    return sample_ids


DOC_PROFILE_PROMPT = None  # set in main() from yaml


def main():
    global DOC_PROFILE_PROMPT
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default=None, help="Solo procesar este doc_id")
    ap.add_argument("--questions", choices=["full", "core"], default="full")
    ap.add_argument("--model", default=None)
    ap.add_argument("--skip-validation-sample", action="store_true")
    args = ap.parse_args()

    model = args.model or default_model()
    run_id = str(uuid.uuid4())
    print(f"Model: {model}  run_id: {run_id}  questions: {args.questions}")

    manifest = load_manifest()
    all_units = load_units()
    prompts = load_prompts()
    common_header = prompts["common_header"]
    questions = prompts["questions"]
    doc_level = prompts["doc_level"]
    DOC_PROFILE_PROMPT = doc_level["DOC_PROFILE"]["prompt"]

    if args.questions == "core":
        questions = {k: v for k, v in questions.items() if k in CORE_QUESTIONS}

    units = [u for u in all_units if args.doc is None or u["doc_id"] == args.doc]
    doc_ids = sorted(set(u["doc_id"] for u in units))
    if args.doc and args.doc not in doc_ids:
        print(f"ERROR: doc_id {args.doc} has no units in coding/units.jsonl", file=sys.stderr)
        sys.exit(1)

    doc_json_cache = {d: load_doc_json(d) for d in doc_ids}
    doc_contexts = {d: build_doc_context(d, manifest, doc_json_cache) for d in doc_ids}

    print(f"Units to code: {len(units)} across {len(doc_ids)} docs; questions: {list(questions)}")

    # ---- unit x question coding ----
    tasks = []
    for u in units:
        header = common_header.replace("{doc_context}", doc_contexts[u["doc_id"]]).replace("{passage}", u["text"])
        for qname, qdef in questions.items():
            tasks.append((u, qname, qdef, header))

    print(f"Total LLM calls (unit-level): {len(tasks)}")
    all_records = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(code_unit_question, model, run_id, u, qname, qdef, header): (u["unit_id"], qname)
                for (u, qname, qdef, header) in tasks}
        done_n = 0
        for fut in as_completed(futs):
            recs = fut.result()
            all_records.extend(recs)
            done_n += 1
            if done_n % 20 == 0:
                print(f"  unit-level {done_n}/{len(tasks)} done")

    # ---- doc profiles ----
    doc_profile_records = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {}
        for d in doc_ids:
            header = common_header.replace("{doc_context}", doc_contexts[d]).replace(
                "{passage}", full_doc_text(d, doc_json_cache))
            futs[ex.submit(code_doc_profile, model, run_id, d, header)] = d
        for fut in as_completed(futs):
            doc_profile_records.append(fut.result())
    print(f"Doc profiles: {len(doc_profile_records)}")

    # ---- write coding/round1/<doc_id>.jsonl ----
    round1_dir = os.path.join(ROOT, "coding/round1")
    os.makedirs(round1_dir, exist_ok=True)
    by_doc = defaultdict(list)
    for r in all_records:
        by_doc[r["doc_id"]].append(r)
    for d, recs in by_doc.items():
        path = os.path.join(round1_dir, f"{d}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(by_doc)} coding/round1/<doc_id>.jsonl files")

    # ---- doc_profiles.jsonl (merge with existing if --doc partial run) ----
    profiles_path = os.path.join(round1_dir, "doc_profiles.jsonl")
    existing_profiles = {}
    if os.path.exists(profiles_path):
        with open(profiles_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                existing_profiles[rec["doc_id"]] = rec
    for r in doc_profile_records:
        existing_profiles[r["doc_id"]] = r
    with open(profiles_path, "w", encoding="utf-8") as f:
        for d in sorted(existing_profiles):
            f.write(json.dumps(existing_profiles[d], ensure_ascii=False) + "\n")
    print(f"Wrote {profiles_path} ({len(existing_profiles)} docs)")

    # ---- definitional_instances.jsonl (merge, chronological) ----
    def_path = os.path.join(round1_dir, "definitional_instances.jsonl")
    existing_def = []
    if os.path.exists(def_path):
        with open(def_path, encoding="utf-8") as f:
            existing_def = [json.loads(l) for l in f]
    # drop existing entries for docs we just recoded (if DEFINITIONAL was in this run)
    if "DEFINITIONAL" in questions:
        existing_def = [r for r in existing_def if r["doc_id"] not in doc_ids]
        new_def = [r for r in all_records if r["question"] == "DEFINITIONAL" and r.get("applies")]
        combined = existing_def + new_def
    else:
        combined = existing_def
    combined.sort(key=lambda r: (manifest.get(r["doc_id"], {}).get("date", ""), r["doc_id"], r["unit_id"]))
    with open(def_path, "w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {def_path} ({len(combined)} definitional instances)")

    # ---- run_meta.json (append run history) ----
    meta_path = os.path.join(round1_dir, "run_meta.json")
    meta = {"runs": []}
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
    quote_checked = [r for r in all_records if r.get("quote_verified") is not None]
    pct_verified = (100 * sum(1 for r in quote_checked if r["quote_verified"]) / len(quote_checked)) if quote_checked else None
    meta["runs"].append({
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "doc_filter": args.doc,
        "questions": list(questions),
        "n_units": len(units),
        "n_unit_question_calls": len(tasks),
        "n_records": len(all_records),
        "n_doc_profiles": len(doc_profile_records),
        "pct_quote_verified": pct_verified,
    })
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Wrote {meta_path}")

    # ---- validation sample (full corpus run only) ----
    if not args.doc and not args.skip_validation_sample:
        results_by_unit_question = defaultdict(list)
        for r in all_records:
            results_by_unit_question[(r["unit_id"], r["question"])].append(r)
        os.makedirs(os.path.join(ROOT, "coding/validation"), exist_ok=True)
        write_validation_sample(all_units, manifest, doc_json_cache, results_by_unit_question)

    print("DONE.")
    if quote_checked:
        print(f"quote_verified: {pct_verified:.1f}% ({sum(1 for r in quote_checked if r['quote_verified'])}/{len(quote_checked)})")


if __name__ == "__main__":
    main()
