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
