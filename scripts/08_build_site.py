"""Fase 7 (HUB): genera index.html — site local consolidado del proyecto.

Re-ejecutable e idempotente: lee data/manifest.csv y data/raw/archive_urls.json,
comprueba en disco qué entregables y qué fases existen, y escribe index.html en
la raíz. No modifica ningún otro archivo. Pensado para correr después de cada
fase del pipeline (incluida Fase 7 / add_document.py) para refrescar el hub.

Uso: .venv/bin/python scripts/08_build_site.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.csv"
ARCHIVE_URLS = ROOT / "data" / "raw" / "archive_urls.json"
OUT = ROOT / "index.html"

FAMILY_COLORS = {
    "Anthropic": "#d96b45",
    "OpenAI": "#e0619b",
    "Cohere": "#cc4455",
    "DeepMind": "#9678e8",
    "ElevenLabs": "#b3901f",
    "None": "#4a5164",
}


def load_manifest():
    if not MANIFEST.exists():
        return []
    with MANIFEST.open(newline="") as f:
        return list(csv.DictReader(f))


def load_archive_urls():
    if not ARCHIVE_URLS.exists():
        return {}
    return json.loads(ARCHIVE_URLS.read_text())


def best_archive_url(doc_id, archive_urls):
    entry = archive_urls.get(doc_id)
    if not entry:
        return None
    fresh = entry.get("fresh_snapshot")
    if fresh and fresh.get("url"):
        return fresh["url"]
    existing = entry.get("existing_snapshot")
    if existing and existing.get("url"):
        return existing["url"]
    return None


def text_relpath(doc_id):
    p = ROOT / "data" / "text" / f"{doc_id}.json"
    return f"data/text/{doc_id}.json" if p.exists() else None


# ---------------------------------------------------------------------------
# Estado de fases (0-7)
# ---------------------------------------------------------------------------

def phase_status(rows):
    phases = []

    def add(n, name, status, detail):
        phases.append({"n": n, "name": name, "status": status, "detail": detail})

    # Fase 0 — manifest
    if rows:
        add(0, "Congelar el corpus (manifest)", "hecho", f"{len(rows)} documentos en data/manifest.csv")
    else:
        add(0, "Congelar el corpus (manifest)", "pendiente", "data/manifest.csv no existe o está vacío")

    # Fase 1 — descarga y texto estructurado
    n_text = sum(1 for r in rows if (ROOT / "data" / "text" / f"{r['doc_id']}.json").exists())
    if rows and n_text == len(rows):
        add(1, "Descarga y archivado", "hecho", f"{n_text}/{len(rows)} documentos con texto extraído")
    elif n_text > 0:
        add(1, "Descarga y archivado", "en curso", f"{n_text}/{len(rows)} documentos con texto extraído")
    else:
        add(1, "Descarga y archivado", "pendiente", "sin textos extraídos en data/text/")

    # Fase 2 — segmentación + término
    lexicon_ok = (ROOT / "coding" / "lexicon_v1.yaml").exists()
    units_ok = (ROOT / "coding" / "units.jsonl").exists() and (ROOT / "coding" / "units.jsonl").stat().st_size > 0
    if lexicon_ok and units_ok:
        n_units = sum(1 for _ in (ROOT / "coding" / "units.jsonl").open())
        add(2, "Segmentación y detección del término", "hecho", f"{n_units} unidades en coding/units.jsonl")
    elif lexicon_ok:
        add(2, "Segmentación y detección del término", "en curso", "lexicón aprobado; faltan unidades")
    else:
        add(2, "Segmentación y detección del término", "pendiente", "sin lexicón de variantes")

    # Fase 3 — evaluación de modelos
    decision_md = ROOT / "coding" / "model_eval" / "decision.md"
    model_eval_dir = ROOT / "coding" / "model_eval"
    if decision_md.exists():
        add(3, "Evaluación de modelos (Ollama Cloud)", "hecho", "coding/model_eval/decision.md")
    elif model_eval_dir.exists() and any(model_eval_dir.iterdir()):
        add(3, "Evaluación de modelos (Ollama Cloud)", "en curso", "coding/model_eval/ tiene archivos, falta decision.md")
    else:
        add(3, "Evaluación de modelos (Ollama Cloud)", "pendiente", "coding/model_eval/ vacío")

    # Fase 4 — codificación ronda 1
    run_meta = ROOT / "coding" / "round1" / "run_meta.json"
    round1_dir = ROOT / "coding" / "round1"
    if run_meta.exists():
        add(4, "Codificación Ronda 1 (LLM)", "hecho", "coding/round1/run_meta.json")
    elif round1_dir.exists() and any(round1_dir.iterdir()):
        add(4, "Codificación Ronda 1 (LLM)", "en curso", "coding/round1/ tiene archivos, falta run_meta.json")
    else:
        add(4, "Codificación Ronda 1 (LLM)", "pendiente", "coding/round1/ vacío")

    # Fase 5 — consolidación ronda 2 (guidebook)
    guidebook = ROOT / "coding" / "guidebook.yaml"
    guidebook_draft = ROOT / "coding" / "guidebook_draft.yaml"
    if guidebook.exists():
        add(5, "Consolidación Ronda 2 (guidebook)", "hecho", "coding/guidebook.yaml")
    elif guidebook_draft.exists():
        add(5, "Consolidación Ronda 2 (guidebook)", "en curso", "borrador: coding/guidebook_draft.yaml")
    else:
        add(5, "Consolidación Ronda 2 (guidebook)", "pendiente", "sin guidebook")

    # Fase 6 — análisis
    outs_6 = [
        ROOT / "analysis" / "networks" / "mapa_autoria_familias.html",
        ROOT / "analysis" / "queries" / "queries.html",
        ROOT / "analysis" / "queries" / "echo_summary.md",
        ROOT / "analysis" / "metaphors_report.md",
    ]
    n6 = sum(1 for p in outs_6 if p.exists())
    if n6 == len(outs_6):
        add(6, "Análisis (redes, queries, ecos, metáforas)", "hecho", "todos los outputs de Fase 6 presentes")
    elif n6 > 0:
        add(6, "Análisis (redes, queries, ecos, metáforas)", "en curso", f"{n6}/{len(outs_6)} outputs presentes")
    else:
        add(6, "Análisis (redes, queries, ecos, metáforas)", "pendiente", "sin outputs de Fase 6")

    # Fase 7 — alta incremental
    incrementales = [r for r in rows if str(r.get("corpus_version", "1")).strip() not in ("", "1")]
    if incrementales:
        add(7, "Alta incremental de documentos", "en curso", f"{len(incrementales)} documento(s) con corpus_version > 1")
    else:
        add(7, "Alta incremental de documentos", "pendiente", "herramienta lista (add_document.py); sin altas todavía")

    return phases


# ---------------------------------------------------------------------------
# Entregables
# ---------------------------------------------------------------------------

DELIVERABLES = [
    ("PLAN.md", "Plan de tesis / operacionalización"),
    ("README.md", "Guía del repositorio"),
    ("interpretacion.html", "Interpretación consolidada"),
    ("analysis/networks/mapa_autoria_familias.html", "Mapa de autoría y familias (red intertextual)"),
    ("analysis/queries/queries.html", "Las tres queries del plan NVivo"),
    ("analysis/queries/echo_summary.md", "Resumen de echo-phrases (SO3)"),
    ("analysis/metaphors_report.md", "Reporte de metáforas (SO1)"),
    ("coding/model_eval/decision.md", "Decisión de evaluación de modelos"),
    ("coding/guidebook_draft.yaml", "Guidebook — borrador de sub-códigos"),
    ("coding/validation/sample_for_frida.csv", "Muestra de validación doble-codificada"),
    ("data/manifest.csv", "Manifest del corpus"),
]


def render_deliverables():
    items = []
    for relpath, label in DELIVERABLES:
        exists = (ROOT / relpath).exists()
        if exists:
            items.append(f'<li class="ok"><a href="{relpath}">{label}</a> <span class="path">{relpath}</span></li>')
        else:
            items.append(f'<li class="pending">{label} <span class="path">{relpath}</span> <em>(pendiente)</em></li>')
    return "\n".join(items)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

STATUS_LABEL = {"hecho": "hecho", "en curso": "en curso", "pendiente": "pendiente"}


def render_phases(phases):
    rows = []
    for p in phases:
        rows.append(
            f'<div class="phase phase-{p["status"].replace(" ", "-")}">'
            f'<div class="phase-n">Fase {p["n"]}</div>'
            f'<div class="phase-body"><div class="phase-name">{p["name"]}</div>'
            f'<div class="phase-detail">{p["detail"]}</div></div>'
            f'<div class="phase-badge">{STATUS_LABEL[p["status"]]}</div>'
            f"</div>"
        )
    return "\n".join(rows)


def build_corpus_json(rows, archive_urls):
    out = []
    for r in rows:
        doc_id = r["doc_id"]
        out.append({
            "doc_id": doc_id,
            "date": r.get("date", ""),
            "speaker": r.get("speaker", ""),
            "genre": r.get("genre", ""),
            "family": r.get("family", "None") or "None",
            "term_status": r.get("term_status", ""),
            "url": r.get("url", ""),
            "archive": best_archive_url(doc_id, archive_urls) or "",
            "text": text_relpath(doc_id) or "",
            "corpus_version": r.get("corpus_version", "1"),
        })
    return out


def main():
    rows = load_manifest()
    archive_urls = load_archive_urls()
    phases = phase_status(rows)
    corpus = build_corpus_json(rows, archive_urls)
    family_colors_json = json.dumps(FAMILY_COLORS)
    corpus_json = json.dumps(corpus, ensure_ascii=False)

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI for the public good — HUB del proyecto</title>
<style>
  :root{{
    --bg:#14161c; --surface:#1a1d24; --ink:#e8ecf3; --ink2:#9aa7bd; --ink3:#6b7689;
    --grid:#232733; --accent:#4590dd;
    --anthropic:#d96b45; --openai:#e0619b; --cohere:#cc4455; --deepmind:#9678e8; --elevenlabs:#b3901f;
    --ok:#52a865; --warn:#c2a33f; --bad:#c25a5a;
  }}
  *{{box-sizing:border-box}}
  html,body{{margin:0;padding:0;background:var(--bg);color:var(--ink);
    font:14px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}}
  .wrap{{max-width:1200px;margin:0 auto;padding:28px 24px 60px}}
  header h1{{font-size:20px;letter-spacing:.03em;margin:0 0 4px;text-transform:uppercase}}
  header .sub{{color:var(--ink2);font-size:13px;margin-bottom:22px}}
  section{{margin-bottom:34px}}
  h2{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink3);
    margin:0 0 12px;border-bottom:1px solid var(--grid);padding-bottom:8px}}
  a{{color:var(--accent);text-decoration:none}}
  a:hover{{text-decoration:underline}}

  .phases{{display:flex;flex-direction:column;gap:6px}}
  .phase{{display:flex;align-items:center;gap:14px;background:var(--surface);
    border:1px solid var(--grid);border-radius:8px;padding:9px 14px}}
  .phase-n{{font-size:11px;color:var(--ink3);min-width:52px;letter-spacing:.06em;text-transform:uppercase}}
  .phase-body{{flex:1;min-width:0}}
  .phase-name{{font-size:13.5px}}
  .phase-detail{{font-size:12px;color:var(--ink3)}}
  .phase-badge{{font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;
    padding:3px 9px;border-radius:20px;white-space:nowrap}}
  .phase-hecho .phase-badge{{background:#1c3324;color:var(--ok)}}
  .phase-en-curso .phase-badge{{background:#332f1c;color:var(--warn)}}
  .phase-pendiente .phase-badge{{background:#2a2530;color:var(--ink3)}}

  ul.deliverables{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:6px 24px}}
  ul.deliverables li{{background:var(--surface);border:1px solid var(--grid);border-radius:8px;
    padding:9px 12px;font-size:13px}}
  ul.deliverables li.pending{{color:var(--ink3)}}
  ul.deliverables li .path{{display:block;font-size:11px;color:var(--ink3);margin-top:2px}}
  ul.deliverables li.pending em{{color:var(--ink3);font-style:normal;font-size:11px}}

  .toolbar{{display:flex;gap:10px;align-items:center;margin-bottom:10px}}
  #filterInput{{flex:1;background:var(--surface);border:1px solid var(--grid);color:var(--ink);
    border-radius:8px;padding:8px 12px;font-size:13px}}
  #filterInput:focus{{outline:1px solid var(--accent)}}
  #corpusCount{{color:var(--ink3);font-size:12px;white-space:nowrap}}

  table{{border-collapse:collapse;width:100%;font-size:12.5px;background:var(--surface);
    border:1px solid var(--grid);border-radius:10px;overflow:hidden}}
  thead th{{cursor:pointer;user-select:none;text-align:left;color:var(--ink3);
    text-transform:uppercase;font-size:10.5px;letter-spacing:.07em;
    padding:9px 10px;border-bottom:1px solid var(--grid);white-space:nowrap}}
  thead th:hover{{color:var(--ink)}}
  thead th.sorted::after{{content:" " attr(data-arrow)}}
  tbody td{{padding:7px 10px;border-bottom:1px solid var(--grid);color:var(--ink2);vertical-align:top}}
  tbody tr:last-child td{{border-bottom:none}}
  tbody tr:hover{{background:#1f232c}}
  .fam-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}
  .links a{{margin-right:10px;font-size:11.5px}}
  .links .none{{color:var(--ink3);font-size:11.5px;margin-right:10px}}
  .term-present{{color:var(--ok)}}
  .term-variant{{color:var(--warn)}}
  .term-absent, .term-check{{color:var(--ink3)}}

  form#addForm{{background:var(--surface);border:1px solid var(--grid);border-radius:10px;
    padding:18px 20px;display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end}}
  form#addForm .field{{display:flex;flex-direction:column;gap:5px;min-width:180px}}
  form#addForm .field.grow{{flex:1;min-width:260px}}
  form#addForm label{{font-size:11px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em}}
  form#addForm input, form#addForm select{{background:var(--bg);border:1px solid var(--grid);
    color:var(--ink);border-radius:6px;padding:8px 10px;font-size:13px}}
  form#addForm button{{background:var(--accent);color:#fff;border:none;border-radius:6px;
    padding:9px 18px;font-size:13px;cursor:pointer;font-weight:600}}
  form#addForm button:hover{{opacity:.9}}
  #staticNote{{display:none;background:var(--surface);border:1px solid var(--grid);border-radius:10px;
    padding:16px 20px;color:var(--ink2);font-size:13px}}
  #staticNote code{{background:#0f1115;padding:2px 7px;border-radius:5px;color:var(--ink)}}
  #addResult{{margin-top:14px;font-size:13px;white-space:pre-wrap;background:#0f1115;
    border-radius:8px;padding:12px 14px;display:none}}

  footer{{color:var(--ink3);font-size:11.5px;margin-top:40px}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>AI for the public good — corpus y análisis</h1>
    <div class="sub">GDS/DSIT 2024-2026 · discurso de "AI for the public good" en el Government Digital Service · HUB local del proyecto</div>
  </header>

  <section id="phases">
    <h2>Estado de fases</h2>
    <div class="phases">
{render_phases(phases)}
    </div>
  </section>

  <section id="deliverables">
    <h2>Entregables</h2>
    <ul class="deliverables">
{render_deliverables()}
    </ul>
  </section>

  <section id="corpus">
    <h2>Corpus (<span id="corpusTotal">{len(corpus)}</span> documentos)</h2>
    <div class="toolbar">
      <input id="filterInput" type="text" placeholder="Filtrar por doc_id, fecha, actor, género, familia o estado del término…">
      <span id="corpusCount"></span>
    </div>
    <div style="overflow-x:auto">
    <table id="corpusTable">
      <thead>
        <tr>
          <th data-key="doc_id">doc_id</th>
          <th data-key="date">fecha</th>
          <th data-key="speaker">actor</th>
          <th data-key="genre">género</th>
          <th data-key="family">familia</th>
          <th data-key="term_status">término</th>
          <th data-key="_links">enlaces</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
    </div>
  </section>

  <section id="add-document">
    <h2>Agregar documento</h2>
    <form id="addForm" method="post" action="/add">
      <div class="field grow">
        <label for="url">URL</label>
        <input type="url" id="url" name="url" placeholder="https://www.gov.uk/government/…" required>
      </div>
      <div class="field">
        <label for="family">Familia (opcional)</label>
        <select id="family" name="family">
          <option value="">—</option>
          <option>Anthropic</option>
          <option>OpenAI</option>
          <option>Cohere</option>
          <option>DeepMind</option>
          <option>ElevenLabs</option>
        </select>
      </div>
      <div class="field">
        <label for="genre">Género (opcional)</label>
        <select id="genre" name="genre">
          <option value="">—</option>
          <option>STRAT</option>
          <option>MOU</option>
          <option>PRGOV</option>
          <option>PRCO</option>
          <option>BLOG</option>
          <option>WMS</option>
          <option>REG</option>
        </select>
      </div>
      <button type="submit">Ejecutar checklist de admisión</button>
    </form>
    <div id="addResult"></div>
    <div id="staticNote">
      Esta página se abrió como archivo (<code>file://</code>), así que el formulario no puede hacer POST.
      Para agregar documentos desde el hub, levanta el servidor local:
      <p><code>.venv/bin/python scripts/serve_site.py</code></p>
      y abre <code>http://localhost:8765</code>.
    </div>
  </section>

  <footer>Generado por scripts/08_build_site.py · re-ejecutable e idempotente.</footer>
</div>

<script>
const CORPUS = {corpus_json};
const FAMILY_COLORS = {family_colors_json};

let sortKey = "date", sortDir = 1;

function fmtLinks(row) {{
  const parts = [];
  parts.push(row.url ? `<a href="${{row.url}}" target="_blank" rel="noopener">original</a>` : '<span class="none">original —</span>');
  parts.push(row.archive ? `<a href="${{row.archive}}" target="_blank" rel="noopener">archivo</a>` : '<span class="none">archivo —</span>');
  parts.push(row.text ? `<a href="${{row.text}}" target="_blank" rel="noopener">texto</a>` : '<span class="none">texto —</span>');
  return `<span class="links">${{parts.join('')}}</span>`;
}}

function renderTable(rows) {{
  const tbody = document.querySelector('#corpusTable tbody');
  tbody.innerHTML = rows.map(r => {{
    const color = FAMILY_COLORS[r.family] || FAMILY_COLORS['None'];
    return `<tr>
      <td>${{r.doc_id}}</td>
      <td>${{r.date}}</td>
      <td>${{r.speaker}}</td>
      <td>${{r.genre}}</td>
      <td><span class="fam-dot" style="background:${{color}}"></span>${{r.family}}</td>
      <td class="term-${{r.term_status}}">${{r.term_status}}</td>
      <td>${{fmtLinks(r)}}</td>
    </tr>`;
  }}).join('');
  document.getElementById('corpusCount').textContent = rows.length + ' / ' + CORPUS.length;
}}

function applyFilterAndSort() {{
  const q = document.getElementById('filterInput').value.trim().toLowerCase();
  let rows = CORPUS.filter(r => !q || Object.values(r).some(v => String(v).toLowerCase().includes(q)));
  rows = rows.slice().sort((a, b) => {{
    const av = (a[sortKey] || '').toString().toLowerCase();
    const bv = (b[sortKey] || '').toString().toLowerCase();
    if (av < bv) return -1 * sortDir;
    if (av > bv) return 1 * sortDir;
    return 0;
  }});
  renderTable(rows);
}}

document.querySelectorAll('#corpusTable thead th[data-key]').forEach(th => {{
  th.addEventListener('click', () => {{
    const key = th.dataset.key;
    if (key === '_links') return;
    if (sortKey === key) {{ sortDir *= -1; }} else {{ sortKey = key; sortDir = 1; }}
    document.querySelectorAll('#corpusTable thead th').forEach(h => {{ h.classList.remove('sorted'); h.removeAttribute('data-arrow'); }});
    th.classList.add('sorted');
    th.setAttribute('data-arrow', sortDir === 1 ? '▲' : '▼');
    applyFilterAndSort();
  }});
}});
document.getElementById('filterInput').addEventListener('input', applyFilterAndSort);
applyFilterAndSort();

// --- Agregar documento ---
if (location.protocol === 'file:') {{
  document.getElementById('addForm').style.display = 'none';
  document.getElementById('staticNote').style.display = 'block';
}} else {{
  document.getElementById('addForm').addEventListener('submit', async (ev) => {{
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const params = new URLSearchParams();
    for (const [k, v] of fd.entries()) params.set(k, v);
    const resultBox = document.getElementById('addResult');
    resultBox.style.display = 'block';
    resultBox.textContent = 'Ejecutando checklist de admisión…';
    try {{
      const resp = await fetch('/add', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
        body: params.toString(),
      }});
      const html = await resp.text();
      document.open(); document.write(html); document.close();
    }} catch (e) {{
      resultBox.textContent = 'Error contactando al servidor local: ' + e;
    }}
  }});
}}
</script>
</body>
</html>
"""
    OUT.write_text(html)
    print(f"index.html generado ({len(corpus)} documentos, {sum(1 for p in phases if p['status']=='hecho')}/{len(phases)} fases hechas) -> {OUT}")


if __name__ == "__main__":
    main()
