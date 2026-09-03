import { BrainCircuit, Pencil, Play, Sparkles, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import type {
  ExpertNoteOut,
  ExpertRunOut,
  LensProposalOut,
  RoundDetailOut,
} from "../../api/types";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Textarea } from "../../components/ui/fields";
import { Busy, EmptyHint, InlineError } from "../../components/ui/feedback";

interface LensExpertPanelProps {
  round: RoundDetailOut;
  docId: number;
  docInRound: boolean;
  lensProposals: LensProposalOut[];
  lensStatus: "idle" | "loading" | "error" | "ready";
  lensError: string | null;
  expertRuns: ExpertRunOut[];
  expertBusy: boolean;
  expertError: string | null;
  onProposeLenses: () => void;
  onSetProposalStatus: (proposalId: number, status: "selected" | "skipped") => void;
  onRunSelected: () => void;
  onKeepNote: (note: ExpertNoteOut) => void;
  onDiscardNote: (note: ExpertNoteOut) => void;
  onMergeNote: (note: ExpertNoteOut, content: string | null) => void;
}

const stateBadge: Record<string, "outline" | "secondary" | "default" | "destructive"> = {
  pending: "secondary",
  accepted: "outline",
  discarded: "destructive",
  "merged-with-edits": "default",
};

export default function LensExpertPanel({
  round,
  docId,
  docInRound,
  lensProposals,
  lensStatus,
  lensError,
  expertRuns,
  expertBusy,
  expertError,
  onProposeLenses,
  onSetProposalStatus,
  onRunSelected,
  onKeepNote,
  onDiscardNote,
  onMergeNote,
}: LensExpertPanelProps) {
  const [editNoteId, setEditNoteId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [mergeBusyId, setMergeBusyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (editNoteId !== null) {
      const note = expertRuns.flatMap((r) => r.notes).find((n) => n.id === editNoteId);
      if (note !== undefined) setEditDraft(note.content);
    }
  }, [editNoteId, expertRuns]);

  const selectedProposals = lensProposals.filter((p) => p.status === "selected" && p.doc_id === docId);
  const pendingNotes = expertRuns.flatMap((r) => r.notes).filter((n) => n.review_state === "pending");

  const runAction = useCallback(async (fn: () => Promise<void>): Promise<void> => {
    setActionError(null);
    try {
      await fn();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.detail : (err as Error).message);
    }
  }, []);

  const keep = (note: ExpertNoteOut): void => {
    void runAction(async () => {
      await onKeepNote(note);
    });
  };
  const discard = (note: ExpertNoteOut): void => {
    void runAction(async () => {
      await onDiscardNote(note);
    });
  };
  const setStatus = (proposal: LensProposalOut, status: "selected" | "skipped"): void => {
    void runAction(async () => {
      await onSetProposalStatus(proposal.id, status);
    });
  };
  const merge = async (note: ExpertNoteOut, content: string | null): Promise<void> => {
    setActionError(null);
    setMergeBusyId(note.id);
    try {
      await onMergeNote(note, content);
      setEditNoteId(null);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setMergeBusyId(null);
    }
  };

  const startEdit = (note: ExpertNoteOut): void => {
    setEditNoteId(note.id);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Lenses & experts · {round.name}
        </h3>
        <Badge variant={round.stage === "reading" ? "secondary" : "outline"}>{round.stage}</Badge>
      </div>

      {actionError !== null && <InlineError message={actionError} />}
      {expertError !== null && <InlineError message={expertError} />}

      {!docInRound ? (
        <div className="rounded-md border p-2 text-sm text-muted-foreground">
          This doc is not part of {round.name}&apos;s doc set. Experts run on docs inside the round — pick this
          doc when creating a round, or select another doc.
        </div>
      ) : (
        <>
          {lensStatus === "error" && <InlineError message={lensError ?? "failed to load lens proposals"} />}
          <div>
            <Button
              size="sm"
              variant="outline"
              className="w-full"
              disabled={lensStatus === "loading"}
              onClick={onProposeLenses}
            >
              <Sparkles className="mr-1 h-3 w-3" />
              {lensStatus === "loading" ? "Proposing…" : "Propose lenses for this doc"}
            </Button>
          </div>

          {lensStatus === "idle" && lensProposals.length === 0 && (
            <EmptyHint>The AI has not proposed lenses for this doc yet.</EmptyHint>
          )}

          {lensProposals.length > 0 && (
            <ul className="space-y-2">
              {lensProposals.map((proposal) => (
                <li key={proposal.id} className="rounded-md border p-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <BrainCircuit className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-sm font-medium">{proposal.title}</span>
                    </div>
                    <Badge variant="outline">{proposal.status}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{proposal.rationale}</p>
                  {proposal.status === "proposed" && (
                    <div className="mt-2 flex gap-2">
                      <Button size="sm" onClick={() => setStatus(proposal, "selected")}>
                        Select
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setStatus(proposal, "skipped")}>
                        Skip
                      </Button>
                    </div>
                  )}
                  {proposal.status === "selected" && (
                    <div className="mt-2 flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setStatus(proposal, "skipped")}
                      >
                        Skip instead
                      </Button>
                    </div>
                  )}
                  {proposal.status === "skipped" && (
                    <div className="mt-2 flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setStatus(proposal, "selected")}
                      >
                        Select instead
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}

          {lensProposals.some((p) => p.status === "proposed") && (
            <EmptyHint>Select the lenses you want to run as experts on this doc.</EmptyHint>
          )}

          <Button
            size="sm"
            className="w-full"
            disabled={selectedProposals.length === 0 || expertBusy}
            onClick={onRunSelected}
          >
            <Play className="mr-1 h-3 w-3" />
            {expertBusy
              ? "Experts reading…"
              : `Run expert${selectedProposals.length === 1 ? "" : "s"} (${selectedProposals.length} selected)`}
          </Button>

          {expertRuns.length > 0 && (
            <div className="space-y-3 pt-1">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Expert notes review
              </h4>
              {expertRuns.map((run) => (
                <div key={run.id} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">{run.lens_title}</Badge>
                    <span className="text-xs text-muted-foreground">{run.doc_path}</span>
                  </div>
                  <ul className="space-y-2">
                    {run.notes.map((note) => (
                      <li key={note.id} className="rounded-md border p-2">
                        <div className="flex items-center justify-between gap-2">
                          <Badge variant={stateBadge[note.review_state] ?? "outline"}>
                            {note.review_state}
                          </Badge>
                          {note.edited_content !== null && (
                            <span className="text-xs text-muted-foreground">edited</span>
                          )}
                        </div>
                        <p className="mt-1 whitespace-pre-wrap text-sm">{note.content}</p>
                        {editNoteId === note.id && (
                          <div className="mt-2 space-y-2">
                            <Textarea
                              value={editDraft}
                              onChange={(e) => setEditDraft(e.target.value)}
                              aria-label="Edited note text"
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                disabled={mergeBusyId === note.id || editDraft.trim().length === 0}
                                onClick={() => void merge(note, editDraft.trim())}
                              >
                                {mergeBusyId === note.id ? "Merging…" : "Add edited to my notes"}
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setEditNoteId(null)}>
                                Cancel
                              </Button>
                            </div>
                          </div>
                        )}
                        {note.review_state === "pending" && (
                          <div className="mt-2 flex flex-wrap gap-2">
                            <Button size="sm" variant="secondary" onClick={() => keep(note)}>
                              Keep
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => void merge(note, null)}
                              disabled={mergeBusyId === note.id}
                            >
                              {mergeBusyId === note.id ? "Merging…" : "Add to my notes"}
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => startEdit(note)}>
                              <Pencil className="mr-1 h-3 w-3" />
                              Edit & add
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => discard(note)}>
                              <Trash2 className="mr-1 h-3 w-3" />
                              Discard
                            </Button>
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {pendingNotes.length === 0 && expertRuns.length > 0 && (
                <EmptyHint>All notes reviewed. Discarded notes are closed; kept notes stay here.</EmptyHint>
              )}
            </div>
          )}
        </>
      )}

      {expertBusy && <Busy>AI experts are reading the doc and writing their notes…</Busy>}
    </div>
  );
}
