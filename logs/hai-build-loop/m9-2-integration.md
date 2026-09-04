# Integration evidence: m9-2 (INT-009 milestone M2 — integration/hardening + INT-009 gate)

Reviewer-owned INTEGRATION RUN (independent of builder reports), 2026-09-04. **OFFLINE** — no live AI
calls, no providers engaged, no lens/expert/generate/tone/critique action was ever fired (one-way cost
door respected). Execution per spec.md v2.0 §11.2 steps 24..25 (emulated legs) and the §11.3 INT-009
done-gate (spec.md:455), plus the §11.1 additive pytest row (spec.md:371). Evidence under
`logs/hai-build-loop/`: `m9-2-backend.log` (uvicorn access), `m9-2-driver-p1.log`,
`m9-2-driver-p3.log` (driver transcripts), `m9-2-browser-console.log`, screenshots
`screens/m9-2-<width>-<surface>.png` (64 files), results JSONs (re-generated inline below from
`/tmp/opencode/m9-2/results/w*.json` — full copies retained in the review session). No code/spec/.hai
changes; nothing committed; tracked worktree delta unchanged (`backend/tests/test_auth_gate.py` +1).

## Verdict

**FAIL — CODE_BLOCKER** (single scoped responsive defect, F-m9-2-1; see Findings). Everything else in
Part A and the whole integration run is green — the failure is one non-wrapping toolbar row on the
report-editor surface at phone widths (390 and 360 CSS px) that clips the "Delete report" control
(R-082: "no clipped or unreachable controls"; §11.2 step 24 reachability; §11.3 emulated-phone leg).
F-m9-2-2 is a WARN-grade companion (round-stage mode row overhangs the viewport by 5/35 px at
390/360; the "Report" mode button stays tappable — center in viewport at both widths).
No SPEC_CHANGE_REQUESTED, no HAI_CHANGE_REQUESTED.

## Environment

- Worktree: branch `built-using-hai`, HEAD `a33e4ad` (m9-1, INT-009 M1). Uncommitted m9-2 delta:
  `backend/tests/test_auth_gate.py` 1 insertion (git status + `git diff HEAD --stat` = 1 file, 1 line).
  Untracked additions produced by this run: `logs/hai-build-loop/{m9-2-backend.log,
  m9-2-driver-p1.log, m9-2-driver-p3.log, m9-2-browser-console.log, m9-2-integration.md}` +
  `screens/m9-2-*.png` (evidence convention; prior milestones leave the same artifacts untracked).
- Backend: FastAPI via `uv run uvicorn app.main:app` (uv toolchain, Python 3.13) on **127.0.0.1:8010**
  (port 8000 was occupied by the pre-existing live container from INT-006/008 — `ss -tln` checked
  before binding; 8010 free). Gate **ON**: `AUTH_API_KEY` read from `backend/.env` into the process env
  (value never recorded, env names only). DB: isolated `WRITER_ASSISTANCE_DB=/tmp/opencode/m9-2/db/
  m9-2.db` — the dev DB `backend/data/writer-assistance.db` was never pointed at (baseline mtime
  2026-09-03 23:17, size 143360, md5 `4cea2ff4…` re-verified unchanged at cleanup).
