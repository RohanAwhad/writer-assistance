# Integration evidence: M-VM-INTEGRATION

Reviewer-run (independent of builder report), 2026-09-03, human-authorized live real-AnthropicVertex run ("Full live 14-step run"). All 14 §11.2 steps executed against the running app; step 14 and the step-6/7/12 UI checks driven in-browser with network capture. Evidence files: `logs/hai-build-loop/step2-ui.log`, `stepB-ui.log`, `stepC-ui.log`, `screens/phase{A,B,C}.requests.log`, `screens/step{1,2,6,7,8,9,10,12,13,14}*.png`, `report-1-export.md`; raw server logs `backend.log`, `frontend.log`.

## Environment
- Commit/worktree identity: HEAD `1d7cb954113a9782e3689dc4b95a8a3d9060f704` (docs: spec v1.6 — report view mode + state alignment) + uncommitted milestone files: `backend/tests/test_api_reports.py` (M, read-path view-mode tests `test_view_mode_read_path_*_and_mutates_nothing`), `frontend/src/screens/workspace/ReportEditor.tsx` (M, view/editor surface switch, R-060/R-061/SD-18/SD-19), `frontend/src/test/viewMode.test.tsx` (new, 7 tests). `devlogs.md` also modified (untracked pre-existing logs/ ignored). Nothing committed.
- Runtime/service versions: python 3.13.5; uvicorn 0.52.4; fastapi 0.141.1 (anthropic[vertex] per pyproject); node v22.17.1; vite 8.2.2; vitest 5.0.0; @playwright/test 1.62.1 with bundled chromium revision 1234 (ms-playwright cache). PIDs: backend uvicorn 3365085 (wrapped by `uv run` 3365082), frontend vite node 3365104.
- Environment variable names present (never values): `WRITER_ASSISTANCE_DB` (set per-run to the isolated DB file; main.py:18-25 + load_dotenv override). backend/.env exists (32 bytes) and per DEC-015 overrides the shell — verified names only: `.env.example` lists `ANTHROPIC_VERTEX_PROJECT_ID, GOOGLE_VERTEX_LOCATION, VERTEX_LOCATION, ANTHROPIC_MODEL, ANTHROPIC_SMALL_FAST_MODEL, VERTEX_ACCESS_TOKEN, ANTHROPIC_BASE_URL, WRITER_ASSISTANCE_DB`; backend/.env holds `ANTHROPIC_MODEL` only (RES-001 names otherwise satisfied from the shell env, which exposes ANTHROPIC_VERTEX_PROJECT_ID / ANTHROPIC_SMALL_FAST_MODEL / VERTEX_LOCATION etc.). `vertex.py` REQUIRED_ENV_VARS satisfied at every AI call.
- Offline/live mode and authorization reference: LIVE AnthropicVertex, model `claude-sonnet-5` per backend/.env (DEC-017); human-authorized 2026-09-03 ("Full live 14-step run"); auth via ADC google-auth. No secret values recorded anywhere in this file or logs.

## Fixture
- Isolated fixture identifiers: project "VM-INT Review Journey 2026-09-03" (id 1) on isolated DB `/tmp/opencode/vm-int-reviewer.db` (fresh; data/writer-assistance.db untouched). Imported tree `/tmp/opencode/wd-vm-int/`: 5 files incl. subdir `research/archive/` (`research/housing-market.md`, `research/remote-work.md`, `research/archive/supply-side.md`, top-level `housing-market.md`, `letter.md`); md5 baseline `/tmp/opencode/wd-vm-int.md5.baseline` (records). Seed method: `cp` of /tmp/opencode/wd-sample-docs/research/{housing-market,remote-work}.md + added files; letter.md is a new top-level doc. Cleanup scope: project lives only in the isolated DB; fixture tree + DB file + baseline removed at cleanup; servers stopped; evidence + logs under logs/hai-build-loop kept.

