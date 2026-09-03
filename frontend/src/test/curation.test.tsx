import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RoundDetailOut } from "../api/types";
import CurateView, { type PoolItem } from "../screens/workspace/CurateView";
import { lastJson, ok, stubFetch } from "./fetchMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

const iso = "2026-09-03T00:00:00+00:00";

const round: RoundDetailOut = {
  id: 1,
  project_id: 2,
  name: "Round 1",
  stage: "reading",
  created_at: iso,
  updated_at: iso,
  docs: [
    { id: 11, path: "brief.md" },
    { id: 12, path: "notes.md" },
  ],
  dump_id: null,
  report_id: null,
};

const poolHighlight: PoolItem = {
  key: "annotation-101",
  kind: "highlight",
  docId: 11,
  docPath: "brief.md",
  text: "The rent cap binds in three districts.",
  entryId: null,
};

const poolNote: PoolItem = {
  key: "annotation-102",
  kind: "human-thought",
  docId: 12,
  docPath: "notes.md",
  text: "Compare with the 2019 study before writing.",
  entryId: null,
};

function renderCurate() {
  return render(
    <CurateView
      round={round}
      poolHighlights={[poolHighlight]}
      poolNotes={[poolNote]}
      poolAiThoughts={[]}
      refreshKey={0}
      onDumpStateChange={() => undefined}
      onGenerate={() => Promise.resolve()}
      onRoundChanged={() => undefined}
    />,
  );
}

describe("curation entry list (R-031)", () => {
  it("adds entries from pools, removes and reorders them, and saves in dump order", async () => {
    const user = userEvent.setup();
    const { calls } = stubFetch((call) => {
      if (call.method === "POST" && call.url.endsWith("/dump")) {
        const body = lastJson<{ entries: Array<{ id: number | null; kind: string; content: string; doc_id: number | null }> }>(calls);
        const savedEntries = body.entries.map((e, i) => ({
          id: i + 1,
          round_id: round.id,
          dump_id: 7,
          kind: e.kind,
          content: e.content,
          doc_id: e.doc_id,
          doc_path: e.doc_id === 11 ? "brief.md" : "notes.md",
          expert_note_id: null,
          position: i,
          created_at: iso,
        }));
        return ok({ round_id: round.id, dump_id: 7, saved: true, entries: savedEntries });
      }
      return ok({ round_id: round.id, dump_id: null, saved: false, entries: [] });
    });

    renderCurate();
    expect(await screen.findByText("Dump entries (0)")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Add Highlights to dump/ }));
    await user.click(screen.getByRole("button", { name: /Add Your notes to dump/ }));

    await waitFor(() => expect(screen.getByText("Dump entries (2)")).toBeInTheDocument());
    const rows = screen.getAllByTestId("dump-entry");
    expect(rows).toHaveLength(2);
    expect(within(rows[0]!).getByText("highlight")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("human thought")).toBeInTheDocument();

    await user.click(within(rows[1]!).getByRole("button", { name: "Remove entry" }));
    await waitFor(() => expect(screen.getByText("Dump entries (1)")).toBeInTheDocument());
    const remaining = screen.getAllByTestId("dump-entry");
    expect(remaining).toHaveLength(1);
    expect(within(remaining[0]!).getByText("highlight")).toBeInTheDocument();
    expect(within(remaining[0]!).queryByText("human thought")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save dump" }));
    await waitFor(() => {
      const post = calls.find((c) => c.method === "POST" && c.url.endsWith("/dump"));
      expect(post).toBeDefined();
      const payload = post?.body as { entries: Array<{ kind: string }> };
      expect(payload.entries.map((e) => e.kind)).toEqual(["highlight"]);
    });
    await waitFor(() => expect(screen.getByText("Dump entries (1)")).toBeInTheDocument());
  });

  it("reorders entries before saving and persists the chosen order", async () => {
    const user = userEvent.setup();
    const { calls } = stubFetch((call) => {
      if (call.method === "POST" && call.url.endsWith("/dump")) {
        const body = lastJson<{ entries: Array<{ id: number | null; kind: string; content: string; doc_id: number | null }> }>(calls);
        return ok({
          round_id: round.id,
          dump_id: 7,
          saved: true,
          entries: body.entries.map((e, i) => ({
            id: i + 1,
            round_id: round.id,
            dump_id: 7,
            kind: e.kind,
            content: e.content,
            doc_id: e.doc_id,
            doc_path: e.doc_id === 11 ? "brief.md" : "notes.md",
            expert_note_id: null,
            position: i,
            created_at: iso,
          })),
        });
      }
      return ok({ round_id: round.id, dump_id: null, saved: false, entries: [] });
    });

    renderCurate();
    await user.click(screen.getByRole("button", { name: /Add Highlights to dump/ }));
    await user.click(screen.getByRole("button", { name: /Add Your notes to dump/ }));
    await waitFor(() => expect(screen.getAllByTestId("dump-entry")).toHaveLength(2));

    let rows = screen.getAllByTestId("dump-entry");
    await user.click(within(rows[1]!).getByRole("button", { name: "Move up" }));
    rows = screen.getAllByTestId("dump-entry");
    expect(within(rows[0]!).getByText("human thought")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("highlight")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save dump" }));
    await waitFor(() => {
      const post = calls.find((c) => c.method === "POST" && c.url.endsWith("/dump"));
      const payload = post?.body as { entries: Array<{ kind: string; content: string }> };
      expect(payload.entries.map((e) => e.kind)).toEqual(["human-thought", "highlight"]);
      expect(payload.entries[0]?.content).toBe(poolNote.text);
      expect(payload.entries[1]?.content).toBe(poolHighlight.text);
    });
  });
});
