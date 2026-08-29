"""Fase 7: servidor local del HUB — sirve la raíz del proyecto y maneja el
alta incremental de documentos vía POST /add + POST /add_confirm.

Solo librería estándar (http.server). Uso:

    .venv/bin/python scripts/serve_site.py

→ http://localhost:8765  (index.html, y cualquier archivo del proyecto)

Flujo de alta:
  POST /add          (url, family, genre) → corre el checklist de admisión
                      (equivalente a add_document.py --dry-run) y devuelve una
                      página con el resultado + botón "Confirmar alta".
  POST /add_confirm   (url, family, genre) → corre el alta completa
                      (equivalente a add_document.py --yes) y devuelve el
                      reporte con enlace de vuelta al hub.
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
import add_document  # noqa: E402  (importado tras ajustar sys.path)

HOST, PORT = "localhost", 8765

PAGE_CSS = """
<style>
  :root{--bg:#14161c;--surface:#1a1d24;--ink:#e8ecf3;--ink2:#9aa7bd;--ink3:#6b7689;
    --grid:#232733;--accent:#4590dd;--ok:#52a865;--warn:#c2a33f;--bad:#c25a5a}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
    font:14px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:820px;margin:0 auto;padding:28px 24px 60px}
  h1{font-size:18px;letter-spacing:.03em;text-transform:uppercase;margin:0 0 6px}
  .sub{color:var(--ink2);font-size:13px;margin-bottom:20px;word-break:break-all}
  a{color:var(--accent);text-decoration:none}
  a:hover{text-decoration:underline}
  .back{display:inline-block;margin-top:20px;font-size:13px}
  table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--grid);
    border-radius:10px;overflow:hidden;font-size:13px}
  td,th{padding:9px 12px;border-bottom:1px solid var(--grid);text-align:left;vertical-align:top}
  tr:last-child td{border-bottom:none}
  .status{font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:2px 9px;
    border-radius:12px;white-space:nowrap}
  .status-pass{background:#1c3324;color:var(--ok)}
  .status-fail{background:#3a2020;color:var(--bad)}
  .status-no-determinable{background:#332f1c;color:var(--warn)}
  .detail{color:var(--ink3);font-size:12px}
  .banner{border-radius:10px;padding:12px 16px;margin:14px 0;font-size:13px}
  .banner-ok{background:#1c3324;color:var(--ok);border:1px solid #2b4a34}
  .banner-warn{background:#332f1c;color:var(--warn);border:1px solid #4a4326}
  .banner-bad{background:#3a2020;color:var(--bad);border:1px solid #4d2b2b}
  form{margin-top:18px}
  button{background:var(--accent);color:#fff;border:none;border-radius:6px;
    padding:10px 20px;font-size:13px;cursor:pointer;font-weight:600}
  button:hover{opacity:.9}
  pre{background:#0f1115;border-radius:8px;padding:14px;overflow-x:auto;font-size:12.5px;color:var(--ink2)}
  code{background:#0f1115;padding:2px 7px;border-radius:5px;color:var(--ink)}
</style>
"""


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
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
        banner = (f'<div class="banner banner-bad">{len(fails)} regla(s) en FALLA. '
                   f'Este documento normalmente NO debería admitirse — revisa el checklist '
                   f'antes de confirmar.</div>')
    elif nd:
        banner = (f'<div class="banner banner-warn">Sin fallas duras. {len(nd)} regla(s) '
                   f'no-determinable — revísalas antes de confirmar.</div>')
    else:
        banner = '<div class="banner banner-ok">Sin fallas ni reglas no-determinables.</div>'

    def esc(v):
        return html.escape(v or "")

    body = f"""
    <h1>Checklist de admisión</h1>
    <div class="sub">{esc(url)}</div>
    {banner}
    <table><tbody>{rows}</tbody></table>
    <form method="post" action="/add_confirm">
      <input type="hidden" name="url" value="{esc(url)}">
      <input type="hidden" name="family" value="{esc(family)}">
      <input type="hidden" name="genre" value="{esc(genre)}">
      <button type="submit">Confirmar alta</button>
    </form>
    <a class="back" href="/index.html">&larr; Volver al hub sin confirmar</a>
    """
    return page("Checklist de admisión", body)


def render_report_page(report: dict) -> bytes:
    if not report["ok"]:
        body = f"""
        <h1>Alta fallida</h1>
        <div class="banner banner-bad">{html.escape(report["error"])}</div>
        <a class="back" href="/index.html">&larr; Volver al hub</a>
        """
        return page("Alta fallida", body)

    r = report["manifest_row"]
    if report["recompute_ok"]:
        recompute_banner = ('<div class="banner banner-ok">Red, term_counts.csv e index.html '
                             'recalculados correctamente.</div>')
    else:
        recompute_banner = (f'<div class="banner banner-warn">El documento quedó admitido, pero el '
                             f'recálculo de red/hub falló: {html.escape(report.get("recompute_error",""))}. '
                             f'Corre <code>.venv/bin/python scripts/08_build_site.py</code> a mano.</div>')

    body = f"""
    <h1>Documento admitido</h1>
    <div class="sub">{html.escape(report["doc_id"])}</div>
    <table><tbody>
      <tr><td>fecha</td><td>{html.escape(r["date"])}</td></tr>
      <tr><td>genre</td><td>{html.escape(r["genre"])}</td></tr>
      <tr><td>speaker</td><td>{html.escape(r["speaker"])}</td></tr>
      <tr><td>family</td><td>{html.escape(r["family"])}</td></tr>
      <tr><td>gds_tier</td><td>{html.escape(r["gds_tier"])} (provisional)</td></tr>
      <tr><td>term_status</td><td>{html.escape(r["term_status"])}</td></tr>
      <tr><td>corpus_version</td><td>{report["corpus_version"]}</td></tr>
      <tr><td>bloques / unidades</td><td>{report["n_blocks"]} / {report["n_units"]}</td></tr>
    </tbody></table>
    {recompute_banner}
    <div class="banner banner-warn">Codificación LLM pendiente:
      <code>{html.escape(report["coding_pending_cmd"])}</code></div>
    <a class="back" href="/index.html">&larr; Volver al hub</a>
    """
    return page("Documento admitido", body)


def render_error_page(title: str, exc: Exception) -> bytes:
    body = f"""
    <h1>{html.escape(title)}</h1>
    <div class="banner banner-bad">{html.escape(str(exc))}</div>
    <pre>{html.escape(traceback.format_exc())}</pre>
    <a class="back" href="/index.html">&larr; Volver al hub</a>
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
            self._send_html(page("No encontrado", "<h1>404</h1><p>Ruta no reconocida.</p>"), 404)
            return
        try:
            url, family, genre = self._read_form()
            if not url:
                self._send_html(page("Falta URL", "<h1>Falta la URL</h1>"
                                      "<a class='back' href='/index.html'>&larr; Volver</a>"), 400)
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
            self._send_html(render_error_page("Error procesando la solicitud", exc), 500)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Sirviendo {ROOT} en http://{HOST}:{PORT}  (Ctrl+C para detener)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
