import type { ExpertNoteOut, RoundDetailOut } from "../../api/types";
import { Badge } from "../../components/ui/badge";
import type { ExpertDocState, LensDocState } from "./state";
import LensExpertPanel from "./LensExpertPanel";

interface RoundReadingPaneProps {
  round: RoundDetailOut | null;
  roundLoading: boolean;
  roundError: string | null;
  docId: number;
  docInRound: boolean;
  lens: LensDocState | null;
  experts: ExpertDocState;
  onProposeLenses: () => void;
  onSetProposalStatus: (proposalId: number, status: "selected" | "skipped") => void;
  onRunSelected: () => void;
  onKeepNote: (note: ExpertNoteOut) => void;
  onDiscardNote: (note: ExpertNoteOut) => void;
  onMergeNote: (note: ExpertNoteOut, content: string | null) => void;
}

export default function RoundReadingPane({
  round,
  roundLoading,
  roundError,
  docId,
  docInRound,
  lens,
  experts,
  onProposeLenses,
  onSetProposalStatus,
  onRunSelected,
  onKeepNote,
  onDiscardNote,
  onMergeNote,
}: RoundReadingPaneProps) {
  if (round === null) {
    return (
      <div data-testid="round-closed" className="rounded-md border p-3 text-sm text-muted-foreground">
        {roundLoading
          ? "Loading round…"
          : roundError !== null
            ? `Round failed to load: ${roundError}`
            : "Select a round from the sidebar to propose lenses and run experts on its docs."}
      </div>
    );
  }
  if (round.stage === "editing") {
    return (
      <div data-testid="round-closed" className="rounded-md border p-3">
        <div className="flex items-center gap-2">
          <Badge variant="outline">editing</Badge>
          <span className="text-sm">{round.name}</span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          This round is in the editing stage: its expert runs and curation are closed (R-042). Annotating
          docs stays available project-wide. Start a new round to run the reading flow again.
        </p>
      </div>
    );
  }
  return (
    <LensExpertPanel
      round={round}
      docId={docId}
      docInRound={docInRound}
      lensProposals={lens?.proposals ?? []}
      lensStatus={lens?.status ?? "idle"}
      lensError={lens?.error ?? null}
      expertRuns={experts.status === "ready" ? experts.runs : []}
      expertBusy={experts.status === "loading"}
      expertError={experts.status === "error" ? experts.error : null}
      onProposeLenses={onProposeLenses}
      onSetProposalStatus={onSetProposalStatus}
      onRunSelected={onRunSelected}
      onKeepNote={onKeepNote}
      onDiscardNote={onDiscardNote}
      onMergeNote={onMergeNote}
    />
  );
}
