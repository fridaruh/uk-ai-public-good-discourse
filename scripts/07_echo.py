#!/usr/bin/env python3
"""
Tarea 1: Detectar echo-phrases entre documentos de gobierno y empresa por familia.
"""

import json
import csv
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Configuración
DATA_DIR = Path(__file__).parent.parent / "data"
TEXT_DIR = DATA_DIR / "text"
MANIFEST_FILE = DATA_DIR / "manifest.csv"
ANALYSIS_DIR = Path(__file__).parent.parent / "analysis" / "queries"
OUTPUT_CSV = ANALYSIS_DIR / "echo_phrases.csv"
OUTPUT_MD = ANALYSIS_DIR / "echo_summary.md"

# Familias
FAMILIES = {"Anthropic", "Cohere", "OpenAI", "DeepMind", "ElevenLabs"}

def normalize_text(text: str) -> str:
    """Normaliza texto: minúsculas, colapsa espacios, quita puntuación excepto apóstrofes."""
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def load_manifest() -> Dict[str, dict]:
    """Carga el manifest como dict {doc_id: {columns}}."""
    docs = {}
    with open(MANIFEST_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            docs[row['doc_id']] = row
    return docs

def load_text_content(doc_id: str) -> str:
    """Carga el contenido de texto de un documento."""
    json_file = TEXT_DIR / f"{doc_id}.json"
    if not json_file.exists():
        return ""
    try:
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)
        blocks = data.get('blocks', [])
        return " ".join(block.get('text', '') for block in blocks)
    except:
        return ""

def categorize_docs(manifest: Dict[str, dict]) -> Dict[str, Dict[str, List[str]]]:
    """Categoriza docs en gobierno vs empresa por familia."""
    categorized = defaultdict(lambda: {'government': [], 'company': []})

    for doc_id, row in manifest.items():
        family = row.get('family', '')
        if family not in FAMILIES:
            continue

        speaker = row.get('speaker', '')
        genre = row.get('genre', '')

        is_government = speaker.startswith('DSIT') or genre in {'MOU', 'PRGOV'}
        is_company = genre == 'PRCO'

        if is_government:
            categorized[family]['government'].append(doc_id)
        if is_company:
            categorized[family]['company'].append(doc_id)

    return dict(categorized)

def find_shared_ngrams_length_n(words1: List[str], words2: List[str], n: int) -> Set[Tuple[str, ...]]:
    """Encuentra n-gramas de longitud exacta n compartidos entre dos listas de palabras."""
    if len(words1) < n or len(words2) < n:
        return set()

    ngrams1 = set(tuple(words1[i:i+n]) for i in range(len(words1) - n + 1))
    ngrams2 = set(tuple(words2[i:i+n]) for i in range(len(words2) - n + 1))
    return ngrams1 & ngrams2

def find_maximal_ngrams(words1: List[str], words2: List[str]) -> List[Tuple[str, ...]]:
    """Encuentra n-gramas compartidos de longitud >= 6 y retorna solo los maximales."""
    max_len = min(len(words1), len(words2))
    if max_len < 6:
        return []

    matches_by_length = {}

    # Busca n-gramas de cada longitud de 6 a max_len
    for n in range(6, max_len + 1):
        shared = find_shared_ngrams_length_n(words1, words2, n)
        if shared:
            matches_by_length[n] = shared

    if not matches_by_length:
        return []

    # Recolecta todos los matches
    all_matches = []
    for matches in matches_by_length.values():
        all_matches.extend(matches)

    # Filtra maximales
    maximal = []
    for candidate in all_matches:
        is_maximal = True
        for other in all_matches:
            if len(other) > len(candidate):
                # Verifica si candidate es substring de other
                for i in range(len(other) - len(candidate) + 1):
                    if other[i:i+len(candidate)] == candidate:
                        is_maximal = False
                        break
            if not is_maximal:
                break
        if is_maximal:
            maximal.append(candidate)

    return maximal

