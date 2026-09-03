import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReportOut, RoundSummary } from "../api/types";
import ReportEditor from "../screens/workspace/ReportEditor";
import RoundStageHeader from "../screens/workspace/RoundStageHeader";
import { error, lastJson, ok, stubFetch, type FetchCall, type StubResponse } from "./fetchMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

const iso = "2026-09-03T00:00:00+00:00";

function reportWith(blocks: ReportOut["blocks"]): ReportOut {
  return { id: 9, round_id: 1, created_at: iso, blocks };
}

const block1 = {
  id: 21,
  report_id: 9,
  position: 0,
  content: "First paragraph of the report.",
  source_entry_ids: [1],
  created_at: iso,
  updated_at: iso,
};

const block2 = {
  id: 22,
  report_id: 9,
  position: 1,
  content: "A **key** claim worth checking.",
  source_entry_ids: [2],
  created_at: iso,
  updated_at: iso,
};

const samples = [{ tone: "formal", text: "Formal sample version of the paragraph." }];

function stubGatedFetch(handler: (call: FetchCall, index: number) => StubResponse): {
  calls: FetchCall[];
  releaseNextPut: () => void;
} {
  const calls: FetchCall[] = [];
  const releases: Array<() => void> = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    let body: unknown = null;
    if (typeof init?.body === "string" && init.body.length > 0) {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    const call: FetchCall = { url, method, body };
    calls.push(call);
    if (method === "PUT") {
      await new Promise<void>((resolve) => {
        releases.push(resolve);
      });
    }
    const response = handler(call, calls.length - 1);
    const status = response.status ?? 200;
    if (status === 204) {
      return new Response(null, { status });
    }
    const jsonBody = response.json !== undefined ? JSON.stringify(response.json) : "{}";
    return new Response(jsonBody, {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn as unknown as typeof fetch);
  return {
    calls,
    releaseNextPut: () => {
      releases.shift()?.();
    },
  };
}

function putBodies(calls: FetchCall[]): string[] {
  return calls
    .filter((c) => c.method === "PUT")
    .map((c) => (c.body as { content: string }).content);
}

describe("view-mode rendering (R-060)", () => {
  it("renders every saved block read-only over the mocked GET /reports payload — no textarea, save state, per-block AI controls, or apply/delete actions", async () => {
    const user = userEvent.setup();
    const { calls } = stubFetch(() => ok(reportWith([block1, block2])));
    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);

    await screen.findByLabelText("Block 1 content");
    expect(screen.getByLabelText("Block 2 content")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete report" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "View" }));

    await waitFor(() => expect(screen.queryByLabelText("Block 1 content")).not.toBeInTheDocument());
    expect(screen.queryByLabelText("Block 2 content")).not.toBeInTheDocument();
    expect(screen.queryByTestId(/save-state-/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Change of tone" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Critique" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save paragraph" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete report" })).not.toBeInTheDocument();

    const first = screen.getByTestId("view-block-21");
    expect(first).toHaveTextContent("First paragraph of the report.");
    const second = screen.getByTestId("view-block-22");
    expect(second).toHaveTextContent("A key claim worth checking.");
    expect(second.querySelector("strong")?.textContent).toBe("key");
    expect(screen.queryByText("**key**")).not.toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Download .md" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);
    expect(calls.map((c) => c.method)).toEqual(["GET"]);
  });

  it("leaves no per-block AI controls behind in view mode even when a tone panel is open", async () => {
    const user = userEvent.setup();
    const { calls } = stubFetch((call) => {
      if (call.method === "POST" && call.url.endsWith("/tone-samples")) {
        return ok({ samples });
      }
      return ok(reportWith([block1]));
    });
    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);

    await screen.findByLabelText("Block 1 content");
    await user.click(screen.getByRole("button", { name: "Change of tone" }));
    const applyButton = await screen.findByTestId("apply-sample-0");
    expect(applyButton).toBeInTheDocument();
    expect(screen.getByText(samples[0]!.text)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "View" }));
    await waitFor(() => expect(screen.queryByLabelText("Block 1 content")).not.toBeInTheDocument());
    expect(screen.queryByTestId(/apply-sample-/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Change of tone" })).not.toBeInTheDocument();
    expect(screen.queryByText(samples[0]!.text)).not.toBeInTheDocument();
    expect(screen.getByTestId("view-block-21")).toHaveTextContent(block1.content);
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);
  });
});

