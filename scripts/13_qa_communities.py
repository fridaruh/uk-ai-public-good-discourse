#!/usr/bin/env python3
"""Internal QA -- detected communities vs. MoU families and speaker groups.

NOT a results script: this lives under analysis/qa/ per PLAN.md Phase 6
("Internal QA (not results): Leiden comparison vs. families/groupings ...
cited only if the author decides to use them as a robustness check").

Input: analysis/networks/intertextual_v0.json, "reference"-type edges only
(explicit-citation edges; "echo" and "supersession" edges are excluded, per
the task -- echo edges in particular are undirected borrowing evidence, not
citation, and would bias a family comparison since they only exist within
MoU families by construction).

Community detection: Leiden (python-igraph, modularity objective) if
python-igraph is importable; otherwise an inline weighted label-propagation
fallback (no heavy new dependency required either way).

Comparison: Adjusted Rand Index (implemented inline, no sklearn) between the
detected community labels and (a) the 5 MoU families (+ "None" for
non-MoU documents) and (b) speaker groups, both read directly off the node
attributes already in intertextual_v0.json.

This network does not depend on Round 1 LLM coding (it is built from the
manifest, full document text, and echo-phrases) so it is already
corpus-complete -- no partial-coverage banner needed here.

Output: analysis/qa/communities_vs_families.md

Idempotent: safe to re-run any time intertextual_v0.json changes (e.g. more
echo edges once Round 1 unblocks further Phase 6B analysis).

Usage:
    .venv/bin/python scripts/13_qa_communities.py
"""
import json
import os
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK = os.path.join(ROOT, "analysis", "networks", "intertextual_v0.json")
OUT = os.path.join(ROOT, "analysis", "qa", "communities_vs_families.md")


# ---------------------------------------------------------------------------
# Adjusted Rand Index (matches sklearn.metrics.adjusted_rand_score)
# ---------------------------------------------------------------------------

def _comb2(x):
    return x * (x - 1) // 2


def adjusted_rand_index(labels_true, labels_pred):
    classes_true = sorted(set(labels_true))
    classes_pred = sorted(set(labels_pred))
    ti = {c: i for i, c in enumerate(classes_true)}
    pi = {c: i for i, c in enumerate(classes_pred)}
    table = np.zeros((len(classes_true), len(classes_pred)), dtype=np.int64)
    for a, b in zip(labels_true, labels_pred):
        table[ti[a], pi[b]] += 1

    sum_comb_rows = sum(_comb2(int(x)) for x in table.sum(axis=1))
    sum_comb_cols = sum(_comb2(int(x)) for x in table.sum(axis=0))
    sum_comb = sum(_comb2(int(x)) for x in table.flatten())
    n = int(table.sum())
    total_comb = _comb2(n)

    expected_index = (sum_comb_rows * sum_comb_cols / total_comb) if total_comb else 0.0
    max_index = 0.5 * (sum_comb_rows + sum_comb_cols)
    denom = max_index - expected_index
    if denom == 0:
        return 1.0 if sum_comb == max_index else 0.0
    return (sum_comb - expected_index) / denom


# ---------------------------------------------------------------------------
# Community detection
# ---------------------------------------------------------------------------

def build_weighted_pairs(nodes, edges):
    node_ids = [n["id"] for n in nodes]
    idx = {nid: i for i, nid in enumerate(node_ids)}
    pair_weight = defaultdict(int)
    for e in edges:
        if e.get("type") != "reference":
            continue
        a, b = e.get("source"), e.get("target")
        if a not in idx or b not in idx or a == b:
            continue
        key = tuple(sorted((idx[a], idx[b])))
        pair_weight[key] += int(e.get("count", 1))
    return node_ids, idx, pair_weight


