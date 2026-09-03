# Build Spec — writer-assistance webapp

- Source of truth: `.hai/state.yaml` (capture commit 4031ecc) — evidence H1..H9, human-approved intents INT-001..004, decisions DEC-001..013.
- Status: human-resolved draft v1.2. Date 2026-09-03. Version 1.2.
- Trace legend: every normative requirement is tagged `Trace: DEC-xx[, DEC-yy]`. Items marked `SD-nn` are agent-derived refinements (soft, reviewable, never override a DEC). Items marked `Depends on soft ASM-nn` rest on malleable agent assumptions and are not hard requirements.

## 1. Purpose & scope

A single-user webapp that helps the human write blogs/articles, letters, reports and docs (INT-001). Writing work is organized as **projects** containing read-only Markdown resource trees the human reads and annotates (INT-002). A joint human–AI **reading round** over a chosen set of docs runs AI **expert lenses** whose notes the human reviews, discards, or adopts (possibly modified) into their own notes, and ends in a human-curated **notes dump** (snippets, highlights, human thoughts, AI thoughts) (INT-003). A **button** generates a report from the dump, then the app **shifts to an editor mode** where the report is edited manually paragraph-by-paragraph, with per-block AI options: a tone change producing **5 samples** and an argument **critique/challenge** (INT-004).

**Non-goals** (deliberate exclusions — no human evidence mandates them): authentication, multi-user, teams, sharing, roles; billing/plugins/marketplaces; mobile apps; any editing/deleting/renaming/write-back of resource files; non-Markdown resource types; real-time collaboration; document export beyond minimal Markdown download (see §9 OQ-04). The app is **local single-user** (human-resolved 2026-09-03).

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
| Local single-user deployment | Human-resolved 2026-09-03 | Runs on the human's machine (FastAPI + Vite); no auth, no hosting; AI creds from env vars |

**Process/lifecycle model** (`SD-9`, agent-derived): a project has a persisted **stage**: `reading` → (report generated) `editing`. Stage is per-project; entering `editing` gates off reading actions (R-042). No data changes hands between modes except the report itself.

**Concurrency model**: single user, one process; AI calls are HTTP-request-scoped; expert runs within a round may be parallelized (`Depends on soft ASM-002`).

## 4. Data model

Legend: **[M]** = decision-mandated entity/semantics; **[SD]** = agent-derived draft shape (soft, reviewable). All rows persist in SQLite (DEC-003).

| Entity | Semantics | Trace / basis |
|---|---|---|
| `Project` **[M]** | Container of a resource tree + human annotations + rounds; `name`, `stage` (SD-9), timestamps | DEC-005; INT-001 |
| `ResourceNode` **[M]** | Dir/file nodes of the project tree; Markdown files only; each file has content + relative path | DEC-005 |
| `ResourceDoc.content` **[M]** | Markdown text **snapshot imported into app storage (SQLite)** when the tree is set up (R-012 read-only guarantee) | DEC-005/006 — human-resolved 2026-09-03: import into app |
| `Annotation` **[M]** | Human-made; two kinds: `highlight` (range/offsets over doc snapshot) and `note` (free text, optional anchor to a highlight/range); authored by human only | DEC-006 |
| `LensProposal` **[SD]** | AI-suggested lens per doc: title, rationale, status (proposed/selected/skipped); human confirms before experts run (SD-3) | DEC-007; `Depends on soft ASM-002` |
| `ExpertRun` **[SD]** | Instance of one lens over one doc within a round; holds its own notes | DEC-007/008; `Depends on soft ASM-002` |
| `ExpertNote` **[M]** | Note text (with optional snippet refs) produced by an `ExpertRun`; distinct from human annotations; review state (pending/accepted/discarded/merged-with-edits) | DEC-008 |
| `ReadingRound` **[SD]** | Human-chosen set of docs; groups the joint reading (R-030); owns expert runs, dump, report | DEC-009 (round is implied by "this round of reading over a set of docs") |
| `NotesDumpEntry` **[M]** | Curated dump item; `kind` ∈ {snippet, highlight, human-thought, ai-thought}; source doc ref; ordering within dump | DEC-009 |
| `NotesDump` **[SD]** | Ordered entry collection, one per round (1:1 with report per round — §9 OQ-02) | DEC-009; `Depends on soft ASM-003` |
| `Report` **[M]** | Generated artifact from one dump; belongs to the round/project | DEC-010 |
| `ReportBlock` **[M]** | One paragraph of the report; `content`, `position`; editable manually; optional links back to source dump entries/docs | DEC-011; block links `Depends on soft ASM-004` |
| `ToneSampleSet` **[SD]** | Result of a tone request: exactly 5 samples with tone labels + target block; **transient** (regenerated per request; not persisted) | DEC-012 (SD-7) |
| `CritiqueResult` **[SD]** | Result of a critique request for a block; **transient** | DEC-013 (SD-8) |

