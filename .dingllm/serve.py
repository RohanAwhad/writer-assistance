"""
Lightweight doc server for .dingllm/ directory.
Renders .md files with marked.js and .mmd files with Mermaid.js (both via CDN).

Usage: python serve.py [--port 8000]
"""

import http.server
import json
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
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; max-width: 1400px; margin: 2rem auto; padding: 0 1rem; color: #1f2328; background: #fff; }}
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
  mermaid.initialize({ startOnLoad: false, theme: 'default' });

  const editor = document.getElementById('mmd-editor');
  const preview = document.getElementById('mmd-preview');
  const status = document.getElementById('save-status');
  let debounceTimer;

  // --- Pan & Zoom state ---
  let viewX = 0, viewY = 0, viewScale = 1;
  let isPanning = false, panStartX = 0, panStartY = 0, panOriginX = 0, panOriginY = 0;

  // --- Node drag state ---
  let dragNode = null, dragStartX = 0, dragStartY = 0, nodeOriginX = 0, nodeOriginY = 0;

  function applyTransform() {
    const svg = preview.querySelector('svg');
    if (!svg) return;
    const g = svg.querySelector('g:first-of-type') || svg.firstElementChild;
    if (!g) return;
    g.style.transform = `translate(${viewX}px, ${viewY}px) scale(${viewScale})`;
    g.style.transformOrigin = '0 0';
  }

  // Zoom with mouse wheel
  preview.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.min(Math.max(viewScale * delta, 0.1), 5);

    // Zoom toward cursor position
    const rect = preview.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    viewX = mx - (mx - viewX) * (newScale / viewScale);
    viewY = my - (my - viewY) * (newScale / viewScale);
    viewScale = newScale;
    applyTransform();
  }, { passive: false });

  // Pan with mouse drag on background
  preview.addEventListener('mousedown', (e) => {
    // If clicking on a node, don't pan — let node drag handle it
    const node = e.target.closest('.node, .nodeGroup');
    if (node) return;
    isPanning = true;
    panStartX = e.clientX;
    panStartY = e.clientY;
    panOriginX = viewX;
    panOriginY = viewY;
    preview.style.cursor = 'grabbing';
  });

  document.addEventListener('mousemove', (e) => {
    if (isPanning) {
      viewX = panOriginX + (e.clientX - panStartX);
      viewY = panOriginY + (e.clientY - panStartY);
      applyTransform();
    }
    if (dragNode) {
      const dx = (e.clientX - dragStartX) / viewScale;
      const dy = (e.clientY - dragStartY) / viewScale;
      dragNode.setAttribute('transform', `translate(${nodeOriginX + dx}, ${nodeOriginY + dy})`);
    }
  });

  document.addEventListener('mouseup', () => {
    isPanning = false;
    preview.style.cursor = '';
    dragNode = null;
  });

  // Drag nodes
  preview.addEventListener('mousedown', (e) => {
    const node = e.target.closest('.node, .nodeGroup');
    if (!node) return;
    e.stopPropagation();
    dragNode = node;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    // Parse existing transform
    const t = node.getAttribute('transform') || 'translate(0,0)';
    const m = t.match(/translate\\(\\s*([-\\d.]+)[,\\s]+([-\\d.]+)\\s*\\)/);
    nodeOriginX = m ? parseFloat(m[1]) : 0;
    nodeOriginY = m ? parseFloat(m[2]) : 0;
  });

  let renderCount = 0;

  async function renderPreview() {
    const src = editor.value;
    preview.innerHTML = '';
    viewX = 0; viewY = 0; viewScale = 1;
    try {
      const id = 'mmd-output-' + (renderCount++);
      const { svg } = await mermaid.render(id, src);
      preview.innerHTML = svg;
      // Remove fixed dimensions so SVG fills container
      const svgEl = preview.querySelector('svg');
      if (svgEl) {
        svgEl.style.maxWidth = 'none';
        svgEl.style.overflow = 'visible';
      }
    } catch (e) {
      preview.innerHTML = '<pre style="color:#cf222e;padding:1rem;">' + e.message + '</pre>';
    }
  }

  editor.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    status.textContent = '';
    debounceTimer = setTimeout(renderPreview, 400);
  });

  // Cmd+S / Ctrl+S to save
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      saveToDisk();
    }
  });

  async function saveToDisk() {
    status.textContent = 'saving...';
    const resp = await fetch(window.location.pathname, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: editor.value,
    });
    if (resp.ok) {
      status.textContent = 'saved';
      setTimeout(() => { status.textContent = ''; }, 2000);
    } else {
      status.textContent = 'save failed!';
    }
  }

  document.getElementById('save-btn').addEventListener('click', saveToDisk);

  // Initial render
  renderPreview();
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
    body = f"""
<div style="display:flex;gap:1rem;height:calc(100vh - 8rem);">
  <div style="flex:1;display:flex;flex-direction:column;min-width:0;">
    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
      <button id="save-btn" style="padding:0.3rem 0.8rem;cursor:pointer;border:1px solid #d1d9e0;border-radius:4px;background:#f6f8fa;">Save</button>
      <span id="save-status" style="font-size:0.85rem;color:#57606a;"></span>
      <span style="font-size:0.75rem;color:#8b949e;margin-left:auto;">Cmd+S to save</span>
    </div>
    <textarea id="mmd-editor" spellcheck="false" style="flex:1;font-family:monospace;font-size:13px;padding:0.75rem;border:1px solid #d1d9e0;border-radius:6px;resize:none;background:#f6f8fa;tab-size:4;">{escaped}</textarea>
  </div>
  <div id="mmd-preview" style="flex:1;overflow:hidden;border:1px solid #d1d9e0;border-radius:6px;padding:1rem;cursor:grab;user-select:none;position:relative;"></div>
</div>"""
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

    def do_POST(self):
        path = unquote(self.path).lstrip("/")
        file_path = ROOT / path

        if not file_path.exists() or file_path.suffix != ".mmd":
            self._respond_json(400, {"error": "can only save .mmd files"})
            return

        # Ensure we're not writing outside ROOT
        if ROOT not in file_path.resolve().parents and file_path.resolve() != ROOT:
            self._respond_json(403, {"error": "forbidden"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        file_path.write_text(body)
        print(f"  saved {file_path.relative_to(ROOT)}")
        self._respond_json(200, {"ok": True})

    def _respond_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

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
