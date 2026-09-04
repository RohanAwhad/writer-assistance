# Devlogs — writer-assistance

## 2026-09-03 — Spec loop from .hai intent

- Source of truth: `.hai/state.yaml` (mission-control capture, commit 4031ecc).
  - 4 human-approved intents INT-001..004, 13 decisions DEC-001..013, evidence H1..H9.
  - 6 agent assumptions ASM-001..006 (soft/malleable per human).
- Task: spec-writer + spec-reviewer subagent loop until reviewer PASS on compliance
  with human intents/decisions; assumptions may be revised; human conflicts escalated.
- Artifact: `spec.md` at repo root.

### Loop outcome

- Writer round 1 -> commit b01d93b. Reviewer round 1 -> **PASS** (no blockers, no escalations).
  All DEC-001..013 covered & faithful; ASM-001..006 restated as soft; no fake trace tags.
- 2 non-blocking NITs (R-042 disable-gate, R-051/052 no-auto-replace) — no action required.
- No conflicting human decisions / unsatisfiable constraints surfaced.
- Spec leaves 6 open questions for the human: OQ-01 resource storage (disk refs vs DB snapshot),
  OQ-02 rounds/reports per project, OQ-03 curation entry mechanics, OQ-04 export scope,
  OQ-05 regeneration after mode shift, OQ-06 custom human-defined lenses.

## 2026-09-03 — OQs resolved; discovery of origin/main

- Discovery: `origin/main` holds a working v1 ("Writer's Desk", 2026-05-06) of the same
  app built the old way. Human decision: do NOT copy main — this branch + .hai harness is
  the experiment; main stays as prior art only. Pushed spec commits to origin/built-using-hai.
- Door-classified the 6 OQs (Amazon one-way/two-way). Human answered (one-way style, asked):
  - OQ-01: **Import into app (snapshot)** — project setup imports markdown tree into SQLite.
  - Run context: **local single-user**, no auth.
- Agent 2-way decisions (human may veto): OQ-02 multiple rounds/project (1 round = 1 dump + 1 report);
  OQ-03 dump = ordered typed-entry list from pools; OQ-04 minimal md export in scope;
  OQ-05 one-shot generation per round, delete report w/ confirm; OQ-06 AI-proposed lenses only v1.
- spec.md bumped to v1.1 with a Resolved-decisions table (§9).

## 2026-09-03 — Spec v1.2..1.4: use cases + verification plan (loop rounds 2-3)

- Human request: spec must include use cases + manual & automatic tests/verifications.
- Writer round 2 (v1.2): §10 14 use cases UC-01..14; §11 verification plan — automatic tests
  (backend pytest/TestClient, frontend vitest/RTL, mypy/ruff/tsc/eslint, env-gated live-AI policy
  SD-12..17), R→test coverage map, 13-step manual checklist, milestone done-gates.
- Reviewer round 2: FAIL — 1 BLOCKER (stage model contradiction: per-project SD-9 vs per-round
  OQ-02/UC-14; agent-internal, no human escalation), 2 WARNs (missing export/delete API rows;
  stack R-001..005 no verification home), 1 NIT.
- Writer round 2b (v1.3): stage moved to round/report consistently (§3/4/5/6/10/11), API rows
  added, stack-R sentence, NIT fixed. Reviewer round 3: PASS (2 wording NITs only).
- NITs fixed inline → v1.4: R-042 wording "for that round", header status precision.
- Commits: 48e734d (v1.2), aa6b389 (v1.3), pending (v1.4).

## 2026-09-03 — Build loops: backend + frontend milestones

- Build loop started (builder ↔ build-reviewer, both audit vs spec.md/.hai).
- **Backend milestone** (f181417): FastAPI+SQLite per §4/§6; import-snapshot resources,
  annotations, lens/expert flow, per-round stage, dump curation, one-shot report gen,
  block editor API, tone-5/critique transient, export.md, confirm-delete. 63 tests offline,
  mypy strict + ruff clean. Reviewer: **PASS-WITH-WARN** (R-042 annotate gating deferred to UI).
- **Frontend milestone** (a9999e4): React+shadcn 3-panel workspace, UC-01..14, 17 vitest tests.
  Reviewer: **FAIL** — 2 SPEC-CHANGE-REQUESTED (persisted annotations/expert runs not listable
  → reload broke UC-02/UC-04 persistence).