Cardinalities **[SD]**: Project 1—N ResourceDoc · Project 1—N Round · Round N—N ResourceDoc (the doc set) · Round 1—1 NotesDump · Round 1—N ExpertRun (per doc×lens) · ExpertRun 1—N ExpertNote · NotesDump 1—N Entry · Round 0..1—1 Report · Report 1—N ReportBlock · ReportBlock N—N NotesDumpEntry (soft link, ASM-004).

## 5. User flows

- **F1 — Set up project** (R-010, R-011): create project → **import** its Markdown tree into app storage (snapshot; human-resolved 2026-09-03) → resources appear read-only. `Trace: DEC-005, DEC-006`
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

All under `/api/v1`, JSON, **local single-user, no auth** (human-resolved 2026-09-03). Sketched per flow; final shape left to implementation.

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
| ASM-002 | Experts = parallel structured LLM calls, one lens each, notes stored per project/resource/expert | depended-on (soft) | R-021, §3, F3/F4, §9 OQ-06 |
| ASM-003 | Expert-note review = list UI with accept/reject/edit merging into human notes | depended-on (soft) | R-022, R-031, F5/F6 |
| ASM-004 | Report stored at paragraph (block) granularity with links to source notes/resources | depended-on (soft) | R-041, §4, F9 |
| ASM-005 | AnthropicVertex env vars valid in the backend runtime | depended-on (soft) | R-004, §3 |
| ASM-006 | `backend/` and `frontend/` dirs are the scaffolding locations | depended-on (soft) | §3 (dirs to be created in this workspace) |

## 8. Assumption log

No revisions made. All six assumptions are used as worded in `.hai/state.yaml`; none conflicted with the decisions or with each other, and the spec's agent-derived details were written to stay consistent with them.

## 9. Open questions — RESOLVED (2026-09-03)

Door classes: **one-way** = irreversible/high-cost mistake, needed human input (asked); **two-way** = rectifiable, agent chose best option, human may veto at any time.

| OQ | Decision | Who/how | Reversal cost |
|---|---|---|---|
| OQ-01 Resource storage | **Import into app**: project setup snapshots the Markdown tree into app storage (SQLite). External file changes after import are not tracked. Highlights/notes anchor to the snapshot. | Human (asked, one-way-style) | Re-pointing to live disk later = re-import + anchor migration |
| OQ-02 Rounds/reports per project | Multiple rounds per project; each round has 1 dump → 1 report. Stage shift applies per round/report. | Agent (two-way) | Trivial to restrict later |
| OQ-03 Curation semantics | Dump = ordered list of typed entries {snippet, highlight, human-thought, ai-thought}, built from per-doc pools + free typing (SD-5). | Agent (two-way) | UI/UX reshape, storage unchanged |
| OQ-04 Export | Minimal in scope: **download report as Markdown**. No PDF/DOCX pipelines. | Agent (two-way) | Feature add/remove |
| OQ-05 Regeneration | Generation is **one-shot per round**; no destructive regenerate. New report = new round. Deleting a report allowed with confirm. | Agent (two-way) | Add regenerate later if wanted |
| OQ-06 Lens control | **AI-proposed lenses only** in v1 (human confirms which run). Hand-defined lenses deferred; schema keeps a hook. | Agent (two-way) | Feature add later |

## 10. Use cases

**Actors**: **Human** — drives the UI; every action is human-initiated (evidence H1..H9). **AI** — the AnthropicVertex client (R-004): proposes lenses, runs experts, generates the report, produces tone samples and critiques. **System** — backend: persists state, enforces the stage gate (SD-9), performs the mode shift.