- Frontend: `npm run build` in `frontend/` → `frontend/dist` (`index-BpZAiECd.js`,
  `index-_ss0hTSX.css`); FastAPI served the built SPA (R-076): GET / → index.html, assets 200 —
  backend log lines 1105/1116/1127 (GET / 200) and 1118/1128/1129 (GET /assets/* 200).
- Browser: playwright 1.62.1 chromium headless from `.hai/node_modules` (browser cache
  `~/.cache/ms-playwright/chromium-1234`); driver scripts under `/tmp/opencode/m9-2/drivers`
  (repo untouched; `.hai/playwright.config.ts` not touched).
- Env var names used (never values): `AUTH_API_KEY`, `WRITER_ASSISTANCE_DB`, `BASE_URL`,
  `REVIEW_AUTH_KEY` (process-only).

## Fixture (isolated DB only)

- md5-baselined Markdown fixture: `alpha.md` (`56e0eb96…`, 317 B), `beta.md` (`86db4517…`, 149 B).
- UI-created (P1 driver, desktop 1280x900, gate-on, through the served SPA): project `int009-rr` (id 5)
  with alpha.md+beta.md imported via the **browser file picker** (multipart → `POST
  /api/v1/projects/5/import 201`, backend log :665); doc alpha.md opened; real **mouse-drag
  selection** produced a highlight (`POST /api/v1/resources/5/highlights 201`, :670) and an
  **anchored note** ("Retention data supports the renewal narrative.", `POST /api/v1/resources/5/notes
  201`, :671); rounds `int009 Round A` (reading, id 5) and `int009 Round B` (editing, id 6) started via
  the new-round dialog (`POST /api/v1/rounds 201`, :672/:676); throwaway project `int009-empty` (id 6)
  created (:681) for the per-width import-dialog legs.
- DB-seeded rows (seed.py, uv-run python vs the isolated DB — method recorded; seed = the state a
  live-AI round would have left, inserted without any AI call): round A — 2 lens proposals (1
  proposed/1 selected), 1 expert run (doc alpha) with 3 pending notes, saved dump + 3 attached entries
  (ai-thought/highlight/human-thought); round B — stage `editing`, own dump + report + 3 ordered
  blocks + source-entry links. Verified via API before the walk: GET /rounds/5 (docs alpha+beta,
  dump 5), GET /rounds/5/dump (3 entries), GET /rounds/5/expert-runs (3 notes), GET /rounds/6 +
  /reports/3 (3 blocks with source ids), GET /reports/3/export.md (200, text/markdown, 282 B).
- Post-walk mutation audit (all UI legs persisted, sqlite direct read): annotation note tap-deleted at
  390 (1 highlight remains); notes → accepted (Keep @390) / discarded (Discard @360) /
  merged-with-edits + new dump entry (Edit & add @768, position 3); lens "Market sizing review"
  selected @390; provider `deepseek` on both projects (round-trip leg clean); round B editing + 3
  blocks intact.

## Part A — code + gates review (reviewer-run commands, exact results)

| Gate | Command (dir) | Result |
|---|---|---|
| m9-2 delta | `git diff HEAD` | exactly 1 insertion in `backend/tests/test_auth_gate.py` (viewport-meta assert); no other tracked file touched |
| delta fidelity | — | assertion string equals the HTML emitted at `backend/app/auth.py:87` byte-for-byte; backend suite otherwise untouched (commit a33e4ad diff = 13 files, all frontend + devlogs.md); spec.md/.hai untouched by m9-1/m9-2 (git diff HEAD~1 HEAD shows no spec/.hai file) |
| backend pytest | `make test` (backend/) | **136 passed, 8 skipped (env-gated `live_ai`), 1 deprecation warning**, exit 0 — includes `test_auth_gate.py` 19 rows incl. the new viewport-meta assertion |
| backend mypy | `make typecheck` | `Success: no issues found in 44 source files`, exit 0 |
| backend ruff | `make lint` | `All checks passed!`, exit 0 |
| frontend vitest | `npm test` (frontend/) | **11 files, 63 tests passed** (incl. responsiveView suite: phone overlay nav, tablet reachability, desktop regression guard, width-change preservation, touch reachability), exit 0 |
| frontend tsc | `npm run typecheck` | clean, exit 0 |
| frontend eslint | `npm run lint` | clean, exit 0 |
| .hai state | `npm run validate-state -- state.yaml` (.hai/) | `valid: 9 intents, 28 decisions, 0 unapproved actions, 34 evidence`, exit 0 |
| static serving (live) | curl/uvicorn log | `/login` carries the viewport meta tag; gate: `/api/v1/projects` → 401, `/` → 302 /login, wrong-key POST → 401 (readiness probe) |

## Integration run — commands and results

Contexts (playwright chromium, CSS-px viewports, touch/mobile emulation per SD-31 tier, UA
iPhone/iPad): 390x844 + 360x800 (phone), 768x1024 (tablet/iPad portrait), 1024x768 (desktop tier +
touch — iPad landscape), 1280x900 (desktop regression). Each context: fresh session → login page →
full surface walk → screenshot per surface. Rotation leg (R-084) in the 390 context: 390 → 768 →
1024 → 768 → 390 with NO reload (0 navigations during the leg). Results JSONs
(`/tmp/opencode/m9-2/results/w*.json`) hold per-surface overflow + control data; digest below.

| Viewport | Page-level horizontal overflow (`docScrollW <= innerW+1`) | Surfaces walked (each screenshot) | Control results |
|---|---|---|---|
| 390x844 | **all 8 surfaces ok** (login, projects, doc-open, annotate panes, curate, report editor, report view, login-after-logout): 390 == 390 | login, projects(+new-project/delete-project dialogs), doc alpha open, round A stage controls, annotate panes (lens + notes review + Keep tap + annotation tap-delete), curate dump (4 entries after merge… 3 at walk time), round B report editor, delete-report dialog, report view, back-to-editor, provider vertex→deepseek round-trip, import dialog (empty project), logout→401→login, rotate leg | 15 screenshots; lens Select/Keep/annotation tap-delete executed by tap; every real tap leg **succeeded**; h-fit failures only F-m9-2-1/F-m9-2-2 |
| 360x800 | **all 7 surfaces ok**: 360 == 360 | same walk minus logout/rotate | Discard executed by tap; all tap legs succeeded; h-fit failures only F-m9-2-1/F-m9-2-2 (same two controls) |
| 768x1024 | **all surfaces ok** (7 checked) | same walk | **0 failures**; Edit & add (merge) executed on tablet by tap; "All notes reviewed" hint visible |
| 1024x768 | all surfaces ok (5 checked) | same walk (desktop three-pane arrangement on touch device) | **0 failures** |
| 1280x900 | all surfaces ok (5 checked) | same walk + export download leg | **0 control failures**; export verified (API GET 200, 282 B — see below) |

Screenshots (64): `screens/m9-2-{390,360,768,1024,1280}-{login,projects,doc-open,stage-controls,
annotate-panes,annotate-panes-after,curate,report-editor,report-view,report-editor-again,
import-dialog,provider}.png`, `m9-2-390-{logout-login,annotate-before-tap-delete}.png`,
`m9-2-rotate-390-{phone-start,phone-back}.png`.

R-084 rotation leg (390 ctx, doc alpha open, round A reading): 768 (strip ✓ doc ✓ round A ✓) →
1024 (strip gone, sidebar ✓ doc ✓ round A ✓) → 768 (strip back) → 390; **0 navigations during leg**
(rotate-leg record); arrangement flipped narrow↔desktop on every boundary without reload; doc/round/
badge preserved on all four sizes.

## Use cases / §11.2 steps 24-25 legs (expected vs actual)

| Leg | Expected (spec) | Actual | Result | Evidence |
|---|---|---|---|---|
| UC-24/step 24 phone journey — login when gated | login page renders usable at phone width, no h-scroll | GET /login 200 + viewport meta; login ok at 390 and 360; overflow ok | PASS | screens m9-2-390/360-login.png; backend log :93-145 login bursts (302s) |
| UC-24 — project + dialogs (new/delete/import/new-round) | dialogs fit viewport, footers reachable | new-project, delete-project, delete-report, import dialogs opened per width; footer buttons present + in-view at all 5 widths | PASS | present records; m9-2-\*-{projects,import-dialog,report-editor}.png |
| UC-24 — doc read full-width, no horizontal page scroll | content reflows, single column | alpha.md read at all widths; docScrollW == innerW everywhere | PASS | overflow records all widths; m9-2-\*-doc-open.png |
| UC-24 — highlight + anchored note from selection (mouse leg) | selection → highlight/note | real mouse-drag selection; POST highlights 201 + notes 201 | PASS (fixture leg) | backend log :670-671; p1 transcript |
| UC-24 — lenses: propose/select, review expert notes, run experts | controls reachable; AI actions not run | propose + run-experts present (never clicked); lens Select tapped @390 (PATCH 200, log :700); note review Keep@390 (:701), Discard@360 (:804), Edit&add@768 (:887); expert-run notes render w/ badges | PASS | tap/present records; m9-2-\*-annotate-panes*.png |
| UC-24 — curate dump + save + generate reachability | curate surface usable at phone width; generate never fired live | curate renders seeded dump entries (3→4 after merge leg); Save dump + Generate present, generate enabled (never clicked); AI thought/highlight/human-thought badges visible | PASS | m9-2-\*-curate.png |
| UC-24 — report editor/view switch, tone/critique reachability, export, delete report | editor/view toggle; AI assists not run; export works; delete dialog | 3 block textareas → View (view-block-* ×3, 0 textareas) → Edit back at every width; tone/critique present (never clicked); export GET 200 text/markdown 282 B (log :1088/:1131); delete-report dialog opened + cancelled | PASS except F-m9-2-1 (delete-report control clip at 390/360) | m9-2-\*-report-{editor,view}.png; report-export record |
| UC-25/iPad 768 portrait | tablet tier; panes overlay or secondary; no h-scroll | 0 failures; overlay nav used; annotate panes via overlay; merge executed by tap | PASS | w768.json; m9-2-768-\*.png |
| UC-25/iPad 1024 landscape | desktop tier with touch input | 0 failures; three-pane layout on touch ctx; taps succeed | PASS | w1024.json |
| UC-24 desktop regression leg | ≥1024 keeps desktop layout; steps-1..18 behavior unchanged | 1024/1280 walks green; desktop regression vitest green (part A); provider PUT round-trips ok | PASS | w1024/w1280.json |
| UC-26/R-084 | resize/rotate across class boundary: no reload, no lost surface, no h-scroll | rotate leg 4 widths, 0 navigations, doc/round/badge preserved every step | PASS | rotate-leg record; m9-2-rotate-390-*.png |
| UC-27/R-085 — tap-reachability incl. hover-hidden delete | coarse pointer reaches everything; delete-annotation tappable without hover | delete-annotation button opacity 1.0 without hover at phone ctx; real tap deleted the note (server 204, log :702); every other tap leg succeeded | PASS | annotation-tap-delete record |
| §11.1 additive pytest row | `GET /login` carries viewport meta | assertion green in make test; live server emits the exact meta (readiness probe) | PASS | Part A table |
| UC-27 — real-device legs (step 26: long-press, hover, on-screen keyboard, tunnel/https, SD-33 tap sizing) | on real phone/iPad via public hostname | **NOT run — residual human legs**, see below | RESIDUAL | — |

## Live calls: none-run gate statement

**No live AI calls were made.** No lens proposal, no expert run, no dump-driven generation, no tone
sample, no critique request was ever issued — the AI-firing controls (Propose lenses, Run experts,
Generate report, Change of tone, Critique) were only presence/visibility-checked and never activated;
their disabled states were asserted where expected. All other network traffic went to the isolated
uvicorn on 127.0.0.1:8010. Provider selector legs switched deepseek→vertex→deepseek (non-AI PUTs,
log :1024/:1025/:1096/:1097) and left the project on `deepseek`.

## Log review

- `m9-2-backend.log` (1131 lines, uvicorn access on 127.0.0.1:8010): no 4xx/5xx beyond the intended
  gate probes (401 wrong-key readiness probe :9; 401 logout-leg probe) — no 500s anywhere. Key cites:
  :5-11 gate-on login surface + 401 probe; :661 POST /projects 201; :665 POST /projects/5/import 201
  (browser-picker multipart); :670/:671 POST highlights/notes 201 (mouse selection legs); :672/:676
  POST /rounds 201; :681 POST /projects 201; :700 PATCH lens-proposals/5 200 (Select tap @390); :701
  PATCH expert-notes/7 200 (Keep @390); :702 DELETE /annotations/6 204 (tap-delete @390); :776 POST
  /logout 302 (@390); :804 PATCH expert-notes/8 200 (Discard @360); :887 POST expert-notes/9/merge
  201 (Edit & add @768); :1024/:1025/:1096/:1097 PUT /projects/5/provider 200 (selector round-trip);
  :1088/:1131 GET /reports/3/export.md 200; :1105/:1116/:1127 GET / 200 (SPA index), :1118/:1128/1129
  GET /assets/* 200 (R-076 static serving through FastAPI).
- `m9-2-browser-console.log` (4 lines, all explained, none an app defect): 2× `DELETE
  /api/v1/annotations/{4,6} ERR_ABORTED` (client-side abort of the delete fetch racing page teardown
  in the driver context — both deletions completed server-side, log :306/:702); 1× `GET /login
  ERR_ABORTED` (logout-leg navigation torn down with the context); 1× console.error 401 = the
  deliberate logout-leg API probe (expected gate response).
- `m9-2-driver-p3.log`: per-context transcripts incl. the action legs (Keep/Discard/merge/tap-delete/
  rotate) and the two context-level failure counts (390: 4, 360: 8 — all F-m9-2-1/F-m9-2-2 records,
  no other class).
- No unhandled page errors, no request failures, no ≥500 responses in any context.

## Failures and retries

- Driver iteration (reviewer-owned, not app defects): (1) project-card accessible-name mismatch
  (`int009-rr project #3` vs exact-name role query) → regex match; (2) generic `getByRole('dialog')`
  hidden-waits collided with the still-open nav overlay at narrow widths → dialog-name-scoped waits;
  (3) doc-row click raced the workspace's initial tree fetch → settle signal (idle-hint) + retry
  wrapper; (4) strict-mode duplicate-text locators → state-conditional checks; (5) blob-download
  event not surfaced in headless at 1280 → export re-verified via the API GET (200, 282 B). Each fix
  recorded in driver logs; the final v5 run is the evidence run.
- App-level: F-m9-2-1 + F-m9-2-2 (below) are the only failures reproduced across runs; both verified
  at fresh-rest geometry (scrollLeft 0) in a dedicated probe (`probe-fresh-rest` transcript).

## Findings

- **F-m9-2-1 (CODE_BLOCKER, layout)** — `frontend/src/screens/workspace/ReportEditor.tsx` toolbar row
  (buttons container `flex items-center gap-2`, no wrap): at fresh-rest 390 and 360 CSS px the row
  spans x=20..459; the rightmost "Delete report" control (x=332, w=127) is clipped to 58/127 px
  visible at 390 and 28/127 px at 360; its center (x≈395.5) sits outside both viewports and the
  overflow-hidden workspace root is not user-scrollable, so the control cannot be scrolled into view
  on a real device; at 360 the visible tap target is below the 44 px touch-target guideline (SD-33
  residual leg list). Violates R-082 ("no clipped or unreachable controls"; delete report must be
  reachable at phone width) and the §11.3 emulated-phone leg (spec.md:455). Impact: report deletion
  from 360-390 px phones is effectively blocked for a normal tap. Correction: allow the toolbar group
  to wrap (`flex-wrap` on the buttons container, same pattern as the report header row and
  RoundStageHeader) so all four controls fit within 320 px; re-run the 360/390 report-editor surface
  leg. Evidence: fresh-rest probe numbers; w390/w360 present records
  (`report-editor: 'delete-report' hFit=false`); screenshots `m9-2-{390,360}-report-editor.png`;
  taps succeeded only via programmatic scroll (driver artifacts, not user-reachable).
- **F-m9-2-2 (WARN, layout)** — `frontend/src/screens/workspace/RoundStageHeader.tsx` mode-button
  group (non-wrapping `flex items-center gap-1.5`): the row's right edge is 395 px, so at 390 the
  "Report" button tail is clipped by 5 px and at 360 by 35 px (button 82%/62% visible; center x≈349
  stays in-viewport at both widths, so taps work — tap legs succeeded). Violates the R-082 "no
  clipped controls" letter at the button's edge; minor because the whole button remains reachable.
  Correction: same wrap/gap fix (or reduce gap/padding by ~40 px). Evidence: w390/w360
  round-stage-controls records; fresh-rest probe (modeBtns right=395 at both widths).
- **N-m9-2-1 (NIT, harness)** — 1280-ctx blob download: headless chromium did not surface the
  `download` event for the SPA's client-side blob export; export itself verified via the API (200,
  text/markdown, attachment, 282 B). No app impact.

## Residual human UX checks (not automatable here — step 26 real-device legs)

Listed as residual per §11.2 step 26 (real phone/iPad through the public hostname
`writer-assistance.rohanawhad.com` — the container/tunnel from INT-006 M3 was left running and out of
scope for this isolated review):
1. **Long-press text selection → highlight + anchored note on a real touchscreen** (R-085 selection
   leg; SD-33 says extend MarkdownView's mouse-only selection plumbing only if this fails — it was
   mouse-verified here at P1: real drag-selection produced highlight + anchored note; long-press
   behavior itself needs a device). Owner: human (step 26).
2. **Hover-visibility semantics on real devices**: verified at emulation level (delete-annotation
   opacity 1.0 without hover at the touch ctx, tap deleted) — final confirmation on device.
3. **On-screen keyboard legs** (typing into note/dump/block/dialog fields, field kept in view): only
   mouse/keyboard input was possible headless; block textareas and note fields were verified reachable
   and tappable at every width.
4. **Real tunnel/https + SD-33 tap-target sizing**: https login/flow and tap targets ≥44 px on the
   physical device; F-m9-2-1's 360-px delete-report target (28 px) is expected to fail this check as
   measured.
5. **Rotation on a physical device** (accelerometer-driven, not viewport-resize): resize-driven
   rotation passed with 0 reloads; physical rotation confirm pending.

Owner/disposition for all residual legs: human step-26 pass after F-m9-2-1 is corrected.

## Cleanup

- Stopped: only the reviewer-started uvicorn (127.0.0.1:8010); the pre-existing 127.0.0.1:8000
  container process (pid 3619411, INT-006/008 work) was never touched. Port 8010 verified free
  after shutdown (`ss -tln`).
- Removed: `/tmp/opencode/m9-2` (fixtures, isolated DB, driver scripts, results copies); driver
  browser processes exited with the node runners.
- Untouched: `backend/data/writer-assistance.db` (mtime/size/md5 identical to the run-start baseline);
  no repo files modified, nothing staged/committed.

---

# Round 2 (independent re-review of F-m9-2-1 / F-m9-2-2 fix), 2026-09-04

## Round-2 verdict

**PASS.** F-m9-2-1 and F-m9-2-2 both closed by the builder's `flex-wrap` fix; re-run of the previously
failing 360/390 report-editor + round-stage-header leg is green at both widths (raw numbers below),
with a fresh 1280 desktop probe confirming the ≥1024 layout is byte-identical in geometry (toolbar
single line, no wrap triggered). Round-1 residuals (step-26 real-device legs) remain human-owned
residual checks and do not block PASS. N-m9-2-1 (round 1 NIT) stands disclosed, unaffected.

## Fix under review (tracked worktree delta vs HEAD a33e4ad)

`git diff HEAD --stat` = 3 files, 4 lines: the round-1 backend assertion
`backend/tests/test_auth_gate.py` (+1, unchanged since round 1) plus exactly two `flex-wrap`
insertions, each one line, no other change:

- `frontend/src/screens/workspace/ReportEditor.tsx:187` — toolbar buttons container
  `flex items-center gap-2` → `flex flex-wrap items-center gap-2` (parent header row at :179 was
  already `flex-wrap`, matching the round-1 suggested pattern).
- `frontend/src/screens/workspace/RoundStageHeader.tsx:50` — mode-button group
  `flex items-center gap-1.5` → `flex flex-wrap items-center gap-1.5` (parent header at :28 was
  already `flex-wrap`).

Desktop-≥1024 invariance argument (verified, not just argued): `flex-wrap` only reflows when a
flex line overflows its container; both parents are already wrapping rows and the inner groups fit
with large margin at ≥1024. Confirmed empirically by the 1280 probe below (all four report-editor
toolbar buttons share top=206.0, single line) and by the unchanged desktop regression suite.

## Gates (round 2, reviewer-run)

| Gate | Command (dir) | Result |
|---|---|---|
| frontend vitest | `npm test` (frontend/) | 11 files, 63 tests passed, exit 0 |
| frontend tsc | `npm run typecheck` (frontend/) | clean, exit 0 |
| frontend eslint | `npm run lint` (frontend/) | clean, exit 0 |
| backend pytest (belt-and-braces; backend delta unchanged from round 1) | `make test` (backend/) | 136 passed, 8 skipped, 1 warning, exit 0 — identical to round 1 |
| repo hygiene | `git status --porcelain` | only the 3 tracked m9-2 files modified; nothing staged/committed |

## Integration re-run (the previously failing leg)

Setup mirrored round 1: isolated DB `/tmp/opencode/m9-2-r2/db/m9-2-r2.db` (fresh; seeded without any
AI call — project `int009-r2` id 1, `alpha.md`/`beta.md` fixtures md5 `a63468d1…`/`6101b748…`,
round 1 `int009 R2 report round` stage `editing`, own dump + report 1 + 3 ordered blocks + 3
source-entry links — state verified via API before the walk: GET /projects 200, GET /rounds/1 200,
GET /reports/1 200). Gate ON (`AUTH_API_KEY` from backend/.env into process env, value never
recorded); uvicorn `app.main:app` on 127.0.0.1:8010 (port verified free; pre-existing 127.0.0.1:8000
container untouched); `npm run build` in frontend/ → fresh dist (`index-DzNNW1L4.js`; round-1 bundle
was `index-BpZAiECd.js`, so the served SPA provably includes the wrap fix — assets 200 in the log).
Driver: playwright 1.62.1 chromium headless from `.hai/node_modules`, iPhone UA, touch/mobile
contexts at 390x844 and 360x800 CSS px. Console/pageerror/requestfailed listeners throughout.

**One setup error caught and corrected mid-run (reviewer-owned, no app impact):** the first uvicorn
start omitted `WRITER_ASSISTANCE_DB` and briefly pointed at the dev DB; it was killed after only
stateless GETs + a cookie-login (no writes — dev DB md5 re-verified identical after, see Cleanup)
and restarted with the isolated DB env set. Isolated-DB probes then returned the seeded fixture.

### Measured numbers (fresh-rest geometry, `getBoundingClientRect`; results JSONs `w390-r2.json`,
`w360-r2.json` retained in this directory)

| Width | Delete report bbox (was, round 1) | Delete report bbox (now) | Fully in viewport | Click → dialog | Cancel → editor intact | Round-stage "Report" tab right edge (was 395) | Report tab fully visible | Page h-scroll (docScrollW vs innerW) |
|---|---|---|---|---|---|---|---|---|
| 390x844 | x=332..459, clipped 58/127 | x=20.0..147.0 (w=127, centerX=83.5) | yes | opened ("Delete report?" dialog, full-width 0..390) | yes, delete button back at same bbox | 110.2 (doc mode) / 110.2 (report mode) | yes (left 20.0, right 110.2) | 390 == 390, none |
| 360x800 | x=332..459, clipped 28/127 | x=20.0..147.0 (w=127, centerX=83.5) | yes | opened (dialog 0..360) | yes, same bbox | 110.2 (doc mode) / 110.2 (report mode) | yes | 360 == 360, none |

Both widths also: mode group right edge 298.4 ≤ viewport (was 395 at both); the group now wraps
internally (Read & annotate + Curate dump line 1, Report line 2) instead of overhanging the
viewport. Delete report, previously clipped/unreachable without programmatic scroll, is now fully
on-screen and was clicked with a plain user-equivalent click at its center — the confirm dialog
opened and Cancel closed it with the editor intact (post-cancel bbox identical: 20.0..147.0).
Numbers reproduced identically across 3 consecutive driver runs (deterministic).

### Desktop regression probe (≥1024 invariance)

1280x900 desktop context (no touch): report-editor toolbar buttons all share top=206.0/bottom=238.0 —
View x=308.0..386.3, Edit x=394.3..467.8, Download .md x=475.8..611.8, Delete report x=619.8..746.8 —
**single line, no wrap**, docScrollW 1280 == innerW (w1280-r2.json). Geometry unchanged from the
round-1 desktop walk (F-m9-2-1 was measured only at 390/360).

### Screenshots (round 2)

`logs/hai-build-loop/screens/m9-2-r2-390-report.png`, `m9-2-r2-360-report.png` (report-editor
surface at each width with the delete-report control on-screen), plus `m9-2-r2-1280-report.png`
(desktop single-line toolbar).

## Round-2 log review

- `m9-2-r2-backend.log` (112 lines, uvicorn access): 89× 200, 19× 302 — the 302s are exclusively the
  intended gate redirects (GET / → /login on fresh contexts and POST /login success redirects);
  **zero 4xx/5xx, zero tracebacks/errors** (status scan). Cites: :5-31 login bursts + fresh SPA
  bundle 200s (`assets/index-DzNNW1L4.js` 200 at :13/:24/:34); :8 GET /api/v1/reports/1 200
  (seed probe); every context walk ends with GET /rounds/1 + GET /reports/1 200. No report DELETE
  was ever issued (dialog cancelled by design).
- `m9-2-r2-console.log`: "(no console errors or request failures)" across both contexts.
- Driver transcripts `w390-r2.transcript.log` / `w360-r2.transcript.log` retained; driver iteration
  (round-2 only): narrow-mode hides the round list behind the "Resources & rounds" overlay, so the
  driver opens it before selecting the round (harness issue, not an app defect — matches round-1
  driver notes about overlay navigation).

## Round-2 findings

None open. F-m9-2-1 and F-m9-2-2 closed; no new defects observed; N-m9-2-1 (round-1 NIT, harness,
blob-download in headless) stands disclosed with no app impact; round-1 step-26 real-device legs
remain residual human UX checks (do not block PASS).

## Round-2 cleanup

- Stopped: only this reviewer's uvicorn (127.0.0.1:8010); port verified free after shutdown.
- Removed: `/tmp/opencode/m9-2-r2` (fixtures, isolated DB, seed, driver scripts, results copies).
  Evidence copies (backend log, console log, results JSONs, transcripts, screenshots) retained
  under `logs/hai-build-loop/` per convention.
- Untouched: `backend/data/writer-assistance.db` — md5 `4cea2ff4…`, size 143360, mtime
  2026-09-03 23:17 unchanged from the round-1 baseline (re-verified after the env-var slip above);
  the pre-existing 127.0.0.1:8000 container was never touched; no repo files modified by this
  review, nothing staged/committed.
