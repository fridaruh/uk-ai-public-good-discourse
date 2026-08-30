#!/usr/bin/env python3
"""Phase 6C -- thematic network: bipartite document<->sub-code, projected onto
a weighted document-document graph (SO1/SO2).

Sub-codes are the consolidated clusters in coding/guidebook_draft.yaml (one
set of clusters per core question -- BENEFICIARY, MECHANISM, SAFEGUARD,
RESPONSIBILITY, PROJECTED_FUTURE, ACTANTS, NATURALISED_ORDER), each cluster's
`candidate_name` being the sub-code label and `member_unit_ids` the units it
covers. coding/units.jsonl resolves unit_id -> doc_id.

Two clusters for the same question that share a candidate_name (the
consolidation heuristic can propose the same name more than once, e.g.
BENEFICIARY:Beneficiary_PublicGood) are merged into one sub-code, since they
are the same code by name.

A document "has" a sub-code if any of its units belongs to that sub-code's
member_unit_ids. The document-document projection weights an edge by the
number of shared sub-codes between the two documents.

Output: analysis/networks/thematic_network.json
    {"nodes": [{"id", "family", "speaker", "n_codes"}],
     "edges": [{"source", "target", "weight", "shared_codes": [names]}],
     "meta": {coverage banner fields}}

This is necessarily partial while Round 1 coding is partial: only documents
that contributed at least one successful, applicable answer to a core
question appear with sub-codes; the guidebook itself carries its own
COVERAGE WARNING (see coding/guidebook_draft.yaml).

Idempotent: safe to re-run once coding/guidebook_draft.yaml (via
scripts/06_consolidate.py) reflects more of the corpus.

Usage:
    .venv/bin/python scripts/10_thematic_network.py
"""
import csv
import itertools
import json
import os
from collections import defaultdict

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDEBOOK = os.path.join(ROOT, "coding", "guidebook_draft.yaml")
UNITS = os.path.join(ROOT, "coding", "units.jsonl")
MANIFEST = os.path.join(ROOT, "data", "manifest.csv")
RUN_META = os.path.join(ROOT, "coding", "round1", "run_meta.json")
OUT = os.path.join(ROOT, "analysis", "networks", "thematic_network.json")

CORE_QUESTIONS = [
    "BENEFICIARY", "MECHANISM", "SAFEGUARD", "RESPONSIBILITY",
    "PROJECTED_FUTURE", "ACTANTS", "NATURALISED_ORDER",
]


def load_manifest():
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        return {r["doc_id"]: r for r in csv.DictReader(f)}


def load_unit_to_doc():
    unit_to_doc = {}
    with open(UNITS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            unit_to_doc[d["unit_id"]] = d["doc_id"]
    return unit_to_doc


def load_run_meta_status():
    if not os.path.exists(RUN_META):
        return None, None
    meta = json.load(open(RUN_META, encoding="utf-8"))
    runs = meta.get("runs", [])
    if not runs:
        return None, None
    run = runs[-1]
    return run.get("pct_calls_succeeded"), run.get("status")


def build_subcodes(guidebook, unit_to_doc):
    """Return {(question, subcode_name): set(doc_id)} -- clusters sharing a
    name within a question are merged."""
    subcode_docs = defaultdict(set)
    subcode_units = defaultdict(set)
    questions = guidebook.get("questions", {})
    for qname in CORE_QUESTIONS:
        qdata = questions.get(qname) or {}
        for cluster in qdata.get("clusters", []):
            name = cluster.get("candidate_name") or "unnamed_cluster"
            key = (qname, name)
            for unit_id in cluster.get("member_unit_ids", []):
                doc_id = unit_to_doc.get(unit_id)
                if doc_id is None:
                    continue
                subcode_docs[key].add(doc_id)
                subcode_units[key].add(unit_id)
    return subcode_docs


def main():
    if not os.path.exists(GUIDEBOOK):
        print(f"{GUIDEBOOK} not found -- run scripts/06_consolidate.py first.")
        return

    manifest = load_manifest()
    unit_to_doc = load_unit_to_doc()
    guidebook = yaml.safe_load(open(GUIDEBOOK, encoding="utf-8"))

    subcode_docs = build_subcodes(guidebook, unit_to_doc)

    # doc_id -> set of "QUESTION:name" sub-code labels
    doc_subcodes = defaultdict(set)
    for (qname, name), docs in subcode_docs.items():
        label = f"{qname}:{name}"
        for doc_id in docs:
            doc_subcodes[doc_id].add(label)

    total_docs = len({d for d, r in manifest.items() if r.get("is_context") != "True"})
    docs_covered = len(doc_subcodes)
    n_subcodes = len(subcode_docs)

    pct_calls, run_status = load_run_meta_status()
    is_partial = pct_calls is None or pct_calls < 99.5

    # Nodes: every non-context document in the manifest (n_codes=0 if it has
    # no sub-codes yet -- makes the partial-coverage gap visible rather than
    # silently dropping undercoded documents from the graph).
    nodes = []
    for doc_id, row in manifest.items():
        if row.get("is_context") == "True":
            continue
        nodes.append({
            "id": doc_id,
            "family": row.get("family", "None"),
            "speaker": row.get("speaker", ""),
            "n_codes": len(doc_subcodes.get(doc_id, set())),
        })

    # Document-document projection weighted by shared sub-codes.
    edges = []
    doc_ids_with_codes = sorted(doc_subcodes.keys())
    for a, b in itertools.combinations(doc_ids_with_codes, 2):
        shared = sorted(doc_subcodes[a] & doc_subcodes[b])
        if shared:
            edges.append({
                "source": a, "target": b,
                "weight": len(shared),
                "shared_codes": shared,
            })
    edges.sort(key=lambda e: -e["weight"])

    banner = None
    if is_partial:
        pct_txt = f"{pct_calls:.1f}%" if pct_calls is not None else "unknown"
        banner = (
            "STATUS: PARTIAL -- regenerate after Round 1 completes. "
            f"Coverage: {docs_covered}/{total_docs} documents contributed at least one sub-code "
            f"({n_subcodes} sub-codes total, from the {len(CORE_QUESTIONS)} core questions with "
            f"guidebook clusters). Latest Round 1 run at {pct_txt} of unit-question calls -- see "
            "coding/round1/run_meta.json. This graph is NOT corpus-wide; re-run "
            "scripts/06_consolidate.py then scripts/10_thematic_network.py once Round 1 completes."
        )

    meta = {
        "status": "PARTIAL" if is_partial else "COMPLETE",
        "docs_covered": docs_covered,
        "docs_total": total_docs,
        "n_subcodes": n_subcodes,
        "n_core_questions": len(CORE_QUESTIONS),
        "core_questions": CORE_QUESTIONS,
        "pct_calls_succeeded_latest_run": pct_calls,
        "n_edges": len(edges),
    }
    if banner:
        meta["banner"] = banner

    out = {"nodes": nodes, "edges": edges, "meta": meta}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"Thematic network: {len(nodes)} document nodes, {n_subcodes} sub-codes, {len(edges)} edges")
    print(f"Coverage: {docs_covered}/{total_docs} documents with at least one sub-code")
    if banner:
        print(banner)
    else:
        print("STATUS: COMPLETE")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