**Happy-path main flow**: UC-01 → UC-02 → UC-03 → UC-04 → UC-05 → UC-06 → UC-07 → UC-08 → UC-12 (import → annotate → lenses → experts → curation → generate → edit → export). **Variants**: optional per-block assists (UC-09..UC-11), deletion (UC-13), iteration via a new round (UC-14). In-flow choices — discarding an expert note, declining to apply a sample — are alternatives inside a use case, not separate UCs. No UC goes beyond INT-001..004 plus the resolved §9 doors (OQ-01..OQ-06); none contradicts a DEC.

| UC | Title | Primary actor | Kind | Main success path (brief) | Trace |
|---|---|---|---|---|---|
| UC-01 | Set up project by importing a Markdown tree | Human | Main | Human creates a project and imports a local Markdown tree; backend snapshots the tree into app storage (OQ-01); files appear as read-only resources listed by path, renderable, with no edit affordance (R-011). | F1 (R-010, R-011) · DEC-005, DEC-006 |
| UC-02 | Read & annotate a resource | Human | Main | Human opens a resource in the rendered view (SD-2), selects text to highlight, attaches a note (optionally anchored to a highlight/range); annotations persist in app storage; resource content is never written back (R-012). | F2 (R-011, R-012) · DEC-006 |
| UC-03 | Propose & confirm expert lenses | Human (AI proposes) | Main | Human asks the AI for lenses on a doc; AI proposes relevant lenses for that doc (e.g. financial, real-estate, political, software-engineering, as content suggests); human confirms the subset to run (SD-3). | F3 (R-020) · DEC-007 |
| UC-04 | Run experts; review, discard, or adopt their notes | Human (AI produces notes) | Main | AI runs one expert per confirmed doc×lens; each expert keeps its own notes. Human reviews each note and chooses keep / discard / edit-and-add; adopted notes (including edited ones) merge into human notes with provenance kept (AI vs human origin). | F4, F5 (R-021, R-022) · DEC-007, DEC-008 |
| UC-05 | Curate a round dump | Human | Main | Human picks the round's doc set, then curates the dump as ordered entries of kinds snippet, highlight, human-thought, ai-thought from per-doc pools plus free typing (SD-5); dump persists per round. | F6 (R-030, R-031) · DEC-009 |
| UC-06 | Generate a report from the dump | Human (AI generates) | Main | Human presses "Generate report"; backend makes a single AI call whose input is the curated dump content; the result is stored as ordered paragraphs/blocks. | F7 (R-040, R-041) · DEC-010 |
| UC-07 | Mode shift into editor | System | Main | After report creation the app shifts the round/project to the editor stage: reading actions (annotate, run experts, curate) are closed or disabled and the report becomes the editing surface. | F8 (R-042) · DEC-010, DEC-011 |
| UC-08 | Manually edit a paragraph block | Human | Main | Human edits the report paragraph by paragraph in the block editor; typing is the primary edit path; edits persist per block. | F9 (R-043) · DEC-011 |
| UC-09 | Tone change: exactly 5 samples | Human (AI generates) | Variant | On a block, human requests a change of tone; AI returns exactly 5 samples in different tones (AI-chosen tone labels, SD-7) generated from the report context (target block + context); block text is unchanged until an explicit apply. | F10 (R-050, R-053) · DEC-012 |
| UC-10 | Apply one sample | Human | Variant | Human previews the 5 samples and explicitly applies one; only that explicit action writes the sample into the block; no auto-replacement ever happens. | F10 (R-051) · DEC-012, DEC-011 |
| UC-11 | Argument critique per block | Human (AI critiques) | Variant | On a block, human requests a critique; AI challenges the argument using the report context; output is shown read-only and never auto-edits the block; human rewrites manually; repeatable (SD-8). | F11 (R-052, R-053) · DEC-013, DEC-011 |
| UC-12 | Download report as Markdown | Human | Main (terminal) | In editor mode, human downloads the report as a Markdown file (minimal export; no PDF/DOCX). | §9 OQ-04 (no §5 flow letter or §2 R-tag exists — export was resolved only as an OQ door) |
| UC-13 | Delete a report (round remains) | Human | Variant (exceptional) | Human deletes the report after an explicit confirm; the round and its dump remain; generation is one-shot per round, so a new report requires a new round (OQ-05). Post-delete stage behavior is unspecified (OQ-05 does not resolve it). | §9 OQ-05 (no §5/§2 tag — resolved only as an OQ door) |
| UC-14 | Start a new round in an existing project | Human | Variant (iteration) | Human starts a new round in a project that already has a report: new doc set → new dump → new report; stage shift applies per round/report; rounds stay independent. | F6..F8 path, §9 OQ-02 (multi-round per project resolved only as an OQ door) |