- **Spec loop resumed** (acd32f5, v1.5): §6 += GET /resources/{id}/annotations,
  GET /rounds/{id}/expert-runs (FB-1/FB-2), UC reload clauses, §11.1 tests. Spec-reviewer PASS.
- **Backend FB** (bbc25be): 2 GET endpoints + expert_runs.lens_proposal_id column + reload
  tests (68 pass). Reviewer PASS (WARN: no migration tooling → make reset-db added).
- **Frontend FB** (dcf62bc): hydration of annotations + expert runs, retry path, curate pool
  prefetch (25 vitest tests). Reviewer: PASS-WITH-WARN → WARNs fixed, full suite green.
- Loop state: build-reviewer satisfied for both milestones. Remaining: integration milestone
  (manual §11.2 checklist w/ real AnthropicVertex — needs Rohan + live env vars).

## 2026-09-03 — Integration milestone: PASS (real Vertex AI)

- Servers: backend :8000 + frontend :5173 (vite proxy), fresh DB, sample docs in /tmp/opencode/wd-sample-docs.
- Live AI gate: 5/5 env-gated tests pass (RUN_LIVE_AI=1).
- Full §11.2 journey over live API w/ real AI: import/read-only, annotate+FB-1 reload,
  lenses (5 proposals), experts (10 notes) + FB-2 reload, review (discard/merge/accept),
  curated dump (4 kinds), generate (2 rounds; one-shot 409), block edit, tone (exactly 5),
  critique, export.md, delete (confirm semantics), new round — all PASS.
- UI: root HTML + proxy JSON OK; source docs byte-identical after run; backend log clean (0 tracebacks).
- Evidence: logs/integration-2026-09-03.md.
- Fixes found: `anthropic[google]` extra invalid in sdk 1.3 → `anthropic[vertex]` (649d450).
- Open for Rohan: ANTHROPIC_MODEL env = `claude-opus-4-8[1m]` (Claude Code alias form) is
  rejected by Vertex; integration ran with `claude-sonnet-5`. Canonical env value decision pending.
- Residual: manual UI click-through (visual/UX) not yet done by human.

## 2026-09-03 — .env config precedence (human decision)

- Human: backend should load `.env` via load_dotenv, `.env` takes precedence over shell env.
- Code: `load_dotenv(override=True)` in backend/app/main.py; python-dotenv dep added;
  backend/.env (gitignored, model fixed to claude-sonnet-5) + backend/.env.example committed.
- Verified: shell ANTHROPIC_MODEL still `claude-opus-4-8[1m]` (broken alias) → after app
  import resolves to claude-sonnet-5; offline suite 68 pass; live AI gate 5/5 (37s).
- .hai: RES-001/ASM-005 updated (agent context; ASM-005 status resolved).

## 2026-09-03 — UI spin (manual click-through) + real fixes

- User cleaned .hai: removed process intents INT-005..008 (spec/build/integration/checkpoint);
  only INT-001..004 remain; evidence pruned (H10-H20 mostly), process facts repointed to INT-001.
  Commit 0c76195 pushed to origin/built-using-hai.
- **Bug (found via browser walkthrough, fixed)**: GET /api/v1/projects/{id}/tree and
  /api/v1/rounds returned 500 under uvicorn — sqlite3.ProgrammingError "objects created in a
  thread can only be used in that same thread" (FastAPI threadpool: dep generator vs endpoint).
  Fix: `check_same_thread=False` in db.connect() (local single-user, per DEC-014). 68 tests pass.
  Why integration passed: it ran via API/test client in-process (same thread) — browser threads
  expose it.
- Walkthrough (playwright, real Vertex AI, claude-sonnet-5 from backend/.env):
  create project -> import 4-file tree + subdir (works), render + read-only badge (ok),
  annotate: text-select highlight + note persist + reload (ok; API verified),
  round create (ok), propose lenses -> 5 proposals (ok), select 2 -> expert runs -> notes
  (ok, real AI), review: add/edit&add/discard (ok; merged notes auto-entry the dump, marked saved),
  curate: free human-thought entry + append + save, generate report (pending B2c run),
  block edit, tone 5 samples, critique, export, delete + new round (pending B3 run).
