import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api/client";
import type { DumpEntryOut, ReportOut } from "../api/types";
import { created, error, noContent, ok, stubFetch } from "./fetchMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

const iso = "2026-09-03T00:00:00+00:00";

describe("api client request mapping", () => {
  it("creates and lists projects", async () => {
    const { calls } = stubFetch((call) => {
      if (call.method === "POST") {
        expect(call.body).toEqual({ name: "essays" });
        return ok({ id: 1, name: "essays", created_at: iso, updated_at: iso });
      }
      return ok([{ id: 1, name: "essays", created_at: iso, updated_at: iso }]);
    });
    const created = await api.createProject("essays");
    expect(created.id).toBe(1);
    const list = await api.listProjects();
    expect(list).toHaveLength(1);
    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual([
      "POST /api/v1/projects",
      "GET /api/v1/projects",
    ]);
  });

  it("imports a tree and fetches the tree", async () => {
    const { calls } = stubFetch((call) => {
      if (call.url.endsWith("/import")) {
        expect(call.body).toEqual({ path: "/tmp/docs" });
        return created({ project_id: 1, imported_files: 3 });
      }
      return ok({
        project_id: 1,
        nodes: [
          { id: 1, parent_id: null, name: "a.md", path: "a.md", kind: "file" },
          { id: 2, parent_id: null, name: "sub", path: "sub", kind: "dir" },
        ],
      });
    });
    const imported = await api.importTree(1, "/tmp/docs");
    expect(imported.imported_files).toBe(3);
    const tree = await api.getTree(1);
    expect(tree.nodes.filter((n) => n.kind === "file").map((n) => n.path)).toEqual(["a.md"]);
    expect(calls[1]?.url).toBe("/api/v1/projects/1/tree");
  });

  it("creates a highlight and a note with the offset contract", async () => {
    const { calls } = stubFetch((call) => {
      if (call.url.endsWith("/highlights")) {
        expect(call.body).toEqual({ start_offset: 4, end_offset: 10, content: "hello" });
        return created({
          id: 1, doc_id: 9, kind: "highlight", start_offset: 4, end_offset: 10,
          content: "hello", created_at: iso, updated_at: iso,
        });
      }
      return created({
        id: 2, doc_id: 9, kind: "note", start_offset: null, end_offset: null,
        content: "thought", created_at: iso, updated_at: iso,
      });
    });
    const highlight = await api.createHighlight(9, { start_offset: 4, end_offset: 10, content: "hello" });
    const note = await api.createNote(9, { content: "thought", start_offset: null, end_offset: null });
    expect(highlight.kind).toBe("highlight");
    expect(note.kind).toBe("note");
    expect(calls.map((c) => c.method)).toEqual(["POST", "POST"]);
  });

  it("deletes an annotation (204) and surfaces backend detail on errors", async () => {
    const { calls } = stubFetch((call) => {
      if (call.method === "DELETE" && call.url.includes("/reports/")) {
        return error(400, "deleting a report requires an explicit confirm=true payload");
      }
      if (call.method === "DELETE") return noContent();
      return ok({});
    });
    await api.deleteAnnotation(7);
    expect(calls[0]?.method).toBe("DELETE");
    const err = await api.deleteReport(2, false).then(
      () => null,
      (e: unknown) => e as ApiError,
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err?.status).toBe(400);
    expect(err?.detail).toContain("explicit confirm");
  });

  it("fetches resource annotations and round expert runs (reload hydration)", async () => {
    const { calls } = stubFetch((call) => {
      if (call.url.endsWith("/annotations")) {
        return ok([
          {
            id: 1, doc_id: 9, kind: "note", start_offset: null, end_offset: null,
            content: "thought", created_at: iso, updated_at: iso,
          },
        ]);
      }
      return ok({
        expert_runs: [
          {
            id: 5, round_id: 1, doc_id: 3, doc_path: "a.md",
            lens_proposal_id: 11, lens_rationale: "financial lens", lens_title: "financial",
            notes: [
              { id: 1, expert_run_id: 5, content: "n1", edited_content: null, review_state: "pending", merged: false, position: 0 },
            ],
          },
        ],
      });
    });
    const annotations = await api.getResourceAnnotations(9);
    expect(annotations).toHaveLength(1);
    expect(annotations[0]?.content).toBe("thought");
    const runs = await api.getRoundExpertRuns(1);
    expect(runs.expert_runs[0]?.lens_proposal_id).toBe(11);
    expect(runs.expert_runs[0]?.lens_rationale).toBe("financial lens");
    expect(runs.expert_runs[0]?.notes[0]?.merged).toBe(false);
    expect(calls.map((c) => c.url)).toEqual([
      "/api/v1/resources/9/annotations",
      "/api/v1/rounds/1/expert-runs",
    ]);
  });

  it("marks lenses selected and runs experts for a round", async () => {
    const { calls } = stubFetch((call) => {
      if (call.url.includes("/lens-proposals/") && call.method === "PATCH") {
        return ok({
          id: 11, doc_id: 3, title: "financial", rationale: "r", status: "selected", created_at: iso,
        });
      }
      return created({
        expert_runs: [
          {
            id: 5, round_id: 1, doc_id: 3, doc_path: "a.md", lens_title: "financial",
            notes: [
              { id: 1, expert_run_id: 5, content: "n1", edited_content: null, review_state: "pending", position: 0 },
            ],
          },
        ],
      });
    });
    const proposal = await api.setLensProposalStatus(11, "selected");
    expect(proposal.status).toBe("selected");
    const runs = await api.runExperts(1, [11]);
    expect(runs.expert_runs[0]?.notes[0]?.content).toBe("n1");
    expect(calls[1]).toMatchObject({ method: "POST", url: "/api/v1/rounds/1/experts" });
  });

  it("saves and fetches the dump with entry payloads", async () => {
    const entry: DumpEntryOut = {
      id: 3, round_id: 1, dump_id: 4, kind: "snippet", content: "text", doc_id: 2,
      doc_path: "b.md", expert_note_id: null, position: 0, created_at: iso,
    };
    const { calls } = stubFetch((call) => {
      if (call.method === "POST") {
        expect(call.body).toEqual({ entries: [{ id: null, kind: "snippet", content: "text", doc_id: 2 }] });
        return ok({ round_id: 1, dump_id: 4, saved: true, entries: [entry] });
      }
      return ok({ round_id: 1, dump_id: 4, saved: true, entries: [entry] });
    });
    const saved = await api.saveDump(1, [{ id: null, kind: "snippet", content: "text", doc_id: 2 }]);
    expect(saved.saved).toBe(true);
    const fetched = await api.getDump(1);
    expect(fetched.entries[0]?.doc_path).toBe("b.md");
    expect(calls[1]?.url).toBe("/api/v1/rounds/1/dump");
  });

  it("generates a report and updates a block", async () => {
    const report: ReportOut = {
      id: 9, round_id: 1, created_at: iso,
      blocks: [{ id: 21, report_id: 9, position: 0, content: "para", source_entry_ids: [3], created_at: iso, updated_at: iso }],
    };
    const { calls } = stubFetch((call) => {
      if (call.method === "POST" && call.url.includes("generate-report")) return created(report);
      if (call.method === "PUT") {
        expect(call.body).toEqual({ content: "edited para" });
        return ok({ ...report.blocks[0], content: "edited para", updated_at: iso });
      }
      return ok(report);
    });
    const generated = await api.generateReport(1);
    expect(generated.blocks[0]?.content).toBe("para");
    const updated = await api.updateBlock(21, "edited para");
    expect(updated.content).toBe("edited para");
    expect(calls[1]).toMatchObject({ method: "PUT", url: "/api/v1/blocks/21" });
  });

  it("fetches tone samples and critique per block", async () => {
    const { calls } = stubFetch((call) => {
      if (call.url.endsWith("/tone-samples")) {
        return ok({ samples: [{ tone: "formal", text: "x" }] });
      }
      return ok({ critique: "challenge" });
    });
    const tone = await api.toneSamples(21);
    expect(tone.samples).toHaveLength(1);
    const critique = await api.critiqueBlock(21);
    expect(critique.critique).toBe("challenge");
    expect(calls.map((c) => c.url)).toEqual([
      "/api/v1/blocks/21/tone-samples",
      "/api/v1/blocks/21/critique",
    ]);
  });

  it("exports markdown as text", async () => {
    const { calls } = stubFetch((call) => {
      expect(call.url).toBe("/api/v1/reports/9/export.md");
      return { status: 200, text: "# Report\n\npara\n" };
    });
    const markdown = await api.exportMarkdown(9);
    expect(markdown).toContain("# Report");
    expect(calls).toHaveLength(1);
  });
});
