"""
Lightweight doc server for .dingllm/ directory.
Renders .md files with marked.js and .mmd files with Mermaid.js (both via CDN).

Usage: python serve.py [--port 8000]
"""

import http.server
import os
import argparse
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).parent

HTML_SHELL = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #1f2328; background: #fff; }}
  a {{ color: #0969da; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  pre {{ background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
  code {{ background: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-size: 85%; }}
  pre code {{ background: none; padding: 0; }}
  .nav {{ margin-bottom: 1.5rem; padding-bottom: 0.5rem; border-bottom: 1px solid #d1d9e0; }}
  .file-list {{ list-style: none; padding: 0; }}
  .file-list li {{ padding: 0.4rem 0; }}
  .file-list .dir {{ font-weight: 600; margin-top: 1rem; }}
  .mermaid {{ display: flex; justify-content: center; margin: 2rem 0; }}
  table {{ border-collapse: collapse; }}
  th, td {{ border: 1px solid #d1d9e0; padding: 0.5rem 1rem; }}
</style>
</head><body>
<div class="nav"><a href="/">index</a></div>
{body}
{scripts}
</body></html>"""

MARKED_SCRIPTS = """
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
  const src = document.getElementById('md-source').textContent;
  document.getElementById('content').innerHTML = marked.parse(src);
</script>
"""

MERMAID_SCRIPTS = """
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true, theme: 'default' });
</script>
"""


def collect_files():
    """Walk ROOT and return a dict of {relative_dir: [filenames]} for .md and .mmd files."""
    tree = {}
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in (".md", ".mmd"):
            continue
        if path.name == "serve.py":
            continue
        rel = path.relative_to(ROOT)
        parent = str(rel.parent) if rel.parent != Path(".") else ""
        tree.setdefault(parent, []).append(rel)
    return tree


def render_index():
    tree = collect_files()
    items = []
    for dir_name in sorted(tree.keys()):
        if dir_name:
            items.append(f'<li class="dir">{dir_name}/</li>')
        for rel_path in sorted(tree[dir_name]):
            suffix_label = "mermaid" if rel_path.suffix == ".mmd" else "md"
            items.append(f'<li><a href="/{rel_path}">{rel_path.name}</a> <small>({suffix_label})</small></li>')
    body = "<h1>.dingllm docs</h1>\n<ul class='file-list'>\n" + "\n".join(items) + "\n</ul>"
    return HTML_SHELL.format(title=".dingllm", body=body, scripts="")


def render_md(path: Path):
    content = path.read_text()
    # Escape for embedding in a hidden <script> tag
    escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = f'<script type="text/plain" id="md-source">{escaped}</script>\n<div id="content"></div>'
    return HTML_SHELL.format(title=path.name, body=body, scripts=MARKED_SCRIPTS)


def render_mmd(path: Path):
    content = path.read_text()
    escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = f'<pre class="mermaid">\n{escaped}\n</pre>'
    return HTML_SHELL.format(title=path.name, body=body, scripts=MERMAID_SCRIPTS)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(self.path).lstrip("/")

        if path == "" or path == "/":
            self._respond(200, render_index())
            return

        file_path = ROOT / path
        if not file_path.exists() or not file_path.is_file():
            self._respond(404, HTML_SHELL.format(title="404", body="<h1>404</h1><p>Not found.</p>", scripts=""))
            return

        if file_path.suffix == ".md":
            self._respond(200, render_md(file_path))
        elif file_path.suffix == ".mmd":
            self._respond(200, render_mmd(file_path))
        elif file_path.suffix == ".png":
            self._respond_binary(200, file_path.read_bytes(), "image/png")
        else:
            self._respond(404, HTML_SHELL.format(title="404", body="<h1>404</h1><p>Unsupported file type.</p>", scripts=""))

    def _respond(self, code, html):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _respond_binary(self, code, data, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        print(f"  {args[0]}")


def main():
    parser = argparse.ArgumentParser(description="Serve .dingllm docs")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = http.server.HTTPServer(("", args.port), Handler)
    print(f"Serving .dingllm at http://localhost:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