## Commands and results
| Command | Exit/result | Evidence |
|---|---|---|
| `WRITER_ASSISTANCE_DB=/tmp/opencode/vm-int-reviewer.db uv run uvicorn app.main:app --port 8000` (backend/, bg) | running | backend.log:4-6 startup complete |
| `npm run dev` (frontend/, bg) | running | frontend.log:1-9 (vite 8.2.2 ready in 185 ms) |
| `curl http://127.0.0.1:8000/api/v1/projects`, `curl -o /dev/null -w %{http_code} http://127.0.0.1:5173/` | `[]` / `200` | readiness pre-checks |
| `curl -X POST /api/v1/projects …` | 201 | {"id":1} |
| `curl -X POST /api/v1/projects/1/import {path:/tmp/opencode/wd-vm-int}` | 201 | {"imported_files":5}; backend.log:7 |
| `md5sum -c /tmp/opencode/wd-vm-int.md5.baseline` (after step 2) | all 5 OK | fixture byte-identical after annotate |
| node scripts phaseA/B/C.mjs (playwright, chromium 1234) | 0 | step2-ui.log / stepB-ui.log / stepC-ui.log |
| `curl -X POST /api/v1/resources/5/lens-proposals` | 201 | backend.log:24 |
| `curl -X PATCH /api/v1/lens-proposals/{1,3} {selected}` + {2,4,5} {skipped} | 200 x5 | backend.log:26-30 |
| `curl -X POST /api/v1/rounds/1/experts` | 201 | backend.log:30 |
| `curl -X PATCH /api/v1/expert-notes/2 {discarded}`; `POST /api/v1/expert-notes/1/merge {content}` | 200 / 201 | backend.log:31-32 |
| `curl -X POST /api/v1/rounds/1/dump` (4 entries) | 200 | backend.log:35 |
| `curl -X POST /api/v1/rounds/1/generate-report` | 201 | report1.json (4 blocks); backend.log:37 |
| `curl -X POST /api/v1/rounds/2/experts` (first attempt) | 502 "AI response is not valid JSON" | backend.log:66 — retried |
| `curl -X POST /api/v1/rounds/2/experts` (retry) | 201 | backend.log:67 |
| `curl -X POST /api/v1/expert-notes/20/merge` | 201 | backend.log:69 |
| `curl -X POST /api/v1/rounds/2/dump`; `…/generate-report` | 200 / 201 | backend.log:71-72; report2.json (5 blocks) |
| `curl -X POST /api/v1/blocks/5/tone-samples` | 200, 5 samples | tone2.json |
| `curl -X POST /api/v1/blocks/6/critique` + before/after GET diff | 200, content diff empty | critique2.json; report2.before/after.txt |
| `uv run pytest -q` (backend/) | 70 passed, 5 skipped (env-gated live-AI) | offline regression |
| `npx vitest run` (frontend/) | 8 files, 32 tests passed (incl. viewMode.test.tsx 7 tests) | verbose run listing |

