import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReportOut } from "../api/types";
import ReportEditor from "../screens/workspace/ReportEditor";
import { lastJson, ok, stubFetch } from "./fetchMock";

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

describe("ReportEditor block editing (R-043)", () => {
  it("typing edits a block and persists via the api client; reload renders the saved text", async () => {
    const user = userEvent.setup();
    let savedContent = block1.content;
    const { calls } = stubFetch((call) => {
      if (call.method === "PUT") {
        savedContent = lastJson<{ content: string }>(calls).content;
        return ok({ ...block1, content: savedContent, updated_at: iso });
      }
      return ok(reportWith([{ ...block1, content: savedContent }]));
    });
    const first = render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);
    const textarea = await screen.findByLabelText("Block 1 content");
    expect(textarea).toHaveValue("First paragraph of the report.");

    await user.clear(textarea);
    await user.type(textarea, "Rewritten opening paragraph.");
    await waitFor(() => expect(screen.getByTestId("save-state-21")).toHaveTextContent("unsaved"));
    await user.tab();

    await waitFor(() => {
      expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);
      expect(calls[1]).toMatchObject({ method: "PUT", url: "/api/v1/blocks/21" });
      expect(lastJson<{ content: string }>(calls).content).toBe("Rewritten opening paragraph.");
    });
    await waitFor(() => expect(screen.getByTestId("save-state-21")).toHaveTextContent("saved"));

    first.unmount();

    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);
    await waitFor(() =>
      expect(screen.getByLabelText("Block 1 content")).toHaveValue("Rewritten opening paragraph."),
    );
  });
});
