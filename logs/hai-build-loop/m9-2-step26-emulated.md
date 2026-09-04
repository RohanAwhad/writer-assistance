# INT-009 §11.2 step-26 emulated device-leg evidence: m9-2-s26 (DEVICE_TEST_AGENT)

Reviewer-owned emulated real-device run, 2026-09-04. **OFFLINE** — no live AI calls, no providers
engaged, no lens/expert/generate/tone/critique action ever fired; the app ran isolated on loopback
with a fresh DB. Scope: §11.2 step 25 ("iPad journey (emulated)"), the step-26 touch legs **as far
as headless emulation can reach** (long-press selection under CDP touch, hover-only controls,
rotation, tap targets, horizontal-scroll scan on every surface), SD-31 tier verification, and the
SD-33 selection-plumbing contingency.

Evidence under `logs/hai-build-loop/`: `m9-2-s26-backend.log` (uvicorn, 3556 lines),
`m9-2-s26-<device>.console.log` (per-device browser console — **all 6 files empty** and
`m9-2-s26-<device>.json` (per-device measurement records), screenshots
`screens/m9-2-s26-*` (51 files). Driver scripts ran from `/tmp/opencode/m9-2-s26/drivers`
(repo untouched; `.hai/playwright.config.ts` never touched).

## Verdict

**PASS-equivalent for the emulated step-26 legs** — scroll scan, tap-target reachability, hover
control, rotation, and tier mapping all green on every context; **one WARN-grade finding
(F-s26-1, touch-selection emulation)** closed per the **SD-33 contingency**: CDP-touch emulation
never creates a native text selection, so the app's mouse-only selection plumbing could not be
proven under emulation — per spec the contingency trigger, the plumbing was extended (minimal
`selectionchange` hook, `frontend/src/components/MarkdownView.tsx`, **+15/−3 lines**), games
verified (suite green, affordance flows via selection → panel → touch-tap → POST 201), and the
real-device leg remains a residual human check. No CODE_BLOCKERs. Two NITs (tap sizing below the
~40 px guideline, one 26 px hidden overflow at 1194 curate). No SPEC_CHANGE_REQUESTED, no
HAI_CHANGE_REQUESTED.

## Environment

- Worktree branch `built-using-hai`; **tracked worktree delta: 1 file, +15/−3 lines** —
  `frontend/src/components/MarkdownView.tsx` (SD-33 contingency; NOT committed, NOT staged;
  spec.md / .hai/state.yaml / .hai/playwright.config.ts untouched). Untracked additions: evidence
  artifacts under `logs/hai-build-loop/` + `screens/`.
- Backend: FastAPI via `uv run uvicorn app.main:app` (Python 3.13, backend dir) on
  **127.0.0.1:8010** (port was free — `ss -tln` before bind; the pre-existing 127.0.0.1:8000
  container from INT-006/008 was NEVER touched). Gate **ON** (`AUTH_API_KEY` sourced from
  `backend/.env` into the process env — value never written anywhere, env NAME only). DB:
  **isolated** `WRITER_ASSISTANCE_DB=/tmp/opencode/m9-2-s26/db/s26.db`; the dev DB
  `backend/data/writer-assistance.db` was never pointed at or touched (md5
  `4cea2ff4e71f710e3f81f09002bc36f1`, size 143360, mtime 2026-09-03 23:17 — re-verified at
  cleanup).
- Frontend: `npm run build` in `frontend/` → fresh dist; uvicorn served the SPA (R-076):
  final bundle `assets/index-CNe9-E7L.js` 200 (backend log :3406-3408; earlier phases served
  `index-DzNNW1L4.js`, the pre-contingency bundle — evidence distinguishes the phases).
  The fixed bundle includes the SD-33 plumbing change.
- Browser: playwright 1.62.1 from `.hai/node_modules` (chromium headless; browser cache
  `~/.cache/ms-playwright/chromium-1234` present — no install needed). Driver scripts under
  `/tmp/opencode/m9-2-s26/drivers` (ESM via createRequire; nothing added to the repo).
- Device contexts: CSS-px viewports with `isMobile`/`hasTouch` per SD-31 tier, DPR per device
  profile, iPhone/iPad UAs (from Playwright's `devices` descriptors).

## Fixture (isolated DB only)

- md5-baselined Markdown fixtures (created for this run): `alpha.md` `bb574e2f…` (775 B),
  `beta.md` `e2e52065…` (487 B), `gamma.md` `0cc46e46…` (478 B).
- UI-created (setup driver, desktop 1280x900, gate-on, through the served SPA, browser picker):
  project `int009-device-s26` + `int009-device-empty` (backend log :22 POST /projects 201 and
  :33/:73); `alpha.md`+`beta.md`+`gamma.md` imported via the browser picker (`POST
  /api/v1/projects/1/import 201`, :77 — port 33128/59236 session; multipart, no server path);
  alpha.md opened; mouse-drag selection → highlight (`POST /resources/1/highlights 201`, :214)
  and anchored note ("Fixture anchor note from the curated selection.", `POST
  /resources/1/notes 201`, :215); round `int009-device A` (reading, id 1) created over all three
  docs via the new-round dialog (`POST /rounds 201`, :216).
- DB-seeded (seed.py, python sqlite3 against the isolated DB — state a live-AI round would have
  left, inserted with no AI call): round A — 2 lens proposals (1 proposed / 1 selected), 1 expert
  run (alpha) with 3 pending expert notes, saved dump + 3 entries (ai-thought / highlight /
  human-thought); round B `int009-device B` — stage `editing`, own dump + 3 entries, report 1 +
  **3 ordered blocks** + report_block_links. Verified via the gate-on API before the walk (all
  statuses logged below): `verify.py` — POST /login 302, GET /projects 200, /rounds/1 200,
  /rounds/1/dump 200, /rounds/1/expert-runs 200, /rounds/2 200, /reports/1 200,
  /reports/1/export.md 200 (log :220-232).

## Commands and results (existing gates re-checked for the contingency change)

| Gate | Command | Result |
|---|---|---|
| frontend tsc | `npm run typecheck` (frontend/) | clean |
| frontend eslint | `npm run lint` | clean (0 warnings after the useCallback wrap) |
| frontend vitest | `npm test` | 11 files, **63 tests passed** (incl. responsiveView + markdown selection suites) |
| frontend build | `npm run build` | success, `index-CNe9-E7L.js` 345.26 kB |
| git diff count | `git diff --stat` | 1 file, +15/−3 |
| .hai state | **not re-run** (repo-process; no .hai change made) | untouched |

## Device matrix (one context per row; 11 surfaces walked per device: projects, projects-create
dialog, doc-open, round-stage-controls, new-round dialog, annotate-panes, curate, report-editor,
report-delete-dialog, report-view, import-dialog — every surface overflow-checked + measured)

| Device | Viewport (CSS px) | Tier per SD-31 (matchMedia) | Page h-scroll (scrollW == innerW) | Controls measured (in/off viewport) | Annotation delete opacity (no hover) | hidden hover-only controls | Long-press leg | Rotation leg | Screenshots |
|---|---|---|---|---|---|---|---|---|---|
| iPhone 13 | 390x844 (DPR 3) | **phone** (768 breakpoint not crossed); narrowControls present, no sidebar | **11/11 PASS** | 24 in / 0 off | **1** | none | CDP long-press + drag: selection 0 (see F-s26-1) | 390x844 → 844x390 → back: 0 navigations, `__noReload`=42, doc preserved, tier flips phone→tablet | `-iphone13-{login,projects,doc-open,annotate-panes,curate,report-editor,report-view,report-delete-dialog,import-dialog,landscape-844,selection-after-{longpress,touchdrag,highlight},selection-cdp-touch}.png` |
| iPhone SE-ish | 360x800 (DPR 2, iPhone UA) | **phone** | 11/11 PASS | 24 in / 0 off | 1 | none | n/a (phone leg run on iPhone 13 ctx) | n/a | `-iphone360-{doc-open,annotate-panes,curate,report-editor,report-view,report-delete-dialog,import-dialog}.png` |
| iPad (gen 7) | 768x1024 (DPR 2, iPad UA) | **tablet** (768–1023); narrowControls present, no sidebar | 11/11 PASS | 24 in / 0 off | 1 | none | n/a | n/a | `-ipad768-{doc-open,annotate-panes,curate,report-editor,report-view,report-delete-dialog,import-dialog}.png` |
| iPad Pro 11 portrait | 834x1194 (DPR 2) | **tablet** | 11/11 PASS | 24 in / 0 off | 1 | none | n/a | **PASS** — 834x1194 → **1194x834** → back: 0 navigations, `__noReload`=42, doc/mode preserved, narrow controls disappear at ≥1024 (three-pane) and return at 834; land overflow 1194==1194 | `-ipadpro11-834-{doc-open,annotate-panes,curate,report-editor,report-view,report-delete-dialog,import-dialog,landscape-1194,back-portrait}.png` |
| iPad Pro 11 landscape | 1194x834 (DPR 2) | **desktop (≥1024)**; sidebar present, no narrow controls | 11/11 PASS (+1 NIT inner overflow, F-s26-3) | 24 in / 0 off | 1 | none | n/a | n/a | `-ipadpro1194-{doc-open,annotate-panes,curate,report-editor,report-view,report-delete-dialog,import-dialog}.png` |
| Desktop regression | 1280x900 (no touch) | **desktop** | 11/11 PASS | 24 in / 0 off | **0** (hover-only by design; `@media(hover:none)` correctly does not match) | 1 (Delete annotation — expected on pointer devices) | n/a | n/a | `-desktop1280-{doc-open,annotate-panes,curate,report-editor,report-view,report-delete-dialog,import-dialog}.png` |

Per-device records: `logs/hai-build-loop/m9-2-s26-<device>.json` (`surfaces`, `controls`,
`hover`, `tier`, `rotation`, `longpress`). Touch contexts all report `hoverNone: true` and
`narrowControls` per tier; desktop1280 reports `hoverNone: false` — the SD-33 `@media
(hover:none)` delete-control rule and the new selectionchange hook both scoped to coarse pointers
only, so **desktop mouse behavior is unchanged** (also covered by the unchanged vitest suites).

Controls measured on every context (all inside viewport, none clipped): New project +
projects dialogs footers (Cancel / Create and open / Delete project), back (Projects), AI
provider select, round stage modes (Read & annotate / Curate dump / Report — single row wrapping
internally; Report tab at x=20..110, fully visible — F-m9-2-1/F-m9-2-2 from m9-2 remain closed),
new-round + delete-report dialogs footers, report toolbar (View / Edit / Download .md / Delete
report — Delete report wraps to its own row at 390/360, x=20..147, fully on-screen), annotation
delete (14x14 px — inside viewport), import dialog footers (Choose files… / Cancel / Import).

## Use cases / §11.2 step 24-26 legs (expected vs actual)

| Leg | Expected (spec) | Actual | Result | Evidence |
|---|---|---|---|---|
| UC-24/step 24 phone journey | no h-scroll, single column, all dialogs reachable | 390 & 360: 11/11 surfaces pageOk; dialogs fit (footer buttons 340x36 at 390, fully inside); annotation/lens panes behind overlay toggles; back to desktop at ≥1024 | PASS | m9-2-s26-iphone13/360 JSONs; backend log walk session :3403-3556 |
| UC-25/iPad portrait 768 | tablet tier, full-width column, panes overlay/tiered | tablet tier; overlay nav + panes; no h-scroll | PASS | ipad768.json; `-ipad768-*.png` |
| UC-25/iPad 1024+ landscape | desktop tier unchanged with touch input | desktop tier at 1194; sidebar layout; taps work | PASS | ipadpro1194.json; `-ipadpro1194-*.png` |
| UC-24/R-084 adaptation | reflow on width change, no reload, no lost surface | both rotate legs: 0 navigations, `__noReload`=42 preserved, active doc + round + mode survive; narrow/desktop chrome flips at the 768/1024 boundaries | PASS | rotation records; `-ipadpro11-834-{landscape-1194,back-portrait}.png`, `-iphone13-landscape-844.png` |
| UC-27/R-085 hover parity | no action hidden behind hover-only styling on touch | delete-annotation computed opacity **1** on all touch context screenshots from the panes overlay; scan of `[class*="group-hover"]` reports zero opacity-0 elements on touch contexts (desktop context: opacity 0 unless hovered — intended) | PASS | hover records per JSON; `-annotate-panes.png` |
| UC-27/R-085 tap targets | primary actions ≈40-44 px, none clipped | none clipped/off-viewport; all measured controls are h=32-36 px (size-sm/default buttons), provider select h=28, delete icon 14x14 — below the guideline → NIT (F-s26-2) | PASS with NIT | controls records; sizes above |
| UC-27/R-085 selection leg (step 26) | long-press-selected text → highlight + anchored note | CDP `Input.dispatchTouchEvent` long-press (700 ms) and touch-drag produce **no text selection** in headless Chromium (`getSelection()` empty; `selectionchange` fired twice for the collapse; no `contextmenu`). Native-equivalent selection (Range #59 API) → app surfaces the selection affordance and a touch-tapped Highlight created the highlight (POST 201, mark rendered). Emulation cannot produce the native gesture → **SD-33 contingency implemented** (MarkdownView selectionchange hook) | WARN → mitigated in-app; real-device confirm still residual (see F-s26-1) | `-selection-after-{longpress,touchdrag,highlight}.png`; longpress JSON; backend :2410 |
| Step 24/25 desktop regression | ≥1024 layout + 1..18 behaviors unchanged | 1194/1280 walks green; hover delete opacity 0 (design), desktop mouse selection unchanged (fixture leg + vitest) | PASS | desktop1280.json |
| §11.3 done-gate environment check | offline, gates green | backend offline suite untouched (no backend change); frontend gates green (above) | PASS | Commands table |

## Live calls: none (statement)

**No live AI calls were made — zero.** No lens proposal, expert run, dump generation, tone sample
or critique was ever issued (the AI-firing controls were present/visibility-checked only, never
activated; "Run expert" was rendered with the seeded lens but never tapped). All traffic went to
the isolated uvicorn on 127.0.0.1:8010.

## Log review

- `m9-2-s26-backend.log` (3556 lines; multiple uvicorn sessions appended — evidence distinguishes
  phases by bundle hash and port client). Cites: gate-on readiness probes :5-14 (GET /login 200,
  GET /api/v1/projects 401, POST /login 302, subsequent 200s); fixture creation :22/:33/:73 (POST
  /projects 201), :77 import 201 (browser-picker multipart), :214/:215 highlights/notes 201
  (mouse fixture leg), :216 POST /rounds 201; verify-probe block :220-233 (all 200 with one 404
  at :233 — the reviewer's ad-hoc `GET /resources/1/highlights` guess; there is no GET highlights
  route — the app uses /annotations; harness-only, no app impact); **post-contingency highlight
  leg :2410 POST /resources/1/highlights 201** (touch-tapped Highlight off a
  selectionchange-driven selection); final walk session :3403-3556 (GET / 302 → login → SPA,
  `assets/index-CNe9-E7L.js` 200 at :3407/:3408, all surface reads 200 including
  /rounds/1/dump/:3549-3552). **No 5xx anywhere; the only 4xx are the intended gate 401/302
  probes and the one harness 404.**
- Browser console logs: **all 6 device console files empty** — zero console.error, zero page
  errors, zero request failures in any context.
- Per-device JSONs: `report.errors` contains only the view-mode textarea-count check
  ("expect 0: 0" → positive check) on every device; no runtime exceptions.

## Failures and retries (harness-side only, no app defects found here)

1. First setup attempts left duplicate projects after two aborted driver runs (locator issues) →
   the isolated DB was recreated (rm + uvicorn restart) and the setup driver re-run once — final
   fixture is the single clean project (evidence: backend log has one coherent 201 sequence
   :73-216 in the final DB session).
2. Driver transition bugs (all harness): SPA keeps URL at `/` (no router) → waitForURL replaced
   with state-based waits once identified; tap on `open-nav-overlay` blocked while the nav
   overlay was already open (backdrop intercept; and the Projects back button behind an open
   overlay) → `ensureNavOpen`/`ensureNavClosed` helpers; import dialog on phone lives inside the
   closed overlay → overlay opened before use. All 6 final-context runs completed with **0
   FATALs**.
3. MarkdownView mouse-drag in the setup driver initially produced a stale-range drag; probing
   (probe-select2.mjs) showed plain drags work — setup uses a simple drag now.

## Findings

| ID | Category | Device | Evidence | Impact | Suggested fix |
|---|---|---|---|---|---|
| F-s26-1 | WARN (then mitigated) | all touch ctxs (emulated) | `-selection-after-longpress/touchdrag.png`; longpress JSONs: `sel:""` both legs, `selectionchange`: 2 (collapse only), `contextmenu`: 0 | Headless Chromium does not emulate the native long-press/drag text-selection gestures, so the app's selection path could not be *proven* by the emulated finger — per SD-33 this is the contingency trigger, not a proven device failure | **Done (SD-33):** `frontend/src/components/MarkdownView.tsx` listens to document `selectionchange` when `(hover: none)` matches and feeds the existing handler (+15/−3). Verified: native-equivalent selection → selection panel + Highlight in panes → touch tap → POST 201 + mark rendered (:2410). Mouse/keyboard path untouched (desktop hover != none; vitest green). Remaining: real-device (step 26) confirmation of the native gesture end-to-end |
| F-s26-2 | NIT (tap sizing) | all devices | controls records (h=32/36 everywhere; provider select h=28; delete icon 14x14) | All controls visible, in-viewport and tap-verified, but below the ~40–44 px SD-33 comfort guideline — real-device tryout may prefer bumping `size="sm"` button height and the delete icon's hit area (SD-33 marks sizing two-way/tunable) | Bump sm-button height (e.g. h-9→h-10) and give the delete icon a padded hitbox (p-2) — after device tryout |
| F-s26-3 | NIT (layout) | iPad Pro 1194 curate | `ipadpro1194.json` curate: root grid `grid-cols-1 … lg:grid-cols-[1fr_320px]` scrollWidth clientWidth +26 (overflow-x-hidden) + two `truncate` spans +14/+4 | Content hides 26 px of scrollable width at ≥1024 curate; screenshots show no visible artifact; desktop side unaffected visually | none required; optional: min-w-0/gap check on the grid child at `lg` |
| F-s26-4 | NIT | 390/360 report surfaces | truncate spans +50/+57 on round-stage name | Round name ellipsizes (intentional `truncate`), complete name viewable only via… no title tooltip on the header — minor discoverability polish | optional: `title` attr on the stage name span |

## Residual human UX checks (cannot be proven headless — keep as step-26 human legs)

1. Native long-press selection on a **real iOS/Android** screen (gesture, magnifier, native
   selection handles + popups) → produce highlight/anchored note — F-s26-1's final confirmation.
2. On-screen keyboard (typing into notes/dump/block/dialog fields, field-in-view behavior):
   automated input is device-independent keyboard; OSK behavior (visual viewport, scroll-into-view)
   needs a device.
3. Physical rotation (accelerometer/viewport resize semantics of the device) — resize-driven
   rotation passed with 0 reloads on both tablets and phones.
4. Tunnel/https on a real phone/iPad via `writer-assistance.rohanawhad.com` (out of scope for
   this isolated offline run; container+tunnel are from INT-006 M3 and were left running).
5. Real hover-fires-vs-touch tap on the delete-annotation control (emulated: opacity 1 + tap
   verified; the real-detail check is the popup timing on each OS).

## Cone-owner note (run provenance)

- App code edited: `frontend/src/components/MarkdownView.tsx` **only** (SD-33 contingency,
  explicitly authorized in the run briefing, kept minimal, re-run).
- spec.md / .hai/state.yaml / .hai/playwright.config.ts: untouched. Nothing staged, nothing
  committed.

## Cleanup

- Stopped: only this run's uvicorn (127.0.0.1:8010); the pre-existing 127.0.0.1:8000 container
  was never touched. Port 8010 verified free after shutdown.
- Removed: `/tmp/opencode/m9-2-s26` (fixtures, isolated DB, drivers, screens copies). Evidence
  copies retained under `logs/hai-build-loop/` + `screens/` (51 png, 6 JSON, 6 console logs,
  1 backend log).
- Untouched: `backend/data/writer-assistance.db` — md5 `4cea2ff4e71f710e3f81f09002bc36f1`,
  size 143360, mtime 2026-09-03 23:17 identical to the run-start baseline; no repo files
  modified beyond the MarkdownView contingency delta; nothing staged/committed.

## Final-round re-run (SD-33 guard version, +27/−3) — BUILD_REVIEWER final round

2026-09-04 (same day, after the F-1 guard landed: `MarkdownView.tsx` now wraps the
selectionchange listener with collapsed-skip / input-textarea-activeElement-skip /
in-container anchor check, lines ~224-239; prior sections above used the guard-less
+15/−3 delta). Re-run on the **final code** with the same isolated technique; the
F-1 anchored-note leg is now proven with the guarded listener. Scope: only the emulated
touch legs (a-e) + gates; no other surface walked.

### Stack (identical technique to the original run)

- Backend: `uv run uvicorn app.main:app` on **127.0.0.1:8010** (port verified free before
  bind), gate ON via `backend/.env` (`load_dotenv`), DB **isolated**
  `WRITER_ASSISTANCE_DB=/tmp/opencode/m9-2-s26-final/db/s26.db`; dev DB untouched.
- Frontend: `npm run build` in `frontend/` → fresh dist; new final bundle
  `assets/index-NmKjymZI.js` served 200 (`m9-2-s26-final-backend.log` :14/:31/:46/:59).
- Browser: playwright 1.62.1 from `.hai/node_modules`; contexts per `devices` descriptors.
- Fixture (fresh): project `int009-final` (POST /projects 201) + `alpha.md`
  (the three-sentence doc above, md5 not baselined this round) imported via the
  multipart API `/api/v1/projects/1/import` 201; resource id 1.
  Doc text: `# Alpha doc` / s1 = "The quick brown fox jumps over the lazy dog."
  (file offsets **13–57**, auto-verified by `str.index`) / s2 = "The dog sleeps under
  the warm sun." (offsets **59–93**).

### Legs (driver `touch.mjs`; output `m9-2-s26-final-iphone13.driver.log`,
rotation leg `ipad.mjs` → `m9-2-s26-final-ipad.driver.log`)

| Leg | Command/technique | Result | Evidence (log lines) |
|---|---|---|---|
| a | iPhone 13 ctx (390×844 DPR3 hasTouch): CDP `Input.dispatchTouchEvent` long-press (700 ms) → `getSelection()` is `""` (headless Chromium still cannot produce the native gesture; same as original run) → native-equivalent Range `addRange` drives `selectionchange` → panel popped with "Selection: “The quick brown fox …”" | **PASS** | iphone log :6, :7-8; `screens/m9-2-s26-final-01-selection-panel.png` |
| b | Touch-tap **Highlight** → POST `/resources/1/highlights` **201**; request payload `{"start_offset":13,"end_offset":57,…}`; API read-back row id 1 anchored 13–57 | **PASS** | iphone log :9-11; backend log :22 |
| c | **F-1 leg**: select s2 (59–93) → tap "Note on selection" → composer opened, textarea focused (`document.activeElement` = TEXTAREA) → tapped textarea + `getSelection().collapse()` (real collapsed `selectionchange` while TEXTAREA active — the guard trigger) → typed "Final-round focused composer note." → tap Save → POST `/resources/1/notes` **201**, payload `{"content":…,"start_offset":59,"end_offset":93}` — **anchor survived the guard scenario**; read-back row id 2 anchored 59–93; row renders "anchored" + s2 snippet | **PASS** | iphone log :13-19; backend log :24 |
| d | iPad (gen 7) ctx: 768×1024 → 1194×834 → 768×1024: **0 navigations**, `__loads` unchanged (1), doc text preserved, no h-scroll, narrow controls flip tablet→desktop→tablet | **PASS** | ipad log :2-15 |
| e | Browser console/pageerror/5xx: **0 / 0 / 0** (both contexts); uvicorn status census 200×37, 201×4, 302×8, **no 4xx/5xx**, no exception/traceback lines | **PASS** | iphone log :21-23; ipad log :17-19; backend log (status census above) |

Screenshots (3): `logs/hai-build-loop/screens/m9-2-s26-final-01-selection-panel.png`
(Selection panel + s1 quote + Highlight/Note-on-selection),
`m9-2-s26-final-02-composer-focused.png`, `m9-2-s26-final-03-note-saved.png`
(highlight anchored + note anchored rows).

### Gates (re-run on final code, this round)

| Gate | Command | Result |
|---|---|---|
| frontend vitest | `npm test` (frontend/) | 11 files, **63/63 passed** |
| tsc | `npm run typecheck` | clean (exit 0) |
| eslint | `npm run lint` | clean (exit 0) |
| .hai state | `npm run validate-state -- state.yaml` (.hai/) | valid: 9 intents, 29 decisions, 0 instructions, 3 research, 14 assumptions, 5 observations, 0 unapproved actions, 35 evidence, 1 open questions |
| diff | `git diff --stat` | 1 file, `frontend/src/components/MarkdownView.tsx` **+27/−3** (guard delta; HEAD `4387f2f` untouched) |

### DEC-029 interplay (check 4)

None. The delta is confined to `MarkdownView.tsx` selection plumbing — no import code,
no import-copy touch, no import-snapshot semantics. The import dialog's "snapshotted into
app storage once; resources become read-only here" copy (`LeftSidebar.tsx:309-311`) is
INT-008/DEC-029 (upload-later, H38) territory — **not this run's scope**, no interaction
with the selectionchange work.

### Cleanup (this round)

- Stopped: this round's uvicorn only (127.0.0.1:8010); pre-existing 127.0.0.1:8000
  container untouched. Port 8010 re-verified free after shutdown.
- Removed: `/tmp/opencode/m9-2-s26-final` (isolated DB, fixtures, drivers, logs).
- Untouched: `backend/data/writer-assistance.db` md5 `4cea2ff4e71f710e3f81f09002bc36f1`
  (size 143360) identical run-start → post-run; no repo files modified beyond the
  MarkdownView delta; nothing staged/committed.
- Evidence written this round: `logs/hai-build-loop/m9-2-s26-final-backend.log`,
  `logs/hai-build-loop/m9-2-s26-final-iphone13.driver.log`,
  `logs/hai-build-loop/m9-2-s26-final-ipad.driver.log`,
  `logs/hai-build-loop/screens/m9-2-s26-final-01/02/03-*.png` (+ this section).

### Residual (unchanged from original run, real-device only)

Headless long-press gesture itself still cannot produce the native selection — the native
gesture end-to-end and the on-screen-keyboard/rotation-accelerometer legs remain real-device
(step 26) human checks; the guarded code path is now proven under emulation.