## Use cases
| Spec use case | Execution method | Expected | Actual | Result | Evidence |
|---|---|---|---|---|---|
| §11.2 step 1 / UC-01 (F1, R-010/R-011) import | API import + browser | ≥3 files incl. subdir listed, rendered, read-only | 5 files imported incl. `research/archive/`; tree lists all by path; doc renders; 0 editable controls in main pane; "read-only" badge; no edit affordance | PASS | tree API; step2-ui.log STEP1 rows {housing-market.md:2, letter.md:1, remote-work.md:1, supply-side.md:1}, heading/path, editable controls {0,0,0} |
| §11.2 step 2 / UC-02 (R-011/R-012) annotate | browser (selection→Highlight; selection→"Note on selection") + reload | highlight + anchored note persist; disk byte-identical | highlight mark + anchored note created (backend.log:15-16 201); both re-render after full page reload; md5 of all 5 fixture files OK | PASS | step2-ui.log; backend.log:12-22 (GET annotations 200 pre/post reload); md5sum -c all OK |
| §11.2 step 3 / UC-03 (R-020) lens proposals | API (live AI) | short list of sensible proposals w/ rationale; confirm 2 | 5 proposals (Org Psych, HR, Labor Econ, Tooling, DEI) each with rationale; confirmed 2 (selected), 3 skipped | PASS | lenses1.json; PATCH 200s backend.log:26-30 |
| §11.2 step 4 / UC-04 (R-021/R-022) experts + review | API (live AI) | notes per expert; discard one; edit-and-add keeps AI-origin in dump | 2 expert runs (Org Psych 10 notes, Labor Econ 9); note 2 discarded (PATCH 200); note 1 merged-with-edits → dump entry id1 kind ai-thought expert_note_id=1 (backend.log:32) | PASS | experts1.json; merge response dump_id 1, kind ai-thought, expert_note_id 1 |
| §11.2 step 5 / UC-05 (R-030/R-031) curate dump over 2 docs | API POST /dump 4 entries | ≥1 entry of each kind in chosen order; persists | saved order snippet(0)→highlight(1)→ai-thought(2)→human-thought(3); GET after re-fetch identical; merged entry kept (position 2, provenance kept) | PASS | dump POST/GET responses; backend.log:35-36 |
| §11.2 step 6 / UC-06+UC-07 (R-040/R-042, DEC-006) generate + mode shift | API generate + browser | report as paragraphs; run-expert/curate closed in UI; annotate stays | stage flipped reading→editing (GET /rounds/1); 4 blocks rendered in editor; UI: round badge `editing`, "Curate dump" disabled (tooltip R-042), reading pane shows closed card, highlight mark + 2 annotations still listed with doc open (annotations stay available) | PASS | report1.json; stepB-ui.log STEP6 lines; backend.log:37,44 |
| §11.2 step 7 / UC-08 (R-043) manual edit x2 | browser typing + reload | edits persist per block | typed suffix edits on blocks 1 and 3; full page reload → both edits present in textarea values (PUT /blocks/1, /blocks/3 logged) | PASS | stepB-ui.log STEP7 lines; phaseB.requests.log 21:45:30-31 PUTs |
| §11.2 step 8 / UC-09 (R-050/R-053) tone x5 | browser (round-1) + API (round-2, labels) | exactly 5 distinct-tone samples reflecting report context; block unchanged | browser: 5 samples, block text unchanged while shown (phase B). API on round-2 report block: exactly 5 samples, labels [confident, conversational, measured, urgent, vivid] — 5 distinct, texts rework the housing-paradox paragraph from report context | PASS | stepB-ui.log STEP8; tone2.json (count 5, distinct 5) |
| §11.2 step 9 / UC-10 (R-051) apply one sample | browser | only that block changes | applied sample index 2 → textarea equals sample text; samples panel closed; single PUT /blocks/1; no other block writes | PASS | stepB-ui.log STEP9; phaseB.requests.log 21:45:41 PUT blocks/1 only |
| §11.2 step 10 / UC-11 (R-052/R-053) critique | browser (round-1) + API (round-2 on block 6) | substantive challenge referencing context; block unchanged; manual rewrite works | round-1: critique 1482 chars challenging the housing/remote disconnect, block content unchanged (pre/post equal), rewrite typed on block 2 and saved (PUT blocks/2). Round-2: critique on block 6 (1795 chars re structural-vs-cyclical causal leap), before/after GET diff empty | PASS | stepB-ui.log STEP10; critique2.json; report2.before.txt/after.txt identical |
| §11.2 step 11 / UC-12 (OQ-04) export | browser download | valid Markdown, paragraphs in order | downloaded report-1-export.md (1972 bytes): 4 paragraphs joined in saved block order (blocks SELECT ORDER BY position; export = "\n\n".join), contains applied tone sample + critique-rewrite text; no stray markup | PASS | report-1-export.md; backend.log:58 |
| §11.2 step 12 / UC-13 (OQ-05) delete report | browser dialog | cancel deletes nothing; confirm deletes report; round+dump remain | Cancel → blocks still present, GET /reports/1 200; Confirm → single DELETE /reports/1 204 (backend.log:59); UI "report deleted — generation is one-shot"; Report button disabled; round badge stays `editing`; GET report 404, round dump_id 1 with 4 entries intact | PASS | stepB-ui.log STEP12; phaseB.requests.log (1 DELETE only); post-delete API checks |
| §11.2 step 13 / UC-14 (OQ-02) new round | API round 2 + UI round 3 | new round starts reading; controls open; second independent report; first round untouched | Round 2 created `reading` (create response), its experts/dump/generate accepted pre-flip; after generate report 2 (5 blocks, id 2) exists, round 2 `editing`. UI round 3 (created via "New round" dialog): badge `reading`, Curate enabled, expert controls pane open (round-closed absent). Round 1 (report deleted, dump 4 entries) untouched | PASS | create round responses; report2.json; stepC-ui.log S13 lines; backend.log:65,71-72,85 |
| §11.2 step 14 / UC-15, UC-16 (R-060/R-061, F12) view mode | browser w/ network watch on round 2 report | view read-only; delete hidden in view; download kept; switch writes nothing; edit persists across surfaces; badge stays `editing` | see below | PASS | stepC-ui.log S14/UC16 lines; phaseC.requests.log |
| UC-15 read report in view mode | browser | rendered read-only surface, no typing/edit affordances, no per-block AI controls | View renders 5 `view-block-*` paragraphs (order matches, block 1 == saved text); 0 textareas; 0 save-state testids; 0 Change-of-tone/Critique buttons; Delete report absent; Download .md present; "Report editor" heading absent in view (h2 flips to "Report", ReportEditor.tsx:181) | PASS | stepC-ui.log S14 view lines |
| UC-16 switch view↔editor without losing state | browser + network capture | switch never writes; stage stays editing; saved content persists; view shows latest saved text; reload returns to editor | Toggle editor→view: 0 writes; toggle view→editor: 0 writes; typed edit saved (1 PUT /blocks/5), view then shows updated text, toggle again: 0 writes; full round-2 session write list = exactly [PUT /blocks/5]; GET /rounds/2 before/after every toggle = `editing` (6 GETs); full reload mid-editing → re-entering report surface lands on EDITOR (heading "Report editor"), edited text present, badge `editing`, server stage unchanged | PASS | stepC-ui.log S14 + UC16; phaseC.requests.log |
| Regression: annotations available in editing stage | browser (round-1 editing) | annotate stays available | highlight marks rendered + 2 annotation items listed while round 1 in `editing` | PASS | stepB-ui.log STEP6 regression line |
| Regression: block GETs during view don't mutate | automated (offline) | GETs mutate nothing | backend `test_view_mode_read_path_returns_saved_blocks_and_mutates_nothing` + `…returns_edited_rows_and_mutates_nothing` in uncommitted test_api_reports.py; pytest 70 passed; round stage/report unchanged across all view GETs during live run | PASS | pytest run; live stage GETs |

