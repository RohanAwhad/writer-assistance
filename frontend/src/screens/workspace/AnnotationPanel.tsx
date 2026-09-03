import { Highlighter, MessageSquarePlus, Trash2 } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { AnnotationOut } from "../../api/types";
import type { SelectionResult } from "../../components/MarkdownView";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Textarea } from "../../components/ui/fields";
import { EmptyHint, InlineError } from "../../components/ui/feedback";

interface AnnotationPanelProps {
  docId: number;
  docContent: string;
  docPath: string;
  annotations: AnnotationOut[];
  selection: SelectionResult | null;
  onAddAnnotation: (annotation: AnnotationOut) => void;
  onDeleteAnnotation: (annotationId: number) => void;
}

function snippet(docContent: string, start: number | null, end: number | null, max = 140): string {
  if (start === null || end === null) return "";
  const text = docContent.slice(start, end);
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

export default function AnnotationPanel({
  docId,
  docContent,
  docPath,
  annotations,
  selection,
  onAddAnnotation,
  onDeleteAnnotation,
}: AnnotationPanelProps) {
  const [noteDraft, setNoteDraft] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [anchorOn, setAnchorOn] = useState(false);
  const [busy, setBusy] = useState<"highlight" | "note" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submitHighlight = async (): Promise<void> => {
    if (selection === null || selection.start === null || selection.end === null) return;
    setError(null);
    setBusy("highlight");
    try {
      const annotation = await api.createHighlight(docId, {
        start_offset: selection.start,
        end_offset: selection.end,
        content: selection.text,
      });
      onAddAnnotation(annotation);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const submitNote = async (): Promise<void> => {
    if (noteDraft.trim().length === 0) return;
    setError(null);
    setBusy("note");
    try {
      const anchored = anchorOn && selection?.status === "ok" && selection.start !== null;
      const annotation = await api.createNote(docId, {
        content: noteDraft.trim(),
        start_offset: anchored ? selection!.start : null,
        end_offset: anchored ? selection!.end : null,
      });
      onAddAnnotation(annotation);
      setNoteDraft("");
      setNoteOpen(false);
      setAnchorOn(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const startAnchoredNote = (): void => {
    setAnchorOn(true);
    setNoteOpen(true);
  };

  const remove = async (annotationId: number): Promise<void> => {
    setError(null);
    try {
      await api.deleteAnnotation(annotationId);
      onDeleteAnnotation(annotationId);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : (err as Error).message);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Annotations
        </h3>
        <Badge variant="outline">read-only doc</Badge>
      </div>
      <p className="truncate text-xs text-muted-foreground" title={docPath}>
        {docPath}
      </p>

      {selection !== null && selection.status === "ok" && (
        <div className="space-y-2 rounded-md border border-primary/30 bg-primary/5 p-2">
          <p className="text-xs text-muted-foreground">
            Selection: “{selection.text.length > 90 ? `${selection.text.slice(0, 90)}…` : selection.text}”
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={busy !== null} onClick={() => void submitHighlight()}>
              <Highlighter className="mr-1 h-3 w-3" />
              {busy === "highlight" ? "Adding…" : "Highlight"}
            </Button>
            <Button size="sm" variant="outline" onClick={startAnchoredNote}>
              <MessageSquarePlus className="mr-1 h-3 w-3" />
              Note on selection
            </Button>
          </div>
        </div>
      )}
      {selection !== null && selection.status === "error" && (
        <InlineError message={selection.message ?? "could not map the selection"} />
      )}

      {error !== null && <InlineError message={error} />}

      {!noteOpen && (
        <Button
          size="sm"
          variant="outline"
          className="w-full"
          onClick={() => {
            setAnchorOn(false);
            setNoteOpen(true);
          }}
        >
          <MessageSquarePlus className="mr-1 h-3 w-3" />
          New note
        </Button>
      )}
      {noteOpen && (
        <div className="space-y-2">
          <Textarea
            autoFocus
            placeholder="Write a note…"
            value={noteDraft}
            onChange={(e) => setNoteDraft(e.target.value)}
            aria-label="Note text"
          />
          {anchorOn && <p className="text-xs text-muted-foreground">This note will anchor to your selection.</p>}
          <div className="flex gap-2">
            <Button size="sm" disabled={noteDraft.trim().length === 0 || busy !== null} onClick={() => void submitNote()}>
              {busy === "note" ? "Saving…" : "Save note"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setNoteOpen(false);
                setAnchorOn(false);
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {annotations.length === 0 ? (
        <EmptyHint>No annotations on this doc yet. Select text to highlight or attach a note.</EmptyHint>
      ) : (
        <ul className="space-y-2">
          {annotations.map((annotation) => (
            <li key={annotation.id} className="group rounded-md border p-2">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <Badge variant={annotation.kind === "highlight" ? "secondary" : "outline"}>
                    {annotation.kind === "highlight" ? "highlight" : "note"}
                  </Badge>
                  {annotation.start_offset !== null && (
                    <span className="text-xs text-muted-foreground">anchored</span>
                  )}
                </div>
                <button
                  type="button"
                  aria-label="Delete annotation"
                  className="text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                  onClick={() => void remove(annotation.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <p className="mt-1 whitespace-pre-wrap text-sm">
                {annotation.content ?? ""}
              </p>
              {annotation.start_offset !== null && (
                <p className="mt-1 border-l-2 pl-2 text-xs italic text-muted-foreground">
                  {snippet(docContent, annotation.start_offset, annotation.end_offset)}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
