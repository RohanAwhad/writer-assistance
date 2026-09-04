# Integration evidence: M-INT007-INTEGRATION (milestone M3 — INT-007 dual live AI providers)

Reviewer-run (independent of builder reports), 2026-09-03/04, human-authorized full live M3 run ("full live M3: DeepSeek + Vertex, real cost accepted"). All 18 §11.2 steps executed against the running app; steps 14/15/16 additionally driven in-browser (chromium 1234 via the repo's playwright install) with network capture. Evidence files: `logs/hai-build-loop/m3-ui.requests.log` (raw /api request trace + console capture), `screens/m3-u*.png`, `m3-report1-export.md`; raw server logs `m3-backend.log`, `m3-backend-nokey.log`, `m3-backend-restored.log`, `m3-frontend.log`.

## Verdict

**PASS** — 1 WARN + 3 NIT (no blockers; no SPEC/HAI change required to close the milestone; ASM-012 resolved — the default model id `deepseek-v4-flash` is accepted by api.deepseek.com, no `DEEPSEEK_MODEL` override needed).

## Environment

- Commit/worktree identity: HEAD `fec867b` (feat: INT-007 M2 — per-project AI provider selector) + d49127d (view-mode docs). No code or spec files modified by this run; nothing committed.
- Runtime: python 3.13.5; uvicorn; fastapi; anthropic[vertex]; node v22.17.1; vite 8.2.2; @playwright/test 1.62.1 (from `.hai/node_modules`, chromium-1234 in ms-playwright cache).
- Servers (all logs in `logs/hai-build-loop/`): backend uvicorn `app.main:app` @ 127.0.0.1:8000, isolated DB via `WRITER_ASSISTANCE_DB=/tmp/opencode/m3-int007-reviewer.db` (fresh, deleted pre-launch), original launch pid 3511724 (uv run) → final restored launch pids 3517971/3517975; frontend vite @ 127.0.0.1:5173 with `/api` proxy → 8000, pids 3511773/3511774. Logs: `m3-backend.log` (311 lines, main session), `m3-backend-nokey.log` (step-18 window), `m3-backend-restored.log` (post-restore), `m3-frontend.log`.
- Environment variable names present (never values): `WRITER_ASSISTANCE_DB` (per-run isolated DB); backend/.env holds `ANTHROPIC_MODEL` only (DEC-015 override; value claude-sonnet-5 — DEC-017); shell (~/.bashrc) exports `DEEPSEEK_API_KEY`, `ANTHROPIC_VERTEX_PROJECT_ID`, `ANTHROPIC_SMALL_FAST_MODEL`, `VERTEX_LOCATION` (fallback; `GOOGLE_VERTEX_LOCATION` unset — vertex.py fallback path exercised, RES-002/ADC via google-auth, `VERTEX_ACCESS_TOKEN` unset). `.env.example` documents both providers' names incl. `DEEPSEEK_API_KEY` + `DEEPSEEK_MODEL` (R-072). **`DEEPSEEK_MODEL` was never set anywhere** (checked: `.env` no; ~/.bashrc no; live server `/proc/<pid>/environ` grep count 0) — every deepseek call used the R-073 default `deepseek-v4-flash`.
- Live-AI authorization reference: human message — "The human EXPLICITLY AUTHORIZED live AI calls for this run (full live M3: DeepSeek + Vertex, real cost accepted)". No secret values recorded in this file or any kept log.
- Run-scoped anomaly note: this host's wall clock read 22:xx local while uvicorn/bg timestamps are UTC (02:xx); timings quoted below are wall-clock deltas measured by the driving scripts, not log timestamps.

## Fixture

- Fixture doc tree `/tmp/opencode/m3-fixture-review/`: `housing-market.md`, `letter.md`, `archive/remote-work.md`, `archive/supply-side.md` (4 files incl. subdir `archive/`); md5 baseline `/tmp/opencode/m3-fixture.md5.baseline` (4 records) verified pre-run, after the vertex journey, and after ALL real-AI steps incl. deepseek — **byte-identical each time (R-011)**.
- Projects on the isolated DB: A "M3 INT-007 Journey A" (id 2; provider **vertex** — set at step 1 so §11.2 steps 1-14 run on AnthropicVertex per §11.3; end-state vertex), B "M3 INT-007 Untouched B" (id 3; provider **deepseek**, never touched after creation), C "M3 UI Fresh DeepSeek C" (id 8; created via the UI at step 15; provider **deepseek**). Legacy-adoption probe DB `/tmp/opencode/m3-legacy.db` (pre-INT-007 projects table, no `ai_provider` column, 1 row), booted separately on :8001.
- Objects (final): A: round 1 (report deleted per step 12, dump intact), round 2 (report 2, 3 blocks, editing); C: rounds 5 (UI) + 6 (report 3, 2 blocks, editing, dump saved); B: none.

## Commands and results

| Command | Exit/result | Evidence |
|---|---|---|
| `RUN_LIVE_AI=1 ANTHROPIC_MODEL=claude-sonnet-5 uv run pytest -m live_ai -v` (backend/) | 5 passed, 104 deselected, 42.74s | step-1 regression gate |
| backend launch `WRITER_ASSISTANCE_DB=… uv run uvicorn app.main:app --port 8000` (bg) | running; `GET /api/v1/projects` → `[]` | m3-backend.log:1-6 |
| frontend `npm run dev` (bg) | running; `/` 200; proxy JSON OK | m3-frontend.log:1-9 |
| `uv run python m3-scripts/journey_m3.py` (steps 1-14, live vertex) | 0; all steps PASS | journey output quoted in UC table; m3-backend.log:19-59 |
| `md5sum -c m3-fixture.md5.baseline` (post-journey, post-UI, post-deepseek) | all 4 OK ×3 | R-011 invariant |
| node `m3-ui.mjs` (playwright; U1-U5) — final of 4 runs (see Failures) | 0 | m3-ui.requests.log; screens/m3-u1..u5 |
| `GET https://api.deepseek.com/models` (env key) | 200: ids `['deepseek-v4-flash','deepseek-v4-pro','deepseek-v4-flash-vision-exp']` | ASM-012 model-list evidence |
| `uv run python ds16_17.py` (steps 16-17, deepseek) | 0 | m3-backend.log:289-302 |
| `uv run python crosstalk.py` (A vertex tone) | 0; 200/5 samples | m3-backend.log:306 |
| `restart_backend.sh nokey` + `step18.py nokey` | C 503 naming DEEPSEEK_API_KEY; A 200 | m3-backend-nokey.log:8,10 |
| `restart_backend.sh` (key restored) + `step18.py restored` | C 201, 5 proposals | m3-backend-restored.log:8 |
| legacy probe: backend on :8001 over seeded pre-INT-007 DB | projects[0] reads `ai_provider: deepseek`; PUT vertex/deepseek round-trips | migrate_legacy_projects (db.py:165-172) |
| backend gates `uv run pytest -q` / `uv run mypy app tests` / `uv run ruff check app tests` | **104 passed, 5 skipped** (live-AI env-gated, SD-16) / mypy clean 41 files / ruff clean | §11.3 backend gate |
| frontend gates `npx vitest run` / `npx tsc --noEmit` / `npx eslint .` / `npm run build` | **9 files / 39 tests passed** / tsc clean / eslint exit 0 / vite build OK | §11.3 frontend gate |

## Use cases (§11.2 steps 1-18)

| §11.2 step / UC | Execution method | Expected | Actual | Result | Evidence |
|---|---|---|---|---|---|
| 1 / UC-01 (R-010, R-011) import | API (project A) | ≥3 files incl. subdir; read-only | 4 files incl. `archive/` imported (`imported_files=4`); tree lists all by path; content renders; no writable resource endpoint exists | PASS | journey step1; m3-backend.log:7-18 |
| 2 / UC-02 (R-011, R-012) annotate | API + reload GET | highlight + anchored note persist; disk byte-identical | highlight id 1 + anchored note id 2 on housing-market.md; `GET /annotations` kinds `[highlight, note]`; fixture md5 OK | PASS | journey step2; m3-backend.log:8-18 |
| 3 / UC-03 (R-020) lenses | API (vertex) | sensible proposals w/ rationale; confirm 2 | **7.6 s**; 5 proposals (Real-Estate Economics, Monetary Policy & Interest Rates, …); 2 selected, 3 skipped | PASS | journey step3; m3-backend.log:19 |
| 4 / UC-04 (R-021, R-022) experts + review | API (vertex) | notes per expert; discard one; edit-and-add keeps provenance | **32.4 s**; 2 runs / 19 notes; note discarded; merge-with-edits → dump entry kind `ai-thought` with `expert_note_id` (provenance); expert-runs re-fetch returns both runs | PASS | journey step4; m3-backend.log:26-33 |
| 5 / UC-05 (R-030, R-031) curate dump (2 docs) | API | ≥1 of each kind, ordered, persists | round 1 over housing-market.md + letter.md; dump order `[snippet, ai-thought, highlight, human-thought]`; GET round-trip identical | PASS | journey step5; m3-backend.log:34-35 |
| 6 / UC-06+07 (R-040, R-042) generate + mode shift | API | report as paragraphs; stage flip; one-shot 409 | **8.0 s**; report 1 (4 blocks); round 1 stage `reading→editing`; second generate → **409** | PASS | journey step6; m3-backend.log:34-38 |
| 7 / UC-08 (R-043) manual edit ×2 | API + reload | edits persist per block | `[M3 EDIT-1]`/`[M3 EDIT-3]` markers present after re-fetch | PASS | journey step7 |
| 8 / UC-09 (R-050, R-053) tone | API (vertex) | exactly 5 distinct tones; block unchanged | **8.5 s**; tones `[confident, conversational, measured, urgent, vivid]`; block byte-identical before/after (R-051) | PASS | journey step8; m3-backend.log:41 |
| 9 / UC-10 (R-051) apply sample | API | only that block changes | block content == applied 'measured' sample text | PASS | journey step9 |
| 10 / UC-11 (R-052, R-053) critique | API (vertex) | substantive; block unchanged; rewrite works | **9.6 s**; 1396-char challenge; block unchanged; manual rewrite PUT saved | PASS | journey step10; m3-backend.log:44 |
| 11 / UC-12 (OQ-04) export | API | valid Markdown, in order | 1389-byte `export.md` `text/markdown`, contains edit markers; kept as m3-report1-export.md | PASS | journey step11 |
| 12 / UC-13 (OQ-05) delete report | API | cancel 400; confirm 204; round+dump remain | confirm:false → **400**; confirm:true → 204; report GET 404; round stage stays `editing`, dump_id intact | PASS | journey step12; m3-backend.log:48-50 |
| 13 / UC-14 (OQ-02) new round | API (vertex) | new round `reading`; second independent report; R1 untouched | round 2 starts `reading`; lens **15.1 s** + experts (1 run) + generate **9.6 s** → report 2 (3 blocks); round 1 untouched (report deleted, dump intact) | PASS | journey step13; m3-backend.log:53-59 |
| 14 / UC-15, UC-16 (R-060, R-061) view mode | browser (A, round-2 report) + API | read-only render; no edit/AI affordances; switching writes nothing; flush; badge `editing` | 3 `view-block-*` paragraphs; **textareas=0, tone buttons=0, critique buttons=0, delete=0, download=1**; writes during view toggle = 0; typed edit flushed on switch (SD-19) then view shows updated text; badge `editing` throughout | PASS | m3-ui.requests.log U4 lines; screens/m3-u4-*.png |
| 15 / UC-17 (R-070, R-071, SD-20) provider selector | browser + API | fresh project `deepseek`; existing projects show `deepseek` (legacy adoption); switch → reload persists; back to deepseek | UI-created C shows **deepseek**; B (created at step 1, untouched) shows **deepseek**; A (switched for the vertex journey) shows **vertex** — persisted; C switched to vertex → reload → vertex → back to deepseek → reload → deepseek | PASS | m3-ui.requests.log U1-U3; screens/m3-u1,u2,u3 |
| 15b / SD-20 legacy adoption | separate boot, pre-INT-007 DB | legacy row adopts column default `deepseek` on schema init | pre-INT-007 row (no `ai_provider` column) reads `deepseek` after `init_schema` → `migrate_legacy_projects` ALTER (db.py:165-172); PUT vertex → vertex → PUT back → deepseek round-trips | PASS | legacy probe (:8001) |
| 16 / ASM-012 probe + first deepseek AI calls (R-070, R-072, R-073) | UI lens click + API lens (deepseek) | model id `deepseek-v4-flash` accepted; valid results | **UI call**: POST lens-proposals 201, 5 proposals with 'proposed' badges (~5 s); **API probe**: **3.0 s**, 5 proposals; `/models` lists `deepseek-v4-flash`; no `DEEPSEEK_MODEL` override anywhere | PASS | m3-ui.requests.log; m3-backend.log:284-289 |
| 17 / R-070, R-071, DEC-017 — deepseek expert/generate/tone/critique + vertex no cross-talk | API (C deepseek; A vertex) | all call kinds parse + persist on deepseek; vertex project unaffected | deepseek: experts **6.9 s** (1 run, 7 notes), generate **6.9 s** (report 3, 2 blocks), tone **9.3 s** (5 distinct), critique **4.7 s** (1439 chars); round 6 `editing`, dump + report persisted; A vertex tone right after: **200, 5 samples (12.0 s)** | PASS | m3-backend.log:296-306; step17 evidence |
| 18 / UC-18 (R-074) config-failure | backend relaunched `env -u DEEPSEEK_API_KEY` | C call 503 naming var; no fallback; vertex never interrupted; restore → success | C lens call → **503** `{"detail":"missing required env var(s): DEEPSEEK_API_KEY"}` in 0.0 s (no retry/fallback); **A vertex tone 200 (5 samples, 16.0 s) in the same no-key window**; normal relaunch → C lens call **201** (3.1 s, 5 proposals) | PASS | m3-backend-nokey.log:8,10; m3-backend-restored.log:8 |

## Live calls and timings

Sanitized request ids omitted (no request-id header exists); auth: vertex ADC google-auth / deepseek Bearer from `DEEPSEEK_API_KEY` env — no secret values recorded. Models: vertex `claude-sonnet-5` (backend/.env, DEC-017; small-fast model from shell env per RES-002), deepseek `deepseek-v4-flash` (R-073 default; DEEPSEEK_MODEL never set).

| Service/model | Gate | Sanitized request identity | Timing | Result | Evidence |
|---|---|---|---|---|---|
| Vertex live pytest suite (5 tests) | §11.3 gate | RUN_LIVE_AI=1 pytest -m live_ai | 42.74 s total | 5/5 passed | pytest output |
| Vertex/claude-sonnet-5 lens proposals (A r1) | step 3 | POST /resources/1/lens-proposals | 7.6 s | 5 proposals | m3-backend.log:19 |
| Vertex/claude-sonnet-5 experts (A r1, 2 lenses) | step 4 | POST /rounds/1/experts | 32.4 s | 2 runs, 19 notes | m3-backend.log:26 |
| Vertex/claude-sonnet-5 generate (A r1) | step 6 | POST /rounds/1/generate-report | 8.0 s | 4 blocks | m3-backend.log:34 |
| Vertex small-fast tone (A r1) | step 8 | POST /blocks/2/tone-samples | 8.5 s | 5 distinct tones | m3-backend.log:41 |
| Vertex small-fast critique (A r1) | step 10 | POST /blocks/1/critique | 9.6 s | 1396 chars | m3-backend.log:44 |
| Vertex/claude-sonnet-5 lens (A r2) | step 13 | POST /resources/5/lens-proposals | ~10 s | 5 proposals | m3-backend.log:53 |
| Vertex/claude-sonnet-5 experts (A r2) | step 13 | POST /rounds/2/experts | 15.1 s | 1 run | m3-backend.log:55 |
| Vertex/claude-sonnet-5 generate (A r2) | step 13 | POST /rounds/2/generate-report | 9.6 s | report 2, 3 blocks | m3-backend.log:59 |
| **DeepSeek/deepseek-v4-flash lens (UI, C)** | step 16 | POST /resources/26/lens-proposals (browser click) | ~5 s | 201, 5 proposals, 0 console errors | m3-backend.log:285; m3-ui.requests.log |
| DeepSeek/deepseek-v4-flash lens (API probe) | step 16 | POST /resources/26/lens-proposals | 3.0 s | 5 proposals | m3-backend.log:289 |
| DeepSeek/deepseek-v4-flash experts (C) | step 17 | POST /rounds/6/experts | 6.9 s | 1 run, 7 notes | m3-backend.log:296 |
| DeepSeek/deepseek-v4-flash generate (C) | step 17 | POST /rounds/6/generate-report | 6.9 s | report 3, 2 blocks | m3-backend.log:300 |
| DeepSeek/deepseek-v4-flash tone (C) | step 17 | POST /blocks/8/tone-samples | 9.3 s | 5 distinct tones | m3-backend.log:301 |
| DeepSeek/deepseek-v4-flash critique (C) | step 17 | POST /blocks/8/critique | 4.7 s | 1439 chars | m3-backend.log:302 |
| Vertex tone (A) — no-cross-talk probe | step 17 | POST /blocks/5/tone-samples | 12.0 s | 200, 5 samples | m3-backend.log:306 |
| Vertex tone (A) — during no-key window | step 18 | POST /blocks/5/tone-samples | 16.0 s | 200, 5 samples (vertex never interrupted) | m3-backend-nokey.log:11 |
| DeepSeek lens with key scrubbed | step 18 | POST /resources/30/lens-proposals | 0.0 s | **503** naming DEEPSEEK_API_KEY, no fallback | m3-backend-nokey.log:8 |
| DeepSeek lens after key restore | step 18 | POST /resources/30/lens-proposals | 3.1 s | 201, 5 proposals | m3-backend-restored.log:8 |

## Log review

- `logs/hai-build-loop/m3-backend.log` (311 lines): status histogram **258×200, 36×201, 6×204, 1×400, 1×404, 1×409 — zero 5xx, zero tracebacks, zero ERROR lines**. The three non-2xx are the deliberate negative checks: m3-backend.log:36 (409 one-shot re-generate), :48 (400 delete-without-confirm), :50 (404 post-delete probe).
- `m3-backend.log:19-59`: full vertex journey (import → generate) request sequence.
- `m3-backend.log:227` + `:285`: UI-triggered deepseek lens POSTs 201 (rerun3 artifacts noted in Failures; rerun4 is the kept session).
- `m3-backend.log:284-302`: deepseek lens/experts/generate/tone/critique sequence (201/200s only).
- `m3-backend-nokey.log:8`: the only 5xx in the whole session set — the deliberate step-18 503; `:10` A vertex 200 immediately after.
- `m3-backend-restored.log:8`: 201 after key restore; clean shutdown/startup lines (no errors).
- `m3-frontend.log:1-9`: vite 8.2.2 ready in 133 ms; nothing else logged (dev server logs no request lines; any proxy failure would surface as 5xx in the UI trace — none).
- `m3-ui.requests.log`: full browser /api trace of the kept UI session; trailing "console errors/warnings" section **empty** (0 console errors, 0 pageerrors, 0 warnings captured across the whole session).

## Failures and retries

All four failures below are **test-script artifacts** of the reviewer's own driving scripts; no product defect was found in any of them. No code changed; none of these touched product behavior. Attempt evidence is preserved (never erased): rerun logs in `/tmp/opencode/m3-scripts/ui/m3-ui.output` history truncated per run — the kept `m3-ui.requests.log` reflects the final run only.

1. Attempt: `journey_m3.py` run 1 — crash `TypeError: call() missing 1 required keyword-only argument: 'expect'` (script bug: PUT provider call omitted `expect`). Fix: default `expect=200` in the helper + idempotent pre-clean of leftover projects. Rerun: full steps 1-14 PASS (first run had created only project A's predecessor, deleted by the pre-clean).
2. Attempt: UI session run 1 — crash at U3 after `page.reload`: the app keeps workspace state in memory (no URL routing), so a reload lands on the Projects list and the provider selector is not visible until the project is re-opened. Fix: `reloadAndReopen()` helper (reload → re-open project → assert persisted value). Rerun 2: U1-U3 PASS.
3. Attempt: UI run 2 — crash `strict mode violation` on `getByRole('button', {name: 'Edit'})`: round rows carry the badge text "editing" whose accessible name contains "edit". Fix: `exact: true` on Edit/View/Report buttons; view-mode export assertion relabeled to "Download .md". Rerun 3: U1-U4 PASS.
4. Attempt: UI run 3 — U5 crash: "Propose lenses for this doc" never appeared because (a) the round-dialog checkbox label-click toggle was unreliable and (b) the run was killed while a stale 120 s wait ("Rationale" text that does not exist in the DOM — proposals render title + rationale paragraphs + a 'proposed' badge, no literal label) burned. Note: that run's UI deepseek lens POST had **already succeeded (201, m3-backend.log:227)** before the kill. Fix: create C's round deterministically via API; wait on the proposals hint text + 'proposed' badge count. Rerun 4 (final): U1-U5 all PASS, including the deepseek UI lens call (201, 5 proposals).

## Residual human UX checks

- All UI-surface steps were genuinely browser-driven: project create dialog (U1), provider selector values + reload persistence (U2/U3), view-mode read-only surface + zero-write toggle + flush-on-switch + badge (U4), deepseek lens click-through with live proposals (U5). Screenshots exist under `logs/hai-build-loop/screens/m3-u*.png` for human eyeballing (styling not judged by the reviewer — no image input).
- NIT M3F4: page reload loses the open-project context (client-held state; matches the established ephemeral-state design, SD-18). If the human wants deep links/bookmarks, URL routing would be needed — out of scope.
- Two browser-visible polish items not exercised visually: tone-label styling inside sample cards and select dropdown styling (DOM values asserted; appearance not inspected).

## INT-007 done-gate → evidence mapping (§11.3 + steps 15-18)

| §11.3 INT-007 gate item | Evidence |
|---|---|
| Provider-boundary offline suite green (pytest/mypy/ruff; transports stubbed per SD-16) | backend gates: 104 passed / 5 skipped (live-AI env-gated), mypy clean (41 files), ruff clean |
| Live-AI suites (`RUN_LIVE_AI=1`, marker `live_ai`) pass against AnthropicVertex | 5/5 passed in 42.74 s (test_live_ai.py) |
| …and against DeepSeek with `DEEPSEEK_API_KEY` set, confirming the accepted model id per ASM-012 (expected `deepseek-v4-flash`, overridable via `DEEPSEEK_MODEL`) | No env-gated deepseek pytest suite exists (see finding M3F1); deepseek live verification done via §11.2 steps 16-17: all five call kinds succeeded through the app with the default id; `/models` lists `deepseek-v4-flash`; DEEPSEEK_MODEL never set |
| §11.2 steps 15-18 green | step 15 selector (fresh deepseek default; legacy adoption incl. genuine pre-INT-007 DB ALTER; vertex switch persists across reload; switch-back) — PASS; step 16 probe (id accepted, UI + API lens calls) — PASS; step 17 (deepseek expert/generate/tone/critique parse+persist; A vertex unaffected — no cross-talk) — PASS; step 18 (env-scrub 503 naming DEEPSEEK_API_KEY, no fallback, vertex uninterrupted, restore → success) — PASS |
| `backend/.env.example` documents both providers' names (R-072) | .env.example lists `ANTHROPIC_VERTEX_PROJECT_ID … ANTHROPIC_BASE_URL` + `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` (lines 2-11) |
| Read-only guarantee re-verified after real-AI steps (§11.3 integration leg) | md5 baseline all-OK ×3 (pre-run, post-vertex-journey, post-deepseek) |
| Exported file valid Markdown | m3-report1-export.md (1389 B) |

## ASM-012 probe outcome

**`deepseek-v4-flash` is an accepted model id at api.deepseek.com — no `DEEPSEEK_MODEL` env override needed.** Evidence: (a) `GET https://api.deepseek.com/models` returns ids `['deepseek-v4-flash', 'deepseek-v4-pro', 'deepseek-v4-flash-vision-exp']`; (b) all live deepseek calls through the app (lens ×3 via UI + API, experts, generate, tone, critique — see Live calls table) returned 201/200 with the R-073 default id in force (`DEEPSEEK_MODEL` verified unset in `.env`, `~/.bashrc`, and the live server's process environ). No spec/env-default update is needed on this account; the alias-form risk that motivated ASM-012/R-073 did not materialize (contrast: `claude-opus-4-8[1m]` on Vertex, RES-002).

## Findings

- **M3F1 (WARN)** — no env-gated `live_ai`-marked DeepSeek pytest suite exists; spec §11.3's "live-AI suites … pass against AnthropicVertex **and against DeepSeek**" clause is only evidenced by the §11.2 steps 16-17 live journey + `/models` probe, not by a `RUN_LIVE_AI=1` suite. Affected: spec §11.3 INT-007 gate wording (and optionally §11.1 coverage map). Impact: low — the gate's intent (confirm accepted deepseek id + live behavior with the key set) is fully evidenced; the gap is repeatability of the deepseek live leg in suite form. Correction (either): (a) add `backend/tests/test_live_deepseek.py` mirroring `test_live_ai.py` (same marker/gate; builds `app.ai.deepseek.build_ai_client`); or (b) amend the §11.3 gate sentence to point the deepseek leg at §11.2 steps 16-17. No code behavior change needed.
- **M3F2 (NIT)** — §11.2 step 15's wording ("an existing project created before this step (e.g. step 1's) … shows `deepseek`") is in tension with §11.3's instruction that steps 1-14 run on AnthropicVertex (the step-1 project must be switched to vertex for the journey, so at step 15 it legitimately shows its persisted `vertex`). Executed with an additional untouched early project (B, deepseek) + a genuine pre-INT-007 DB adoption probe. Affected: spec §11.2 step 15 example. Impact: none (behavior correct; wording could name "a project whose provider was never changed"). No spec change required.
- **M3F3 (NIT)** — deepseek lens proposals were created twice on the same doc in C (once via UI, once via the step-16 API probe), producing duplicate proposal rows (each propose call adds a fresh set — existing design, ASM-011 SD-3 semantics). Test-hygiene note only; no user-visible defect.
- **M3F4 (NIT)** — full page reload drops the open-project workspace (no URL routing); persistence checks therefore re-open the project after reload (helper in the UI script). Pre-existing client-state design (SD-18 extends to project selection); listed for the human, not a defect.

No CODE_BLOCKER, no SPEC_CHANGE_REQUESTED, no HAI_CHANGE_REQUESTED. Nothing in the run contradicts DEC-024..027, ASM-012 (now resolved by the probe), or ASM-013/SD-20 (per-project granularity worked as specced; OQ-08 stays open in state.yaml until the human veto window closes — no evidence here argues for a per-round override).

## Cleanup

- Processes stopped: backend uvicorn pids 3517971/3517975 (final launch; earlier launches 3511724, 3517466/3517470 also stopped during step 18 restarts), legacy probe backend :8001 (pid 3518061 family), frontend vite pids 3511773/3511774.
- Fixture resources removed: `/tmp/opencode/m3-fixture-review/` tree, `/tmp/opencode/m3-int007-reviewer.db`, `/tmp/opencode/m3-legacy.db`, `/tmp/opencode/m3-fixture.md5.baseline`, `/tmp/opencode/m3-scripts/` (working scripts + probe JSONs; key facts quoted in this file). `backend/data/writer-assistance.db` untouched (isolated DB only).
- Kept: this evidence file, `m3-backend.log`, `m3-backend-nokey.log`, `m3-backend-restored.log`, `m3-frontend.log`, `m3-ui.requests.log`, `screens/m3-u*.png`, `m3-report1-export.md` under `logs/hai-build-loop/`. Nothing committed; spec.md/.hai/state.yaml/devlogs.md untouched.