## Live calls and timings
Sanitized request ids omitted (none recorded); auth ADC, no secret values. Model claude-sonnet-5 (backend/.env DEC-017); tone/critique route via small-fast model per RES-002.

| Service/model | Gate | Sanitized request id | Timing | Result | Evidence |
|---|---|---|---|---|---|
| Vertex/claude-sonnet-5 lens proposals | §11.2 step 3 | POST /resources/5/lens-proposals | ~7 s wall | 5 proposals w/ rationale | lenses1.json; backend.log:24 |
| Vertex/claude-sonnet-5 expert notes (round 1, 2 lenses) | §11.2 step 4 | POST /rounds/1/experts | ~31 s wall | 19 notes across 2 runs | experts1.json; backend.log:30 |
| Vertex/claude-sonnet-5 report generation (round 1) | §11.2 step 6 | POST /rounds/1/generate-report | ~10 s wall | 4 ordered blocks | report1.json; backend.log:37 |
| Vertex small-fast tone samples (round 1, via UI) | §11.2 step 8 | POST /blocks/1/tone-samples | ~10 s (21:45:32→21:45:41 PUT apply) | 5 samples; block unchanged | phaseB.requests.log; stepB-ui.log |
| Vertex small-fast critique (round 1, via UI) | §11.2 step 10 | POST /blocks/1/critique | ~10 s (21:45:42) | 1482-char challenge | stepB-ui.log STEP10 |
| Vertex/claude-sonnet-5 experts (round 2 attempt 1) | step 13 | POST /rounds/2/experts | 502 | "AI response is not valid JSON" | backend.log:66; failures section |
| Vertex/claude-sonnet-5 experts (round 2 retry) | step 13 | POST /rounds/2/experts | ~26 s wall | 16 notes across 2 runs | experts2b.json; backend.log:67 |
| Vertex/claude-sonnet-5 report generation (round 2) | step 13 | POST /rounds/2/generate-report | ~14 s wall | 5 ordered blocks | report2.json; backend.log:72 |
| Vertex small-fast tone samples (round 2, labels) | step 8 evidence | POST /blocks/5/tone-samples | ~10 s wall | exactly 5 distinct labels | tone2.json |
| Vertex small-fast critique (round 2, block 6) | step 10 evidence | POST /blocks/6/critique | ~14 s wall | 1795-char challenge; content unchanged | critique2.json; diff |

