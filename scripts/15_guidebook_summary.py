"""Generates analysis/guidebook_summary.html: a navigable, reviewable view of
coding/guidebook_draft.yaml (Phase 5 candidate sub-codes) and the top of
analysis/metaphors_report.md, for the author to review before naming the
final codebook. Pure Python; safe to re-run any time the draft changes.
"""
import html
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GB = yaml.safe_load((ROOT / "coding" / "guidebook_draft.yaml").read_text())
OUT = ROOT / "analysis" / "guidebook_summary.html"

QUESTION_THEORY = {
    "BENEFICIARY": "Gee (2014), subject tool",
    "MECHANISM": "Gee (2014), fill-in tool",
    "SAFEGUARD": "Gee (2014), fill-in tool",
    "RESPONSIBILITY": "Gee (2014), subject tool",
    "PROJECTED_FUTURE": "Jasanoff & Kim (2015)",
    "ACTANTS": "Kaplan (2020)",
    "NATURALISED_ORDER": "Lears (1985); Gee (2014)",
}


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def parse_metaphors_top(md_text, n=15):
    blocks = re.split(r"\n### \d+\. ", md_text)[1:]
    items = []
    for b in blocks[:n]:
        title_m = re.match(r'"([^"]+)"\s*\(n=(\d+)\)', b)
        if not title_m:
            continue
        expr, count = title_m.group(1), title_m.group(2)

        def field(label):
            m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", b)
            return m.group(1).strip() if m else ""

        items.append({
            "expr": expr, "count": count,
            "formula": field("Suggested formula"),
            "source": field("Suggested source domain"),
            "target": field("Suggested target domain"),
            "highlights": field("What it highlights"),
            "hides": field("What it hides"),
        })
    return items


def main():
    q_stats = {q: {"n_applies_true": d["n_applies_true"], "n_clusters": len(d["clusters"])}
               for q, d in GB["questions"].items()}
    total_instances = sum(s["n_applies_true"] for s in q_stats.values())
    total_clusters = sum(s["n_clusters"] for s in q_stats.values())

    metaphors_path = ROOT / "analysis" / "metaphors_report.md"
    metaphors = parse_metaphors_top(metaphors_path.read_text()) if metaphors_path.exists() else []

    nav_items = "".join(
        f'<a href="#{q.lower()}" class="navlink">{esc(q.replace("_", " ").title())}'
        f'<span class="navcount">{d["n_clusters"]}</span></a>'
        for q, d in GB["questions"].items())

    sections = []
    for q, data in GB["questions"].items():
        clusters = sorted(data["clusters"], key=lambda c: -c["n_instances"])
        ratio = len(clusters) / max(data["n_applies_true"], 1)
        granular_flag = (
            '<span class="badge badge-warn">Low merge rate '
            f'({len(clusters)} clusters / {data["n_applies_true"]} instances) '
            '&mdash; likely needs manual grouping, not just a name</span>'
            if ratio > 0.4 else ""
        )
        cards = []
        for c in clusters:
            quotes = "".join(f'<li>&ldquo;{esc(qt)}&rdquo;</li>' for qt in c.get("example_quotes", [])[:3])
            cards.append(f'''
    <div class="cluster-card">
      <div class="cluster-head">
        <span class="cluster-name">{esc(c["candidate_name"])}</span>
        <span class="cluster-n">{c["n_instances"]} instance{"s" if c["n_instances"] != 1 else ""}</span>
      </div>
      <ul class="quotes">{quotes}</ul>
      <div class="rename-row">
        <label>Final name: <input type="text" class="rename-input" placeholder="{esc(c["candidate_name"])}"
          data-question="{esc(q)}" data-draft="{esc(c["candidate_name"])}"></label>
      </div>
    </div>''')
        sections.append(f'''
<section id="{q.lower()}" class="qsection">
  <h2>{esc(q.replace("_", " ").title())}
    <span class="theory">{esc(QUESTION_THEORY.get(q, ""))}</span></h2>
  <p class="qmeta">{data["n_applies_true"]} coded instances &middot; {len(clusters)} candidate clusters</p>
  {granular_flag}
  <div class="cluster-grid">{"".join(cards)}</div>
</section>''')

    metaphor_cards = "".join(f'''
    <div class="cluster-card">
      <div class="cluster-head">
        <span class="cluster-name">&ldquo;{esc(m["expr"])}&rdquo;</span>
        <span class="cluster-n">n={esc(m["count"])}</span>
      </div>
      <p class="mformula">{esc(m["formula"])}</p>
      <p class="mdomains"><b>Source:</b> {esc(m["source"])} &nbsp;&rarr;&nbsp; <b>Target:</b> {esc(m["target"])}</p>
      <p class="mhh"><b>Highlights:</b> {esc(m["highlights"])}</p>
      <p class="mhh"><b>Hides:</b> {esc(m["hides"])}</p>
    </div>''' for m in metaphors)

    html_out = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guidebook review — corpus v1</title>
<style>
:root{{
  --canvas:#ffffff; --band:#f7f7f7; --card:#ffffff; --card-fill:#eef0f3;
  --ink:#0a0b0d; --body:#5b616e; --muted:#7c828a; --hairline:#dee1e6;
  --accent:#0052ff; --accent-active:#003ecc; --warn-bg:#fff4e0; --warn-ink:#7a4a00;
}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--canvas);color:var(--ink);
  font:15px/1.55 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 24px 80px;display:grid;
  grid-template-columns:220px 1fr;gap:32px}}
