import { ArrowLeft, FileText, Folder, MessageSquarePlus } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type {
  AnnotationOut,
  DumpOut,
  ExpertNoteOut,
  ResourceOut,
  RoundDetailOut,
  RoundSummary,
  TreeOut,
} from "../api/types";
import MarkdownView, { type SelectionResult } from "../components/MarkdownView";
import ProviderSelector from "../components/ProviderSelector";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyHint, InlineError } from "../components/ui/feedback";
import { Separator } from "../components/ui/misc";
import { OverlayPanel } from "../components/ui/overlay";
import { useDeviceClass } from "../lib/useViewport";
import AnnotationPanel from "./workspace/AnnotationPanel";
import CurateView, { type PoolItem } from "./workspace/CurateView";
import LeftSidebar from "./workspace/LeftSidebar";
import ReportEditor from "./workspace/ReportEditor";
import RoundReadingPane from "./workspace/RoundReadingPane";
import RoundStageHeader, { type StageMode } from "./workspace/RoundStageHeader";
import type { DocData, ExpertDocState, LensDocState } from "./workspace/state";

interface WorkspaceScreenProps {
  projectId: number;
  projectName: string;
  onBack: () => void;
}

interface RoundDetailState {
  status: "loading" | "ready" | "error";
  detail: RoundDetailOut | null;
  error: string | null;
}