Note on UC-12..UC-14: export, deletion, and multi-round reuse were resolved as §9 doors (OQ-04, OQ-05, OQ-02 — agent two-way choices), so they have no `Trace: DEC` chain and no normative R-tag in §2. They are in scope; giving them hard R-numbers or flow letters would require a human-approvable revision of §2/§5, deliberately not done here.

## 11. Verification & test plan

Scope note: spec-only — this section plans verification and adds no product requirements. The R-tags cited are the normative anchors (§2). Test-tool and policy choices are agent-derived: `SD-12`..`SD-16` below; milestone gates are `SD-17`.

### 11.1 Automatic tests — strategy + coverage map

**Runners and static checks** (tool choices agent-derived):
- Backend unit + API tests: **pytest**, with FastAPI **TestClient** against the §6 endpoints — `SD-12`.
- Backend static checks: **mypy** + **ruff** — `SD-13`.
- Frontend component tests: **vitest** + React Testing Library — `SD-14`.
- Frontend static checks: **tsc** + **eslint** — `SD-15`.

**Mock/env policy** (`SD-16`, agent-derived): CI runs fully offline. Every test that would touch AnthropicVertex mocks the AI-client wrapper (the single module boundary per R-004). Any test needing live RES-001 env vars is env-gated (marker/skip) and never part of the default CI run — CI must not depend on ASM-005.

**Backend unit tests**:
- AI-client wrapper (R-004): with the AnthropicVertex client mocked, all five call kinds — lens proposal, expert run, report generation, tone samples, critique — route through the wrapper; assert request payload shape and response parsing.
- Dump→report input shaping (R-040, R-041): generation request is built from the round's curated dump entries only; the response parses into ordered blocks.
- Tone request/parse (R-050, R-053): payload carries target block + report context; parsing enforces exactly 5 labeled samples.
- Critique request/parse (R-052, R-053): payload carries block + report context; the call path never mutates the block (R-052).
- Read-only invariant (R-011, R-012): drive a full reading → annotate → (mocked) generate → edit path at service level; assert the imported resource snapshot is byte-identical throughout and no code path writes resource content.
- Schema/CRUD round-trips: project, resources, rounds, dump entries, blocks; stage transition `reading`→`editing`; after the shift, reading-stage operations are rejected (R-042 gate).

**Backend API tests** (TestClient, AI mocked) — §6 endpoint coverage per flow: import scan + tree (F1), annotations CRUD (F2), lens proposals + expert runs + merge-with-provenance (F3..F5), dump save/get (F6), generate-report returns blocks and flips stage (F7/F8), block PUT persists manual edits (F9), tone-samples returns exactly 5 (F10), critique returns text without editing the block (F11), delete-report requires an explicit confirm payload (OQ-05).

**Frontend component tests** (vitest + RTL; network mocked at the api-client boundary):
- api client maps frontend calls to the §6 endpoints.
- Block editor (R-043): typing edits a block and persists via the api client; saved text renders after reload.
- Tone-sample preview/apply (R-051): samples render while block text stays unchanged; content changes only when the human explicitly applies one sample.
- Critique panel (R-052): critique renders read-only; no control auto-edits the block.
- Curation entry list (R-031): entries add/reorder/save in dump order.
- Reading-mode gating (R-042): after the stage shift, reading/curation UI is absent or disabled.

**Coverage map** (behavior-critical requirements → covering automatic test):

