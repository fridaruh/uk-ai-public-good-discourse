#!/usr/bin/env python
"""Fase 3 - Evaluacion de modelos (Ollama Cloud).

Corre las 11 preguntas de coding/prompts/prompts_v1.yaml sobre una muestra
estratificada de 6 unidades, para cada modelo candidato, y calcula metricas
de fidelidad verbatim / validez JSON / applies=false razonable para decidir
el modelo ganador de la Fase 4.

Salidas: coding/model_eval/results.csv (registro por unidad x pregunta x modelo)
         coding/model_eval/decision.md (resumen y decision)
"""
import csv
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OLLAMA_URL = "http://localhost:11434/api/generate"
TIMEOUT = 180
RETRIES = 2

MODELS = [
    "gpt-oss:120b-cloud",
    "glm-5.3:cloud",
    "kimi-k3:cloud",
    "deepseek-v4-flash:cloud",
]

# Muestra estratificada (ver justificacion en decision.md)
SAMPLE_UNIT_IDS = [
    "2025-02-10_STRAT_GDS_AIPlaybookUKGovernment::s130",   # STRAT larga
    "2025-07-21_MOU_OpenAI_AIOpportunities::s02",           # MOU
    "2026-01-27_PRCO_Anthropic_GOVUKPartnership::s01",      # PRCO
    "2026-01-20_BLOG_GDS_OurRoadmapLaunch::s03",            # BLOG
    "2025-12-10_PRCO_DeepMind_StrengtheningPartnership::s06",  # retrieval=semantic
    "2026-01-19_WMS_DSIT_RoadmapMinisterialStatement::full",   # full_short_doc (WMS)
]


