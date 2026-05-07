# Writer's Desk - Development Log

## 2026-05-06 — Initial Build (v1)

### What was built
Full-stack writing assistance webapp: "Writer's Desk"

**Backend** (Python FastAPI + SQLite):
- `backend/app/db.py` — SQLite schema + async CRUD helpers (projects, resources, lenses, notes, reports, report_blocks)
- `backend/app/ai.py` — AnthropicVertex integration (Claude Sonnet 4.5) for:
  - Lens generation (3-5 expert perspectives per document)
  - Lens notes (3-7 observations per perspective)
  - Report synthesis from accumulated notes
  - Tone variations (5 tones per paragraph)
  - Argument critique (critique + suggestions + probing questions)
- `backend/app/main.py` — FastAPI app with full REST API (projects, resources, lenses, notes, reports CRUD + AI endpoints)

**Frontend** (React + TypeScript + Vite + shadcn UI base-nova + Tailwind v4):
- `src/lib/api.ts` — Type-safe API client
- `src/pages/ProjectsPage.tsx` — Project listing + creation
- `src/pages/ProjectWorkspace.tsx` — 3-panel workspace (resources, document viewer + AI lenses, notes)
- `src/pages/ReportEditor.tsx` — Editable report blocks with tone variations + argument challenge

### Key decisions
- **AnthropicVertex** with `region='global'` and model `claude-sonnet-4-5@20250929`
- **shadcn base-nova** style (supports xs/icon-xs/icon-sm sizes, CardAction, DialogFooter showCloseButton)
- **Vite proxy** to backend at `/api` — no CORS issues in dev
- AI functions are synchronous (blocking) — adequate for single-user app

### Gotchas
- AnthropicVertex requires `requests` package alongside `google-auth`
- Model ID format for Vertex is `claude-sonnet-4-5@20250929` (with @), not `claude-sonnet-4-5-20250929` (with -)
- Region must be `global`, not `us-east5` for this project

### How to run
```bash
./run.sh
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

### Sample docs
`sample_docs/` contains housing market and remote work articles for testing.

## 2026-05-06 — Fix upload UX + markdown viewer (v1.1)

### Changes
- **Upload UX**: Added drag-and-drop support on left panel + click-to-upload empty state (no more broken popup)
- **Markdown viewer**: Custom CSS prose styles (`.markdown-body` in index.css) replacing `@tailwindcss/typography` which has no Tailwind v4 compatible version. Styles: headings with proper hierarchy, h2 border-bottom, code blocks, blockquotes, tables, links, selection highlight color.
- **Text selection popup**: New `SelectionPopup` component — select text in the markdown viewer → popup appears with "Add as Note" button → opens dialog with the highlighted quote pre-filled
- **Scrolling fix**: Center panel markdown reader uses native `overflow-y-auto` instead of radix/base-ui ScrollArea (which didn't scroll properly in flex layout)
- **Note highlight support**: API client now passes `highlight` field when creating notes from text selection

### Gotchas
- `@tailwindcss/typography` v0.5.x is NOT compatible with Tailwind v4 — no v4 version exists yet, must write prose styles manually
- base-ui `ScrollArea` doesn't work well in flex layouts for scrollable content — use native overflow instead

### What's next
- Authentication (multi-user)
- File/directory tree view for resources
- Report export (PDF, docx)
- History/versioning for reports
