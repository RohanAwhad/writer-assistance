# Build Spec — writer-assistance webapp

- Source of truth: `.hai/state.yaml` (capture commit 4031ecc) — evidence H1..H9, human-approved intents INT-001..004, decisions DEC-001..013.
- Status: draft for review. Version 1.0. Date 2026-09-03.
- Trace legend: every normative requirement is tagged `Trace: DEC-xx[, DEC-yy]`. Items marked `SD-nn` are agent-derived refinements (soft, reviewable, never override a DEC). Items marked `Depends on soft ASM-nn` rest on malleable agent assumptions and are not hard requirements.

## 1. Purpose & scope

A single-user webapp that helps the human write blogs/articles, letters, reports and docs (INT-001). Writing work is organized as **projects** containing read-only Markdown resource trees the human reads and annotates (INT-002). A joint human–AI **reading round** over a chosen set of docs runs AI **expert lenses** whose notes the human reviews, discards, or adopts (possibly modified) into their own notes, and ends in a human-curated **notes dump** (snippets, highlights, human thoughts, AI thoughts) (INT-003). A **button** generates a report from the dump, then the app **shifts to an editor mode** where the report is edited manually paragraph-by-paragraph, with per-block AI options: a tone change producing **5 samples** and an argument **critique/challenge** (INT-004).

**Non-goals** (deliberate exclusions — no human evidence mandates them): authentication, multi-user, teams, sharing, roles; billing/plugins/marketplaces; mobile apps; any editing/deleting/renaming/write-back of resource files; non-Markdown resource types; real-time collaboration; document export pipelines (see OQ-04).

## 2. Normative requirements

### 2.1 Stack and AI client — INT-001

- R-001: Backend is **Python FastAPI**. `Trace: DEC-001`
- R-002: Frontend is **React with shadcn/ui**. `Trace: DEC-002`
- R-003: Database is **SQLite for now**. `Trace: DEC-003`
- R-004: **All AI calls** (lens proposals, expert reads, report generation, tone samples, critiques) go through the **AnthropicVertex client**; credentials come from existing environment variables, not hardcoded config. `Trace: DEC-004` (Reference env var names per RES-001: `ANTHROPIC_VERTEX_PROJECT_ID`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `GOOGLE_VERTEX_LOCATION`, `VERTEX_ACCESS_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_CUSTOM_MODEL_OPTION*`. Depends on soft ASM-005 for the vars being exported in the backend runtime.)
- R-005: The app's output artifact serves the writing kinds blogs/articles, letters, reports and docs. `Trace: INT-001` (No kind-specific templates required — see Non-goals.)

### 2.2 Projects and resources — INT-002

- R-010: A **project** contains a tree of directories/files/sub-directories of **Markdown files**, which act as that project's **resources**. `Trace: DEC-005`
- R-011: Resources are **read-only for the human**: the human reads them and makes notes/highlights; resources themselves are **never edited** by the app or the human through the app. The UI must expose no edit affordance for resource content. `Trace: DEC-005, DEC-006`
- R-012: The human creates **notes** and **highlights** against resources; these annotations are stored separately from the resource files (never written into the files). `Trace: DEC-006`

### 2.3 AI expert lenses and their notes — INT-003

- R-020: The AI **reads the resources** and, per doc, **proposes relevant expert lenses** for that doc — e.g. financial, real-estate, political, software-engineering — as appropriate to content. `Trace: DEC-007`
- R-021: Each chosen lens runs as an **AI expert that keeps its own notes** about the doc(s) it read. Expert notes are stored distinctly from human notes, attributable to (project, reading round, doc, expert). `Trace: DEC-007, DEC-008` (Storage shape: `Depends on soft ASM-002`.)
- R-022: The human can **review expert notes**, **discard them**, or **add them (possibly modified) to the human notes**. Merged items keep provenance of their origin so the dump can still show AI-vs-human authorship where relevant. `Trace: DEC-008` (Review mechanics: `Depends on soft ASM-003`.)