export default function WorkspaceScreen({ projectId, projectName, onBack }: WorkspaceScreenProps) {
  const deviceClass = useDeviceClass();
  // INT-009 (SD-31/32): below 1024 CSS px the side-by-side panes move behind
  // overlay panels opened from controls on the content surface; >= 1024 keeps
  // the three-pane arrangement unchanged. Narrow-mode is derived UI state.
  const narrow = deviceClass !== "desktop";
  const [navOverlayOpen, setNavOverlayOpen] = useState(false);
  const [panesOverlayOpen, setPanesOverlayOpen] = useState(false);

  useEffect(() => {
    if (!narrow) {
      setNavOverlayOpen(false);
      setPanesOverlayOpen(false);
    }
  }, [narrow]);

  const [tree, setTree] = useState<TreeOut | null>(null);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [rounds, setRounds] = useState<RoundSummary[] | null>(null);
  const [roundsError, setRoundsError] = useState<string | null>(null);

  const [docs, setDocs] = useState<Record<number, DocData>>({});
  const [activeDocId, setActiveDocId] = useState<number | null>(null);
  const [docError, setDocError] = useState<string | null>(null);
  const [docLoadingId, setDocLoadingId] = useState<number | null>(null);
  const [selection, setSelection] = useState<SelectionResult | null>(null);

  const [activeRoundId, setActiveRoundId] = useState<number | null>(null);
  const [roundDetailStates, setRoundDetailStates] = useState<Record<number, RoundDetailState>>({});
  const [mode, setMode] = useState<StageMode>("doc");
  const [curateReloadKey, setCurateReloadKey] = useState(0);
  const [lensByDoc, setLensByDoc] = useState<Record<number, LensDocState>>({});
  const [expertsByRoundDoc, setExpertsByRoundDoc] = useState<Record<string, ExpertDocState>>({});
  const [dumpByRound, setDumpByRound] = useState<Record<number, DumpOut | null>>({});

  const loadTree = useCallback(async () => {
    setTreeError(null);
    try {
      setTree(await api.getTree(projectId));
    } catch (err) {
      setTree(null);
      setTreeError(err instanceof ApiError ? err.detail : (err as Error).message);
    }
  }, [projectId]);

  const loadRounds = useCallback(async () => {
    setRoundsError(null);
    try {
      const list = await api.listRounds(projectId);
      setRounds(list);
      if (list.length === 0) setActiveRoundId(null);
    } catch (err) {
      setRounds(null);
      setRoundsError(err instanceof ApiError ? err.detail : (err as Error).message);
    }
  }, [projectId]);

  const refreshRoundDetail = useCallback(async (roundId: number) => {
    setRoundDetailStates((prev) => ({ ...prev, [roundId]: { status: "loading", detail: null, error: null } }));
    try {
      const detail = await api.getRound(roundId);
      setRoundDetailStates((prev) => ({ ...prev, [roundId]: { status: "ready", detail, error: null } }));
    } catch (err) {
      setRoundDetailStates((prev) => ({
        ...prev,
        [roundId]: {
          status: "error",
          detail: null,
          error: err instanceof ApiError ? err.detail : (err as Error).message,
        },
      }));
    }
  }, []);

  useEffect(() => {
    void loadTree();
    void loadRounds();
  }, [loadTree, loadRounds]);

  const docCache = activeDocId !== null ? (docs[activeDocId] ?? null) : null;

  const ensureDoc = useCallback(
    async (docId: number) => {
      setActiveDocId(docId);
      setDocError(null);
      if (docs[docId] !== undefined) {
        if (lensByDoc[docId] === undefined) {
          api
            .listLensProposals(docId)
            .then((proposals) =>
              setLensByDoc((prev) => ({ ...prev, [docId]: { status: "ready", proposals, error: null } })),
            )
            .catch((err) =>
              setLensByDoc((prev) => ({
                ...prev,
                [docId]: {
                  status: "error",
                  proposals: [],
                  error: err instanceof ApiError ? err.detail : (err as Error).message,
                },
              })),
            );
        }
        return;
      }
      setDocLoadingId(docId);
      try {
        const [resource, annotations] = await Promise.all([
          api.getResource(docId),
          api.getResourceAnnotations(docId),
        ]);
        setDocs((prev) => ({ ...prev, [docId]: { resource, annotations } }));
        setLensByDoc((prev) => ({ ...prev, [docId]: { status: "loading", proposals: [], error: null } }));
        const proposals = await api.listLensProposals(docId);
        setLensByDoc((prev) => ({ ...prev, [docId]: { status: "ready", proposals, error: null } }));
      } catch (err) {
        setDocError(err instanceof ApiError ? err.detail : (err as Error).message);
      } finally {
        setDocLoadingId(null);
      }
    },
    [docs, lensByDoc],
  );

  const addAnnotation = (annotation: AnnotationOut): void => {
    const docId = annotation.doc_id;
    setDocs((prev) => {
      const doc = prev[docId];
      if (doc === undefined) return prev;
      return { ...prev, [docId]: { ...doc, annotations: [...doc.annotations, annotation] } };
    });
    setSelection({ status: "empty", text: "", start: null, end: null, message: null });
  };

  const removeAnnotation = (annotationId: number): void => {
    setDocs((prev) => {
      const docId = activeDocId;
      if (docId === null) return prev;
      const doc = prev[docId];
      if (doc === undefined) return prev;
      return {
        ...prev,
        [docId]: { ...doc, annotations: doc.annotations.filter((a) => a.id !== annotationId) },
      };
    });
  };

  const roundDetailState = activeRoundId !== null ? (roundDetailStates[activeRoundId] ?? null) : null;
  const roundDetail = roundDetailState?.detail ?? null;
  const roundSummary = useMemo(
    () => (rounds ?? []).find((r) => r.id === activeRoundId) ?? null,
    [rounds, activeRoundId],
  );

  const selectRound = async (roundId: number | null): Promise<void> => {
    setActiveRoundId(roundId);
    setMode("doc");
    if (roundId !== null && roundDetailStates[roundId] === undefined) {
      await refreshRoundDetail(roundId);
    }
  };

  const refreshActiveRoundDetail = async (): Promise<void> => {
    if (activeRoundId !== null) {
      const detail = await api.getRound(activeRoundId);
      setRoundDetailStates((prev) => ({
        ...prev,
        [activeRoundId]: { status: "ready", detail, error: null },
      }));
    }
  };

  const docInRound = useMemo(() => {
    if (roundDetail === null || activeDocId === null) return false;
    return roundDetail.docs.some((d) => d.id === activeDocId);
  }, [roundDetail, activeDocId]);

  const lensState = activeDocId !== null ? (lensByDoc[activeDocId] ?? null) : null;
  const expertKey = activeRoundId !== null && activeDocId !== null ? `${activeRoundId}:${activeDocId}` : null;
  const expertState: ExpertDocState =
    expertKey !== null ? (expertsByRoundDoc[expertKey] ?? { status: "idle" }) : { status: "idle" };

  useEffect(() => {
    if (activeRoundId === null || activeDocId === null) return;
    const detail = roundDetailStates[activeRoundId]?.detail;
    if (detail === null || detail === undefined || detail.stage !== "reading") return;
    if (!detail.docs.some((d) => d.id === activeDocId)) return;
    const key = `${activeRoundId}:${activeDocId}`;
    const current = expertsByRoundDoc[key];
    if (current !== undefined && current.status !== "idle") return;
    let cancelled = false;
    void (async () => {
      try {
        const result = await api.getRoundExpertRuns(activeRoundId);
        const runs = result.expert_runs.filter((r) => r.doc_id === activeDocId);
        if (cancelled) return;
        setExpertsByRoundDoc((prev) => {
          const prevState = prev[key];
          if (prevState === undefined || prevState.status === "idle") {
            return { ...prev, [key]: { status: "ready", runs } };
          }
          if (prevState.status === "ready") {
            const existingIds = new Set(prevState.runs.map((r) => r.id));
            const fresh = runs.filter((r) => !existingIds.has(r.id));
            return fresh.length === 0
              ? prev
              : { ...prev, [key]: { status: "ready", runs: [...prevState.runs, ...fresh] } };
          }
          return prev;
        });
      } catch (err) {
        if (cancelled) return;
        setExpertsByRoundDoc((prev) => {
          const prevState = prev[key];
          if (prevState === undefined || prevState.status === "idle") {
            return {
              ...prev,
              [key]: {
                status: "error",
                error: err instanceof ApiError ? err.detail : (err as Error).message,
              },
            };
          }
          return prev;
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeRoundId, activeDocId, roundDetailStates, expertsByRoundDoc]);

  const retryExpertLoad = (): void => {
    if (expertKey === null) return;
    setExpertsByRoundDoc((prev) => {
      const current = prev[expertKey];
      if (current === undefined || current.status !== "error") return prev;
      return { ...prev, [expertKey]: { status: "idle" } };
    });
  };

  const proposeLensesForDoc = async (): Promise<void> => {
    const docId = activeDocId;
    if (docId === null) return;
    setLensByDoc((prev) => ({ ...prev, [docId]: { status: "loading", proposals: [], error: null } }));
    try {
      await api.proposeLenses(docId);
      const proposals = await api.listLensProposals(docId);
      setLensByDoc((prev) => ({ ...prev, [docId]: { status: "ready", proposals, error: null } }));
    } catch (err) {
      setLensByDoc((prev) => ({
        ...prev,
        [docId]: {
          status: "error",
          proposals: [],
          error: err instanceof ApiError ? err.detail : (err as Error).message,
        },
      }));
    }
  };

  const setProposalStatus = async (proposalId: number, status: "selected" | "skipped"): Promise<void> => {
    const updated = await api.setLensProposalStatus(proposalId, status);
    setLensByDoc((prev) => {
      const docId = updated.doc_id;
      const current = prev[docId];
      if (current === undefined) return prev;
      return {
        ...prev,
        [docId]: {
          ...current,
          proposals: current.proposals.map((p) => (p.id === proposalId ? updated : p)),
        },
      };
    });
  };

  const patchExpertNote = (key: string, updated: ExpertNoteOut): void => {
    setExpertsByRoundDoc((prev) => {
      const current = prev[key];
      if (current === undefined || current.status !== "ready") return prev;
      const runs = current.runs.map((run) => {
        if (!run.notes.some((n) => n.id === updated.id)) return run;
        return { ...run, notes: run.notes.map((n) => (n.id === updated.id ? updated : n)) };
      });
      return { ...prev, [key]: { status: "ready", runs } };
    });
  };

  const keepNote = async (note: ExpertNoteOut): Promise<void> => {
    const updated = await api.updateExpertNote(note.id, "accepted");
    if (expertKey !== null) patchExpertNote(expertKey, updated);
  };

  const discardNote = async (note: ExpertNoteOut): Promise<void> => {
    const updated = await api.updateExpertNote(note.id, "discarded");
    if (expertKey !== null) patchExpertNote(expertKey, updated);
  };

  const mergeNote = async (note: ExpertNoteOut, content: string | null): Promise<void> => {
    await api.mergeExpertNote(note.id, content ?? undefined);
    if (expertKey !== null) {
      patchExpertNote(expertKey, {
        ...note,
        review_state: "merged-with-edits",
        edited_content: content ?? note.content,
      });
    }
    setCurateReloadKey((prev) => prev + 1);
    await loadRounds();
    await refreshActiveRoundDetail();
  };

  const runSelectedExperts = async (): Promise<void> => {
    const docId = activeDocId;
    if (docId === null || activeRoundId === null) return;
    const selectedIds = (lensByDoc[docId]?.proposals ?? [])
      .filter((p) => p.status === "selected" && p.doc_id === docId)
      .map((p) => p.id);
    if (selectedIds.length === 0) return;
    const key = `${activeRoundId}:${docId}`;
    setExpertsByRoundDoc((prev) => ({ ...prev, [key]: { status: "loading" } }));
    try {
      const result = await api.runExperts(activeRoundId, selectedIds);
      setExpertsByRoundDoc((prev) => {
        const current = prev[key];
        const existing = current?.status === "ready" ? current.runs : [];
        return {
          ...prev,
          [key]: { status: "ready", runs: [...existing, ...result.expert_runs] },
        };
      });
    } catch (err) {
      setExpertsByRoundDoc((prev) => ({
        ...prev,
        [key]: { status: "error", error: err instanceof ApiError ? err.detail : (err as Error).message },
      }));
    }
  };

  const refreshRoundsAndRound = async (): Promise<void> => {
    await loadRounds();
    if (activeRoundId !== null) await refreshActiveRoundDetail();
  };

  const handleGenerate = async (): Promise<void> => {
    if (activeRoundId === null) {
      throw new ApiError(400, "no active round");
    }
    await api.generateReport(activeRoundId);
    setDumpByRound((prev) => ({ ...prev, [activeRoundId]: null }));
    await refreshRoundsAndRound();
    setMode("report");
  };

  const handleReportDeleted = async (): Promise<void> => {
    await refreshRoundsAndRound();
    setMode("doc");
  };

  const handleDumpStateChange = (dump: DumpOut | null): void => {
    if (activeRoundId !== null) {
      setDumpByRound((prev) => ({ ...prev, [activeRoundId]: dump }));
    }
  };

  const roundForHeader = roundDetail ?? roundSummary;

  const modeAllowed: Record<StageMode, boolean> = {
    doc: true,
    curate: roundSummary !== null && roundSummary.stage === "reading",
    report: roundForHeader !== null && roundForHeader.report_id !== null,
  };

  useEffect(() => {
    if (mode === "curate" && !modeAllowed.curate) setMode("doc");
    if (mode === "report" && !modeAllowed.report) setMode("doc");
  }, [mode, modeAllowed.curate, modeAllowed.report]);

  const curatePrefetching = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (mode !== "curate") return;
    const detail = roundDetailStates[activeRoundId ?? -1]?.detail;
    if (detail === null || detail === undefined || detail.stage !== "reading") return;
    const missing = detail.docs.filter(
      (d) => docs[d.id] === undefined && d.id !== docLoadingId && !curatePrefetching.current.has(d.id),
    );
    if (missing.length === 0) return;
    for (const d of missing) curatePrefetching.current.add(d.id);
    let cancelled = false;
    void (async () => {
      await Promise.all(
        missing.map(async (d) => {
          try {
            const [resource, annotations] = await Promise.all([
              api.getResource(d.id),
              api.getResourceAnnotations(d.id),
            ]);
            if (cancelled) return;
            setDocs((prev) =>
              prev[d.id] !== undefined ? prev : { ...prev, [d.id]: { resource, annotations } },
            );
          } catch {
            curatePrefetching.current.delete(d.id);
          }
        }),
      );
    })();
    return () => {
      cancelled = true;
    };
  }, [mode, activeRoundId, roundDetailStates, docLoadingId, docs]);

  const poolAnnotations = useMemo(() => {
    const highlights: PoolItem[] = [];
    const notes: PoolItem[] = [];
    if (roundDetail === null) return { highlights, notes };
    const docsInRound = new Set(roundDetail.docs.map((d) => d.id));
    for (const [docIdStr, doc] of Object.entries(docs)) {
      const docId = Number(docIdStr);
      if (!docsInRound.has(docId)) continue;
      const path = roundDetail.docs.find((d) => d.id === docId)?.path ?? null;
      for (const annotation of doc.annotations) {
        const text =
          annotation.content ??
          (annotation.start_offset !== null && annotation.end_offset !== null
            ? doc.resource.content.slice(annotation.start_offset, annotation.end_offset)
            : "");
        if (text.length === 0) continue;
        const item: PoolItem = {
          key: `annotation-${annotation.id}`,
          kind: annotation.kind === "highlight" ? "highlight" : "human-thought",
          docId,
          docPath: path,
          text,
          entryId: null,
        };
        if (annotation.kind === "highlight") highlights.push(item);
        else notes.push(item);
      }
    }
    return { highlights, notes };
  }, [roundDetail, docs]);

  const poolAiThoughts = useMemo(() => {
    const items: PoolItem[] = [];
    const dump = activeRoundId !== null ? (dumpByRound[activeRoundId] ?? null) : null;
    if (dump !== null) {
      for (const entry of dump.entries) {
        if (entry.kind === "ai-thought") {
          items.push({
            key: `ai-${entry.id}`,
            kind: "ai-thought",
            docId: entry.doc_id,
            docPath: entry.doc_path,
            text: entry.content,
            entryId: entry.id,
          });
        }
      }
    }
    return items;
  }, [dumpByRound, activeRoundId]);

  const activeDoc = docCache;
  const docResource: ResourceOut | null = activeDoc?.resource ?? null;

  const markRanges = useMemo(() => {
    if (activeDoc === null) return [];
    return activeDoc.annotations.flatMap((a) =>
      a.kind === "highlight" && a.start_offset !== null && a.end_offset !== null
        ? [{ start: a.start_offset, end: a.end_offset }]
        : [],
    );
  }, [activeDoc]);

  const openDocFromNav = (docId: number): void => {
    setNavOverlayOpen(false);
    void ensureDoc(docId);
  };

  const selectRoundFromNav = (roundId: number | null): void => {
    setNavOverlayOpen(false);
    void selectRound(roundId);
  };

  const panesArea =
    docResource === null ? (
      <EmptyHint>Open a resource to annotate it and to run the round flow on its docs.</EmptyHint>
    ) : (
      <div className="space-y-4">
        <AnnotationPanel
          docId={docResource.id}
          docContent={docResource.content}
          docPath={docResource.path}
          annotations={activeDoc?.annotations ?? []}
          selection={selection}
          onAddAnnotation={addAnnotation}
          onDeleteAnnotation={removeAnnotation}
        />
        <Separator />
        <RoundReadingPane
          round={roundDetailState?.detail ?? null}
          roundLoading={roundDetailState?.status === "loading" && activeRoundId !== null}
          roundError={roundDetailState?.error ?? null}
          docId={docResource.id}
          docInRound={docInRound}
          lens={lensState}
          experts={expertState}
          onRetryExperts={retryExpertLoad}
          onProposeLenses={() => void proposeLensesForDoc()}
          onSetProposalStatus={(proposalId, status) => void setProposalStatus(proposalId, status)}
          onRunSelected={() => void runSelectedExperts()}
          onKeepNote={keepNote}
          onDiscardNote={discardNote}
          onMergeNote={(note, content) => mergeNote(note, content)}
        />
      </div>
    );

  return (
    <div className="flex h-viewport overflow-hidden bg-background">
      {!narrow && (
        <LeftSidebar
          projectId={projectId}
          tree={tree}
          treeError={treeError}
          activeDocId={activeDocId}
          onOpenDoc={(docId) => void ensureDoc(docId)}
          onTreeChanged={() => void loadTree()}
          rounds={rounds}
          roundsError={roundsError}
          activeRoundId={activeRoundId}
          onSelectRound={(roundId) => void selectRound(roundId)}
          onRoundsChanged={() => void loadRounds()}
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-11 shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-1.5 border-b px-4 py-1.5">
          <div className="flex min-w-0 items-center gap-2">
            <Button variant="ghost" size="sm" onClick={onBack}>
              <ArrowLeft className="mr-1 h-3 w-3" />
              Projects
            </Button>
            <span className="truncate text-sm font-semibold">{projectName}</span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {tree !== null && (
              <span>
                {tree.nodes.filter((n) => n.kind === "file").length} resources
              </span>
            )}
            <Badge variant="outline">local · single-user</Badge>
            <ProviderSelector projectId={projectId} />
          </div>
        </header>
        {narrow && (
          <div
            data-testid="narrow-surface-controls"
            className="flex shrink-0 flex-wrap items-center gap-2 border-b px-4 py-1.5"
          >
            <Button
              size="sm"
              variant="outline"
              onClick={() => setNavOverlayOpen(true)}
              data-testid="open-nav-overlay"
            >
              <Folder className="mr-1 h-3 w-3" />
              Resources & rounds
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setPanesOverlayOpen(true)}
              data-testid="open-panes-overlay"
            >
              <MessageSquarePlus className="mr-1 h-3 w-3" />
              Annotate & round
            </Button>
          </div>
        )}
        {roundForHeader !== null && (
          <RoundStageHeader
            round={roundForHeader}
            mode={mode}
            curateAllowed={modeAllowed.curate}
            reportAllowed={modeAllowed.report}
            onMode={(m) => setMode(m)}
          />
        )}
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 overflow-hidden bg-background">
            {mode === "curate" && roundDetail !== null && roundDetail.stage === "reading" && (
              <CurateView
                round={roundDetail}
                poolHighlights={poolAnnotations.highlights}
                poolNotes={poolAnnotations.notes}
                poolAiThoughts={poolAiThoughts}
                refreshKey={curateReloadKey}
                onDumpStateChange={handleDumpStateChange}
                onGenerate={() => handleGenerate()}
                onRoundChanged={() => void refreshRoundsAndRound()}
              />
            )}
            {mode === "report" && roundForHeader !== null && roundForHeader.report_id !== null && (
              <ReportEditor
                reportId={roundForHeader.report_id}
                roundName={roundForHeader.name}
                onReportDeleted={() => void handleReportDeleted()}
              />
            )}
            {mode === "doc" && (
              <div className="h-full overflow-y-auto">
                {docLoadingId !== null && <div className="p-5"><EmptyHint>Loading document…</EmptyHint></div>}
                {docError !== null && <div className="p-5"><InlineError message={docError} /></div>}
                {docResource === null && docLoadingId === null && docError === null && (
                  <div className="p-5">
                    <EmptyHint>
                      {tree !== null && tree.nodes.length === 0
                        ? "This project has no resources. Use Import to upload Markdown files from your browser."
                        : "Select a resource from the tree to read it. Resources are read-only — annotate instead of editing."}
                    </EmptyHint>
                  </div>
                )}
                {docResource !== null && (
                  <div className="mx-auto max-w-3xl px-8 py-6">
                    <div className="mb-3 flex items-center justify-between gap-3 border-b pb-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="truncate font-mono text-xs text-muted-foreground">
                          {docResource.path}
                        </span>
                      </div>
                      <Badge variant="outline">read-only</Badge>
                    </div>
                    <MarkdownView
                      docText={docResource.content}
                      markRanges={markRanges}
                      onSelection={setSelection}
                    />
                  </div>
                )}
              </div>
            )}
          </main>
          {!narrow && <aside className="w-[360px] shrink-0 overflow-y-auto border-l p-4">{panesArea}</aside>}
        </div>
      </div>
      {narrow && navOverlayOpen && (
        <OverlayPanel side="left" title="Resources & rounds" onClose={() => setNavOverlayOpen(false)}>
          <LeftSidebar
            projectId={projectId}
            tree={tree}
            treeError={treeError}
            activeDocId={activeDocId}
            onOpenDoc={openDocFromNav}
            onTreeChanged={() => void loadTree()}
            rounds={rounds}
            roundsError={roundsError}
            activeRoundId={activeRoundId}
            onSelectRound={selectRoundFromNav}
            onRoundsChanged={() => void loadRounds()}
            className="w-full border-r-0"
          />
        </OverlayPanel>
      )}
      {narrow && panesOverlayOpen && (
        <OverlayPanel side="right" title="Annotate & round" onClose={() => setPanesOverlayOpen(false)}>
          <div className="p-4">{panesArea}</div>
        </OverlayPanel>
      )}
    </div>
  );
}
