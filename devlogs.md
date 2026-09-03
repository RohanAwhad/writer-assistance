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
