import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReportOut } from "../api/types";
import ReportEditor from "../screens/workspace/ReportEditor";
import { lastJson, ok, stubFetch } from "./fetchMock";

afterEach(() => {
  vi.unstubAllGlobals();
});

const iso = "2026-09-03T00:00:00+00:00";

const report: ReportOut = {
  id: 9,
  round_id: 1,
  created_at: iso,
  blocks: [
    {
      id: 21,
      report_id: 9,
      position: 0,
      content: "The original paragraph under discussion.",
      source_entry_ids: [1],
      created_at: iso,
      updated_at: iso,
    },
  ],
};

const samples = [
  { tone: "formal", text: "Formal sample version of the paragraph." },
  { tone: "conversational", text: "Conversational sample version of the paragraph." },
  { tone: "punchy", text: "Punchy sample version of the paragraph." },
  { tone: "warm", text: "Warm sample version of the paragraph." },
  { tone: "analytical", text: "Analytical sample version of the paragraph." },
];

describe("tone samples (R-050/R-051)", () => {
  it("renders exactly 5 samples without touching the block, and applies only on explicit Apply", async () => {
    const user = userEvent.setup();
    const { calls } = stubFetch((call) => {
      if (call.method === "POST" && call.url.endsWith("/tone-samples")) {
        return ok({ samples });
      }
      if (call.method === "PUT") {
        return ok({ ...report.blocks[0]!, content: lastJson<{ content: string }>(calls).content, updated_at: iso });
      }
      return ok(report);
    });
    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);

    const textarea = await screen.findByLabelText("Block 1 content");
    await user.click(screen.getByRole("button", { name: "Change of tone" }));

    const sampleRows = await screen.findAllByTestId(/apply-sample-/);
    expect(sampleRows).toHaveLength(5);
    for (const sample of samples) {
      expect(screen.getByText(sample.text)).toBeInTheDocument();
    }
    expect(screen.getByText("formal")).toBeInTheDocument();

    expect(textarea).toHaveValue("The original paragraph under discussion.");
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);

    const firstRow = screen.getByText(samples[0]!.text).closest(".rounded-md");
    expect(firstRow).not.toBeNull();
    await user.click(within(firstRow as HTMLElement).getByRole("button", { name: "Preview" }));

    expect(screen.getByText(/Previewing “formal”/)).toBeInTheDocument();
    expect(screen.getByText("Current paragraph")).toBeInTheDocument();
    expect(screen.getAllByText("The original paragraph under discussion.").length).toBeGreaterThan(0);
    expect(textarea).toHaveValue("The original paragraph under discussion.");

    const applyButtons = screen.getAllByTestId(/apply-sample-/);
    await user.click(applyButtons[0]!);

    await waitFor(() => {
      expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);
      const put = calls.find((c) => c.method === "PUT");
      expect(put).toMatchObject({ url: "/api/v1/blocks/21" });
      expect(lastJson<{ content: string }>(calls).content).toBe(samples[0]!.text);
    });
    await waitFor(() => {
      expect(screen.queryByText(/5 tone samples/)).not.toBeInTheDocument();
    });
    expect(await screen.findByLabelText("Block 1 content")).toHaveValue(samples[0]!.text);
  });
});