- Observations: round-doc checkboxes default all-checked; label click toggled unexpected rows
  (test-script quirk, not app bug). Console 404 = favicon only. Rounds list shows "· dump"
  once the round's dump exists.

## 2026-09-03 — Spec v1.6: view mode intent (INT-005/DEC-018) + state alignment

- Human added new intent (H22, commit 733562d): report **view mode** alongside editing mode
  (INT-005/DEC-018, "like just how we have editing mode").
- Spec loop (writer ↔ fresh reviewer, 2 rounds):
  - Writer r1 → v1.6: §2.7 **R-060/R-061** (Trace: DEC-018), **F12**, **UC-15/16**, **SD-18/19**
    (view = ephemeral client sub-mode of the report surface; no new persistence, no stage
    change — SD-9/DEC-011 intact); §11.1 coverage-map rows, manual step 14 (13→14 gates).
    Also repaired pre-existing staleness: header source-of-truth, phantom **ASM-006** removed,
    §7 synced to real ASM-001..005 + 007..011, monorepo wording, evidence-set mentions.
  - Reviewer r1 → **FAIL**: R1F1 blocker — DEC-015/DEC-017 (config/.env, vertex wiring) absent
    from spec body; §11.2 still said "env vars exported", contradicting DEC-015 .env mechanism.
  - Writer r2: **DEC-015** (.env via load_dotenv override=True, precedence) + **DEC-017**
    (anthropic[vertex] extra, claude-sonnet-5 live model) added as §3 rows + R-004 parenthetical
    + §11.2 precondition + §11.3 gate; **R-042** gate scoped to round-bound ops (expert runs,
    curation) — annotating stays resource-scoped/open per DEC-006; ASM-003→ASM-008 repoint on
    R-031/§4 NotesDump; trace legend accepts INT-xx.
  - Reviewer r2 → **PASS** (3 cosmetic NITs disclosed: DEC-014/016 not id-tagged, UC-15 kind
    label, R-060 embeds SD-2 styling clause — not fixed).
- Handoff returned; spec v1.6 committed; next: hai-build-loop for view-mode milestone.

## 2026-09-03 — M-VM-BACKEND milestone: view-mode read-path test slice

- Spec §11.1 view-mode read-path test (R-060/R-061) added as 2 additive API tests in
  `backend/tests/test_api_reports.py` (FakeAI offline, TestClient): reads return saved rows
  and mutate nothing.
- Test 1 (`test_view_mode_read_path_returns_saved_blocks_and_mutates_nothing`): generate →
  DB snapshot (reports row, report_blocks rows, reading_rounds stage/updated_at) → GET
  /reports/{id} + GET /reports/{id}/export.md + GET /rounds/{id} → payload equals saved rows;
  DB state byte-identical after the GETs.
- Test 2 (`test_view_mode_read_path_returns_edited_rows_and_mutates_nothing`): same read-path
  probe after a PUT /blocks/{id} manual edit — the view surface reads the rows the editor
  writes (updated_at in the report GET; edited content in both GETs).
- No production change (expected — view mode adds no backend behavior); no real defect found.
- Gates run from backend/: pytest 70 passed, 5 skipped (env-gated live-AI, SD-16); mypy
  clean (35 files); ruff clean. Prior suite was 68 — delta +2.

## 2026-09-03 — M-VM-FRONTEND milestone: view-mode surface (R-060/R-061)

- `ReportEditor.tsx` gains an ephemeral View/Edit sub-mode (SD-18: default editor on mount,
  no persistence, no stage change): header View/Edit switch, view branch renders each block
  read-only via the MarkdownView renderer (SD-2 style), export stays in both surfaces,
  Delete gated to the editor (SD-19).
- Write pipeline unified per block card: single-flight save + bounded convergence loop
  (retype detection via textRef vs PUT target), apply-sample routed through the same
  pipeline, flush-before-switch with all-or-nothing semantics (failed/empty flush keeps the
  editor open with the error visible — no silent drop, no stale view render).
- Tests: new `frontend/src/test/viewMode.test.tsx` (7 tests: read-only rendering incl.
  binding absence of tone controls; toggle preservation + zero-write switching; mid-flight
  keystroke re-save; apply-behind-dirty-save serialization; flush-failure retention + retry;
  empty-block refusal).
