#!/usr/bin/env python
"""Phase 5 (preparation) -- Round 2 consolidation, DRAFT for the author's review.

For each core question, embeds the answer_summary values from
coding/round1/*.jsonl with embeddinggemma, groups them by cosine similarity
(threshold ~0.75, simple union-find), and writes coding/guidebook_draft.yaml
with candidate clusters. The final decision (name, definition, inclusion
rule) belongs to the author -- this script only proposes.

The 8 beneficiary nodes from the NVivo plan (Beneficiary_PublicGood,
_PublicBenefit, _Taxpayer, _Distributive, _Sovereignty, _PublicInterest,
_WorkingPeople, _Economy) are used as seeds to name BENEFICIARY clusters
when a cluster's content matches them.

Usage:
    .venv/bin/python scripts/06_consolidate.py
"""
import glob
import json
import os
import re

import numpy as np
import requests
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "embeddinggemma"
SIM_THRESHOLD = 0.75

CORE_QUESTIONS = [
    "BENEFICIARY", "MECHANISM", "SAFEGUARD", "RESPONSIBILITY",
    "PROJECTED_FUTURE", "ACTANTS", "NATURALISED_ORDER",
]

BENEFICIARY_SEEDS = {
    "Beneficiary_PublicGood": ["public good", "the public good", "society", "everyone"],
    "Beneficiary_PublicBenefit": ["public benefit", "benefits", "wider public"],
    "Beneficiary_Taxpayer": ["taxpayer", "taxpayers", "value for money"],
    "Beneficiary_Distributive": ["every citizen", "all", "everyone benefits", "distributed"],
    "Beneficiary_Sovereignty": ["sovereign", "sovereignty", "national capability", "the uk"],
    "Beneficiary_PublicInterest": ["public interest"],
    "Beneficiary_WorkingPeople": ["working people", "workers", "workforce"],
    "Beneficiary_Economy": ["the economy", "growth", "businesses", "industry"],
}


def load_records():
    records = []
    for path in sorted(glob.glob(os.path.join(ROOT, "coding/round1/*.jsonl"))):
        if os.path.basename(path) in ("doc_profiles.jsonl", "definitional_instances.jsonl"):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    return records


def embed(texts, batch_size=32):
    vecs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "input": batch}, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        vecs.extend(data["embeddings"])
    return np.array(vecs, dtype=np.float32)


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def cosine_sim_matrix(vecs):
    norm = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
    return norm @ norm.T


def cluster_question(qname, recs):
    """recs: list of dicts with answer_summary, verbatim_quote, unit_id, doc_id."""
    texts = [r["answer_summary"] for r in recs if r.get("answer_summary")]
    recs = [r for r in recs if r.get("answer_summary")]
    if not recs:
        return []
    vecs = embed(texts)
    sims = cosine_sim_matrix(vecs)
    n = len(recs)
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if sims[i, j] >= SIM_THRESHOLD:
                uf.union(i, j)

    groups = {}
    for i in range(n):
        root = uf.find(i)
        groups.setdefault(root, []).append(i)

    clusters = []
    for root, idxs in groups.items():
        members = [recs[i] for i in idxs]
        clusters.append(members)
    clusters.sort(key=len, reverse=True)
    return clusters


def name_candidate(qname, members):
    """Heuristic short snake_case label from the most common short field value."""
    labels = []
    key_map = {
        "BENEFICIARY": "beneficiary", "MECHANISM": "mechanism", "SAFEGUARD": "safeguard",
        "RESPONSIBILITY": "responsible", "PROJECTED_FUTURE": "future",
        "ACTANTS": "actant", "NATURALISED_ORDER": "order",
    }
    field = key_map.get(qname)
    for m in members:
        summ = m.get("answer_summary", "")
        if field:
            mo = re.search(rf"{field}=([^;]+)", summ)
            if mo:
                labels.append(mo.group(1).strip().lower())
    if not labels:
        labels = [m.get("answer_summary", "cluster")[:30] for m in members]

    # majority vote
    from collections import Counter
    common = Counter(labels).most_common(1)[0][0]
    slug = re.sub(r"[^a-z0-9]+", "_", common).strip("_")[:40] or "unnamed_cluster"

    if qname == "BENEFICIARY":
        for seed_name, keywords in BENEFICIARY_SEEDS.items():
            if any(kw in common for kw in keywords):
                return seed_name
    return slug


def main():
    records = load_records()
    if not records:
        print("No records in coding/round1/*.jsonl yet -- run scripts/05_code.py first.")
        return

    by_q = {}
    for r in records:
        by_q.setdefault(r.get("question"), []).append(r)

    guidebook = {
        "status": "DRAFT_pending_author",
        "generated_from": "coding/round1/*.jsonl",
        "similarity_threshold": SIM_THRESHOLD,
        "embedding_model": EMBED_MODEL,
        "note": (
            "Clusters proposed automatically by cosine similarity of "
            "answer_summary. candidate_name is a heuristic label -- "
            "the author decides the final name, definition and "
            "inclusion/exclusion rule in guidebook.yaml."
        ),
        "questions": {},
    }

    for qname in CORE_QUESTIONS:
        recs = [r for r in by_q.get(qname, []) if r.get("applies")]
        if not recs:
            guidebook["questions"][qname] = {"clusters": [], "n_applies_true": 0}
            continue
        clusters = cluster_question(qname, recs)
        q_out = []
        for cl in clusters:
            name = name_candidate(qname, cl)
            examples = []
            for m in cl[:3]:
                examples.append(m.get("verbatim_quote") or "")
            q_out.append({
                "candidate_name": name,
                "n_instances": len(cl),
                "example_quotes": examples,
                "member_unit_ids": sorted(set(m["unit_id"] for m in cl)),
                "status": "DRAFT_pending_author",
            })
        guidebook["questions"][qname] = {
            "n_applies_true": len(recs),
            "n_clusters": len(q_out),
            "clusters": q_out,
        }
        print(f"{qname}: {len(recs)} instances -> {len(q_out)} clusters")

    out_path = os.path.join(ROOT, "coding/guidebook_draft.yaml")
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(guidebook, f, allow_unicode=True, sort_keys=False, width=100)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