def load_manifest():
    manifest = {}
    with open(os.path.join(ROOT, "data/manifest.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            manifest[row["doc_id"]] = row
    return manifest


def doc_title(doc_id):
    path = os.path.join(ROOT, "data/text", doc_id + ".json")
    if not os.path.exists(path):
        # strip CONTEXT_ prefix if present
        return doc_id
    d = json.load(open(path, encoding="utf-8"))
    for b in d["blocks"]:
        if b["structural_position"] == "title":
            return b["text"].strip()
    return doc_id


def build_doc_context(doc_id, manifest):
    row = manifest.get(doc_id, {})
    title = doc_title(doc_id)
    return f"{title} | {row.get('date','?')} | {row.get('genre','?')} | {row.get('speaker','?')} | {row.get('family','None')}"


def load_units():
    units = {}
    with open(os.path.join(ROOT, "coding/units.jsonl"), encoding="utf-8") as f:
        for line in f:
            u = json.loads(line)
            units[u["unit_id"]] = u
    return units


def load_prompts():
    with open(os.path.join(ROOT, "coding/prompts/prompts_v1.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def call_ollama(model, prompt, retries=RETRIES):
    last_err = None
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
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
            elapsed = time.time() - t0
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                last_err = data["error"]
                continue
            return data.get("response", ""), elapsed, None
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            time.sleep(1)
    return "", 0.0, last_err


def verify_quotes(passage, parsed):
    """Return (n_quotes, n_verbatim_ok)."""
    n, ok = 0, 0
    instances = parsed.get("instances", []) if isinstance(parsed, dict) else []
    for inst in instances:
        if not isinstance(inst, dict):
            continue
        q = inst.get("verbatim_quote")
        if q:
            n += 1
            if q in passage:
                ok += 1
    return n, ok


def run_one(model, qname, qdef, common_header, unit, doc_context):
    passage = unit["text"]
    header = common_header.replace("{doc_context}", doc_context).replace("{passage}", passage)
    full_prompt = header + "\n" + qdef["prompt"]
    raw, elapsed, err = call_ollama(model, full_prompt)
    record = {
        "model": model,
        "unit_id": unit["unit_id"],
        "question": qname,
        "passage_len": len(passage),
        "elapsed_s": round(elapsed, 2),
        "raw_response": raw,
        "error": err,
        "json_valid": False,
        "applies": None,
        "n_quotes": 0,
        "n_quotes_verbatim_ok": 0,
    }
    if err:
        return record
    try:
        parsed = json.loads(raw)
        record["json_valid"] = True
        record["applies"] = parsed.get("applies") if isinstance(parsed, dict) else None
        n, ok = verify_quotes(passage, parsed)
        record["n_quotes"] = n
        record["n_quotes_verbatim_ok"] = ok
    except Exception as e:  # noqa: BLE001
        record["error"] = f"json_parse_error: {e}"
    return record


def main():
    manifest = load_manifest()
    units = load_units()
    prompts = load_prompts()
    common_header = prompts["common_header"]
    questions = prompts["questions"]

    missing = [u for u in SAMPLE_UNIT_IDS if u not in units]
    if missing:
        print("WARNING missing sample units:", missing, file=sys.stderr)

    sample_units = [units[u] for u in SAMPLE_UNIT_IDS if u in units]
    doc_contexts = {u["doc_id"]: build_doc_context(u["doc_id"], manifest) for u in sample_units}

    tasks = []
    for model in MODELS:
        for unit in sample_units:
            for qname, qdef in questions.items():
                tasks.append((model, qname, qdef, unit))

    print(f"Total calls: {len(tasks)} ({len(MODELS)} models x {len(sample_units)} units x {len(questions)} questions)")

    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {
            ex.submit(run_one, model, qname, qdef, common_header, unit, doc_contexts[unit["doc_id"]]): (model, unit["unit_id"], qname)
            for (model, qname, qdef, unit) in tasks
        }
        done_n = 0
        for fut in as_completed(futs):
            rec = fut.result()
            results.append(rec)
            done_n += 1
            if done_n % 20 == 0:
                print(f"  {done_n}/{len(tasks)} done")

    out_csv = os.path.join(ROOT, "coding/model_eval/results.csv")
    fieldnames = ["model", "unit_id", "question", "passage_len", "elapsed_s", "json_valid",
                  "applies", "n_quotes", "n_quotes_verbatim_ok", "error", "raw_response"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in fieldnames})

    print(f"Wrote {out_csv} ({len(results)} rows)")

    # ---- Metrics per model ----
    from collections import defaultdict
    agg = defaultdict(lambda: {"n": 0, "json_valid": 0, "n_quotes": 0, "n_quotes_ok": 0,
                                "applies_false": 0, "applies_true": 0, "errors": 0})
    short_passage_threshold = 700
    short_applies_false = defaultdict(int)
    short_total = defaultdict(int)

    for r in results:
        m = r["model"]
        a = agg[m]
        a["n"] += 1
        if r["json_valid"]:
            a["json_valid"] += 1
        if r["error"]:
            a["errors"] += 1
        a["n_quotes"] += r["n_quotes"]
        a["n_quotes_ok"] += r["n_quotes_verbatim_ok"]
        if r["applies"] is True:
            a["applies_true"] += 1
        elif r["applies"] is False:
            a["applies_false"] += 1
        if r["passage_len"] < short_passage_threshold:
            short_total[m] += 1
            if r["applies"] is False:
                short_applies_false[m] += 1

    metrics_path = os.path.join(ROOT, "coding/model_eval/decision.md")
    lines = []
    lines.append("# Fase 3 -- Evaluacion de modelos (Ollama Cloud)\n")
    lines.append(f"Fecha de corrida: {time.strftime('%Y-%m-%d')}\n")
    lines.append("\n## Candidatos probados\n")
    lines.append(
        "Los 4 nombres sugeridos en el plan original "
        "(`deepseek-v3.1:671b-cloud`, `kimi-k2:1t-cloud`, `qwen3-coder:480b-cloud`, "
        "`glm-4.6:cloud`) ya no existen en el catalogo de Ollama Cloud vigente al "
        f"correr ({time.strftime('%Y-%m-%d')}) -- `ollama pull` devolvio "
        "`pull model manifest: file does not exist` para los 4. Se resolvio el "
        "catalogo vigente contra `ollama.com/search?c=cloud` y se sustituyeron por "
        "la generacion vigente de los mismos proveedores/familias:\n\n"
        "| Placeholder original | Sustituto vigente que se probo |\n"
        "|---|---|\n"
        "| `glm-4.6:cloud` | `glm-5.3:cloud` |\n"
        "| `kimi-k2:1t-cloud` | `kimi-k3:cloud` |\n"
        "| `deepseek-v3.1:671b-cloud` | `deepseek-v4-flash:cloud` |\n"
        "| `qwen3-coder:480b-cloud` | no disponible (`qwen3.5:*-cloud` fallo pull; se omite) |\n\n"
        "`gpt-oss:120b-cloud` (linea base ya probada) se mantiene como candidato.\n"
        "Los 4 candidatos evaluados se verificaron con una llamada corta a "
        "`/api/generate` antes de la corrida completa.\n"
    )

    lines.append("\n## Metricas por modelo (6 unidades x 11 preguntas = 66 llamadas/modelo)\n")
    lines.append("| Modelo | % JSON valido | % fidelidad verbatim (citas OK / citas totales) | applies=true | applies=false | errores | tiempo medio (s) |\n")
    lines.append("|---|---|---|---|---|---|---|\n")

    summary_rows = []
    for m in MODELS:
        a = agg[m]
        pct_json = 100 * a["json_valid"] / a["n"] if a["n"] else 0
        pct_fid = 100 * a["n_quotes_ok"] / a["n_quotes"] if a["n_quotes"] else float("nan")
        avg_time = sum(r["elapsed_s"] for r in results if r["model"] == m) / a["n"] if a["n"] else 0
        summary_rows.append((m, pct_json, pct_fid, a["applies_true"], a["applies_false"], a["errors"], avg_time))
        lines.append(
            f"| {m} | {pct_json:.1f}% | {pct_fid:.1f}% ({a['n_quotes_ok']}/{a['n_quotes']}) | "
            f"{a['applies_true']} | {a['applies_false']} | {a['errors']} | {avg_time:.1f} |\n"
        )

    lines.append("\n## Applies=false razonables en pasajes cortos (<700 caracteres)\n")
    lines.append("| Modelo | applies=false / llamadas en pasajes cortos |\n|---|---|\n")
    for m in MODELS:
        lines.append(f"| {m} | {short_applies_false[m]}/{short_total[m]} |\n")

    # Decision: gana fidelidad verbatim; empates los decide validez JSON
    ranked = sorted(
        summary_rows,
        key=lambda row: (
            -1 if row[2] != row[2] else -row[2],  # nan pushed last (fidelity desc)
            -row[1],  # json valid desc
        ),
    )
    winner = ranked[0]
    lines.append("\n## Decision\n")
    lines.append(
        f"**Modelo ganador: `{winner[0]}`** (fidelidad verbatim {winner[2]:.1f}%, "
        f"JSON valido {winner[1]:.1f}%). Regla aplicada: gana fidelidad verbatim "
        "(criterio de decision predefinido); los empates se rompen por % de JSON "
        "valido. Proveedor: Ollama Cloud. Fecha de decision: "
        f"{time.strftime('%Y-%m-%d')}. Este texto puede citarse casi directo en el "
        "capitulo de metodos.\n"
    )
    lines.append(
        "\nNota de alcance: el acuerdo con Frida sobre la muestra (Fase 3, punto 4 "
        "del PLAN) queda pendiente -- este reporte solo cubre las metricas "
        "automaticas (JSON valido, fidelidad verbatim, applies=false razonable). "
        "La adjudicacion humana se hace en la validacion 15-20% de la Fase 4.\n"
    )

    with open(metrics_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Wrote {metrics_path}")
    print("WINNER:", winner[0])


if __name__ == "__main__":
    main()