## Log review
- `logs/hai-build-loop/backend.log:4-6`: uvicorn startup complete, listening on 8000 (isolated DB; no access to data/writer-assistance.db).
- `logs/hai-build-loop/backend.log:15-16`: highlights + notes POST 201 (step 2 browser writes).
- `logs/hai-build-loop/backend.log:37`: generate-report 201 — round-1 mode flip.
- `logs/hai-build-loop/backend.log:58-59`: export.md GET 200 then single DELETE /reports/1 204 — step 11/12.
- `logs/hai-build-loop/backend.log:62`: GET /reports/1 404 — expected post-delete verification.
- `logs/hai-build-loop/backend.log:66`: 502 on first round-2 experts attempt (transient AI JSON parse failure) — immediately retried 201 at :67. Only 5xx in the whole log; no tracebacks, no 500s, no unhandled exceptions across 105 lines.
- `logs/hai-build-loop/backend.log:71-72`: round-2 dump 200 + generate-report 201.
- `logs/hai-build-loop/backend.log:85-91`: UI round-3 create 201 and doc reads — reading controls open.
- `logs/hai-build-loop/frontend.log:1-9`: vite dev server ready in 185 ms; no errors/unhandled rejections logged during the session (vite logs nothing else; no favicon 404 or any 4xx/5xx surfaced in the dev-server log — proxy errors would appear here).
- `logs/hai-build-loop/screens/phaseC.requests.log`: round-2 session network trace — 6× `GET /api/v1/rounds/2` (stage probes, all `editing`), 1× `GET /api/v1/reports/2`, exactly 1 write `PUT /api/v1/blocks/5` (the typed edit), no DELETE/POST/PATCH — UC-16 switch-writes-nothing verified from raw trace.
- `logs/hai-build-loop/screens/phaseB.requests.log`: round-1 session writes — 2 PUTs (typing edits), 1 POST tone, 1 PUT (apply), 1 POST critique, 1 PUT (rewrite), 1 DELETE (report) — exactly the human actions; delete dialog cancel produced no request.

## Failures and retries
- Attempt: `POST /rounds/2/experts` first call. Exact failure: `{"detail":"AI response is not valid JSON"}` (HTTP 502 Bad Gateway, backend.log:66). Routing category: WARN (transient model-output parse failure inside the existing parser boundary — no code change warranted; the same endpoint succeeded on round 1 and on retry). Fix: retried the identical request. Rerun evidence: backend.log:67 201 Created; experts2b.json (2 runs, 16 notes). No code touched, no state corrupted (failed call wrote nothing).

## Residual human UX checks
- none material. All UI-surface steps were genuinely browser-driven (tree/read-only, highlight+anchored-note+reload, editing-stage control closure, typed edits + reload, tone panel + apply, delete cancel/confirm dialog, new-round dialog, full view-mode flow with network watch). Tone-label *visual* styling and screenshot aesthetics were not inspected (model has no image input); label count/distinctness and rendering were asserted from DOM + API payloads. Screenshots exist under logs/hai-build-loop/screens/ for human eyeballing.

## Cleanup
- Processes stopped: uvicorn (PID 3365085 + `uv run` 3365082) and vite (PID 3365104) killed via background-job termination.
- Fixture resources removed: `/tmp/opencode/wd-vm-int/` tree, `/tmp/opencode/vm-int-reviewer.db`, `/tmp/opencode/wd-vm-int.md5.baseline`, `/tmp/opencode/vm-pw/` working scripts.
- Kept: evidence file + raw logs under logs/hai-build-loop/ (backend.log, frontend.log, step*-ui.log, screens/, report-1-export.md). data/writer-assistance.db untouched (only isolated DB was used).
