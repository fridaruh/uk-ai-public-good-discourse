"""Renders the repo's .md deliverables into readable, themed HTML pages
(Coinbase light theme, consistent with the rest of the site), so they're
readable in a browser without a Markdown-aware viewer.

Read-only render: never edits the source .md. Re-run any time a .md changes;
output paths mirror the source (PLAN.md -> PLAN.html, dir/x.md -> dir/x.html).
"""
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent

SOURCES = [
    "PLAN.md",
    "README.md",
    "HANDOFF.md",
    "analysis/metaphors_report.md",
    "analysis/qa/communities_vs_families.md",
    "analysis/queries/echo_summary.md",
    "coding/model_eval/decision.md",
]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{
  --canvas:#ffffff; --band:#f7f7f7; --ink:#0a0b0d; --body:#5b616e; --muted:#7c828a;
  --hairline:#dee1e6; --card-fill:#eef0f3; --accent:#0052ff; --accent-active:#003ecc;
}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--canvas);color:var(--ink);
  font:16px/1.7 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}}
.topbar{{background:var(--band);border-bottom:1px solid var(--hairline);padding:12px 24px}}
.topbar a{{color:var(--accent);text-decoration:none;font-size:13px;font-weight:500}}
.topbar a:hover{{color:var(--accent-active)}}
.wrap{{max-width:840px;margin:0 auto;padding:40px 24px 100px}}
h1{{font-size:28px;font-weight:600;margin:0 0 8px;line-height:1.3}}
h2{{font-size:21px;font-weight:600;margin:36px 0 12px;padding-top:8px;border-top:1px solid var(--hairline)}}
h1+h2, h1+p+h2{{border-top:none;padding-top:0}}
h3{{font-size:17px;font-weight:600;margin:24px 0 8px}}
h4{{font-size:14px;font-weight:600;margin:18px 0 6px;color:var(--body)}}
p,li{{color:var(--ink)}}
p{{margin:0 0 14px}}
ul,ol{{margin:0 0 14px;padding-left:24px}}
li{{margin-bottom:4px}}
a{{color:var(--accent);text-decoration:none}}
a:hover{{text-decoration:underline}}
code{{background:var(--card-fill);padding:2px 6px;border-radius:4px;font-size:0.9em;
  font-family:ui-monospace,Menlo,Consolas,monospace}}
pre{{background:var(--card-fill);padding:14px 16px;border-radius:8px;overflow-x:auto;
  font-size:13px;line-height:1.5;margin:0 0 16px}}
pre code{{background:none;padding:0}}
blockquote{{border-left:3px solid var(--accent);margin:0 0 16px;padding:2px 0 2px 16px;
  color:var(--body)}}
hr{{border:none;border-top:1px solid var(--hairline);margin:28px 0}}
table{{border-collapse:collapse;width:100%;margin:0 0 20px;font-size:14px}}
.table-wrap{{overflow-x:auto;margin:0 0 20px}}
.table-wrap table{{margin:0}}
th,td{{border:1px solid var(--hairline);padding:8px 12px;text-align:left;vertical-align:top}}
th{{background:var(--band);font-weight:600;font-size:13px}}
tr:nth-child(even) td{{background:var(--band)}}
.note{{background:var(--card-fill);border-radius:8px;padding:10px 14px;font-size:13px;
  color:var(--body);margin-bottom:28px}}
</style>
</head>
<body>
<div class="topbar"><a href="{home}">&larr; Project hub</a></div>
<div class="wrap">
<div class="note">Rendered from <code>{src}</code> for readability &mdash; this page is
generated, not authored; edit the source file, then re-run
<code>scripts/16_render_markdown.py</code>.</div>
{body}
</div>
</body>
</html>
"""

MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"])


MD_LINK = re.compile(r'href="([^"#]+)\.md(#[^"]*)?"')


def retarget_md_links(html, rendered_rels):
    """Points hrefs at rendered .md files to the sibling .html, leaving links
    to .md files that weren't rendered (e.g. DESIGN.md) untouched."""
    def repl(m):
        path, anchor = m.group(1), m.group(2) or ""
        if (path + ".md") in rendered_rels or path.lstrip("./") + ".md" in rendered_rels:
            return f'href="{path}.html{anchor}"'
        return m.group(0)
    return MD_LINK.sub(repl, html)


def wrap_tables(html):
    out, in_table = [], False
    for line in html.split("\n"):
        if line.strip().startswith("<table>"):
            out.append('<div class="table-wrap">')
            in_table = True
        out.append(line)
        if line.strip().startswith("</table>"):
            out.append("</div>")
            in_table = False
    return "\n".join(out)


def main():
    rendered_rels = {Path(rel).name for rel in SOURCES}
    for rel in SOURCES:
        src = ROOT / rel
        if not src.exists():
            print(f"skip (missing): {rel}")
            continue
        MD.reset()
        body = wrap_tables(retarget_md_links(MD.convert(src.read_text()), rendered_rels))
        title = src.stem.replace("_", " ").title()
        depth = len(Path(rel).parts) - 1
        home = ("../" * depth + "index.html") if depth else "index.html"
        out = src.with_suffix(".html")
        out.write_text(PAGE.format(title=title, body=body, src=rel, home=home))
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