def detect_communities_igraph(node_ids, pair_weight):
    import igraph as ig
    g = ig.Graph()
    g.add_vertices(len(node_ids))
    if pair_weight:
        g.add_edges(list(pair_weight.keys()))
        g.es["weight"] = list(pair_weight.values())
    if g.ecount() == 0:
        membership = list(range(len(node_ids)))
        modularity = float("nan")
    else:
        part = g.community_leiden(objective_function="modularity",
                                   weights="weight", n_iterations=10)
        membership = list(part.membership)
        modularity = g.modularity(membership, weights="weight")
    return membership, modularity, "Leiden (python-igraph, modularity objective)"


def detect_communities_label_propagation(node_ids, pair_weight, max_iter=100, seed=0):
    """Fallback: synchronous weighted label propagation. Used only if
    python-igraph is not importable."""
    n = len(node_ids)
    neighbors = defaultdict(list)  # i -> [(j, w), ...]
    for (i, j), w in pair_weight.items():
        neighbors[i].append((j, w))
        neighbors[j].append((i, w))
    labels = list(range(n))
    rng = np.random.RandomState(seed)
    for _ in range(max_iter):
        changed = False
        order = list(range(n))
        rng.shuffle(order)
        for i in order:
            if not neighbors[i]:
                continue
            weight_by_label = defaultdict(int)
            for j, w in neighbors[i]:
                weight_by_label[labels[j]] += w
            best = max(weight_by_label.items(), key=lambda kv: (kv[1], -kv[0]))[0]
            if best != labels[i]:
                labels[i] = best
                changed = True
        if not changed:
            break
    # renumber labels 0..k-1
    remap = {}
    membership = []
    for lb in labels:
        if lb not in remap:
            remap[lb] = len(remap)
        membership.append(remap[lb])
    return membership, "weighted label propagation (inline fallback, no python-igraph)"


def graph_modularity(node_ids, pair_weight, membership):
    m = sum(pair_weight.values())
    if m == 0:
        return float("nan")
    deg = defaultdict(int)
    for (i, j), w in pair_weight.items():
        deg[i] += w
        deg[j] += w
    q = 0.0
    for (i, j), w in pair_weight.items():
        if membership[i] == membership[j]:
            q += w
    q = q / m
    expected = 0.0
    for c in set(membership):
        d_c = sum(deg[i] for i in range(len(node_ids)) if membership[i] == c)
        expected += (d_c / (2 * m)) ** 2
    return q - expected


