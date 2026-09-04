import { ArrowDown, ArrowUp, FileText, ListPlus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { DumpEntryIn, DumpEntryKind, DumpEntryOut, DumpOut, RoundDetailOut } from "../../api/types";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Textarea } from "../../components/ui/fields";
import { EmptyHint, InlineError } from "../../components/ui/feedback";

export interface PoolItem {
  key: string;
  kind: "highlight" | "human-thought" | "ai-thought";
  docId: number | null;
  docPath: string | null;
  text: string;
  entryId: number | null;
}

interface CurateViewProps {
  round: RoundDetailOut;
  poolHighlights: PoolItem[];
  poolNotes: PoolItem[];
  poolAiThoughts: PoolItem[];
  refreshKey: number;
  onDumpStateChange: (dump: DumpOut | null) => void;
  onGenerate: () => void;
  onRoundChanged: () => void;
}

const kindLabel: Record<DumpEntryKind, string> = {
  snippet: "snippet",
  highlight: "highlight",
  "human-thought": "human thought",
  "ai-thought": "AI thought",
};

const kindBadge: Record<DumpEntryKind, "outline" | "secondary" | "default"> = {
  snippet: "outline",
  highlight: "secondary",
  "human-thought": "secondary",
  "ai-thought": "default",
};

export default function CurateView({
  round,
  poolHighlights,
  poolNotes,
  poolAiThoughts,
  refreshKey,
  onDumpStateChange,
  onGenerate,
  onRoundChanged,
}: CurateViewProps) {
  const [saved, setSaved] = useState<DumpOut | null>(null);
  const [draft, setDraft] = useState<DumpEntryOut[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [freeKind, setFreeKind] = useState<DumpEntryKind>("human-thought");
  const [freeDocId, setFreeDocId] = useState<number | null>(null);
  const [freeText, setFreeText] = useState("");
  const [freeError, setFreeError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const dump = await api.getDump(round.id);
      setSaved(dump);
      setDraft([...dump.entries]);
      onDumpStateChange(dump);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.detail : (err as Error).message);
      setSaved(null);
      setDraft([]);
    }
  }, [round.id, onDumpStateChange]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const dirty = useMemo(() => {
    if (saved === null) return false;
    if (saved.entries.length !== draft.length) return true;
    for (let i = 0; i < draft.length; i += 1) {
      const a = saved.entries[i];
      const b = draft[i];
      if (a === undefined || b === undefined) return true;
      if (a.id !== b.id || a.kind !== b.kind || a.content !== b.content) return true;
    }
    return false;
  }, [saved, draft]);

  const draftIds = useMemo(() => new Set(draft.map((e) => e.id)), [draft]);
  const highlightPool = poolHighlights.filter((item) => item.entryId === null || !draftIds.has(item.entryId));
  const notePool = poolNotes.filter((item) => item.entryId === null || !draftIds.has(item.entryId));
  const aiPool = poolAiThoughts.filter((item) => item.entryId === null || !draftIds.has(item.entryId));

  const poolAdd = (item: PoolItem): void => {
    const entry: DumpEntryOut = {
      id: item.entryId ?? 0,
      round_id: round.id,
      dump_id: null,
      kind: item.kind,
      content: item.text,
      doc_id: item.docId,
      doc_path: item.docPath,
      expert_note_id: null,
      position: null,
      created_at: "",
    };
    setDraft((prev) => (item.entryId !== null && prev.some((e) => e.id === item.entryId) ? prev : [...prev, entry]));
  };

  const addFreeEntry = (): void => {
    setFreeError(null);
    const content = freeText.trim();
    if (content.length === 0) {
      setFreeError("entry text is required");
      return;
    }
    if ((freeKind === "snippet" || freeKind === "highlight") && freeDocId === null) {
      setFreeError("a source doc is required for snippet and highlight entries");
      return;
    }
    const docId = freeDocId;
    const docPath = docId !== null ? round.docs.find((d) => d.id === docId)?.path ?? null : null;
    const entry: DumpEntryOut = {
      id: 0,
      round_id: round.id,
      dump_id: null,
      kind: freeKind,
      content,
      doc_id: docId,
      doc_path: docPath,
      expert_note_id: null,
      position: null,
      created_at: "",
    };
    setDraft((prev) => [...prev, entry]);
    setFreeText("");
  };

  const move = (index: number, delta: -1 | 1): void => {
    setDraft((prev) => {
      const next = [...prev];
      const target = index + delta;
      const item = next[index];
      if (item === undefined || target < 0 || target >= next.length) return prev;
      const other = next[target]!;
      next[index] = other;
      next[target] = item;
      return next;
    });
  };

  const removeAt = (index: number): void => {
    setDraft((prev) => prev.filter((_e, i) => i !== index));
  };

  const save = async (): Promise<void> => {
    setSaveError(null);
    setSaving(true);
    try {
      const payload: DumpEntryIn[] = draft.map((entry) => ({
        id: entry.id === 0 ? null : entry.id,
        kind: entry.kind,
        content: entry.content,
        doc_id: entry.doc_id,
      }));
      const result = await api.saveDump(round.id, payload);
      setSaved(result);
      setDraft([...result.entries]);
      onDumpStateChange(result);
      onRoundChanged();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const generate = async (): Promise<void> => {
    setGenerateError(null);
    setGenerating(true);
    try {
      await onGenerate();
    } catch (err) {
      setGenerateError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  const canGenerate = !generating && !dirty && saved !== null && saved.entries.length > 0;

  const docOptions = round.docs;

  return (
    <div className="mx-auto flex h-full w-full max-w-5xl flex-col gap-4 p-5">
      <div>
        <h2 className="text-lg font-semibold">Curate the notes dump · {round.name}</h2>
        <p className="text-sm text-muted-foreground">
          Compose the ordered dump this round&apos;s report will be generated from. Entries may come from the
          pools below or be typed freely. Kind, order and content are saved together.
        </p>
      </div>

      {loadError !== null && <InlineError message={loadError} />}
      {saveError !== null && <InlineError message={saveError} />}
      {generateError !== null && <InlineError message={generateError} />}

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-x-hidden overflow-y-auto lg:grid-cols-[1fr_320px] lg:overflow-hidden">
        <div className="flex min-h-0 flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Dump entries ({draft.length})</h3>
            <div className="flex items-center gap-2">
              {dirty && <span className="text-xs text-muted-foreground">unsaved changes</span>}
              {!dirty && saved !== null && <span className="text-xs text-muted-foreground">saved</span>}
              <Button size="sm" disabled={!dirty || saving} onClick={() => void save()}>
                {saving ? "Saving…" : "Save dump"}
              </Button>
            </div>
          </div>
          {draft.length === 0 ? (
            <EmptyHint>
              No entries yet. Add items from the pools on the right, or type a free-thought entry below, then
              reorder to taste and save.
            </EmptyHint>
          ) : (
            <ol className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
              {draft.map((entry, index) => (
                <li
                  key={entry.id === 0 ? `new-${index}` : entry.id}
                  data-testid="dump-entry"
                  className="flex items-start gap-2 rounded-md border bg-card p-2"
                >
                  <div className="flex flex-col gap-0.5 pt-0.5">
                    <button
                      type="button"
                      aria-label="Move up"
                      disabled={index === 0}
                      className="text-muted-foreground disabled:opacity-30"
                      onClick={() => move(index, -1)}
                    >
                      <ArrowUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      aria-label="Move down"
                      disabled={index === draft.length - 1}
                      className="text-muted-foreground disabled:opacity-30"
                      onClick={() => move(index, 1)}
                    >
                      <ArrowDown className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={kindBadge[entry.kind]}>{kindLabel[entry.kind]}</Badge>
                      {entry.doc_path !== null && (
                        <span className="truncate text-xs text-muted-foreground">{entry.doc_path}</span>
                      )}
                    </div>
                    <p className="mt-1 whitespace-pre-wrap text-sm">{entry.content}</p>
                  </div>
                  <button
                    type="button"
                    aria-label="Remove entry"
                    className="text-muted-foreground hover:text-destructive"
                    onClick={() => removeAt(index)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ol>
          )}
        </div>

        <div className="min-h-0 overflow-y-auto space-y-4 border-l pl-4">
          <section>
            <h3 className="flex items-center gap-1.5 text-sm font-semibold">
              <FileText className="h-4 w-4 text-muted-foreground" />
              Pools
            </h3>
            {highlightPool.length === 0 && notePool.length === 0 && aiPool.length === 0 && (
              <p className="mt-2 text-sm text-muted-foreground">
                Nothing to add yet — highlights and notes you make on this round&apos;s docs and AI thoughts
                merged from expert notes appear here.
              </p>
            )}
            {highlightPool.length > 0 && (
              <PoolList title="Highlights" items={highlightPool} onAdd={poolAdd} />
            )}
            {notePool.length > 0 && <PoolList title="Your notes" items={notePool} onAdd={poolAdd} />}
            {aiPool.length > 0 && (
              <PoolList title="AI thoughts" items={aiPool} onAdd={poolAdd} />
            )}
          </section>

          <section className="space-y-2">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold">
              <ListPlus className="h-4 w-4 text-muted-foreground" />
              Type an entry
            </h3>
            {freeError !== null && <InlineError message={freeError} />}
            <select
              aria-label="Entry kind"
              className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm"
              value={freeKind}
              onChange={(e) => setFreeKind(e.target.value as DumpEntryKind)}
            >
              <option value="human-thought">human thought</option>
              <option value="ai-thought">AI thought</option>
              <option value="snippet">snippet</option>
              <option value="highlight">highlight</option>
            </select>
            <select
              aria-label="Source doc"
              className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm"
              value={freeDocId ?? ""}
              onChange={(e) => setFreeDocId(e.target.value === "" ? null : Number(e.target.value))}
            >
              <option value="">{freeKind === "snippet" || freeKind === "highlight" ? "choose a source doc…" : "no doc (optional)"}</option>
              {docOptions.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.path}
                </option>
              ))}
            </select>
            <Textarea
              placeholder="Entry text…"
              aria-label="Free entry text"
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
            />
            <Button
              size="sm"
              variant="secondary"
              disabled={freeText.trim().length === 0}
              onClick={addFreeEntry}
            >
              Append to dump
            </Button>
          </section>
        </div>
      </div>

      <div className="flex items-center justify-between border-t pt-3">
        <div className="text-xs text-muted-foreground">
          {dirty
            ? "Save the dump before generating — generation uses the saved dump."
            : "The report is generated from the saved dump in one call."}
        </div>
        <Button size="lg" disabled={!canGenerate} onClick={() => void generate()}>
          {generating ? "Generating report…" : "Generate report"}
        </Button>
      </div>
    </div>
  );
}

function PoolList({
  title,
  items,
  onAdd,
}: {
  title: string;
  items: PoolItem[];
  onAdd: (item: PoolItem) => void;
}) {
  return (
    <div className="mt-2">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h4>
      <ul className="mt-1 space-y-1">
        {items.map((item) => (
          <li key={item.key} className="group flex items-start justify-between gap-2 rounded border px-2 py-1">
            <div className="min-w-0">
              <p className="line-clamp-3 whitespace-pre-wrap text-xs">{item.text}</p>
              {item.docPath !== null && (
                <p className="mt-0.5 truncate text-[10px] text-muted-foreground">{item.docPath}</p>
              )}
            </div>
            <button
              type="button"
              aria-label={`Add ${title} to dump`}
              className="shrink-0 text-muted-foreground hover:text-foreground"
              onClick={() => onAdd(item)}
            >
              <ListPlus className="h-3.5 w-3.5" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