describe("view ↔ editor switching (R-061)", () => {
  const summary: RoundSummary = {
    id: 1,
    project_id: 1,
    name: "Round 1",
    stage: "editing",
    doc_count: 1,
    created_at: iso,
    dump_id: 7,
    report_id: 9,
  };

  it("toggling preserves content and the editing badge, never writes by itself, flushes a dirty block exactly once, and view renders post-save content", async () => {
    const user = userEvent.setup();
    let savedContent = block1.content;
    const { calls } = stubFetch((call) => {
      if (call.method === "PUT") {
        savedContent = lastJson<{ content: string }>(calls).content;
        return ok({ ...block1, content: savedContent, updated_at: iso });
      }
      return ok(reportWith([{ ...block1, content: savedContent }]));
    });
    render(
      <div>
        <RoundStageHeader
          round={summary}
          mode="report"
          curateAllowed={false}
          reportAllowed
          onMode={() => undefined}
        />
        <ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />
      </div>,
    );

    const textarea = await screen.findByLabelText("Block 1 content");
    expect(screen.getByTestId("round-stage-badge")).toHaveTextContent("editing");

    await user.clear(textarea);
    await user.type(textarea, "Opening rewritten for the view flow.");
    await user.click(screen.getByRole("button", { name: "View" }));

    const flushed = await screen.findByTestId("view-block-21");
    await waitFor(() => expect(flushed).toHaveTextContent("Opening rewritten for the view flow."));
    expect(screen.queryByLabelText("Block 1 content")).not.toBeInTheDocument();
    expect(screen.getByTestId("round-stage-badge")).toHaveTextContent("editing");
    const putsAfterFlush = calls.filter((c) => c.method === "PUT");
    expect(putsAfterFlush).toHaveLength(1);
    expect(putsAfterFlush[0]).toMatchObject({ url: "/api/v1/blocks/21" });
    expect(lastJson<{ content: string }>(calls).content).toBe("Opening rewritten for the view flow.");

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const reopened = await screen.findByLabelText("Block 1 content");
    expect(reopened).toHaveValue("Opening rewritten for the view flow.");
    expect(screen.getByTestId("round-stage-badge")).toHaveTextContent("editing");
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);

    await user.clear(reopened);
    await user.type(reopened, "Second revision, saved explicitly.");
    await user.click(screen.getByRole("button", { name: "Save paragraph" }));
    await waitFor(() => expect(screen.getByTestId("save-state-21")).toHaveTextContent("saved"));
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: "View" }));
    const afterSave = await screen.findByTestId("view-block-21");
    await waitFor(() =>
      expect(afterSave).toHaveTextContent("Second revision, saved explicitly."),
    );
    expect(screen.getByTestId("round-stage-badge")).toHaveTextContent("editing");
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(2);
  });
});

describe("view mode flush convergence (M2F1)", () => {
  it("re-saves keystrokes typed while a save is in flight before switching — no stale render, no dropped text", async () => {
    const user = userEvent.setup();
    const { calls, releaseNextPut } = stubGatedFetch((call) => {
      if (call.method === "PUT") {
        return ok({ ...block1, content: (call.body as { content: string }).content, updated_at: iso });
      }
      return ok(reportWith([block1]));
    });
    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);

    const textarea = (await screen.findByLabelText("Block 1 content")) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "Saved on first blur.");
    await user.click(screen.getByRole("button", { name: "View" }));
    await waitFor(() => expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1));

    await user.click(textarea);
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    await user.type(textarea, " plus later keystrokes.");

    releaseNextPut();
    await waitFor(() => expect(calls.filter((c) => c.method === "PUT")).toHaveLength(2));

    releaseNextPut();
    const viewBlock = await screen.findByTestId("view-block-21");
    await waitFor(() =>
      expect(viewBlock).toHaveTextContent("Saved on first blur. plus later keystrokes."),
    );
    expect(screen.queryByLabelText("Block 1 content")).not.toBeInTheDocument();
    expect(putBodies(calls)).toEqual([
      "Saved on first blur.",
      "Saved on first blur. plus later keystrokes.",
    ]);
  });
});

