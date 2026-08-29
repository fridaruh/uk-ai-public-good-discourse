"""Cierre de Fase 1: QA global de data/text/*.json y fusión de metadatos al manifest.

Chequea por documento: JSON válido, bloques no vacíos, exactamente un bloque
'title', posiciones estructurales dentro del vocabulario, longitud total plausible.
Fusiona fetch_status/format/n_blocks/source desde data/raw/<doc_id>.meta.json.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.csv"
VOCAB = {"title", "pillar_name", "section_heading", "body", "quotation"}
MIN_CHARS = {"STRAT": 1000, "MOU": 1000, "REG": 1000, "BLOG": 500, "WMS": 500,
             "PRGOV": 500, "PRCO": 400}


def main():
    rows = list(csv.DictReader(MANIFEST.open()))
    problems = []
    for r in rows:
        doc_id = r["doc_id"]
        tpath = ROOT / "data" / "text" / f"{doc_id}.json"
        mpath = ROOT / "data" / "raw" / f"{doc_id}.meta.json"
        if not tpath.exists():
            problems.append(f"{doc_id}: falta data/text JSON")
            r["fetch_status"] = "missing"
            continue
        doc = json.loads(tpath.read_text())
        blocks = doc.get("blocks", [])
        titles = [b for b in blocks if b["structural_position"] == "title"]
        badpos = {b["structural_position"] for b in blocks} - VOCAB
        total = sum(len(b["text"]) for b in blocks)
        quotes = sum(1 for b in blocks if b["structural_position"] == "quotation")
        pillars = sum(1 for b in blocks if b["structural_position"] == "pillar_name")
        if not blocks:
            problems.append(f"{doc_id}: sin bloques")
        if len(titles) != 1:
            problems.append(f"{doc_id}: {len(titles)} bloques title (esperado 1)")
        if badpos:
            problems.append(f"{doc_id}: posiciones fuera de vocabulario {badpos}")
        if total < MIN_CHARS.get(r["genre"], 400):
            problems.append(f"{doc_id}: solo {total} chars (umbral {MIN_CHARS.get(r['genre'])})")
        meta = json.loads(mpath.read_text()) if mpath.exists() else {}
        r["fetch_status"] = meta.get("fetch_status", "ok?")
        r["n_blocks"] = len(blocks)
        r["n_quotes"] = quotes
        r["n_pillars"] = pillars
        r["total_chars"] = total
        r["source"] = meta.get("source", "direct")

    fieldnames = list(rows[0].keys())
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    ok = sum(1 for r in rows if r["fetch_status"] == "ok")
    print(f"QA: {ok}/{len(rows)} ok; {len(problems)} problemas")
    for p in problems:
        print(f"  ! {p}")
    print("\nResumen por documento:")
    for r in rows:
        print(f"  {r['doc_id'][:55]:57s} {r['fetch_status']:7s} blocks={r['n_blocks']:>4} "
              f"quotes={r['n_quotes']:>2} pillars={r['n_pillars']:>2} chars={r['total_chars']:>6} src={r['source']}")


if __name__ == "__main__":
    main()
