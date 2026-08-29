"""Fase 7: alta incremental de documentos al corpus.

    add_document.py <url> [--family Anthropic|Cohere|OpenAI|DeepMind|ElevenLabs]
                    [--genre STRAT|MOU|PRGOV|PRCO|BLOG|WMS|REG]
                    [--dry-run] [--yes]

1. Checklist de admisión (reglas de la hoja `method`, aplicadas como filtro
   explícito ANTES de escribir nada en disco): ventana ene-2024/jul-2026,
   speaker-no-publisher, frontera funcional del centro digital, criterio de
   blogs, producer-vs-scrutineer, written-vs-spoken. `--dry-run` imprime el
   checklist y termina sin tocar nada.
2. Si el checklist se aprueba (o se fuerza con `--yes`): descarga (UA
   navegador, fallback archive.org), extrae al esquema de data/text/ (mismo
   formato de bloques que 02a/02b: title/section_heading/body/quotation),
   añade la fila al manifest (corpus_version = siguiente), genera sus
   unidades de codificación en coding/units.jsonl con la misma lógica de
   04_segment.py, y recalcula red + term_counts + el HUB (index.html).

Nada entra automático: sin --yes, se pide confirmación interactiva después
de mostrar el checklist. La codificación LLM (Fase 4) del doc nuevo NO se
dispara aquí — queda como nota en el reporte final.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.csv"
TEXT_DIR = ROOT / "data" / "text"
RAW_DIR = ROOT / "data" / "raw"
UNITS = ROOT / "coding" / "units.jsonl"
LEXICON = ROOT / "coding" / "lexicon_v1.yaml"
TERM_COUNTS = ROOT / "analysis" / "queries" / "term_counts.csv"
NETWORK_HTML = ROOT / "analysis" / "networks" / "mapa_autoria_familias.html"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"}
TIMEOUT = 30

WINDOW_START = date(2024, 1, 1)
WINDOW_END = date(2026, 7, 31)

FAMILIES = ["Anthropic", "Cohere", "OpenAI", "DeepMind", "ElevenLabs"]
COMPANY_DOMAINS = {
    "anthropic.com": "Anthropic",
    "cohere.com": "Cohere",
    "openai.com": "OpenAI",
    "deepmind.google": "DeepMind",
    "elevenlabs.io": "ElevenLabs",
}
GOV_DOMAINS = ("gov.uk", "parliament.uk", "campaign.gov.uk")
SCRUTINY_DOMAINS = (
    "committees.parliament.uk", "nao.org.uk", "ico.org.uk", "publicaccountscommittee",
)
HANSARD_DOMAINS = ("hansard.parliament.uk",)
GENRES = {"STRAT", "MOU", "PRGOV", "PRCO", "BLOG", "WMS", "REG"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def clean_text(s: str) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def slugify(title: str) -> str:
    """Convierte un título a Slug CamelCase corto, estilo doc_id existente."""
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    words = re.findall(r"[A-Za-z0-9]+", t)
    stop = {"the", "a", "an", "of", "and", "to", "for", "in", "on", "with", "uk"}
    keep = [w for w in words if w.lower() not in stop] or words
    slug = "".join(w[:1].upper() + w[1:] for w in keep[:6])
    return slug[:60] or "Untitled"


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def fetch(session, url):
    """GET con reintentos; devuelve requests.Response o levanta la excepción."""
    last_exc = None
    for attempt in range(3):
        try:
            r = session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise last_exc


def wayback_fallback(session, url):
    """Consulta la Wayback availability API; devuelve snapshot url o None."""
    try:
        r = session.get("https://archive.org/wayback/available", params={"url": url}, timeout=20)
        r.raise_for_status()
        data = r.json()
        closest = (data.get("archived_snapshots") or {}).get("closest")
        if closest and closest.get("available"):
            return closest.get("url"), closest.get("timestamp")
    except Exception:  # noqa: BLE001
        pass
    return None, None


# ---------------------------------------------------------------------------
# Checklist de admisión
# ---------------------------------------------------------------------------

def guess_date(soup: BeautifulSoup, resp) -> str | None:
    """Heurística: meta tags de fecha, luego texto 'Published' de gov.uk."""
    for sel, attr in [
        ('meta[property="article:published_time"]', "content"),
        ('meta[name="date"]', "content"),
        ('meta[name="DC.date.issued"]', "content"),
        ('meta[property="og:updated_time"]', "content"),
        ('time[datetime]', "datetime"),
    ]:
        el = soup.select_one(sel)
        if el and el.get(attr):
            m = re.search(r"\d{4}-\d{2}-\d{2}", el.get(attr))
            if m:
                return m.group(0)
    # gov.uk: "Published <D Month Year>"
    text = soup.get_text(" ", strip=True)
    m = re.search(r"Published\s*:?\s*(\d{1,2}\s+\w+\s+\d{4})", text)
    if m:
        try:
            d = datetime.strptime(m.group(1), "%d %B %Y")
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def run_checklist(url: str, session) -> dict:
    """Evalúa las reglas de admisión y devuelve {rules: [...], fetched: {...}}."""
    rules = []
    fetched = {"ok": False, "soup": None, "resp": None, "is_pdf": False,
               "text": "", "title": url, "used_archive": False}

    def add(name, status, detail):
        rules.append({"rule": name, "status": status, "detail": detail})

    # --- intento de descarga (solo lectura, no se escribe nada en disco) ---
    try:
        resp = fetch(session, url)
        is_pdf = "pdf" in resp.headers.get("Content-Type", "").lower() or url.lower().endswith(".pdf")
        fetched.update(ok=True, resp=resp, is_pdf=is_pdf)
        if not is_pdf:
            soup = BeautifulSoup(resp.content, "lxml")
            fetched["soup"] = soup
            fetched["text"] = clean_text(soup.get_text(" ", strip=True))
            h1 = soup.find("h1")
            if h1 and clean_text(h1.get_text()):
                fetched["title"] = clean_text(h1.get_text())
            elif soup.title:
                fetched["title"] = clean_text(soup.title.get_text())
        fetch_note = f"descarga directa OK (status {resp.status_code})"
    except Exception as exc:  # noqa: BLE001
        arch_url, ts = wayback_fallback(session, url)
        if arch_url:
            try:
                resp = fetch(session, arch_url)
                is_pdf = "pdf" in resp.headers.get("Content-Type", "").lower() or url.lower().endswith(".pdf")
                fetched.update(ok=True, resp=resp, is_pdf=is_pdf, used_archive=True)
                if not is_pdf:
                    soup = BeautifulSoup(resp.content, "lxml")
                    fetched["soup"] = soup
                    fetched["text"] = clean_text(soup.get_text(" ", strip=True))
                fetch_note = f"descarga directa falló ({exc}); recuperado vía archive.org snapshot {ts}"
            except Exception as exc2:  # noqa: BLE001
                fetch_note = f"descarga directa falló ({exc}); fallback archive.org también falló ({exc2})"
        else:
            fetch_note = f"descarga directa falló ({exc}); sin snapshot en archive.org"
    add("Descarga (directa / fallback archive.org)", "pass" if fetched["ok"] else "fail", fetch_note)

    dom = domain_of(url)

    # Rule 1 — ventana temporal / supersession
    doc_date = guess_date(fetched["soup"], fetched.get("resp")) if fetched["soup"] else None
    if doc_date:
        try:
            d = datetime.strptime(doc_date, "%Y-%m-%d").date()
            in_window = WINDOW_START <= d <= WINDOW_END
            add("Rule 1 — ventana ene-2024/jul-2026", "pass" if in_window else "fail",
                f"fecha detectada {doc_date}" + ("" if in_window else " (fuera de ventana)"))
        except ValueError:
            add("Rule 1 — ventana ene-2024/jul-2026", "no-determinable", f"fecha no parseable: {doc_date!r}")
    else:
        add("Rule 1 — ventana ene-2024/jul-2026", "no-determinable",
            "no se pudo detectar la fecha de publicación automáticamente; confirmar a mano")

    # Rule 3 — speaker, no publisher (¿de quién es la voz?)
    if dom in COMPANY_DOMAINS:
        add("Rule 3 — speaker-no-publisher", "pass",
            f"dominio de empresa ({dom}) → voz = {COMPANY_DOMAINS[dom]}")
    elif any(dom == g or dom.endswith("." + g) for g in GOV_DOMAINS):
        add("Rule 3 — speaker-no-publisher", "pass",
            f"dominio gubernamental ({dom}) → voz = gobierno; confirmar actor exacto (GDS/DSIT/CDDO/PMO)")
    else:
        add("Rule 3 — speaker-no-publisher", "no-determinable",
            f"dominio {dom!r} no es ni gov.uk/parliament.uk ni dominio de empresa MoU; "
            "verificar que la voz del texto sea la del actor y no de un tercero que lo reporta")

    # Rule 4 — frontera funcional del centro digital
    kw = r"\bgds\b|government digital service|\bi\.ai\b|incubator for (artificial intelligence|ai)|" \
         r"dsit\b|science, innovation and technology|digital government|public services?.{0,20}\bai\b|" \
         r"memorandum of understanding|ai opportunities"
    low = fetched["text"].lower()
    if low and re.search(kw, low):
        add("Rule 4 — frontera funcional del centro digital", "pass",
            "el texto menciona GDS/DSIT/i.AI o gobierno digital / IA en servicios públicos")
    elif low:
        add("Rule 4 — frontera funcional del centro digital", "no-determinable",
            "no se detectaron palabras clave del centro digital; revisar a mano si cae dentro del alcance")
    else:
        add("Rule 4 — frontera funcional del centro digital", "no-determinable",
            "sin texto extraído para evaluar (PDF o descarga fallida)")

    # Rule 5 — criterio de blogs
    if "/blog" in urlparse(url).path.lower() or "blog." in dom:
        is_recognised_blog = dom.startswith("gds.blog") or dom in COMPANY_DOMAINS or "blog." + dom.split(".", 1)[-1] == dom
        recognised = dom.startswith("gds.blog") or any(c in dom for c in COMPANY_DOMAINS)
        add("Rule 5 — criterio de blogs", "pass" if recognised else "no-determinable",
            f"URL de blog ({dom}); " + ("blog institucional reconocido (GDS / empresa MoU)"
             if recognised else "blog no reconocido — confirmar que es voz institucional, no personal/terceros"))
    else:
        add("Rule 5 — criterio de blogs", "pass", "no es una URL de blog (no aplica)")

    # producer-vs-scrutineer
    if any(s in dom for s in SCRUTINY_DOMAINS):
        add("Producer vs. scrutineer", "fail",
            f"dominio de escrutinio/auditoría ({dom}) → contexto, NO corpus")
    else:
        add("Producer vs. scrutineer", "pass", "no es un órgano de escrutinio parlamentario/auditoría")

    # written-vs-spoken (Hansard fuera)
    if any(h in dom for h in HANSARD_DOMAINS) or "hansard" in url.lower():
        add("Written vs. spoken (Hansard fuera)", "fail",
            "Hansard / transcripción de intervención oral → fuera del corpus")
    else:
        add("Written vs. spoken (Hansard fuera)", "pass", "no es una transcripción de Hansard")

    fetched["guessed_date"] = doc_date
    return {"rules": rules, "fetched": fetched}


def print_checklist(url, result):
    print(f"\n=== Checklist de admisión — {url} ===")
    for r in result["rules"]:
        mark = {"pass": "PASA", "fail": "FALLA", "no-determinable": "NO-DETERMINABLE"}[r["status"]]
        print(f"  [{mark:16s}] {r['rule']}")
        print(f"                     {r['detail']}")
    fails = [r for r in result["rules"] if r["status"] == "fail"]
    print()
    if fails:
        print(f"RESULTADO: {len(fails)} regla(s) en FALLA — requiere revisión explícita de Frida antes de admitir.")
    else:
        nd = [r for r in result["rules"] if r["status"] == "no-determinable"]
        print(f"RESULTADO: sin fallas duras. {len(nd)} regla(s) no-determinable — Frida decide.")


# ---------------------------------------------------------------------------
# Extracción a esquema data/text
# ---------------------------------------------------------------------------

CAPTURE_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "blockquote"}
SKIP_TAGS = {"script", "style", "nav", "aside", "footer", "form", "figure", "table"}


def walk_html(el):
    for child in el.find_all(recursive=False):
        name = getattr(child, "name", None)
        if name is None:
            continue
        if name in CAPTURE_TAGS:
            yield child
        elif name in SKIP_TAGS:
            continue
        else:
            yield from walk_html(child)


def get_container(soup):
    for sel in ("article .entry-content", ".entry-content", "#content .govspeak",
                "main .govspeak", "#content", "main", "article"):
        el = soup.select_one(sel)
        if el is not None and len(el.get_text(strip=True)) > 200:
            return el
    return soup.body or soup


def extract_html_blocks(soup, title_text):
    container = get_container(soup)
    blocks, heading_stack, n = [], {}, 0

    def next_id():
        nonlocal n
        n += 1
        return f"b{n:03d}"

    def heading_path(max_level):
        return [heading_stack[l] for l in sorted(heading_stack) if l <= max_level]

    blocks.append({"block_id": next_id(), "structural_position": "title", "heading_path": [], "text": title_text})
    for el in walk_html(container):
        text = clean_text(el.get_text(" ", strip=True))
        if not text:
            continue
        name = el.name
        if name == "h1":
            continue
        if name in ("h2", "h3", "h4"):
            level = int(name[1])
            for l in list(heading_stack):
                if l >= level:
                    del heading_stack[l]
            heading_stack[level] = text
            blocks.append({"block_id": next_id(), "structural_position": "section_heading",
                            "heading_path": heading_path(level - 1), "text": text})
            continue
        pos = "quotation" if name == "blockquote" else "body"
        blocks.append({"block_id": next_id(), "structural_position": pos,
                        "heading_path": heading_path(4), "text": text})
    return blocks


def extract_pdf_blocks(pdf_bytes, title_hint):
    import fitz  # pymupdf
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    blocks, n = [], 0

    def next_id():
        nonlocal n
        n += 1
        return f"b{n:03d}"

    title_text = title_hint
    blocks.append({"block_id": next_id(), "structural_position": "title", "heading_path": [], "text": title_text})
    for page in doc:
        for b in page.get_text("blocks"):
            text = clean_text(b[4])
            if not text or len(text) < 3:
                continue
            blocks.append({"block_id": next_id(), "structural_position": "body", "heading_path": [], "text": text})
    doc.close()
    return blocks


def build_doc_json(url, blocks, fmt):
    return {
        "source_url": url,
        "fetched_at": datetime.now().astimezone().isoformat(),
        "format": fmt,
        "blocks": blocks,
    }


# ---------------------------------------------------------------------------
# Heurísticas de atributos (espejo de 01_manifest.py / 04_segment.py)
# ---------------------------------------------------------------------------

def guess_family(url, text, family_flag):
    if family_flag:
        return family_flag
    dom = domain_of(url)
    if dom in COMPANY_DOMAINS:
        return COMPANY_DOMAINS[dom]
    low = (text or "").lower()
    for fam in FAMILIES:
        if fam.lower() in low[:4000]:
            return fam
    return "None"


def guess_genre(url, text, family, genre_flag):
    if genre_flag:
        return genre_flag
    path = urlparse(url).path.lower()
    dom = domain_of(url)
    low = (text or "").lower()
    if dom in COMPANY_DOMAINS:
        return "PRCO"
    if "written-statement" in path or "written-statements" in path:
        return "WMS"
    if "memorandum of understanding" in low or "/mou" in path:
        return "MOU"
    if "/government/news/" in path:
        return "PRGOV"
    if "blog." in dom or "/blog/" in path:
        return "BLOG"
    if "regulation" in low[:2000] or "white paper" in low[:2000]:
        return "REG"
    return "STRAT"


def guess_speaker(url, family, genre):
    dom = domain_of(url)
    if dom in COMPANY_DOMAINS:
        return COMPANY_DOMAINS[dom]
    if genre == "MOU" and family != "None":
        return f"DSIT_and_{family}"
    if genre == "PRCO" and family != "None":
        return family
    if "gds.blog" in dom:
        return "GDS"
    return "DSIT"


def assign_doc_id(doc_date, genre, speaker, title, existing_ids):
    actor = re.sub(r"[^A-Za-z0-9]", "", speaker.split("_")[-1]) or "Unknown"
    slug = slugify(title)
    base = f"{doc_date}_{genre}_{actor}_{slug}"
    doc_id, i = base, 2
    while doc_id in existing_ids:
        doc_id = f"{base}{i}"
        i += 1
    return doc_id


# ---------------------------------------------------------------------------
# Lexicón / term_status / unidades (misma lógica que 04_segment.py)
# ---------------------------------------------------------------------------

def load_lexicon():
    lex = yaml.safe_load(LEXICON.read_text())
    rx = lambda pats: [re.compile(p, re.I) for p in pats]
    return rx(lex["nominal"]), rx(lex["variant_nominal"]), rx(lex["distributive"])


def hits(rxs, text):
    out = []
    for r in rxs:
        out += [m.group(0) for m in r.finditer(text)]
    return out


def sections(blocks):
    secs, cur, cur_head = [], [], "(inicio)"
    for b in blocks:
        if b["structural_position"] in ("section_heading", "pillar_name"):
            if cur:
                secs.append((cur_head, cur))
            cur_head, cur = b["text"][:120], [b]
        else:
            cur.append(b)
    if cur:
        secs.append((cur_head, cur))
    return secs


def build_units_and_term_status(doc_id, blocks):
    rx_nom, rx_var, rx_dis = load_lexicon()
    full = "\n".join(b["text"] for b in blocks)
    n_nom, n_var, n_dis = hits(rx_nom, full), hits(rx_var, full), hits(rx_dis, full)
    term_status = "present" if n_nom else ("variant" if n_var else "absent")

    doc_units = []
    for si, (head, sblocks) in enumerate(sections(blocks)):
        text = "\n".join(b["text"] for b in sblocks)
        u_nom, u_var, u_dis = hits(rx_nom, text), hits(rx_var, text), hits(rx_dis, text)
        if u_nom or u_var or u_dis:
            doc_units.append({
                "unit_id": f"{doc_id}::s{si:02d}", "doc_id": doc_id, "heading": head,
                "block_ids": [b["block_id"] for b in sblocks], "text": text, "retrieval": "lexicon",
                "hits_nominal": u_nom, "hits_variant": u_var, "hits_distributive": u_dis})
    if not doc_units and len(full) <= 9000:
        doc_units.append({
            "unit_id": f"{doc_id}::full", "doc_id": doc_id, "heading": blocks[0]["text"][:120],
            "block_ids": [b["block_id"] for b in blocks], "text": full, "retrieval": "full_short_doc",
            "hits_nominal": [], "hits_variant": [], "hits_distributive": []})

    counts_row = {"doc_id": doc_id, "n_nominal": len(n_nom), "n_variant": len(n_var),
                  "n_distributive": len(n_dis), "nominal_forms": "; ".join(sorted(set(f.lower() for f in n_nom)))}
    return term_status, doc_units, counts_row


def gds_tier_of(speaker, full_text):
    low = full_text.lower()
    if speaker in ("GDS", "CDDO", "DSIT_and_GDS") or "GDS" in speaker:
        return "T1"
    if re.search(r"\bgds\b|government digital service|\bi\.ai\b|incubator for (artificial intelligence|ai)|ai playbook|service standard", low):
        return "T2"
    return "T3"


# ---------------------------------------------------------------------------
# Manifest / recompute
# ---------------------------------------------------------------------------

def read_manifest():
    with MANIFEST.open(newline="") as f:
        return list(csv.DictReader(f)), f


def next_corpus_version(rows):
    versions = []
    for r in rows:
        try:
            versions.append(int(float(r.get("corpus_version", 1) or 1)))
        except ValueError:
            versions.append(1)
    return (max(versions) if versions else 1) + 1


def append_manifest_row(row):
    rows, _ = read_manifest()
    fieldnames = list(rows[0].keys()) if rows else list(row.keys())
    for k in row:
        if k not in fieldnames:
            fieldnames.append(k)
    rows.append(row)
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def append_units(doc_units):
    with UNITS.open("a") as f:
        for u in doc_units:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")


def append_term_counts(row, manifest_row):
    exists = TERM_COUNTS.exists()
    fields = ["doc_id", "genre", "speaker", "family", "n_nominal", "n_variant", "n_distributive", "nominal_forms"]
    full_row = {"doc_id": row["doc_id"], "genre": manifest_row["genre"], "speaker": manifest_row["speaker"],
                "family": manifest_row["family"], "n_nominal": row["n_nominal"], "n_variant": row["n_variant"],
                "n_distributive": row["n_distributive"], "nominal_forms": row["nominal_forms"]}
    with TERM_COUNTS.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow(full_row)


def rebuild_network_html():
    """Corre 06_network_v0.py y re-embebe el JSON en mapa_autoria_familias.html."""
    subprocess.run([sys.executable, str(ROOT / "scripts" / "06_network_v0.py")],
                    check=True, cwd=str(ROOT))
    data = json.loads((ROOT / "analysis" / "networks" / "intertextual_v0.json").read_text())
    html = NETWORK_HTML.read_text()
    new_block = "const DATA = " + json.dumps(data, indent=1, ensure_ascii=False) + ";"
    html2, count = re.subn(r"const DATA = \{.*?\n\};", new_block, html, flags=re.S)
    if count == 0:
        raise RuntimeError("no se encontró 'const DATA = {...};' en mapa_autoria_familias.html")
    NETWORK_HTML.write_text(html2)


def rebuild_all_recompute():
    rebuild_network_html()
    subprocess.run([sys.executable, str(ROOT / "scripts" / "08_build_site.py")], check=True, cwd=str(ROOT))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def admit_document(url: str, family: str | None, genre: str | None, result: dict, session) -> dict:
    """Post-checklist: descarga ya resuelta en `result['fetched']` → extrae,
    escribe en data/text/, añade fila al manifest y unidades a units.jsonl,
    y recalcula red + term_counts + hub. Devuelve un reporte (dict).

    Se asume que el checklist ya se corrió (`run_checklist`); esta función no
    vuelve a evaluar reglas de admisión, solo materializa el alta.
    """
    fetched = result["fetched"]
    if not fetched["ok"]:
        return {"ok": False, "error": "No se pudo descargar el documento (ni directo ni por archive.org)."}

    if fetched["is_pdf"]:
        title = url.rsplit("/", 1)[-1]
        blocks = extract_pdf_blocks(fetched["resp"].content, title)
        fmt = "pdf"
    else:
        blocks = extract_html_blocks(fetched["soup"], fetched["title"])
        title = fetched["title"]
        fmt = "html"

    full_text = "\n".join(b["text"] for b in blocks)
    doc_date = fetched.get("guessed_date") or datetime.now().strftime("%Y-%m-%d")
    family = guess_family(url, full_text, family)
    genre = guess_genre(url, full_text, family, genre)
    speaker = guess_speaker(url, family, genre)

    rows, _ = read_manifest()
    existing_ids = {r["doc_id"] for r in rows}
    doc_id = assign_doc_id(doc_date, genre, speaker, title, existing_ids)

    term_status, doc_units, counts_row = build_units_and_term_status(doc_id, blocks)
    tier = gds_tier_of(speaker, full_text)
    corpus_version = next_corpus_version(rows)

    archive_url = ""
    try:
        arch_url, _ts = wayback_fallback(session, url)
        archive_url = arch_url or ""
    except Exception:  # noqa: BLE001
        pass

    manifest_row = {
        "doc_id": doc_id, "excel_row": "", "date": doc_date, "genre": genre,
        "actor_raw": speaker, "speaker": speaker, "side": "Public", "family": family,
        "gds_tier": tier, "stage": "", "term_status": term_status, "url": url,
        "archive_url": archive_url, "corpus_version": corpus_version, "is_context": False,
        "fetch_status": "ok", "n_blocks": len(blocks), "n_quotes": sum(1 for b in blocks if b["structural_position"] == "quotation"),
        "n_pillars": sum(1 for b in blocks if b["structural_position"] == "pillar_name"),
        "total_chars": len(full_text), "source": "archive_fallback" if fetched["used_archive"] else "direct",
        "gds_tier_source": "auto_provisional",
    }

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    doc_json = build_doc_json(url, blocks, fmt)
    doc_json["doc_id"] = doc_id
    (TEXT_DIR / f"{doc_id}.json").write_text(json.dumps(doc_json, indent=2, ensure_ascii=False))

    append_manifest_row(manifest_row)
    append_units(doc_units)
    append_term_counts(counts_row, manifest_row)

    report = {
        "ok": True, "doc_id": doc_id, "manifest_row": manifest_row,
        "n_blocks": len(blocks), "n_units": len(doc_units), "corpus_version": corpus_version,
        "coding_pending_cmd": f".venv/bin/python scripts/05_code.py --doc {doc_id}",
    }
    try:
        rebuild_all_recompute()
        report["recompute_ok"] = True
    except Exception as exc:  # noqa: BLE001
        report["recompute_ok"] = False
        report["recompute_error"] = str(exc)
    return report


def print_report(report: dict):
    if not report["ok"]:
        print(report["error"])
        return
    r = report["manifest_row"]
    print(f"\nDocumento admitido: {report['doc_id']}")
    print(f"  fecha={r['date']} genre={r['genre']} speaker={r['speaker']} family={r['family']} "
          f"gds_tier={r['gds_tier']} term_status={r['term_status']}")
    print(f"  corpus_version={report['corpus_version']} · {report['n_blocks']} bloques · "
          f"{report['n_units']} unidades de codificación")
    if report["recompute_ok"]:
        print("\nRecalculado: analysis/networks/intertextual_v0.json, mapa_autoria_familias.html "
              "(DATA re-embebido), analysis/queries/term_counts.csv, index.html.")
    else:
        print(f"\nADVERTENCIA: el recálculo de red/hub falló ({report['recompute_error']}). "
              f"El documento sí quedó admitido en el manifest y en coding/units.jsonl.")
    print(f"\ncodificación pendiente: {report['coding_pending_cmd']}")


def main():
    ap = argparse.ArgumentParser(description="Alta incremental de un documento al corpus (Fase 7).")
    ap.add_argument("url")
    ap.add_argument("--family", choices=FAMILIES, default=None)
    ap.add_argument("--genre", choices=sorted(GENRES), default=None)
    ap.add_argument("--dry-run", action="store_true", help="solo imprime el checklist, no toca disco")
    ap.add_argument("--yes", action="store_true", help="salta la confirmación interactiva (para uso desde serve_site.py)")
    args = ap.parse_args()

    session = requests.Session()
    result = run_checklist(args.url, session)
    print_checklist(args.url, result)

    if args.dry_run:
        return 0

    fails = [r for r in result["rules"] if r["status"] == "fail"]
    if fails and not args.yes:
        print("\nHay reglas en FALLA. Este documento normalmente NO debería admitirse.")

    if not args.yes:
        try:
            ans = input("\n¿Aprobar la admisión de este documento? [y/N]: ").strip().lower()
        except EOFError:
            ans = ""
        if ans != "y":
            print("Admisión cancelada por el usuario.")
            return 1

    report = admit_document(args.url, args.family, args.genre, result, session)
    print_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