describe("apply-tone write serialization (M2F2)", () => {
  it("serializes an apply behind an in-flight dirty save — one PUT per write, view shows the applied text", async () => {
    const user = userEvent.setup();
    const { calls, releaseNextPut } = stubGatedFetch((call) => {
      if (call.method === "POST" && call.url.endsWith("/tone-samples")) {
        return ok({ samples });
      }
      if (call.method === "PUT") {
        return ok({ ...block1, content: (call.body as { content: string }).content, updated_at: iso });
      }
      return ok(reportWith([block1]));
    });
    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);

    const textarea = await screen.findByLabelText("Block 1 content");
    await user.click(screen.getByRole("button", { name: "Change of tone" }));
    await screen.findByTestId("apply-sample-0");

    await user.clear(textarea);
    await user.type(textarea, "Junk draft typed while samples are open.");
    await user.click(screen.getByTestId("apply-sample-0"));
    await waitFor(() => expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1));

    releaseNextPut();
    await waitFor(() => expect(calls.filter((c) => c.method === "PUT")).toHaveLength(2));

    releaseNextPut();
    await waitFor(() => expect(screen.queryByTestId(/apply-sample-/)).not.toBeInTheDocument());
    expect(await screen.findByLabelText("Block 1 content")).toHaveValue(samples[0]!.text);

    await user.click(screen.getByRole("button", { name: "View" }));
    const viewBlock = await screen.findByTestId("view-block-21");
    await waitFor(() => expect(viewBlock).toHaveTextContent(samples[0]!.text));
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(2);
    expect(putBodies(calls)).toEqual(["Junk draft typed while samples are open.", samples[0]!.text]);
  });
});

describe("flush-failure honesty (M2F3)", () => {
  it("keeps the editor open with the save error and the typed text when a flush PUT fails; a recovered retry switches to view", async () => {
    const user = userEvent.setup();
    let failingPutsLeft = 1;
    const { calls } = stubFetch((call) => {
      if (call.method === "PUT") {
        if (failingPutsLeft > 0) {
          failingPutsLeft -= 1;
          return error(500, "backend hiccup");
        }
        return ok({ ...block1, content: (call.body as { content: string }).content, updated_at: iso });
      }
      return ok(reportWith([block1]));
    });
    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);

    const textarea = await screen.findByLabelText("Block 1 content");
    await user.clear(textarea);
    await user.type(textarea, "Text that must survive.");

    await user.click(screen.getByRole("button", { name: "View" }));
    await waitFor(() => expect(screen.getByTestId("save-state-21")).toHaveTextContent("save failed"));
    expect(screen.getByText("backend hiccup")).toBeInTheDocument();
    expect(screen.getByLabelText("Block 1 content")).toHaveValue("Text that must survive.");
    expect(screen.queryByTestId("view-block-21")).not.toBeInTheDocument();
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "View" }));
    const viewBlock = await screen.findByTestId("view-block-21");
    await waitFor(() => expect(viewBlock).toHaveTextContent("Text that must survive."));
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(2);
    expect(putBodies(calls)[1]).toBe("Text that must survive.");
  });

  it("refuses to switch to view while a block is empty — editor stays, error shown, no PUT", async () => {
    const user = userEvent.setup();
    const { calls } = stubFetch((call) => {
      if (call.method === "PUT") {
        return ok({ ...block1, content: (call.body as { content: string }).content, updated_at: iso });
      }
      return ok(reportWith([block1]));
    });
    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);

    const textarea = await screen.findByLabelText("Block 1 content");
    await user.clear(textarea);

    await user.click(screen.getByRole("button", { name: "View" }));
    await waitFor(() => expect(screen.getByText("a block cannot be empty")).toBeInTheDocument());
    expect(screen.getByTestId("save-state-21")).toHaveTextContent("save failed");
    expect(screen.getByLabelText("Block 1 content")).toHaveValue("");
    expect(screen.queryByTestId("view-block-21")).not.toBeInTheDocument();
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);

    await user.type(textarea, "Now it has content.");
    await user.click(screen.getByRole("button", { name: "View" }));
    const viewBlock = await screen.findByTestId("view-block-21");
    await waitFor(() => expect(viewBlock).toHaveTextContent("Now it has content."));
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);
  });
});