- Reviewer rounds: r1 PASS_WITH_WARN (M2F1 mid-flight stale flush, M2F2 apply-PUT bypass,
  M2F3 untested failure paths) → r2 PASS (fixes + 5 tests; 2 NITs disclosed).
- Gates run from frontend/: vitest 8 files / 32 tests passed; tsc clean; eslint clean;
  vite build ok.

## 2026-09-03 — M-VM-INTEGRATION milestone: live 14-step §11.2 journey (real Vertex)

- Human authorized the full live run (real AnthropicVertex, claude-sonnet-5 from
  backend/.env per DEC-015/DEC-017). Isolated DB via WRITER_ASSISTANCE_DB, fixture doc tree
  under /tmp/opencode, servers logged to logs/hai-build-loop/, browser automation via the
  repo's playwright install.
- Steps 1-14 all PASS against the running app: import (5 files + subdir), annotate +
  reload + on-disk byte-identity, AI lenses (5 proposals, 2 confirmed), AI experts
  (19 notes; discard + edit-and-add with provenance), 4-kind curated dump, generate →
  editing stage with run-expert/curate UI closed while annotating stays available (R-042
  scope), typed block edits persist, tone exactly 5, apply-sample single PUT, critique
  (block unchanged), export.md valid, delete confirm semantics, new round independent,
  and **step 14 view mode**: read-only paragraphs, no textareas/save-states/AI buttons,
  delete absent/download present, toggles wrote zero requests, reload lands on editor with
  content preserved, badge stays `editing` (UC-15/UC-16).
- Log review: backend.log sole 5xx = one transient 502 retried 201; no tracebacks; expected
  404 after delete. Offline gates re-run green (backend 70 passed/5 skipped; frontend 32
  passed). Reviewer verdict **PASS**, no findings; evidence:
  logs/hai-build-loop/M-VM-INTEGRATION-integration.md.
- All §11.3 milestones green → spec v1.6 fully built. Uncommitted until human authorizes.


## 2026-09-03 — Spec v1.7: INT-007 dual live AI providers (spec loop)

- INT-007 captured in state (DEC-024..027, H26/H28/H29/H31/H33) via checkpoint;
  DEC-020 hostname pinned to writer.assistance.rohanawhad.com (H34) same session.
- Spec loop (fresh writer + fresh reviewer subagents, spec.md v1.6 → v1.7):
  - R-004 reworded to provider-boundary semantics (DEC-004 as amended by DEC-024).
  - New §2.8 R-070..R-074: dual providers behind AIClient boundary (R-070),
    in-app per-project selector not env var (R-071, DEC-027), DEEPSEEK_API_KEY
    runtime config + .env.example docs (R-072, DEC-026/DEC-015), env-configurable
    deepseek model id, fallback deepseek-v4-flash, unverified (R-073, ASM-012),
    clean 503 when selected provider unconfigured, no fallback (R-074).
  - SD-20 (agent two-way, resolves OQ-08): selector per project; ai_provider
    column; fresh + legacy rows default deepseek on schema init; SD-21 provider
    resolution at call time via project context.
  - UC-17/UC-18; §11.2 steps 15-18 appended (1-14 untouched); §11.3 INT-007 gate.
- Reviewer round 1: PASS + 2 WARN (S1F1 step-18 env scrub — ~/.bashrc exports
  DEEPSEEK_API_KEY so .env removal alone can't reproduce 503; S1F2 stale R-004
  coverage row) + 4 NIT; all 6 fixed by writer round 2 and verified by diff.
- INT-006 (container/tunnel/auth) deliberately out of scope — separate run.
- ASM-013 rewritten (agent context): per-project resolution recorded (SD-20),
  OQ-08 stays open in state.yaml until human veto window closes.

## 2026-09-03 — INT-007 backend provider layer (M1: R-070..R-074, SD-20/SD-21)