header{{grid-column:1/-1}}
h1{{font-size:22px;font-weight:600;margin:0 0 4px}}
.sub{{color:var(--body);font-size:14px;margin:0 0 20px}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px}}
.stat{{background:var(--card-fill);border-radius:8px;padding:10px 16px}}
.stat b{{display:block;font-size:20px;font-weight:600}}
.stat span{{font-size:12px;color:var(--muted)}}
nav{{position:sticky;top:20px;align-self:start;font-size:13px}}
.navlink{{display:flex;justify-content:space-between;padding:6px 10px;border-radius:6px;
  color:var(--body);text-decoration:none;margin-bottom:2px}}
.navlink:hover{{background:var(--band);color:var(--ink)}}
.navcount{{color:var(--muted)}}
main{{min-width:0}}
.qsection{{border-top:1px solid var(--hairline);padding:28px 0}}
.qsection:first-child{{border-top:none;padding-top:0}}
h2{{font-size:18px;font-weight:600;margin:0 0 2px;display:flex;align-items:baseline;gap:10px}}
.theory{{font-size:12px;font-weight:400;color:var(--muted)}}
.qmeta{{font-size:13px;color:var(--body);margin:0 0 10px}}
.badge-warn{{display:inline-block;background:var(--warn-bg);color:var(--warn-ink);
  font-size:12px;padding:4px 10px;border-radius:6px;margin-bottom:12px}}
.cluster-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.cluster-card{{background:var(--card);border:1px solid var(--hairline);border-radius:10px;padding:14px}}
.cluster-head{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;gap:8px}}
.cluster-name{{font-weight:600;font-size:14px;font-family:ui-monospace,Menlo,monospace}}
.cluster-n{{font-size:12px;color:var(--muted);white-space:nowrap}}
.quotes{{margin:0 0 10px;padding-left:18px;font-size:13px;color:var(--body)}}
.quotes li{{margin-bottom:4px}}
.rename-row{{border-top:1px solid var(--hairline);padding-top:8px}}
.rename-row label{{font-size:12px;color:var(--muted);display:flex;flex-direction:column;gap:4px}}
.rename-input{{border:1px solid var(--hairline);border-radius:6px;padding:6px 8px;font-size:13px;
  font-family:ui-monospace,Menlo,monospace;color:var(--ink)}}
.rename-input:focus{{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}}
.mformula{{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:var(--accent-active);margin:0 0 6px}}
.mdomains,.mhh{{font-size:13px;color:var(--body);margin:0 0 4px}}
#export-bar{{position:sticky;bottom:0;background:var(--canvas);border-top:1px solid var(--hairline);
  padding:12px 0;margin-top:20px;display:flex;gap:10px;align-items:center}}
button{{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:9px 16px;
  font-size:13px;font-weight:500;cursor:pointer}}
button:hover{{background:var(--accent-active)}}
#export-note{{font-size:12px;color:var(--muted)}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Guidebook review — Phase 5 candidate sub-codes</h1>
  <p class="sub">Auto-clustered by cosine similarity (embeddinggemma, threshold 0.75) from
    {total_instances} coded Round 1 instances into {total_clusters} candidate clusters.
    <b>These are suggestions.</b> Type the final name in each box, then use
    &ldquo;Export renamed guidebook&rdquo; to download a starting <code>guidebook.yaml</code> —
    still to be reviewed, merged, split and documented by the author before it is final.</p>
  <div class="stats">
    {"".join(f'<div class="stat"><b>{esc(s["n_clusters"])}</b><span>{esc(q.replace("_"," ").title())}</span></div>' for q, s in q_stats.items())}
  </div>
</header>
<nav>{nav_items}
  <a href="#metaphors" class="navlink">Top metaphors<span class="navcount">{len(metaphors)}</span></a>
</nav>
<main>
{"".join(sections)}
<section id="metaphors" class="qsection">
  <h2>Top metaphors <span class="theory">Lakoff &amp; Johnson (1980)</span></h2>
  <p class="qmeta">Most frequent of 388 distinct expressions &mdash; see the full
    <a href="metaphors_report.md">metaphors_report.md</a> for all of them.</p>
  <div class="cluster-grid">{metaphor_cards}</div>
</section>
<div id="export-bar">
  <button onclick="exportYaml()">Export renamed guidebook &darr;</button>
  <span id="export-note">Downloads guidebook.yaml with your typed names (blank = keep the draft name)</span>
</div>
</main>
</div>
<script>
function exportYaml(){{
  const inputs = document.querySelectorAll('.rename-input');
  const byQ = {{}};
  inputs.forEach(inp => {{
    const q = inp.dataset.question, draft = inp.dataset.draft;
    const final = inp.value.trim() || draft;
    (byQ[q] = byQ[q] || []).push({{draft, final}});
  }});
  let yaml = "# Author-renamed guidebook (starting point) -- generated from guidebook_summary.html\\n";
  yaml += "# Review, merge, split and add inclusion/exclusion rules before treating as final.\\n";
  for (const [q, pairs] of Object.entries(byQ)) {{
    yaml += `${{q}}:\\n`;
    pairs.forEach(p => {{ yaml += `  - draft_name: ${{p.draft}}\\n    final_name: ${{p.final}}\\n`; }});
  }}
  const blob = new Blob([yaml], {{type:'text/yaml'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'guidebook_renamed.yaml'; a.click();
}}
</script>
</body>
</html>'''
    OUT.write_text(html_out)
    print(f"Wrote {OUT} ({total_clusters} clusters across {len(q_stats)} questions, "
          f"{len(metaphors)} metaphors)")


if __name__ == "__main__":
    main()
