"""Fase 1 (parcial): descarga y extrae texto estructurado de los documentos
GUBERNAMENTALES (gov.uk / parliament.uk) del corpus.

Lee data/manifest.csv, toma solo las filas cuyo host de `url` contiene
"gov.uk" o "parliament", y para cada una:

1. Descarga la URL a data/raw/<doc_id>.<ext> (pdf u html, sigue redirects).
   Si la página de gov.uk es una landing page delgada de una publicación con
   PDF/HTML adjunto, sigue el adjunto y usa ese contenido como principal.
2. Extrae bloques de texto ESTRUCTURADO a data/text/<doc_id>.json.
3. Escribe metadata de descarga en data/raw/<doc_id>.meta.json.
4. Si la descarga falla, reintenta vía web.archive.org.
5. Verifica: blocks no vacío, exactamente un bloque "title", longitud plausible.

Dos documentos (los dos Written Ministerial Statements en dominios
*.parliament.uk) están protegidos por un challenge JS de Cloudflare que
`requests` no puede resolver; su HTML/PDF ya fue pre-descargado a mano vía
navegador real y se referencia aquí en PREFETCHED_HTML / PREFETCHED_PDF.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import fitz  # pymupdf
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.csv"
RAW_DIR = ROOT / "data" / "raw"
TEXT_DIR = ROOT / "data" / "text"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"}
TIMEOUT = 30
RETRIES = 2
MIN_CONTENT_CHARS = 900  # umbral para decidir si una landing page es "delgada"

MIN_TOTAL_CHARS = {
    "STRAT": 1000, "MOU": 1000, "REG": 1000,
    "BLOG": 500, "WMS": 500, "PRGOV": 500,
}

PRINCIPLE_RE = re.compile(r"^(Principle|Pillar|Mission)\s+\d+\b", re.IGNORECASE)
POINT_PLAN_RE = re.compile(r"point plan", re.IGNORECASE)
WMS_BOILERPLATE_RE = re.compile(r"^House of (Commons|Lords):\s*Written Statement", re.IGNORECASE)
DINGBAT_FONT_RE = re.compile(r"(dingbat|wingding|symbol)", re.IGNORECASE)
BARE_NUMBERING_RE = re.compile(r"^\d{1,4}\.?$")

# Documentos ya descargados a mano vía navegador real porque el dominio está
# detrás de un challenge JS de Cloudflare que `requests` no resuelve.
PREFETCHED_HTML = {
    "2025-01-21_WMS_DSIT_BlueprintMinisterialStatement": (
        "https://questions-statements.parliament.uk/written-statements/detail/2025-01-21/hcws375"
    ),
}
PREFETCHED_PDF = {
    "2026-01-19_WMS_DSIT_RoadmapMinisterialStatement": (
        "https://commonsbusiness.parliament.uk/Document/101491/Pdf"
    ),
}

# Overrides puntuales para heading -> pillar_name donde el patrón no es
# detectable por regex genérica (headings sin numeración tipo "Principle N").
PILLAR_HEADING_OVERRIDES = {
    "2026-01-20_STRAT_GDS_RoadmapModernDigitalGov": {
        "Join up public sector services",
        "Harness the power of AI for the public good",
        "Strengthen and extend our digital and data public infrastructure",
        "Elevate leadership, invest in talent",
        "Fund for outcomes, procure for growth and innovation",
        "Commit to transparency, drive accountability",
    }
}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(s: str) -> str:
    s = _CONTROL_CHARS_RE.sub(" ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------
# Descarga con reintentos
# --------------------------------------------------------------------------

def fetch_with_retry(session, url, retries=RETRIES):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_exc


def is_pdf_response(resp) -> bool:
    ctype = resp.headers.get("Content-Type", "").lower()
    if "pdf" in ctype:
        return True
    return urlparse(resp.url).path.lower().endswith(".pdf")


# --------------------------------------------------------------------------
# Selección de contenedor principal / título por sitio
# --------------------------------------------------------------------------

def get_container(soup: BeautifulSoup, url: str):
    host = urlparse(url).netloc
    if "gds.blog.gov.uk" in host:
        return soup.select_one("article .entry-content") or soup.select_one(".entry-content")
    if "questions-statements.parliament.uk" in host:
        return soup.select_one(".primary-content")
    if "campaign.gov.uk" in host:
        return soup.select_one("main")
    main = soup.select_one("#content") or soup.select_one("main")
    if main is not None:
        gs = main.select_one(".govspeak")
        if gs is not None:
            return gs
        return main
    return soup.select_one("main") or soup.body


def get_title(soup: BeautifulSoup, url: str, doc_id: str) -> str:
    host = urlparse(url).netloc
    if "questions-statements.parliament.uk" in host:
        h1 = soup.select_one(".hero-banner h1") or soup.find("h1")
    else:
        h1 = soup.find("h1")
    if h1 is not None:
        t = clean_text(h1.get_text(" ", strip=True))
        if t:
            return t
    if soup.title is not None:
        t = clean_text(soup.title.get_text())
        if t:
            return re.sub(r"\s*[-|]\s*GOV\.UK$", "", t)
    return doc_id


# --------------------------------------------------------------------------
# Resolución de landing pages delgadas (publicación con adjunto HTML/PDF)
# --------------------------------------------------------------------------

def find_attachment_links(soup: BeautifulSoup, base_url: str):
    html_links, pdf_links = [], []
    for a in soup.select(".gem-c-attachment a[href], .attachment a[href]"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        if full.lower().endswith(".pdf"):
            pdf_links.append(full)
        else:
            html_links.append(full)
    return html_links, pdf_links


def resolve_main_content(session, url):
    """Devuelve dict con keys: kind ('html'|'pdf'), resp/soup/container o pdf_url."""
    resp = fetch_with_retry(session, url)
    if is_pdf_response(resp):
        return {"kind": "pdf", "resp": resp}

    soup = BeautifulSoup(resp.content, "lxml")
    container = get_container(soup, resp.url)
    text_len = len(container.get_text(strip=True)) if container is not None else 0

    is_publication_landing = (
        "gov.uk" in urlparse(resp.url).netloc and "/publications/" in urlparse(resp.url).path
    )
    if text_len >= MIN_CONTENT_CHARS or not is_publication_landing:
        return {"kind": "html", "resp": resp, "soup": soup, "container": container}

    html_links, pdf_links = find_attachment_links(soup, resp.url)
    for link in html_links:
        try:
            resp2 = fetch_with_retry(session, link)
            if is_pdf_response(resp2):
                continue
            soup2 = BeautifulSoup(resp2.content, "lxml")
            container2 = get_container(soup2, resp2.url)
            if container2 is not None and len(container2.get_text(strip=True)) >= MIN_CONTENT_CHARS:
                return {"kind": "html", "resp": resp2, "soup": soup2, "container": container2}
        except Exception:  # noqa: BLE001
            continue

    if pdf_links:
        try:
            resp3 = fetch_with_retry(session, pdf_links[0])
            return {"kind": "pdf", "resp": resp3}
        except Exception:  # noqa: BLE001
            pass

    # No se encontró nada mejor: usar lo que hay (posible failed en verificación).
    return {"kind": "html", "resp": resp, "soup": soup, "container": container}


# --------------------------------------------------------------------------
# Extracción de bloques desde HTML
# --------------------------------------------------------------------------

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


def extract_html_blocks(container, title_text, doc_id):
    blocks = []
    heading_stack = {}  # level(int) -> text
    pillar_overrides = PILLAR_HEADING_OVERRIDES.get(doc_id, set())

    def current_heading_path(max_level):
        return [heading_stack[l] for l in sorted(heading_stack) if l <= max_level]

    n = 0

    def next_id():
        nonlocal n
        n += 1
        return f"b{n:03d}"

    # bloque de título (siempre primero, un único bloque)
    blocks.append({
        "block_id": next_id(),
        "structural_position": "title",
        "heading_path": [],
        "text": title_text,
    })

    for el in walk_html(container):
        text = clean_text(el.get_text(" ", strip=True))
        if not text:
            continue
        name = el.name
        if name == "h1":
            # el h1 ya se usó como título; no se re-emite.
            continue
        if name in ("h2", "h3", "h4"):
            level = int(name[1])
            for l in list(heading_stack):
                if l >= level:
                    del heading_stack[l]
            heading_stack[level] = text
            pos = "pillar_name" if (PRINCIPLE_RE.match(text) or text in pillar_overrides) else "section_heading"
            blocks.append({
                "block_id": next_id(),
                "structural_position": pos,
                "heading_path": current_heading_path(level - 1),
                "text": text,
            })
            continue
        if name == "blockquote":
            pos = "quotation"
        else:
            pos = "body"
        blocks.append({
            "block_id": next_id(),
            "structural_position": pos,
            "heading_path": current_heading_path(4),
            "text": text,
        })
    return blocks


# --------------------------------------------------------------------------
# Extracción de bloques desde PDF
# --------------------------------------------------------------------------

def is_bold_span(span) -> bool:
    font = span.get("font", "")
    if re.search(r"(bold|-bd\b|semibold|black)", font, re.IGNORECASE):
        return True
    return bool(span.get("flags", 0) & 16)


def extract_pdf_blocks(pdf_path, doc_id):
    doc = fitz.open(pdf_path)

    pages_blocks = []  # por página: lista de bloques con lines->spans
    size_counts = Counter()
    for page in doc:
        d = page.get_text("dict")
        page_blk = []
        for block in d["blocks"]:
            lines = block.get("lines", [])
            if not lines:
                continue
            runs = []  # (text, size, bold, font)
            for line in lines:
                for span in line.get("spans", []):
                    t = span.get("text", "")
                    if not t.strip():
                        continue
                    runs.append((t, round(span["size"], 1), is_bold_span(span), span.get("font", "")))
                    size_counts[round(span["size"], 1)] += len(t)
            if runs:
                page_blk.append(runs)
        pages_blocks.append(page_blk)

    if not size_counts:
        return [], doc_id

    body_size = size_counts.most_common(1)[0][0]

    # título: texto con el tamaño de fuente máximo global, tomado de la
    # primera página donde aparece ese tamaño (normalmente la portada).
    max_size = max(size_counts)
    title_parts = []
    title_page = None
    for pno, page_blk in enumerate(pages_blocks):
        for runs in page_blk:
            for t, sz, bold, _ in runs:
                if sz == max_size:
                    if title_page is None:
                        title_page = pno
                    if pno == title_page:
                        title_parts.append(t.strip())
        if title_page is not None and pno > title_page:
            break
    title_text = clean_text(" ".join(title_parts)) or doc_id

    # Caso especial: PDFs de "written statement" parlamentarios (p.ej.
    # commonsbusiness.parliament.uk) no destacan el título con un tamaño de
    # fuente mayor; el texto más grande es la cabecera administrativa
    # ("House of Commons: Written Statement..."). En ese caso, el título
    # real es el primer bloque de esa misma página que no sea boilerplate.
    if WMS_BOILERPLATE_RE.match(title_text) and title_page is not None:
        for runs in pages_blocks[title_page]:
            cand = clean_text("".join(t for t, _, _, _ in runs))
            if not cand or WMS_BOILERPLATE_RE.match(cand):
                continue
            if re.search(r"^(Written Statement made by|Department for|Minister)", cand, re.IGNORECASE):
                continue
            if len(cand) < 200:
                title_text = cand
            break

    # tamaños de heading: > body_size, en runs íntegramente en negrita
    heading_sizes = sorted(
        {sz for sz in size_counts if sz > body_size and sz != max_size}, reverse=True
    )
    # nivel 1..N por tamaño descendente
    level_by_size = {sz: i + 1 for i, sz in enumerate(heading_sizes)}

    def is_toc_page(page_blk):
        flat = [t for runs in page_blk for t, _, _, _ in runs]
        if len(flat) < 6:
            return False
        numeric = sum(1 for t in flat if re.fullmatch(r"\d{1,4}", t.strip()))
        return numeric / len(flat) > 0.15

    # detección de encabezados/pies de página repetidos ("running header"):
    # texto corto con un número de página fusionado como prefijo/sufijo
    # (p.ej. "14A blueprint for modern digital government") que se repite
    # en varias páginas -> no es contenido, es chrome. Solo se cuentan
    # candidatos donde quitar el número SÍ cambia el texto, para no atrapar
    # subtítulos legítimos que se repiten sin numeración (p.ej. "Practical
    # recommendations").
    def strip_page_num(t):
        return re.sub(r"^\d{1,4}\s*", "", re.sub(r"\s*\d{1,4}$", "", t)).strip()

    running_hf_counts = Counter()
    for pno, page_blk in enumerate(pages_blocks):
        if pno == 0 or is_toc_page(page_blk):
            continue
        for runs in page_blk:
            t = clean_text("".join(r[0] for r in runs))
            norm = strip_page_num(t)
            if norm and norm != t and 3 < len(norm) < 150:
                running_hf_counts[norm] += 1
    running_headers_footers = {t for t, c in running_hf_counts.items() if c >= 3}

    blocks = []
    n = 0

    def next_id():
        nonlocal n
        n += 1
        return f"b{n:03d}"

    blocks.append({
        "block_id": next_id(),
        "structural_position": "title",
        "heading_path": [],
        "text": title_text,
    })

    heading_stack = {}  # level -> text
    last_heading_text = ""
    last_heading_block = None  # referencia al último bloque de heading emitido
    last_heading_size = None
    last_heading_level = None

    def current_heading_path(max_level):
        return [heading_stack[l] for l in sorted(heading_stack) if l <= max_level]

    def classify_heading_text(text, level):
        if PRINCIPLE_RE.match(text):
            return "pillar_name"
        if re.match(r"^\d+\.\s", text):
            parent_path = current_heading_path(level - 1)
            if any(POINT_PLAN_RE.search(h) for h in parent_path):
                return "pillar_name"
        return "section_heading"

    for pno, page_blk in enumerate(pages_blocks):
        if pno == 0:
            continue  # portada, ya usada para el título
        if is_toc_page(page_blk):
            continue
        for runs in page_blk:
            # descarta bloques que son puramente un glifo de viñeta decorativo
            # (fuentes símbolo tipo ZapfDingbats/Wingdings) sin contenido real.
            if all(DINGBAT_FONT_RE.search(font) for _, _, _, font in runs):
                continue
            full_text = clean_text("".join(t for t, _, _, _ in runs))
            if not full_text or full_text == title_text:
                continue
            norm_text = strip_page_num(full_text)
            if norm_text != full_text and norm_text in running_headers_footers:
                continue
            if BARE_NUMBERING_RE.match(full_text):
                # marcador de lista numerada que quedó como bloque aislado
                # (list marker con hanging indent); sin valor analítico.
                continue
            sizes = {sz for _, sz, _, _ in runs}
            all_bold = all(bold for _, _, bold, _ in runs)
            uniform_heading_size = len(sizes) == 1 and next(iter(sizes)) in level_by_size and all_bold

            if uniform_heading_size:
                sz = next(iter(sizes))
                level = level_by_size[sz]
                # una misma línea lógica de heading puede llegar partida en
                # varios "bloques" de PyMuPDF (salto de línea manual, etc.):
                # si el heading anterior es del mismo tamaño/nivel y no hubo
                # nada entremedio, se funde en el mismo bloque.
                if (
                    last_heading_block is not None
                    and last_heading_size == sz
                    and last_heading_level == level
                    and blocks[-1] is last_heading_block
                ):
                    merged_text = clean_text(last_heading_block["text"] + " " + full_text)
                    last_heading_block["text"] = merged_text
                    heading_stack[level] = merged_text
                    last_heading_text = merged_text
                    last_heading_block["structural_position"] = classify_heading_text(merged_text, level)
                    continue

                for l in list(heading_stack):
                    if l >= level:
                        del heading_stack[l]
                heading_stack[level] = full_text
                last_heading_text = full_text
                pos = classify_heading_text(full_text, level)
                new_block = {
                    "block_id": next_id(),
                    "structural_position": pos,
                    "heading_path": current_heading_path(level - 1),
                    "text": full_text,
                }
                blocks.append(new_block)
                last_heading_block = new_block
                last_heading_size = sz
                last_heading_level = level
                continue

            last_heading_block = None
            last_heading_size = None
            last_heading_level = None

            # detectar lista numerada de pilares con lead en negrita, solo
            # dentro de una sección que hable explícitamente de "point plan"
            numbered = re.match(r"^\d+\.\s*", full_text)
            first_bold_idx = next((i for i, r in enumerate(runs) if r[2]), None)
            leads_with_bold = (
                first_bold_idx is not None
                and clean_text("".join(t for t, _, _, _ in runs[:first_bold_idx])) in ("", numbered.group(0).strip() if numbered else "")
            )
            if numbered and leads_with_bold and POINT_PLAN_RE.search(last_heading_text):
                lead_chars = []
                for i in range(first_bold_idx, len(runs)):
                    t, sz, bold, _ = runs[i]
                    if bold:
                        lead_chars.append(t)
                    else:
                        break
                lead = clean_text("".join(lead_chars)).rstrip(":").strip()
                rest = full_text[len(numbered.group(0)):]
                rest = rest[len(lead):].lstrip(": ").strip() if rest.startswith(lead) else rest
                if lead:
                    blocks.append({
                        "block_id": next_id(),
                        "structural_position": "pillar_name",
                        "heading_path": current_heading_path(4),
                        "text": lead,
                    })
                if rest:
                    blocks.append({
                        "block_id": next_id(),
                        "structural_position": "body",
                        "heading_path": current_heading_path(4),
                        "text": rest,
                    })
                continue

            blocks.append({
                "block_id": next_id(),
                "structural_position": "body",
                "heading_path": current_heading_path(4),
                "text": full_text,
            })

    doc.close()
    return blocks, title_text


# --------------------------------------------------------------------------
# Manifest / filtrado
# --------------------------------------------------------------------------

def load_gov_rows():
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        host = urlparse(row["url"]).netloc
        if "gov.uk" in host or "parliament" in host:
            out.append(row)
    return out


# --------------------------------------------------------------------------
# Archive.org fallback
# --------------------------------------------------------------------------

def try_archive_fallback(session, url):
    snap_url = f"https://web.archive.org/web/2/{url}"
    resp = fetch_with_retry(session, snap_url, retries=1)
    return resp


# --------------------------------------------------------------------------
# Pipeline por documento
# --------------------------------------------------------------------------

def genre_from_doc_id(doc_id):
    m = re.match(r"^(?:CONTEXT_)?\d{4}-\d{2}-\d{2}_([A-Z]+)_", doc_id)
    return m.group(1) if m else None


def verify_blocks(blocks, genre, doc_id):
    problems = []
    if not blocks:
        problems.append("blocks vacío")
        return problems
    n_titles = sum(1 for b in blocks if b["structural_position"] == "title")
    if n_titles != 1:
        problems.append(f"n_title={n_titles} (esperado 1)")
    total_chars = sum(len(b["text"]) for b in blocks)
    min_chars = MIN_TOTAL_CHARS.get(genre, 500)
    if total_chars < min_chars:
        problems.append(f"total_chars={total_chars} < min {min_chars} (genre={genre})")
    return problems


def process_doc(session, doc_id, url):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    meta = {
        "doc_id": doc_id,
        "fetch_status": "failed",
        "http_status": None,
        "content_type": None,
        "final_url": url,
        "sha256": None,
        "bytes": None,
        "n_blocks": 0,
        "error": None,
    }

    try:
        if doc_id in PREFETCHED_HTML:
            raw_path = RAW_DIR / f"{doc_id}.html"
            content = raw_path.read_bytes()
            meta.update({
                "http_status": 200, "content_type": "text/html",
                "final_url": PREFETCHED_HTML[doc_id], "source": "browser_prefetch",
            })
            soup = BeautifulSoup(content, "lxml")
            container = get_container(soup, meta["final_url"])
            title_text = get_title(soup, meta["final_url"], doc_id)
            blocks = extract_html_blocks(container, title_text, doc_id)
            fmt = "html"
        elif doc_id in PREFETCHED_PDF:
            raw_path = RAW_DIR / f"{doc_id}.pdf"
            content = raw_path.read_bytes()
            meta.update({
                "http_status": 200, "content_type": "application/pdf",
                "final_url": PREFETCHED_PDF[doc_id], "source": "browser_prefetch",
            })
            blocks, _title = extract_pdf_blocks(raw_path, doc_id)
            fmt = "pdf"
        else:
            result = resolve_main_content(session, url)
            resp = result["resp"]
            meta["http_status"] = resp.status_code
            meta["content_type"] = resp.headers.get("Content-Type")
            meta["final_url"] = resp.url
            if result["kind"] == "pdf":
                raw_path = RAW_DIR / f"{doc_id}.pdf"
                content = resp.content
                raw_path.write_bytes(content)
                blocks, _title = extract_pdf_blocks(raw_path, doc_id)
                fmt = "pdf"
            else:
                raw_path = RAW_DIR / f"{doc_id}.html"
                content = resp.content
                raw_path.write_bytes(content)
                soup = result["soup"]
                container = result["container"]
                title_text = get_title(soup, meta["final_url"], doc_id)
                blocks = extract_html_blocks(container, title_text, doc_id)
                fmt = "html"

        genre = genre_from_doc_id(doc_id)
        problems = verify_blocks(blocks, genre, doc_id)

        if problems:
            raise RuntimeError("; ".join(problems))

        meta["fetch_status"] = "ok"
        meta["sha256"] = sha256_bytes(content)
        meta["bytes"] = len(content)
        meta["n_blocks"] = len(blocks)

        text_doc = {
            "doc_id": doc_id,
            "source_url": meta["final_url"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "format": fmt,
            "blocks": blocks,
        }
        (TEXT_DIR / f"{doc_id}.json").write_text(
            json.dumps(text_doc, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return meta

    except Exception as exc:  # noqa: BLE001
        first_error = str(exc)
        log(f"[{doc_id}] fallo en fuente primaria: {first_error}")
        # fallback archive.org
        try:
            resp = try_archive_fallback(session, url)
            meta["http_status"] = resp.status_code
            meta["content_type"] = resp.headers.get("Content-Type")
            meta["final_url"] = resp.url
            meta["source"] = "archive_org"
            if is_pdf_response(resp):
                raw_path = RAW_DIR / f"{doc_id}.pdf"
                content = resp.content
                raw_path.write_bytes(content)
                blocks, _title = extract_pdf_blocks(raw_path, doc_id)
                fmt = "pdf"
            else:
                raw_path = RAW_DIR / f"{doc_id}.html"
                content = resp.content
                raw_path.write_bytes(content)
                soup = BeautifulSoup(content, "lxml")
                container = get_container(soup, url)  # usar host original para elegir selector
                title_text = get_title(soup, url, doc_id)
                blocks = extract_html_blocks(container, title_text, doc_id)
                fmt = "html"

            genre = genre_from_doc_id(doc_id)
            problems = verify_blocks(blocks, genre, doc_id)
            if problems:
                raise RuntimeError("; ".join(problems))

            meta["fetch_status"] = "ok"
            meta["sha256"] = sha256_bytes(content)
            meta["bytes"] = len(content)
            meta["n_blocks"] = len(blocks)
            meta["error"] = f"primary_failed: {first_error}"

            text_doc = {
                "doc_id": doc_id,
                "source_url": meta["final_url"],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "format": fmt,
                "blocks": blocks,
            }
            (TEXT_DIR / f"{doc_id}.json").write_text(
                json.dumps(text_doc, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return meta
        except Exception as exc2:  # noqa: BLE001
            meta["fetch_status"] = "failed"
            meta["error"] = f"primary: {first_error} | archive_org: {exc2}"
            return meta


def main():
    rows = load_gov_rows()
    log(f"{len(rows)} documentos gov.uk/parliament a procesar")
    session = requests.Session()

    results = []
    for row in rows:
        doc_id, url = row["doc_id"], row["url"]
        log(f"--- {doc_id} ---")
        meta = process_doc(session, doc_id, url)
        (RAW_DIR / f"{doc_id}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        results.append(meta)
        log(f"    status={meta['fetch_status']} n_blocks={meta['n_blocks']} error={meta['error']}")

    ok = sum(1 for m in results if m["fetch_status"] == "ok")
    log(f"\nTotal: {ok}/{len(results)} ok")


if __name__ == "__main__":
    main()