### 2.4 Reading round and curated notes dump — INT-003

- R-030: A **reading round** operates on a **set of docs** the human chooses from the project resources; the human and the AI read that set together (AI's contribution enters via expert notes and AI thoughts). `Trace: DEC-009`
- R-031: The **human curates** the round's output as a **notes dump** that may contain: snippets, highlights, human thoughts, and AI thoughts. Curation means the human selects/orders/composes these items; the dump is persisted per round. `Trace: DEC-009` (Curation UX: `Depends on soft ASM-003`.)

### 2.5 Report generation and mode shift — INT-004

- R-040: A **button** ("Generate report") creates the report **from the curated notes dump** of the round (a single AI call whose input is the dump content). `Trace: DEC-010`
- R-041: The generated report is stored at **paragraph granularity**: the paragraph is the unit **block**. `Trace: DEC-011` (Block storage: `Depends on soft ASM-004`.)
- R-042: **After report creation the app shifts to editor mode**: the reading-round actions (annotating, running experts, curating) are closed/disabled for that report, and the report becomes the editing surface. `Trace: DEC-010, DEC-011`
- R-043: In editor mode the human edits the report **manually, paragraph by paragraph** (block by block); typing is the primary edit path. `Trace: DEC-011`

### 2.6 Per-block AI assistance in editor mode — INT-004

- R-050: Per block, option (a) **change of tone**: the AI generates **5 samples in different tones** for that block, **based on the context of the report** (not the block alone). `Trace: DEC-012`
- R-051: Tone samples only change block content by explicit human action (e.g. preview → apply one sample); the samples themselves never auto-replace text. `Trace: DEC-012, DEC-011`
- R-052: Per block, option (b): the AI **critiques and challenges the argument** of that block so the human can formulate it better. Critique output does not auto-edit the block; the human rewrites manually. `Trace: DEC-013, DEC-011`
- R-053: Both per-block assists use the report context as AI input (target block text plus report context). `Trace: DEC-012, DEC-013`

## 3. Architecture overview

| Choice | Decision | Note |
|---|---|---|
| Python FastAPI backend | DEC-001 | REST API + (prod) static serving of built frontend |
| React + shadcn/ui frontend | DEC-002 | `SD-10`: Vite + Tailwind as the standard shadcn/ui toolchain (agent-derived) |
| SQLite database | DEC-003 | Single file; all entities below persisted |
| AnthropicVertex client for **every** AI call | DEC-004 | One client wrapper module; env-var credentials per RES-001; `Depends on soft ASM-005` |
| Monorepo layout `backend/` + `frontend/` | `Depends on soft ASM-006` | `SD-11`: create at repo root (absent in this workspace copy today) |

**Process/lifecycle model** (`SD-9`, agent-derived): a project has a persisted **stage**: `reading` → (report generated) `editing`. Stage is per-project; entering `editing` gates off reading actions (R-042). No data changes hands between modes except the report itself.

**Concurrency model**: single user, one process; AI calls are HTTP-request-scoped; expert runs within a round may be parallelized (`Depends on soft ASM-002`).

## 4. Data model

Legend: **[M]** = decision-mandated entity/semantics; **[SD]** = agent-derived draft shape (soft, reviewable). All rows persist in SQLite (DEC-003).

| Entity | Semantics | Trace / basis |
|---|---|---|
| `Project` **[M]** | Container of a resource tree + human annotations + rounds; `name`, `stage` (SD-9), timestamps | DEC-005; INT-001 |
| `ResourceNode` **[M]** | Dir/file nodes of the project tree; Markdown files only; each file has content + relative path | DEC-005 |
| `ResourceDoc.content` **[SD]** | Markdown text **snapshot imported into SQLite** when the tree is set up (R-012 read-only guarantee); `Depends on soft ASM-001` flow | DEC-005/006 — see OQ-01 |
| `Annotation` **[M]** | Human-made; two kinds: `highlight` (range/offsets over doc snapshot) and `note` (free text, optional anchor to a highlight/range); authored by human only | DEC-006 |
| `LensProposal` **[SD]** | AI-suggested lens per doc: title, rationale, status (proposed/selected/skipped); human confirms before experts run (SD-3) | DEC-007; `Depends on soft ASM-002` |
| `ExpertRun` **[SD]** | Instance of one lens over one doc within a round; holds its own notes | DEC-007/008; `Depends on soft ASM-002` |
| `ExpertNote` **[M]** | Note text (with optional snippet refs) produced by an `ExpertRun`; distinct from human annotations; review state (pending/accepted/discarded/merged-with-edits) | DEC-008 |
| `ReadingRound` **[SD]** | Human-chosen set of docs; groups the joint reading (R-030); owns expert runs, dump, report | DEC-009 (round is implied by "this round of reading over a set of docs") |
| `NotesDumpEntry` **[M]** | Curated dump item; `kind` ∈ {snippet, highlight, human-thought, ai-thought}; source doc ref; ordering within dump | DEC-009 |
| `NotesDump` **[SD]** | Ordered entry collection, one per round (1:1 with report per round — see OQ-02) | DEC-009; `Depends on soft ASM-003` |
| `Report` **[M]** | Generated artifact from one dump; belongs to the round/project | DEC-010 |
| `ReportBlock` **[M]** | One paragraph of the report; `content`, `position`; editable manually; optional links back to source dump entries/docs | DEC-011; block links `Depends on soft ASM-004` |
| `ToneSampleSet` **[SD]** | Result of a tone request: exactly 5 samples with tone labels + target block; **transient** (regenerated per request; not persisted) | DEC-012 (SD-7) |
| `CritiqueResult` **[SD]** | Result of a critique request for a block; **transient** | DEC-013 (SD-8) |

Cardinalities **[SD]**: Project 1—N ResourceDoc · Project 1—N Round · Round N—N ResourceDoc (the doc set) · Round 1—1 NotesDump · Round 1—N ExpertRun (per doc×lens) · ExpertRun 1—N ExpertNote · NotesDump 1—N Entry · Round 0..1—1 Report · Report 1—N ReportBlock · ReportBlock N—N NotesDumpEntry (soft link, ASM-004).

## 5. User flows

- **F1 — Set up project** (R-010, R-011): create project → import/scan its Markdown tree (SD-1, `Depends on soft ASM-001`) → resources appear read-only. `Trace: DEC-005, DEC-006`
- **F2 — Read & annotate** (R-011, R-012): open a resource in a rendered Markdown view (SD-2); select text to highlight; attach notes; nothing writes back to the file. `Trace: DEC-006`
- **F3 — Lens proposal** (R-020): human asks AI for lenses on a doc; proposals listed per doc; human confirms which to run (SD-3). `Trace: DEC-007`
- **F4 — Expert runs** (R-021): AI experts (one per doc×lens) read the docs and produce their own notes. `Trace: DEC-007, DEC-008`
- **F5 — Expert note review** (R-022): review list per expert with actions: keep / discard / edit-and-add-to-human-notes (provenance preserved) (SD-4). `Trace: DEC-008`
- **F6 — Round curation** (R-030, R-031): human picks the doc set for the round, then curates the notes dump — composing ordered entries of snippets, highlights, own thoughts, and AI thoughts (SD-5). `Trace: DEC-009`
- **F7 — Generate report** (R-040): "Generate report" button → backend calls the AI with the dump → report created as ordered paragraphs. `Trace: DEC-010`
- **F8 — Mode shift** (R-042): project enters editor mode; reading actions disabled. `Trace: DEC-010, DEC-011`
- **F9 — Manual editing** (R-043): blocks edited by typing, paragraph by paragraph. `Trace: DEC-011`
- **F10 — Per-block tone** (R-050..R-051): on a block, "Change of tone" → 5 samples in different tones (AI-chosen tone labels, SD-7) using report context; preview and optionally apply one. `Trace: DEC-012`
- **F11 — Per-block critique** (R-052..R-053): on a block, "Critique" → AI challenges the argument using report context; human rewrites based on it; repeatable (SD-8). `Trace: DEC-013`

## 6. API surface sketch — DRAFT (backend endpoints the UI needs; shapes not final)

All under `/api/v1`, JSON, single-user (no auth). Sketched per flow; final shape left to implementation.

- `POST /projects`, `GET /projects`, `GET /projects/{id}` — project CRUD (F1)
- `POST /projects/{id}/scan` — import resource tree snapshot (F1, SD-1)
- `GET /projects/{id}/tree`, `GET /resources/{id}` (content) (F1, F2)
- `POST /resources/{id}/highlights` | `POST /resources/{id}/notes` | `PUT/DELETE /annotations/{id}` (F2)
- `POST /resources/{id}/lens-proposals` — AI proposes lenses (F3)
- `POST /rounds` — create round with doc set; `GET /rounds/{id}` (F6)
- `POST /rounds/{id}/experts` (run confirmed lenses), `GET /expert-runs/{id}/notes`, `PATCH /expert-notes/{id}` (review state), `POST /expert-notes/{id}/merge` (F4, F5)
- `POST /rounds/{id}/dump` (save curated ordered entries), `GET /rounds/{id}/dump` (F6)
- `POST /rounds/{id}/generate-report` — returns report + blocks; flips project stage (F7, F8)
- `GET /reports/{id}` (blocks), `PUT /blocks/{id}` (manual edit) (F9)
- `POST /blocks/{id}/tone-samples` — returns 5 samples given report context (F10)
- `POST /blocks/{id}/critique` — returns critique given report context (F11)

## 7. Assumptions table

| ID | Wording used in spec | Status | Referenced by |
|---|---|---|---|
| ASM-001 | Reading UI is a multi-stage flow (browse, read/annotate, run experts, review) | depended-on (soft) | F1..F6, §4 |
| ASM-002 | Experts = parallel structured LLM calls, one lens each, notes stored per project/resource/expert | depended-on (soft) | R-021, §3, F3/F4, OQ-06 |
| ASM-003 | Expert-note review = list UI with accept/reject/edit merging into human notes | depended-on (soft) | R-022, R-031, F5/F6 |
| ASM-004 | Report stored at paragraph (block) granularity with links to source notes/resources | depended-on (soft) | R-041, §4, F9 |
| ASM-005 | AnthropicVertex env vars valid in the backend runtime | depended-on (soft) | R-004, §3 |
| ASM-006 | `backend/` and `frontend/` dirs are the scaffolding locations | depended-on (soft) | §3 (dirs to be created in this workspace) |

## 8. Assumption log

No revisions made. All six assumptions are used as worded in `.hai/state.yaml`; none conflicted with the decisions or with each other, and the spec's agent-derived details were written to stay consistent with them.

## 9. Open questions (for the human)

- **OQ-01 — Resource storage**: spec default (SD-1) snapshots Markdown content into SQLite at scan time (stable anchors for highlights, strong read-only guarantee). Alternative: reference files on disk live. Would change the data model (§4).
- **OQ-02 — Rounds/reports per project**: spec default is multiple rounds per project, each with one dump and one report; the stage shift (R-042) applies after a report exists. If only one report ever exists per project, the model can shrink.
- **OQ-03 — Curation semantics**: spec default (SD-5) is an ordered-entry editor fed by per-doc pools (human notes, accepted expert notes, highlights/snippets). If curation is meant as a free-form scratchpad instead, F6 and the dump API change.
- **OQ-04 — Export**: is getting the final report out of the app (copy to clipboard / download as Markdown) in scope for v1?
- **OQ-05 — Regeneration**: after mode shift, may the human regenerate the report (replacing blocks) or is generation one-shot per round? Editing work would be lost on regenerate.
- **OQ-06 — Lens control**: spec default is AI-proposed lenses only, human confirms before running (per ASM-002). Should the human also be able to define custom lenses by hand in v1?