| R | Behavior under test | Covered by |
|---|---|---|
| R-004 | All AI calls via one AnthropicVertex wrapper; env-var credentials | AI-client wrapper unit tests (client mocked) |
| R-011 | Resources read-only; never edited by app or human through app | Read-only invariant unit test; annotation API tests assert snapshot unchanged |
| R-012 | Annotations stored separately, never written into files | Read-only invariant + annotation CRUD API tests |
| R-040 | Report generated from the curated dump only | Dump→report input-shaping unit test; generate-report API test (mocked, single call) |
| R-042 | Mode shift gates off reading actions | Stage-gate API test; frontend reading-mode gating test |
| R-043 | Manual paragraph-by-paragraph block editing | Block PUT API test; block editor component test |
| R-050 | Exactly 5 tone samples, different tones, report context | Tone parse unit test; tone-samples API test asserts count 5 |
| R-051 | No auto-replace; apply is explicit | Tone preview/apply component test; API test asserts endpoint does not write block |
| R-052 | Critique never auto-edits the block | Critique unit/API tests assert block unchanged; critique panel component test |
| R-053 | Both assists receive report context (block + context) | Tone and critique payload-shaping unit tests |

Residual requirements (R-010, R-020..R-022, R-030, R-041 storage semantics) are exercised through the mocked expert/curation/round API tests above; no dedicated adversarial tests planned for them.

### 11.2 Manual verification checklist (running local app, real AI)

Precondition: backend + frontend running locally; the backend process must have the RES-001 env vars exported (`Depends on soft ASM-005` — if missing, steps 3, 4, 6, 8, 10 fail with an AI-call error by design; no app-side fallback). Each step: action → R-tag → expected observable outcome.

1. **Import**: create a project; import a sample Markdown tree (≥3 files, incl. a subdirectory, with headings/paragraphs/bullets). → R-010, R-011. Expected: resources listed by path; content renders; no edit affordance on any resource.
2. **Annotate**: open a resource; highlight a sentence; add a note anchored to it; reload the page. → R-011, R-012. Expected: highlight and note persist; the source file on disk is byte-identical (diff it).
3. **Lens proposal**: request AI lenses on one doc. → R-020. Expected: a short list of sensible lens proposals with rationale; confirm 2 of them.
4. **Experts + review**: run the confirmed experts; in the review list discard one note and edit-and-add another to the human notes. → R-021, R-022. Expected: expert notes appear per expert; the adopted (edited) note appears in human notes and keeps its AI-origin marker in the dump.
5. **Curate dump**: start a round over 2 docs; compose a dump with ≥1 entry of each kind (snippet, highlight, human-thought, ai-thought) in a chosen order; save. → R-030, R-031. Expected: dump persists and renders in the saved order.
6. **Generate + mode shift**: press "Generate report". → R-040, R-042. Expected: a report appears as paragraphs; the UI is now in editor mode — annotate/run-expert/curate controls are gone or disabled.
7. **Manual edit**: edit two paragraphs by typing; reload the page. → R-043. Expected: edits persist per block.
8. **Tone request**: on a block choose change of tone. → R-050, R-053. Expected: exactly 5 samples with distinct tone labels whose wording reflects the report context; block text is unchanged.
9. **Apply sample**: apply one sample. → R-051. Expected: only that block's text becomes the chosen sample; the other 4 are discarded.
10. **Critique**: on another block request a critique. → R-052, R-053. Expected: a substantive challenge that references the report context; block text unchanged; manual rewrite works.
11. **Export**: download the report as Markdown; open the file. → §9 OQ-04. Expected: valid Markdown with paragraphs in report order.
12. **Delete report**: attempt delete and cancel in the confirm dialog; then delete with confirm. → §9 OQ-05. Expected: cancel path deletes nothing; after confirm the report is gone while the round and its dump remain listed.
13. **New round**: in the same project start a new round, pick docs, generate a second report. → §9 OQ-02. Expected: a second, independent report exists; the first round's report and dump are untouched.

### 11.3 Verification gates — when a milestone counts as "done"

Gates are project-process policy, not product requirements (`SD-17`, agent-derived). All automatic gates run offline (mock policy `SD-16`):

- **Backend milestone done** when: `pytest` (unit + API, AI mocked) fully green; `mypy` clean on `backend/`; `ruff` clean.
- **Frontend milestone done** when: `vitest` fully green; `tsc` clean; `eslint` clean.
- **Integration milestone done** when: all 13 manual checklist steps (§11.2) are green against real AnthropicVertex (RES-001 env valid per ASM-005); the read-only guarantee (R-011) is re-verified on disk after the real-AI steps; the exported file is valid Markdown (§9 OQ-04).
- Release = backend + frontend + integration gates all green.
