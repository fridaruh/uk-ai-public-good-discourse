"""Phase 7: local HUB server — serves the project root and handles
incremental document intake via POST /add + POST /add_confirm.

Standard library only (http.server). Usage:

    .venv/bin/python scripts/serve_site.py

→ http://localhost:8765  (index.html, and any file in the project)

Intake flow:
  POST /add          (url, family, genre) → runs the admission checklist
                      (equivalent to add_document.py --dry-run) and returns a
                      page with the result + a "Confirm intake" button.
  POST /add_confirm   (url, family, genre) → runs the full intake
                      (equivalent to add_document.py --yes) and returns the
                      report with a link back to the hub.
"""
from __future__ import annotations

import html
import sys
import traceback
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import add_document  # noqa: E402  (imported after adjusting sys.path)

HOST, PORT = "localhost", 8765

PAGE_CSS = """
<style>
  :root{--bg:#ffffff;--surface:#ffffff;--surface-soft:#f7f7f7;--surface-strong:#eef0f3;
    --ink:#0a0b0d;--body:#5b616e;--muted:#7c828a;
    --hairline:#dee1e6;--accent:#0052ff;--accent-active:#003ecc;
    --ok:#05b169;--warn:#a87700;--bad:#cf202f}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--body);
    font:14px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:820px;margin:0 auto;padding:28px 24px 60px}
  h1{font-size:18px;font-weight:600;letter-spacing:.03em;text-transform:uppercase;margin:0 0 6px;color:var(--ink)}
  .sub{color:var(--muted);font-size:13px;margin-bottom:20px;word-break:break-all}
  a, a:visited{color:var(--accent);text-decoration:none}
  a:hover{color:var(--accent-active);text-decoration:underline}
  .back{display:inline-block;margin-top:20px;font-size:13px}
  table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--hairline);
    border-radius:10px;overflow:hidden;font-size:13px}
  td,th{padding:9px 12px;border-bottom:1px solid var(--hairline);text-align:left;vertical-align:top;color:var(--body)}
  tr:last-child td{border-bottom:none}
  .status{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:2px 9px;
    border-radius:12px;white-space:nowrap}
  .status-pass{background:var(--surface-strong);color:var(--ok)}
  .status-fail{background:transparent;color:var(--bad);padding-left:0}
  .status-no-determinable{background:var(--surface-strong);color:var(--warn)}
  .detail{color:var(--muted);font-size:12px}
  .banner{border-radius:8px;padding:12px 16px;margin:14px 0;font-size:13px;
    background:var(--surface-soft);border-left:4px solid transparent}
  .banner-ok{border-left-color:var(--ok);color:var(--ink)}
  .banner-warn{border-left-color:var(--warn);color:var(--ink)}
  .banner-bad{border-left-color:var(--bad);color:var(--bad)}
  form{margin-top:18px}
  button{background:var(--accent);color:#fff;border:none;border-radius:100px;
    padding:10px 22px;font-size:13px;cursor:pointer;font-weight:600}
  button:hover{background:var(--accent-active)}
  pre{background:var(--surface-strong);border-radius:8px;padding:14px;overflow-x:auto;font-size:12.5px;color:var(--body)}
  code{background:var(--surface-strong);padding:2px 7px;border-radius:5px;color:var(--ink)}
</style>
"""


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>{PAGE_CSS}</head>
<body><div class="wrap">{body}</div></body></html>""".encode("utf-8")


def render_checklist_page(url, family, genre, result) -> bytes:
    fails = [r for r in result["rules"] if r["status"] == "fail"]
    nd = [r for r in result["rules"] if r["status"] == "no-determinable"]
    rows = "".join(
        f'<tr><td><span class="status status-{r["status"]}">{r["status"]}</span></td>'
        f'<td>{html.escape(r["rule"])}<div class="detail">{html.escape(r["detail"])}</div></td></tr>'
        for r in result["rules"]
    )
    if fails:
        banner = (f'<div class="banner banner-bad">{len(fails)} rule(s) FAILED. '
                   f'This document would not normally be admitted — review the checklist '
                   f'before confirming.</div>')
    elif nd:
        banner = (f'<div class="banner banner-warn">No hard failures. {len(nd)} rule(s) '
                   f'not determinable — review them before confirming.</div>')
    else:
        banner = '<div class="banner banner-ok">No failures and no undetermined rules.</div>'

    def esc(v):
        return html.escape(v or "")

    body = f"""
    <h1>Admission checklist</h1>
    <div class="sub">{esc(url)}</div>
    {banner}
    <table><tbody>{rows}</tbody></table>
    <form method="post" action="/add_confirm">
      <input type="hidden" name="url" value="{esc(url)}">
      <input type="hidden" name="family" value="{esc(family)}">
      <input type="hidden" name="genre" value="{esc(genre)}">
      <button type="submit">Confirm intake</button>
    </form>
    <a class="back" href="/index.html">&larr; Back to hub without confirming</a>
    """
    return page("Admission checklist", body)


def render_report_page(report: dict) -> bytes:
    if not report["ok"]:
        body = f"""
        <h1>Intake failed</h1>
        <div class="banner banner-bad">{html.escape(report["error"])}</div>
        <a class="back" href="/index.html">&larr; Back to hub</a>
        """
        return page("Intake failed", body)

    r = report["manifest_row"]
    if report["recompute_ok"]:
        recompute_banner = ('<div class="banner banner-ok">Network, term_counts.csv, and index.html '
                             'recalculated successfully.</div>')
    else:
        recompute_banner = (f'<div class="banner banner-warn">The document was admitted, but the '
                             f'network/hub recalculation failed: {html.escape(report.get("recompute_error",""))}. '
                             f'Run <code>.venv/bin/python scripts/08_build_site.py</code> manually.</div>')

    body = f"""
    <h1>Document admitted</h1>
    <div class="sub">{html.escape(report["doc_id"])}</div>
    <table><tbody>
      <tr><td>date</td><td>{html.escape(r["date"])}</td></tr>
      <tr><td>genre</td><td>{html.escape(r["genre"])}</td></tr>
      <tr><td>speaker</td><td>{html.escape(r["speaker"])}</td></tr>
      <tr><td>family</td><td>{html.escape(r["family"])}</td></tr>
      <tr><td>gds_tier</td><td>{html.escape(r["gds_tier"])} (provisional)</td></tr>
      <tr><td>term_status</td><td>{html.escape(r["term_status"])}</td></tr>
      <tr><td>corpus_version</td><td>{report["corpus_version"]}</td></tr>
      <tr><td>blocks / units</td><td>{report["n_blocks"]} / {report["n_units"]}</td></tr>
    </tbody></table>
    {recompute_banner}
    <div class="banner banner-warn">LLM coding pending:
      <code>{html.escape(report["coding_pending_cmd"])}</code></div>
    <a class="back" href="/index.html">&larr; Back to hub</a>
    """
    return page("Document admitted", body)


def render_error_page(title: str, exc: Exception) -> bytes:
    body = f"""
    <h1>{html.escape(title)}</h1>
    <div class="banner banner-bad">{html.escape(str(exc))}</div>
    <pre>{html.escape(traceback.format_exc())}</pre>
    <a class="back" href="/index.html">&larr; Back to hub</a>
    """
    return page(title, body)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _read_form(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        parsed = parse_qs(raw)
        get1 = lambda k: (parsed.get(k) or [""])[0].strip()
        return get1("url"), get1("family") or None, get1("genre") or None

    def _send_html(self, content: bytes, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path not in ("/add", "/add_confirm"):
            self._send_html(page("Not found", "<h1>404</h1><p>Unrecognized route.</p>"), 404)
            return
        try:
            url, family, genre = self._read_form()
            if not url:
                self._send_html(page("Missing URL", "<h1>Missing URL</h1>"
                                      "<a class='back' href='/index.html'>&larr; Back</a>"), 400)
                return
            import requests
            session = requests.Session()
            result = add_document.run_checklist(url, session)

            if self.path == "/add":
                self._send_html(render_checklist_page(url, family, genre, result))
            else:  # /add_confirm
                report = add_document.admit_document(url, family, genre, result, session)
                self._send_html(render_report_page(report))
        except Exception as exc:  # noqa: BLE001
            self._send_html(render_error_page("Error processing the request", exc), 500)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving {ROOT} at http://{HOST}:{PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
