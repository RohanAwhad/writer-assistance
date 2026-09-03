import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReportOut } from "../api/types";
import ReportEditor from "../screens/workspace/ReportEditor";
import { ok, stubFetch } from "./fetchMock";

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
      content: "Rent controls reduce supply, so they must be harmful.",
      source_entry_ids: [1],
      created_at: iso,
      updated_at: iso,
    },
  ],
};

const critiqueText =
  "The claim assumes supply elasticity dominates. Does the evidence for short-run vs long-run responses support that? Who benefits and who pays under the policy?";

describe("critique panel (R-052/R-053)", () => {
  it("renders the critique read-only and never auto-edits the block; repeatable", async () => {
    const user = userEvent.setup();
    let critiqueRequests = 0;
    const { calls } = stubFetch((call) => {
      if (call.method === "POST" && call.url.endsWith("/critique")) {
        critiqueRequests += 1;
        return ok({ critique: critiqueText });
      }
      return ok(report);
    });

    render(<ReportEditor reportId={9} roundName="Round 1" onReportDeleted={() => undefined} />);
    await screen.findByLabelText("Block 1 content");

    await user.click(screen.getByRole("button", { name: "Critique" }));
    const panel = await screen.findByTestId("critique-text");
    expect(panel).toHaveTextContent("supply elasticity dominates");

    const textarea = screen.getByLabelText("Block 1 content");
    expect(textarea).toHaveValue("Rent controls reduce supply, so they must be harmful.");
    expect(calls.some((c) => c.method === "PUT")).toBe(false);

    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    await waitFor(() => expect(screen.queryByTestId("critique-text")).not.toBeInTheDocument());
    expect(textarea).toHaveValue("Rent controls reduce supply, so they must be harmful.");

    await user.click(screen.getByRole("button", { name: "Critique" }));
    await screen.findByTestId("critique-text");
    expect(critiqueRequests).toBe(2);
    expect(calls.some((c) => c.method === "PUT")).toBe(false);
    expect(textarea).toHaveValue("Rent controls reduce supply, so they must be harmful.");
  });
});