def process_echo_phrases():
    """Procesa echo-phrases."""
    manifest = load_manifest()
    categorized = categorize_docs(manifest)

    echoes = []
    all_family_matches = defaultdict(set)

    for family in FAMILIES:
        if family not in categorized:
            continue

        gov_docs = categorized[family]['government']
        comp_docs = categorized[family]['company']

        if not gov_docs or not comp_docs:
            continue

        # Carga y normaliza textos
        gov_texts = {}
        for doc_id in gov_docs:
            text = load_text_content(doc_id)
            if text:
                gov_texts[doc_id] = normalize_text(text)

        comp_texts = {}
        for doc_id in comp_docs:
            text = load_text_content(doc_id)
            if text:
                comp_texts[doc_id] = normalize_text(text)

        if not gov_texts or not comp_texts:
            continue

        # Convierte a listas de palabras
        gov_words = {doc_id: text.split() for doc_id, text in gov_texts.items()}
        comp_words = {doc_id: text.split() for doc_id, text in comp_texts.items()}

        # Encuentra matches entre cada par gobierno-empresa
        for gov_doc, gov_word_list in gov_words.items():
            for comp_doc, comp_word_list in comp_words.items():
                maximal = find_maximal_ngrams(gov_word_list, comp_word_list)

                for ngram in maximal:
                    gov_date = manifest[gov_doc]['date']
                    comp_date = manifest[comp_doc]['date']

                    if gov_date < comp_date:
                        published_first = 'government'
                    elif comp_date < gov_date:
                        published_first = 'company'
                    else:
                        published_first = 'same_day'

                    phrase_text = " ".join(ngram)

                    echoes.append({
                        'family': family,
                        'gov_doc': gov_doc,
                        'company_doc': comp_doc,
                        'n_words': len(ngram),
                        'phrase': phrase_text,
                        'published_first': published_first,
                        'ngram_tuple': ngram
                    })

                    all_family_matches[family].add(ngram)

    # Detecta fórmulas
    for echo in echoes:
        ngram = echo['ngram_tuple']
        count = sum(1 for f in FAMILIES if ngram in all_family_matches.get(f, set()))
        echo['formulaic'] = count >= 2
        del echo['ngram_tuple']

    return echoes

def write_echo_csv(echoes: List[dict]):
    """Escribe CSV de echo-phrases."""
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'family', 'gov_doc', 'company_doc', 'n_words', 'phrase', 'published_first', 'formulaic'
        ])
        writer.writeheader()
        for echo in echoes:
            writer.writerow(echo)

def write_echo_summary(echoes: List[dict]):
    """Escribe resumen en Markdown."""
    by_family = defaultdict(list)
    for echo in echoes:
        by_family[echo['family']].append(echo)

    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write("# Echo Phrases Summary\n\n")

        for family in sorted(FAMILIES):
            if family not in by_family:
                f.write(f"## {family}\n\nNo echoes found.\n\n")
                continue

            family_echoes = by_family[family]
            formulaic_count = sum(1 for e in family_echoes if e['formulaic'])
            non_formulaic_count = len(family_echoes) - formulaic_count

            non_formulaic = [e for e in family_echoes if not e['formulaic']]
            longest = max(non_formulaic, key=lambda e: e['n_words']) if non_formulaic else None

            first_counts = defaultdict(int)
            for echo in family_echoes:
                first_counts[echo['published_first']] += 1

            most_common_first = max(first_counts.items(), key=lambda x: x[1])[0] if first_counts else 'unknown'

            f.write(f"## {family}\n\n")
            f.write(f"- **Total echoes**: {len(family_echoes)}\n")
            f.write(f"- **Formulaic**: {formulaic_count}\n")
            f.write(f"- **Non-formulaic**: {non_formulaic_count}\n")

            if longest:
                f.write(f"- **Longest non-formulaic echo**: {longest['n_words']} words\n")
                f.write(f"  - Phrase: \"{longest['phrase']}\"\n")

            f.write(f"- **Published first (majority)**: {most_common_first}\n\n")

if __name__ == '__main__':
    echoes = process_echo_phrases()
    write_echo_csv(echoes)
    write_echo_summary(echoes)
    print(f"Processed {len(echoes)} echo phrases")
    print(f"Output: {OUTPUT_CSV}")
    print(f"Summary: {OUTPUT_MD}")