def main():
    if not os.path.exists(NETWORK):
        print(f"{NETWORK} not found -- run scripts/06_network_v0.py first.")
        return

    data = json.load(open(NETWORK, encoding="utf-8"))
    nodes, edges = data["nodes"], data["edges"]
    node_ids, idx, pair_weight = build_weighted_pairs(nodes, edges)

    n_reference_edges = sum(1 for e in edges if e.get("type") == "reference")
    n_unique_pairs = len(pair_weight)

    try:
        membership, modularity, method = detect_communities_igraph(node_ids, pair_weight)
    except ImportError:
        membership, method = detect_communities_label_propagation(node_ids, pair_weight)
        modularity = graph_modularity(node_ids, pair_weight, membership)

    n_communities = len(set(membership))
    isolated = sum(1 for i in range(len(node_ids)) if not any(
        i in pair for pair in pair_weight.keys()))

    family_by_id = {n["id"]: n.get("family", "None") for n in nodes}
    speaker_by_id = {n["id"]: n.get("speaker", "") for n in nodes}
    family_labels = [family_by_id[nid] for nid in node_ids]
    speaker_labels = [speaker_by_id[nid] for nid in node_ids]

    ari_family = adjusted_rand_index(family_labels, membership)
    ari_speaker = adjusted_rand_index(speaker_labels, membership)

    n_families = len(set(family_labels))
    n_speakers = len(set(speaker_labels))

    # community -> members, for the audit table
    comm_members = defaultdict(list)
    for i, nid in enumerate(node_ids):
        comm_members[membership[i]].append(nid)

    lines = []
    lines.append("# INTERNAL QA — not a finding\n\n")
    lines.append(
        "This is a robustness check on the intertextual network's structure, not a claim about "
        "the corpus. It compares communities found by unsupervised graph clustering against two "
        "attributes the author already assigned by hand (MoU family, speaker). It lives in "
        "`analysis/qa/` and is cited only if the author decides it is useful as a robustness check "
        "in the methods section.\n\n"
    )
    lines.append(
        f"**Method:** {method}, run on the document-document graph built from "
        f"`analysis/networks/intertextual_v0.json`, **reference-type edges only** "
        f"({n_reference_edges} reference edges -> {n_unique_pairs} unique document pairs after "
        "merging duplicate/bidirectional edges and summing counts as weights). \"echo\" and "
        "\"supersession\" edges are excluded: echo edges exist by construction only within MoU "
        "families and would inflate agreement with the family attribute; supersession is a single "
        "hand-coded edge. This network does not depend on Round 1 LLM coding, so it is already "
        "corpus-complete (all 35 manifest documents, including the CONTEXT document).\n\n"
    )

    lines.append("## Comparison table\n\n")
    lines.append("| Metric | Value |\n|---|---|\n")
    lines.append(f"| Documents (nodes) | {len(node_ids)} |\n")
    lines.append(f"| Reference edges (unique pairs) | {n_unique_pairs} |\n")
    lines.append(f"| Isolated nodes (no reference edge) | {isolated} |\n")
    lines.append(f"| Communities detected | {n_communities} |\n")
    lines.append(f"| Modularity of detected partition | {modularity:.3f} |\n" if modularity == modularity
                  else "| Modularity of detected partition | n/a (no edges) |\n")
    lines.append(f"| MoU family groups (ground truth a) | {n_families} |\n")
    lines.append(f"| **ARI vs. MoU family** | **{ari_family:.3f}** |\n")
    lines.append(f"| Speaker groups (ground truth b) | {n_speakers} |\n")
    lines.append(f"| **ARI vs. speaker** | **{ari_speaker:.3f}** |\n")
    lines.append("\n")

    lines.append("## Detected communities (audit)\n\n")
    lines.append("| Community | n docs | Members (doc_id) |\n|---|---|---|\n")
    for c in sorted(comm_members, key=lambda c: -len(comm_members[c])):
        members = comm_members[c]
        lines.append(f"| {c} | {len(members)} | {', '.join(sorted(members))} |\n")
    lines.append("\n")

    lines.append("## Honest reading\n\n")
    lines.append(
        f"ARI ranges from ~0 (no better than chance agreement) to 1 (identical partitions); "
        f"{ari_family:.3f} against family and {ari_speaker:.3f} against speaker should be read "
        f"against a graph with {isolated}/{len(node_ids)} isolated nodes (documents that cite or "
        "are cited by no other corpus document) -- Leiden puts every isolated node in its own "
        "singleton community, which mechanically depresses agreement with any coarser grouping "
        "like family or speaker unless that grouping also isolates the same documents. A high ARI "
        "here would mean explicit citation structure alone recovers who-authored-with-whom or "
        "which-MoU-family-a-document-belongs-to; a low ARI means citation structure and "
        "family/speaker membership are largely independent signals in this corpus -- which is "
        "itself informative (it says the intertextual network is not just reproducing the manifest "
        "attributes) but should not be read as a validation or invalidation of the family/speaker "
        "coding, since the reference graph is sparse and directional by design (a document only "
        "gets an edge if it explicitly names another corpus document), not a semantic-similarity "
        "graph built to recover those groupings in the first place.\n"
    )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Communities: {n_communities} (modularity {modularity:.3f})" if modularity == modularity
          else f"Communities: {n_communities} (modularity n/a)")
    print(f"ARI vs family: {ari_family:.3f}")
    print(f"ARI vs speaker: {ari_speaker:.3f}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
