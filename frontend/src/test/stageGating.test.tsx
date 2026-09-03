import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RoundDetailOut, RoundSummary } from "../api/types";
import RoundReadingPane from "../screens/workspace/RoundReadingPane";
import RoundStageHeader, { type StageMode } from "../screens/workspace/RoundStageHeader";

afterEach(() => {
  vi.unstubAllGlobals();
});

const iso = "2026-09-03T00:00:00+00:00";

function readingRound(id: number, name: string): RoundDetailOut {
  return {
    id,
    project_id: 1,
    name,
    stage: "reading",
    created_at: iso,
    updated_at: iso,
    docs: [{ id: 11, path: "brief.md" }],
    dump_id: null,
    report_id: null,
  };
}

function editingRoundWithReport(): RoundDetailOut {
  return {
    id: 2,
    project_id: 1,
    name: "Round 2",
    stage: "editing",
    created_at: iso,
    updated_at: iso,
    docs: [{ id: 11, path: "brief.md" }],
    dump_id: 7,
    report_id: 9,
  };
}

const emptyProps = {
  roundLoading: false,
  roundError: null,
  docId: 11,
  docInRound: true,
  lens: null,
  experts: { status: "idle" } as const,
  onProposeLenses: () => undefined,
  onSetProposalStatus: () => Promise.resolve(),
  onRunSelected: () => undefined,
  onKeepNote: () => Promise.resolve(),
  onDiscardNote: () => Promise.resolve(),
  onMergeNote: () => Promise.resolve(),
};

describe("per-round stage gating (R-042)", () => {
  it("a reading round shows the lens/expert reading UI", () => {
    render(<RoundReadingPane round={readingRound(1, "Round 1")} {...emptyProps} />);
    expect(screen.queryByTestId("round-closed")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Propose lenses/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run expert/ })).toBeInTheDocument();
  });

  it("an editing round closes the reading UI; a new reading round reopens it", () => {
    const { rerender } = render(<RoundReadingPane round={editingRoundWithReport()} {...emptyProps} />);
    expect(screen.getByTestId("round-closed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Propose lenses/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Run expert/ })).not.toBeInTheDocument();
    expect(screen.getByText(/expert runs and curation are closed/)).toBeInTheDocument();

    rerender(<RoundReadingPane round={readingRound(3, "Round 3")} {...emptyProps} />);
    expect(screen.queryByTestId("round-closed")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Propose lenses/ })).toBeInTheDocument();
  });

  it("stage header disables curation for an editing round and enables it for a fresh reading round", async () => {
    const user = userEvent.setup();
    const onMode = vi.fn((_mode: StageMode) => undefined);
    const editingSummary: RoundSummary = {
      id: 2, project_id: 1, name: "Round 2", stage: "editing", doc_count: 1,
      created_at: iso, dump_id: 7, report_id: 9,
    };
    const { rerender } = render(
      <RoundStageHeader
        round={editingSummary}
        mode="report"
        curateAllowed={false}
        reportAllowed
        onMode={onMode}
      />,
    );
    const curateButton = screen.getByRole("button", { name: /Curate dump/ });
    expect(curateButton).toBeDisabled();
    expect(screen.getByRole("button", { name: /Report/ })).toBeEnabled();
    expect(screen.getByTestId("round-stage-badge")).toHaveTextContent("editing");

    const readingSummary: RoundSummary = {
      id: 3, project_id: 1, name: "Round 3", stage: "reading", doc_count: 1,
      created_at: iso, dump_id: null, report_id: null,
    };
    rerender(
      <RoundStageHeader
        round={readingSummary}
        mode="doc"
        curateAllowed
        reportAllowed={false}
        onMode={onMode}
      />,
    );
    const reopened = screen.getByRole("button", { name: /Curate dump/ });
    expect(reopened).toBeEnabled();
    expect(screen.getByTestId("round-stage-badge")).toHaveTextContent("reading");
    await user.click(reopened);
    expect(onMode).toHaveBeenCalledWith("curate");
  });
});
