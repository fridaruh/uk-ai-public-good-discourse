"""Phase 7 (HUB): generates index.html — the project's consolidated local site.

Re-runnable and idempotent: reads data/manifest.csv and data/raw/archive_urls.json,
checks on disk which deliverables and which phases exist, and writes index.html
at the root. Does not modify any other file. Meant to run after each pipeline
phase (including Phase 7 / add_document.py) to refresh the hub.

Usage: .venv/bin/python scripts/08_build_site.py
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
# Phase status (0-7)
# ---------------------------------------------------------------------------

def phase_status(rows):
    phases = []

    def add(n, name, status, detail):
        phases.append({"n": n, "name": name, "status": status, "detail": detail})

    # Phase 0 — manifest
    if rows:
        add(0, "Freeze the corpus (manifest)", "hecho", f"{len(rows)} documents in data/manifest.csv")
    else:
        add(0, "Freeze the corpus (manifest)", "pendiente", "data/manifest.csv does not exist or is empty")

    # Phase 1 — download and structured text
    n_text = sum(1 for r in rows if (ROOT / "data" / "text" / f"{r['doc_id']}.json").exists())
    if rows and n_text == len(rows):
        add(1, "Download and archiving", "hecho", f"{n_text}/{len(rows)} documents with extracted text")
    elif n_text > 0:
        add(1, "Download and archiving", "en curso", f"{n_text}/{len(rows)} documents with extracted text")
    else:
        add(1, "Download and archiving", "pendiente", "no extracted texts in data/text/")

    # Phase 2 — segmentation + term
    lexicon_ok = (ROOT / "coding" / "lexicon_v1.yaml").exists()
    units_ok = (ROOT / "coding" / "units.jsonl").exists() and (ROOT / "coding" / "units.jsonl").stat().st_size > 0
    if lexicon_ok and units_ok:
        n_units = sum(1 for _ in (ROOT / "coding" / "units.jsonl").open())
        add(2, "Segmentation and term detection", "hecho", f"{n_units} units in coding/units.jsonl")
    elif lexicon_ok:
        add(2, "Segmentation and term detection", "en curso", "lexicon approved; units missing")
    else:
        add(2, "Segmentation and term detection", "pendiente", "no variant lexicon")

    # Phase 3 — model evaluation
    decision_md = ROOT / "coding" / "model_eval" / "decision.md"
    model_eval_dir = ROOT / "coding" / "model_eval"
    if decision_md.exists():
        add(3, "Model evaluation (Ollama Cloud)", "hecho", "coding/model_eval/decision.md")
    elif model_eval_dir.exists() and any(model_eval_dir.iterdir()):
        add(3, "Model evaluation (Ollama Cloud)", "en curso", "coding/model_eval/ has files, decision.md missing")
    else:
        add(3, "Model evaluation (Ollama Cloud)", "pendiente", "coding/model_eval/ empty")

    # Phase 4 — round 1 coding
    run_meta = ROOT / "coding" / "round1" / "run_meta.json"
    round1_dir = ROOT / "coding" / "round1"
    if run_meta.exists():
        add(4, "Round 1 Coding (LLM)", "hecho", "coding/round1/run_meta.json")
    elif round1_dir.exists() and any(round1_dir.iterdir()):
        add(4, "Round 1 Coding (LLM)", "en curso", "coding/round1/ has files, run_meta.json missing")
    else:
        add(4, "Round 1 Coding (LLM)", "pendiente", "coding/round1/ empty")

    # Phase 5 — round 2 consolidation (guidebook)
    guidebook = ROOT / "coding" / "guidebook.yaml"
    guidebook_draft = ROOT / "coding" / "guidebook_draft.yaml"
    if guidebook.exists():
        add(5, "Round 2 Consolidation (guidebook)", "hecho", "coding/guidebook.yaml")
    elif guidebook_draft.exists():
        add(5, "Round 2 Consolidation (guidebook)", "en curso", "draft: coding/guidebook_draft.yaml")
    else:
        add(5, "Round 2 Consolidation (guidebook)", "pendiente", "no guidebook")

    # Phase 6 — analysis
    outs_6 = [
        ROOT / "analysis" / "networks" / "authorship_family_map.html",
        ROOT / "analysis" / "queries" / "queries.html",
        ROOT / "analysis" / "queries" / "echo_summary.md",
        ROOT / "analysis" / "metaphors_report.md",
    ]
    n6 = sum(1 for p in outs_6 if p.exists())
    if n6 == len(outs_6):
        add(6, "Analysis (networks, queries, echoes, metaphors)", "hecho", "all Phase 6 outputs present")
    elif n6 > 0:
        add(6, "Analysis (networks, queries, echoes, metaphors)", "en curso", f"{n6}/{len(outs_6)} outputs present")
    else:
        add(6, "Analysis (networks, queries, echoes, metaphors)", "pendiente", "no Phase 6 outputs")

    # Phase 7 — incremental document intake
    incrementales = [r for r in rows if str(r.get("corpus_version", "1")).strip() not in ("", "1")]
    if incrementales:
        add(7, "Incremental document intake", "en curso", f"{len(incrementales)} document(s) with corpus_version > 1")
    else:
        add(7, "Incremental document intake", "pendiente", "tool ready (add_document.py); no intakes yet")

    return phases


# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------

DELIVERABLES = [
    ("PLAN.md", "Thesis plan / operationalization"),
    ("README.md", "Repository guide"),
    ("HANDOFF.md", "Handoff guide — continuing this project on a new machine"),
    ("interpretation.html", "Consolidated interpretation"),
    ("analysis/networks/authorship_family_map.html", "Authorship and family map (intertextual network)"),
    ("analysis/queries/queries.html", "The three queries from the NVivo plan"),
    ("analysis/queries/echo_summary.md", "Echo-phrases summary (SO3)"),
    ("analysis/metaphors_report.md", "Metaphors report (SO1)"),
    ("coding/model_eval/decision.md", "Model evaluation decision"),
    ("coding/guidebook_draft.yaml", "Guidebook — sub-codes draft"),
    ("analysis/guidebook_summary.html", "Guidebook review — interactive cluster naming"),
    ("coding/validation/sample_for_author.csv", "Double-coded validation sample"),
    ("data/manifest.csv", "Corpus manifest"),
]


def render_deliverables():
    items = []
    for relpath, label in DELIVERABLES:
        exists = (ROOT / relpath).exists()
        if exists:
            items.append(f'<li class="ok"><a href="{relpath}">{label}</a> <span class="path">{relpath}</span></li>')
        else:
            items.append(f'<li class="pending">{label} <span class="path">{relpath}</span> <em>(pending)</em></li>')
    return "\n".join(items)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

STATUS_LABEL = {"hecho": "✓ done", "en curso": "in progress", "pendiente": "pending"}


def render_phases(phases):
    rows = []
    for p in phases:
        rows.append(
            f'<div class="phase phase-{p["status"].replace(" ", "-")}">'
            f'<div class="phase-n">Phase {p["n"]}</div>'
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
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI for the public good — Project hub</title>
<style>
  :root{{
    --bg:#ffffff; --surface:#ffffff; --surface-soft:#f7f7f7; --surface-strong:#eef0f3;
    --ink:#0a0b0d; --body:#5b616e; --muted:#7c828a;
    --hairline:#dee1e6; --accent:#0052ff; --accent-active:#003ecc;
    --anthropic:#d96b45; --openai:#e0619b; --cohere:#cc4455; --deepmind:#9678e8; --elevenlabs:#b3901f;
    --ok:#05b169; --warn:#a87700; --bad:#cf202f;
  }}
  *{{box-sizing:border-box}}
  html,body{{margin:0;padding:0;background:var(--bg);color:var(--body);
    font:14px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}}
  .wrap{{max-width:1200px;margin:0 auto;padding:28px 24px 60px}}
  header h1{{font-size:20px;font-weight:600;letter-spacing:.03em;margin:0 0 4px;
    text-transform:uppercase;color:var(--ink)}}
  header .sub{{color:var(--muted);font-size:13px;margin-bottom:22px}}
  section{{margin-bottom:34px}}
  section:nth-of-type(even){{background:var(--surface-soft);margin-left:-24px;margin-right:-24px;
    padding:20px 24px;border-radius:16px}}
  h2{{font-size:13px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
    margin:0 0 12px;border-bottom:1px solid var(--hairline);padding-bottom:8px}}
  a, a:visited{{color:var(--accent);text-decoration:none}}
  a:hover{{color:var(--accent-active);text-decoration:underline}}

  .phases{{display:flex;flex-direction:column;gap:6px}}
  .phase{{display:flex;align-items:center;gap:14px;background:var(--surface);
    border:1px solid var(--hairline);border-radius:8px;padding:9px 14px}}
  .phase-n{{font-size:11px;color:var(--muted);min-width:52px;letter-spacing:.06em;text-transform:uppercase}}
  .phase-body{{flex:1;min-width:0}}
  .phase-name{{font-size:13.5px;color:var(--ink)}}
  .phase-detail{{font-size:12px;color:var(--muted)}}
  .phase-badge{{font-size:10.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
    padding:3px 9px;border-radius:20px;white-space:nowrap;background:var(--surface-strong)}}
  .phase-hecho .phase-badge{{color:var(--ok)}}
  .phase-en-curso .phase-badge{{color:var(--warn)}}
  .phase-pendiente .phase-badge{{color:var(--muted)}}

  ul.deliverables{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:6px 24px}}
  ul.deliverables li{{background:var(--surface);border:1px solid var(--hairline);border-radius:8px;
    padding:9px 12px;font-size:13px;color:var(--ink)}}
  ul.deliverables li.pending{{color:var(--muted)}}
  ul.deliverables li .path{{display:block;font-size:11px;color:var(--muted);margin-top:2px}}
  ul.deliverables li.pending em{{color:var(--muted);font-style:normal;font-size:11px}}

  .toolbar{{display:flex;gap:10px;align-items:center;margin-bottom:10px}}
  #filterInput{{flex:1;background:var(--surface);border:1px solid var(--hairline);color:var(--ink);
    border-radius:8px;padding:8px 12px;font-size:13px}}
  #filterInput:focus{{outline:2px solid var(--accent);border-color:var(--accent)}}
  #corpusCount{{color:var(--muted);font-size:12px;white-space:nowrap}}

  table{{border-collapse:collapse;width:100%;font-size:12.5px;background:var(--surface);
    border:1px solid var(--hairline);border-radius:10px;overflow:hidden}}
  thead th{{cursor:pointer;user-select:none;text-align:left;color:var(--muted);
    background:var(--surface-strong);text-transform:uppercase;font-size:10.5px;letter-spacing:.07em;
    padding:9px 10px;border-bottom:1px solid var(--hairline);white-space:nowrap}}
  thead th:hover{{color:var(--ink)}}
  thead th.sorted::after{{content:" " attr(data-arrow)}}
  tbody td{{padding:7px 10px;border-bottom:1px solid var(--hairline);color:var(--body);vertical-align:top}}
  tbody tr:last-child td{{border-bottom:none}}
  tbody tr:hover{{background:var(--surface-soft)}}
  .fam-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}
  .links a{{margin-right:10px;font-size:11.5px}}
  .links .none{{color:var(--muted);font-size:11.5px;margin-right:10px}}
  .term-present{{color:var(--ok)}}
  .term-variant{{color:var(--warn)}}
  .term-absent, .term-check{{color:var(--muted)}}

  form#addForm{{background:var(--surface);border:1px solid var(--hairline);border-radius:10px;
    padding:18px 20px;display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end}}
  form#addForm .field{{display:flex;flex-direction:column;gap:5px;min-width:180px}}
  form#addForm .field.grow{{flex:1;min-width:260px}}
  form#addForm label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}}
  form#addForm input, form#addForm select{{background:var(--surface);border:1px solid var(--hairline);
    color:var(--ink);border-radius:6px;padding:8px 10px;font-size:13px}}
  form#addForm input:focus, form#addForm select:focus{{outline:none;border-color:var(--accent)}}
  form#addForm button{{background:var(--accent);color:#fff;border:none;border-radius:100px;
    padding:10px 22px;font-size:13px;cursor:pointer;font-weight:600}}
  form#addForm button:hover{{background:var(--accent-active)}}
  #staticNote{{display:none;background:var(--surface);border:1px solid var(--hairline);border-radius:10px;
    padding:16px 20px;color:var(--body);font-size:13px}}
  #staticNote code{{background:var(--surface-strong);padding:2px 7px;border-radius:5px;color:var(--ink)}}
  #addResult{{margin-top:14px;font-size:13px;white-space:pre-wrap;background:var(--surface-strong);
    color:var(--ink);border-radius:8px;padding:12px 14px;display:none}}

  footer{{color:var(--muted);font-size:11.5px;margin-top:40px}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>AI for the public good — corpus and analysis</h1>
    <div class="sub">GDS/DSIT 2024-2026 · "AI for the public good" discourse at the Government Digital Service · local project hub</div>
  </header>

  <section id="phases">
    <h2>Phase status</h2>
    <div class="phases">
{render_phases(phases)}
    </div>
  </section>

  <section id="deliverables">
    <h2>Deliverables</h2>
    <ul class="deliverables">
{render_deliverables()}
    </ul>
  </section>

  <section id="corpus">
    <h2>Corpus (<span id="corpusTotal">{len(corpus)}</span> documents)</h2>
    <div class="toolbar">
      <input id="filterInput" type="text" placeholder="Filter by doc_id, date, speaker, genre, family, or term status…">
      <span id="corpusCount"></span>
    </div>
    <div style="overflow-x:auto">
    <table id="corpusTable">
      <thead>
        <tr>
          <th data-key="doc_id">doc_id</th>
          <th data-key="date">date</th>
          <th data-key="speaker">speaker</th>
          <th data-key="genre">genre</th>
          <th data-key="family">family</th>
          <th data-key="term_status">term</th>
          <th data-key="_links">links</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
    </div>
  </section>

  <section id="add-document">
    <h2>Add document</h2>
    <form id="addForm" method="post" action="/add">
      <div class="field grow">
        <label for="url">URL</label>
        <input type="url" id="url" name="url" placeholder="https://www.gov.uk/government/…" required>
      </div>
      <div class="field">
        <label for="family">Family (optional)</label>
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
        <label for="genre">Genre (optional)</label>
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
      <button type="submit">Run admission checklist</button>
    </form>
    <div id="addResult"></div>
    <div id="staticNote">
      This page was opened as a file (<code>file://</code>), so the form cannot POST.
      To add documents from the hub, start the local server:
      <p><code>.venv/bin/python scripts/serve_site.py</code></p>
      and open <code>http://localhost:8765</code>.
    </div>
  </section>

  <footer>Generated by scripts/08_build_site.py · re-runnable and idempotent.</footer>
</div>

<script>
const CORPUS = {corpus_json};
const FAMILY_COLORS = {family_colors_json};

let sortKey = "date", sortDir = 1;

function fmtLinks(row) {{
  const parts = [];
  parts.push(row.url ? `<a href="${{row.url}}" target="_blank" rel="noopener">original</a>` : '<span class="none">original —</span>');
  parts.push(row.archive ? `<a href="${{row.archive}}" target="_blank" rel="noopener">archive</a>` : '<span class="none">archive —</span>');
  parts.push(row.text ? `<a href="${{row.text}}" target="_blank" rel="noopener">text</a>` : '<span class="none">text —</span>');
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

// --- Add document ---
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
    resultBox.textContent = 'Running admission checklist…';
    try {{
      const resp = await fetch('/add', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
        body: params.toString(),
      }});
      const html = await resp.text();
      document.open(); document.write(html); document.close();
    }} catch (e) {{
      resultBox.textContent = 'Error contacting local server: ' + e;
    }}
  }});
}}
</script>
</body>
</html>
"""
    OUT.write_text(html)
    print(f"index.html generated ({len(corpus)} documents, {sum(1 for p in phases if p['status']=='hecho')}/{len(phases)} phases done) -> {OUT}")


if __name__ == "__main__":
    main()