- Builder milestone (authorized; uncommitted until human authorizes):
  - DeepSeek provider `app/ai/deepseek.py`: OpenAI-compatible chat-completions
    transport at api.deepseek.com over plain httpx (httpx promoted from dev to
    runtime dep — the anthropic SDK depends on httpx2, not httpx, so plain httpx
    was project-only; the promotion fixes the latent gap where a production
    install without the dev group would lack deepseek's transport);
    single DEEPSEEK_MODEL for all five call kinds (SD-21); shared ChatFn type +
    MAX_TOKENS_* moved to app/ai/client.py (single source, both providers).
  - Settings R-072/R-073: DEEPSEEK_API_KEY required (ConfigError at build),
    DEEPSEEK_MODEL fallback deepseek-v4-flash (the only occurrence of the id
    besides .env.example); both names documented in .env.example.
  - Persistence SD-20/R-071: projects.ai_provider TEXT NOT NULL DEFAULT
    'deepseek' CHECK(...) in SCHEMA + migrate_legacy_projects() ALTER in
    init_schema (legacy rows adopt deepseek on next schema init, idempotent).
    ProjectOut/ProjectDetail carry ai_provider; PUT /projects/{id}/provider
    (ProviderUpdate Literal schema) persists + returns project payload.
  - Resolution SD-21: deps.py per-provider lazy cache (get_ai_client_for_provider)
    + three typed FastAPI deps resolving entity id -> project -> provider:
    get_ai_client_for_{resource,round,block} (block -> report -> round ->
    project); old single get_ai_client/AiDep singleton removed; services keep
    receiving AIClient unchanged; conftest overrides the three resolvers with
    FakeAI (offline story intact).
  - Failure semantics R-074: selected provider's env missing at build ->
    ConfigError -> 503 naming the var; no fallback path exists; entity 404s
    precede config errors (dep validates before building).
- Tests added (29): deepseek env/settings + envelope + five-kind routing;
  resolution (fresh default, legacy adoption, per-provider cache, no-fallback
  unit); provider endpoint (accept/reject/persist/surface + legacy API);
  UC-18 API boundary 503 naming vars, vertex isolation, 404 precedence.
- Gates: pytest 99 passed/5 skipped (live), mypy strict clean (40 files),
  ruff check clean. Two-way choices: httpx runtime dep vs urllib; three typed
  per-shape resolver deps vs one multi-param dep (explicit, no query-param
  leakage, conftest overrides each); client.py as shared ChatFn/MAX_TOKENS home
  (vertex.py's anthropic import stays module-owned).
- Notes: transport failures map to AIError -> 502 at both providers' chat
  boundaries per the R-074 parenthetical — vertex wraps anthropic SDK APIError
  (vertex.py chat); deepseek wraps raw httpx.HTTPError, its non-2xx statuses,
  and the 200-with-non-JSON-body decode edge (review M1Fn-02 + M1F2-01). 5
  offline API-boundary tests in backend/tests/test_api_transport_failures.py
  assert 502 responses naming the failure; config errors stay 503, entity
  errors 404. Gates after: pytest 104 passed/5 skipped, mypy 41 files clean,
  ruff clean. DEEPSEEK_MODEL id unverified = ASM-012, live probe M3.

## 2026-09-03 — M3 integration: INT-007 dual-provider live run (real DeepSeek + Vertex)

- Human authorized the full live M3 run (real api.deepseek.com + AnthropicVertex,
  one-way-door pause). Evidence: logs/hai-build-loop/M-INT007-INTEGRATION-integration.md.
- Steps 1-14 regression on live Vertex all PASS (import → view mode, incl. browser
  UC-15/16); existing live Vertex suite 5/5 (42.7s) — no regression after M1 vertex.py
  transport wrap.
- INT-007 steps 15-18 all PASS: fresh project selector default `deepseek` (SD-20);
  legacy rows (genuine pre-INT-007 DB boot, :8001 probe) adopt `deepseek` on
  `migrate_legacy_projects` (db.py:165-172); switch vertex↔deepseek persists on reload;
  real deepseek journey (lenses/experts/generate/tone/critique) all 2xx + parsed +
  persisted; step 18 `env -u DEEPSEEK_API_KEY` → 503 naming DEEPSEEK_API_KEY, no
  fallback, vertex project 200 in the same window, restore → 201.
- **ASM-012 probe RESOLVED**: api.deepseek.com accepts `deepseek-v4-flash` (default,
  DEEPSEEK_MODEL override not needed). No spec/env-default follow-up.
- M3F1 WARN (no env-gated deepseek live suite) fixed: backend/tests/test_live_deepseek.py
  (3 tests mirroring test_live_ai.py) — live run 3 passed/15s; default suite now
  104 passed/8 skipped (5 vertex + 3 deepseek env-gated). mypy 42 files, ruff clean.
- Reviewer verdicts: M3 PASS (final round; NITs M3F2..M3F6 — F5 citation lines fixed
  in evidence). Full offline suite re-run green after live run.
- All §11.3 gates green → spec v1.7 INT-007 fully built. Loop close: commit + push
  per standing authorization.

## 2026-09-03 — Spec v1.8: INT-006 container deployment + auth gate (spec loop)

- Spec loop (fresh writer + fresh reviewer subagents, spec.md v1.7 → v1.8):
  - New §2.9 R-075..R-078: AUTH_API_KEY login gate w/ custom server-rendered login
    screen + HttpOnly session cookie (R-075, DEC-021/022), SPA static serving +
    /api preservation (R-076, DEC-019), single multi-stage container w/ named
    volume fresh DB + no-compose (R-077, DEC-019/023), fail-closed boot when key
    missing in container (R-078, DEC-021).
  - SD-22..27 (agent-owned): gate-off default keeps offline suites green (SD-24),
    HMAC-signed stateless cookie derived from AUTH_API_KEY — no new secret (SD-23),
    --network host + bind 127.0.0.1 (SD-26), threat model bounded to loopback (SD-27).
  - F14 login/logout; UC-19..22; §11.2 steps 19..23 appended; §11.3 three INT-006
    done-gates (auth-gate, container, public-exposure).
  - Reviewer r1 FAIL (S2F-1 blocker: step-20 docker `-e ANTHROPIC_MODEL` injects
    Vertex-invalid shell alias + ANTHROPIC_SMALL_FAST_MODEL never passed → vertex
    live leg unexecutable; NITs S2F-2..4) → writer r2 fixed all → reviewer r2 PASS
    (1 procedural NIT S2F2-1 applied: drop `-e` flag for shell-absent vars).
- DEC-014 "no hosting" scope amendment disclosed (§1/§3/§8). No state changes.

## 2026-09-03 — INT-006 M1: auth gate + static serving (build loop)

- Builder: backend/app/auth.py (gate middleware, HMAC-signed wa_session cookie
  from AUTH_API_KEY, server-rendered /login, POST /logout), create_app(auth_key,
  static_dir) params; SPA static mount + fallback w/ /api 404-JSON preservation;
  .env.example += AUTH_API_KEY; frontend client 401 → /login nav + re-nav guard;
  vite proxy /login /logout. Gate-off default keeps conftest untouched + suite
  green (SD-24); module app gated via .env key.
- Gates: backend 123 passed/8 skipped (19 new auth tests); mypy 44 files; ruff
  clean; frontend 42 tests; tsc/eslint/build clean.
- Reviewer: PASS_WITH_WARN → M1F-1 WARN (spec §6 draft row said logout → 204;
  code 302 → /login per F14/UC-20) — §6 amended at this boundary; NITs M1F-2
  (gate-off+dist GET /login → SPA index, combo never in deployment), M1F-3
  (conftest gains fallback when dist exists — harmless, prefix-guarded) accepted.

## 2026-09-03 — INT-006 M2: container packaging (build loop)

- Dockerfile (multi-stage node:24-slim build → python:3.13-slim runtime; uv
  0.11.16 pinned from ghcr; uv sync --frozen --no-dev; non-root uid 1000;
  layout /app/backend + /app/frontend/dist so the static default resolves
  in-image; ENV WRITER_ASSISTANCE_DB=/data/writer-assistance.db; EXPOSE 8000;
  fail-closed CMD per R-078/SD-24 — AUTH_API_KEY unset → exit 1 before uvicorn).
- .dockerignore: .env/data/node_modules/dist/logs/.git/.hai + caches. No compose.
- Reviewer-owned offline smoke (build + run, no live AI): (a) 401 JSON /api,
  302 /login, wrong key 401 no cookie, login → wa_session, SPA 200, fresh DB on
  /data volume; (b) key-less boot exits 1, port refused, volume untouched;
  (c) project + session survive restart. Reviewer PASS, NITs only (CMD one-line
  vs SD-24 "two-line" phrasing; floating base tags; warm-cache assumption).
- Cleanup confirmed: containers/volume/image removed.
