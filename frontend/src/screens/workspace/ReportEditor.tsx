import { Download, Feather, Loader2, MessageSquareWarning, Trash2, Wand2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { ReportBlockOut, ReportOut, ToneSampleOut } from "../../api/types";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Textarea } from "../../components/ui/fields";
import { EmptyHint, InlineError } from "../../components/ui/feedback";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../components/ui/dialog";

interface ReportEditorProps {
  reportId: number;
  roundName: string;
  onReportDeleted: () => void;
}

interface AssistState {
  tone: {
    busy: boolean;
    samples: ToneSampleOut[] | null;
    error: string | null;
  };
  critique: { busy: boolean; text: string | null; error: string | null };
}

const emptyAssist = (): AssistState => ({
  tone: { busy: false, samples: null, error: null },
  critique: { busy: false, text: null, error: null },
});

export default function ReportEditor({ reportId, roundName, onReportDeleted }: ReportEditorProps) {
  const [report, setReport] = useState<ReportOut | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [assists, setAssists] = useState<Record<number, AssistState>>({});
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    setLoadError(null);
    api
      .getReport(reportId)
      .then(setReport)
      .catch((err) => setLoadError(err instanceof ApiError ? err.detail : (err as Error).message));
  }, [reportId]);

  const setBlockContent = (blockId: number, content: string): void => {
    setReport((prev) => {
      if (prev === null) return prev;
      return {
        ...prev,
        blocks: prev.blocks.map((b) => (b.id === blockId ? { ...b, content } : b)),
      };
    });
  };

  const assistFor = (blockId: number): AssistState => assists[blockId] ?? emptyAssist();
  const patchAssist = (blockId: number, patch: Partial<AssistState>): void => {
    setAssists((prev) => ({ ...prev, [blockId]: { ...(prev[blockId] ?? emptyAssist()), ...patch } }));
  };

  const requestTone = async (block: ReportBlockOut): Promise<void> => {
    patchAssist(block.id, { tone: { busy: true, samples: null, error: null } });
    try {
      const result = await api.toneSamples(block.id);
      patchAssist(block.id, { tone: { busy: false, samples: result.samples, error: null } });
    } catch (err) {
      patchAssist(block.id, {
        tone: {
          busy: false,
          samples: null,
          error: err instanceof ApiError ? err.detail : (err as Error).message,
        },
      });
    }
  };

  const applyTone = async (block: ReportBlockOut, sample: ToneSampleOut): Promise<void> => {
    const current = assistFor(block.id).tone;
    patchAssist(block.id, { tone: { busy: true, samples: current.samples, error: null } });
    try {
      const updated = await api.updateBlock(block.id, sample.text);
      setBlockContent(updated.id, updated.content);
      patchAssist(block.id, { tone: { busy: false, samples: null, error: null } });
    } catch (err) {
      patchAssist(block.id, {
        tone: {
          busy: false,
          samples: current.samples,
          error: err instanceof ApiError ? err.detail : (err as Error).message,
        },
      });
    }
  };

  const requestCritique = async (block: ReportBlockOut): Promise<void> => {
    patchAssist(block.id, { critique: { ...assistFor(block.id).critique, busy: true, error: null } });
    try {
      const result = await api.critiqueBlock(block.id);
      patchAssist(block.id, { critique: { busy: false, text: result.critique, error: null } });
    } catch (err) {
      patchAssist(block.id, {
        critique: {
          busy: false,
          text: assistFor(block.id).critique.text,
          error: err instanceof ApiError ? err.detail : (err as Error).message,
        },
      });
    }
  };

  const handleExport = async (): Promise<void> => {
    setExportError(null);
    setExporting(true);
    try {
      const markdown = await api.exportMarkdown(reportId);
      const blob = new Blob([markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${reportId}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async (): Promise<void> => {
    setDeleteError(null);
    setDeleting(true);
    try {
      await api.deleteReport(reportId, true);
      setDeleteOpen(false);
      onReportDeleted();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  if (loadError !== null) {
    return <div className="p-5"><InlineError message={loadError} /></div>;
  }
  if (report === null) {
    return <div className="p-5"><EmptyHint>Loading report…</EmptyHint></div>;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-5 py-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Report editor</h2>
          <Badge variant="outline">{roundName}</Badge>
          <span className="text-xs text-muted-foreground">
            editing stage — this round&apos;s reading actions are closed
          </span>
        </div>
        <div className="flex items-center gap-2">
          {exportError !== null && <InlineError message={exportError} />}
          <Button size="sm" variant="outline" disabled={exporting} onClick={() => void handleExport()}>
            <Download className="mr-1 h-3 w-3" />
            {exporting ? "Exporting…" : "Download .md"}
          </Button>
          <Button size="sm" variant="destructive" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="mr-1 h-3 w-3" />
            Delete report
          </Button>
        </div>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {report.blocks.length === 0 ? (
          <EmptyHint>The report has no paragraphs.</EmptyHint>
        ) : (
          report.blocks.map((block) => (
            <BlockEditorCard
              key={block.id}
              block={block}
              assist={assistFor(block.id)}
              onBlockContentSaved={setBlockContent}
              onTone={() => void requestTone(block)}
              onApplyTone={(sample) => void applyTone(block, sample)}
              onCloseTone={() =>
                patchAssist(block.id, { tone: { busy: false, samples: null, error: null } })
              }
              onCritique={() => void requestCritique(block)}
              onCloseCritique={() =>
                patchAssist(block.id, {
                  critique: { busy: false, text: null, error: null },
                })
              }
            />
          ))
        )}
      </div>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete report?</DialogTitle>
            <DialogDescription>
              The report is removed but {roundName} and its curated dump remain. Generation is one-shot per
              round — a new report requires a new round.
            </DialogDescription>
          </DialogHeader>
          {deleteError !== null && <InlineError message={deleteError} />}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" disabled={deleting} onClick={() => void handleDelete()}>
              {deleting ? "Deleting…" : "Delete report"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface BlockCardProps {
  block: ReportBlockOut;
  assist: AssistState;
  onBlockContentSaved: (blockId: number, content: string) => void;
  onTone: () => void;
  onApplyTone: (sample: ToneSampleOut) => void;
  onCloseTone: () => void;
  onCritique: () => void;
  onCloseCritique: () => void;
}

function BlockEditorCard({
  block,
  assist,
  onBlockContentSaved,
  onTone,
  onApplyTone,
  onCloseTone,
  onCritique,
  onCloseCritique,
}: BlockCardProps) {
  const [text, setText] = useState(block.content);
  const [saveState, setSaveState] = useState<"clean" | "dirty" | "saving" | "failed">("clean");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const lastSyncedContent = useRef(block.content);

  useEffect(() => {
    if (lastSyncedContent.current === block.content) return;
    lastSyncedContent.current = block.content;
    if (saveState !== "dirty" && saveState !== "failed") setText(block.content);
  }, [block.content, saveState]);

  const save = async (): Promise<void> => {
    if (text === block.content) {
      setSaveState("clean");
      return;
    }
    if (text.trim().length === 0) {
      setSaveError("a block cannot be empty");
      setSaveState("failed");
      return;
    }
    setSaveState("saving");
    setSaveError(null);
    try {
      const updated = await api.updateBlock(block.id, text);
      onBlockContentSaved(updated.id, updated.content);
      setSaveState("clean");
    } catch (err) {
      setSaveState("failed");
      setSaveError(err instanceof ApiError ? err.detail : (err as Error).message);
    }
  };

  const statusLabel =
    saveState === "clean"
      ? "saved"
      : saveState === "saving"
        ? "saving…"
        : saveState === "failed"
          ? "save failed"
          : "unsaved changes";

  return (
    <div className="rounded-lg border bg-card">
      <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">paragraph {block.position + 1}</Badge>
          {block.source_entry_ids.length > 0 && (
            <span className="text-xs text-muted-foreground">
              sourced from {block.source_entry_ids.length} dump entr{block.source_entry_ids.length === 1 ? "y" : "ies"}
            </span>
          )}
        </div>
        <span
          className={`text-xs ${saveState === "failed" ? "text-destructive" : "text-muted-foreground"}`}
          data-testid={`save-state-${block.id}`}
        >
          {statusLabel}
        </span>
      </div>
      <div className="space-y-2 p-3">
        <Textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (saveState === "clean") setSaveState("dirty");
          }}
          onBlur={() => {
            if (saveState === "dirty" || saveState === "failed") void save();
          }}
          aria-label={`Block ${block.position + 1} content`}
          className="min-h-[90px] text-sm leading-relaxed"
        />
        {saveError !== null && <InlineError message={saveError} />}

        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" disabled={assist.tone.busy} onClick={onTone}>
            <Wand2 className="mr-1 h-3 w-3" />
            {assist.tone.busy ? "Generating samples…" : "Change of tone"}
          </Button>
          <Button size="sm" variant="outline" disabled={assist.critique.busy} onClick={onCritique}>
            <MessageSquareWarning className="mr-1 h-3 w-3" />
            {assist.critique.busy ? "Critiquing…" : "Critique"}
          </Button>
          {(saveState === "dirty" || saveState === "failed") && (
            <Button size="sm" onClick={() => void save()}>
              Save paragraph
            </Button>
          )}
        </div>

        {assist.tone.error !== null && <InlineError message={assist.tone.error} />}
        {assist.tone.samples !== null && (
          <div className="space-y-2 rounded-md border border-primary/20 bg-muted/30 p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">
                {assist.tone.samples.length} tone sample{assist.tone.samples.length === 1 ? "" : "s"}
              </span>
              <Button size="sm" variant="ghost" onClick={onCloseTone}>
                <X className="mr-1 h-3 w-3" />
                Discard samples
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Block text is unchanged until you apply a sample.
            </p>
            <div className="space-y-2">
              {assist.tone.samples.map((sample, index) => (
                <div key={index} className="rounded-md border bg-background p-2">
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline">{sample.tone}</Badge>
                    <div className="flex gap-2">
                      {previewIndex === index ? (
                        <Button size="sm" variant="secondary" onClick={() => setPreviewIndex(null)}>
                          Hide preview
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => setPreviewIndex(index)}>
                          Preview
                        </Button>
                      )}
                      <Button
                        size="sm"
                        data-testid={`apply-sample-${index}`}
                        onClick={() => onApplyTone(sample)}
                      >
                        Apply
                      </Button>
                    </div>
                  </div>
                  <p className="mt-1.5 whitespace-pre-wrap text-sm">{sample.text}</p>
                </div>
              ))}
            </div>
            {previewIndex !== null && assist.tone.samples[previewIndex] !== undefined && (
              <div className="grid grid-cols-2 gap-3 rounded-md border bg-background p-3">
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Current paragraph
                  </p>
                  <p className="text-sm">{block.content}</p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-primary">
                    Previewing “{assist.tone.samples[previewIndex]!.tone}”
                  </p>
                  <p className="text-sm">{assist.tone.samples[previewIndex]!.text}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {assist.critique.error !== null && <InlineError message={assist.critique.error} />}
        {assist.critique.text !== null && (
          <div className="rounded-md border border-primary/20 bg-muted/30 p-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-sm font-medium">
                <Feather className="h-4 w-4 text-muted-foreground" />
                Critique — read-only; rewrite the paragraph yourself
              </span>
              <Button size="sm" variant="ghost" onClick={onCloseCritique}>
                <X className="mr-1 h-3 w-3" />
                Dismiss
              </Button>
            </div>
            <div className="mt-2 whitespace-pre-wrap text-sm leading-relaxed" data-testid="critique-text">
              {assist.critique.text}
            </div>
          </div>
        )}
        {assist.critique.busy && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Running critique…
          </div>
        )}
      </div>
    </div>
  );
}
