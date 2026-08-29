"""Red intertextual preliminar (v0) — SO2, Fairclough.

Detección de referencias explícitas entre documentos del corpus por alias de
título (curados, en minúsculas). Los alias largos se enmascaran antes de buscar
los cortos para no contar dos veces (p. ej. "response to the AI Opportunities
Action Plan" vs "AI Opportunities Action Plan").

Regla MoU: mención de "memorandum of understanding" + nombre de la empresa →
referencia al MoU de esa familia.

Salida: analysis/networks/intertextual_v0.json (nodos con atributos del manifest,
aristas con tipo, conteo y evidencia). Preliminar: Frida audita las aristas con
la evidencia incluida; Fase 6 añade ecos y códigos compartidos.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "networks" / "intertextual_v0.json"

# alias (minúsculas) -> doc_id destino; orden de match: más largo primero
ALIASES = {
    "2024-01-18_STRAT_CDDO_GenerativeAIFramework": [
        "generative ai framework"],
    "2024-02-06_REG_DSIT_ProInnovationAIRegulation": [
        "pro-innovation approach to ai regulation", "ai regulation white paper",
        "pro-innovation approach to regulating ai"],
    "2025-01-13_STRAT_DSIT_AIActionPlanGovResponse": [
        "government response to the ai opportunities action plan",
        "response to the ai opportunities action plan"],
    "CONTEXT_2025-01-13_STRAT_DSIT_AIOpportunitiesActionPlan": [
        "ai opportunities action plan"],
    "2026-01-29_STRAT_DSIT_AIActionPlanOneYearOn": [
        "ai opportunities action plan: one year on", "one year on report"],
    "2025-01-12_PRGOV_PMO_BlueprintTurbochargeAI": [
        "blueprint to turbocharge"],
    "2025-01-21_STRAT_GDS_BlueprintModernDigitalGov": [
        "blueprint for modern digital government",
        "blueprint for a modern digital government"],
    "2025-01-21_STRAT_GDS_StateOfDigitalGovReview": [
        "state of digital government review", "state of digital government"],
    "2025-02-10_STRAT_GDS_AIPlaybookUKGovernment": [
        "artificial intelligence playbook", "ai playbook"],
    "2026-01-20_STRAT_GDS_RoadmapModernDigitalGov": [
        "roadmap for modern digital government"],
    "2025-08-18_BLOG_GDS_AIExemplarsProgramme": [
        "ai exemplars programme", "ai exemplars"],
    "2025-09-16_PRCO_OpenAI_StargateUK": ["stargate uk"],
}

MOU_DOCS = {
    "Anthropic": "2025-02-14_MOU_Anthropic_AIOpportunities",
    "Cohere": "2025-06-16_MOU_Cohere_AIOpportunities",
    "OpenAI": "2025-07-21_MOU_OpenAI_AIOpportunities",
    "DeepMind": "2025-12-11_MOU_DeepMind_AIOpportunitiesSecurity",
    "ElevenLabs": "2026-06-08_MOU_ElevenLabs_AIOpportunities",
}
COMPANY_TOKENS = {"Anthropic": ["anthropic"], "Cohere": ["cohere"],
                  "OpenAI": ["openai", "open ai"],
                  "DeepMind": ["deepmind", "google deepmind"],
                  "ElevenLabs": ["elevenlabs", "eleven labs"]}

SUPERSESSION = [
    # citing (nuevo) -> cited (retirado): el Playbook sustituye al GenAI Framework
    ("2025-02-10_STRAT_GDS_AIPlaybookUKGovernment",
     "2024-01-18_STRAT_CDDO_GenerativeAIFramework"),
]


def load_text(doc_id):
    p = ROOT / "data" / "text" / f"{doc_id}.json"
    doc = json.loads(p.read_text())
    return "\n".join(b["text"] for b in doc["blocks"]).lower()


def snippet(text, pos, width=90):
    s = max(0, pos - width)
    return re.sub(r"\s+", " ", text[s:pos + width]).strip()


def main():
    rows = list(csv.DictReader((ROOT / "data" / "manifest.csv").open()))
    texts = {r["doc_id"]: load_text(r["doc_id"]) for r in rows}

    # pares (alias, target) ordenados por longitud desc para enmascarar largos primero
    pairs = sorted(((a, t) for t, al in ALIASES.items() for a in al),
                   key=lambda x: -len(x[0]))

    edges = []
    for r in rows:
        src = r["doc_id"]
        text = texts[src]
        masked = text
        for alias, target in pairs:
            if target == src:
                # el propio título del doc: enmascarar para no regalarlo a alias más cortos
                masked = masked.replace(alias, "#" * len(alias))
                continue
            count, first_pos = 0, None
            while True:
                i = masked.find(alias)
                if i < 0:
                    break
                count += 1
                if first_pos is None:
                    first_pos = i
                masked = masked[:i] + "#" * len(alias) + masked[i + len(alias):]
            if count:
                edges.append({"source": src, "target": target, "type": "reference",
                              "count": count, "evidence": snippet(text, first_pos)})
        # regla MoU
        if "memorandum of understanding" in text or re.search(r"\bmou\b", text):
            for fam, mou_id in MOU_DOCS.items():
                if src == mou_id or r["family"] not in (fam, "None"):
                    continue
                # solo dentro de la familia o docs sin familia que nombren a la empresa
                if any(tok in text for tok in COMPANY_TOKENS[fam]):
                    if r["family"] == fam or src.endswith("AIAdoptionSummitPartnerships"):
                        m = re.search(r"memorandum of understanding|\bmou\b", text)
                        edges.append({"source": src, "target": mou_id,
                                      "type": "reference", "count": 1,
                                      "evidence": snippet(text, m.start())})

    for a, b in SUPERSESSION:
        edges.append({"source": a, "target": b, "type": "supersession", "count": 1,
                      "evidence": "El AI Playbook sustituye al Generative AI Framework (gov.uk, 2025-02-10)."})

    indeg = {}
    for e in edges:
        indeg[e["target"]] = indeg.get(e["target"], 0) + e["count"]

    nodes = []
    for r in rows:
        short = r["doc_id"].split("_", 3)[-1] if not r["doc_id"].startswith("CONTEXT") \
            else r["doc_id"].split("_", 4)[-1]
        nodes.append({
            "id": r["doc_id"], "label": short, "date": r["date"],
            "genre": r["genre"], "speaker": r["speaker"], "family": r["family"],
            "term_status": r["term_status"], "in_degree": indeg.get(r["doc_id"], 0),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=1, ensure_ascii=False))
    print(f"{len(nodes)} nodos, {len(edges)} aristas -> {OUT}")
    print("\nTop referenciados (in-degree):")
    for n in sorted(nodes, key=lambda n: -n["in_degree"])[:10]:
        print(f"  {n['in_degree']:>3}  {n['id']}")
    print("\nAristas por tipo:", {t: sum(1 for e in edges if e['type'] == t)
                                   for t in {e['type'] for e in edges}})


if __name__ == "__main__":
    main()
