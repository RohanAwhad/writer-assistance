import { ChevronDown, ChevronRight, FileText, Folder, FolderOpen, Plus } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { api, ApiError } from "../../api/client";
import type { RoundSummary, TreeNodeOut, TreeOut } from "../../api/types";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Checkbox, Separator } from "../../components/ui/misc";
import { Input, Label } from "../../components/ui/fields";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { EmptyHint, InlineError } from "../../components/ui/feedback";
import { cn } from "../../lib/utils";

interface LeftSidebarProps {
  projectId: number;
  tree: TreeOut | null;
  treeError: string | null;
  activeDocId: number | null;
  onOpenDoc: (docId: number) => void;
  onTreeChanged: () => void;
  rounds: RoundSummary[] | null;
  roundsError: string | null;
  activeRoundId: number | null;
  onSelectRound: (roundId: number | null) => void;
  onRoundsChanged: () => void;
  className?: string;
}

interface FileNode {
  node: TreeNodeOut;
  depth: number;
}

function buildFileRows(tree: TreeOut): FileNode[] {
  const childrenOf = new Map<number | null, TreeNodeOut[]>();
  for (const n of tree.nodes) {
    const list = childrenOf.get(n.parent_id) ?? [];
    list.push(n);
    childrenOf.set(n.parent_id, list);
  }
  const rows: FileNode[] = [];
  const walk = (parent: number | null, depth: number): void => {
    for (const n of childrenOf.get(parent) ?? []) {
      rows.push({ node: n, depth });
      if (n.kind === "dir") walk(n.id, depth + 1);
    }
  };
  walk(null, 0);
  return rows;
}

function visibleRows(files: FileNode[], collapsed: Set<number>): FileNode[] {
  const parentOf = new Map<number, number | null>();
  for (const f of files) parentOf.set(f.node.id, f.node.parent_id);
  const hidden = (nodeId: number): boolean => {
    let parent = parentOf.get(nodeId);
    while (parent !== null && parent !== undefined) {
      if (collapsed.has(parent)) return true;
      parent = parentOf.get(parent);
    }
    return false;
  };
  return files.filter((f) => !hidden(f.node.id));
}

export default function LeftSidebar({
  projectId,
  tree,
  treeError,
  activeDocId,
  onOpenDoc,
  onTreeChanged,
  rounds,
  roundsError,
  activeRoundId,
  onSelectRound,
  onRoundsChanged,
  className,
}: LeftSidebarProps) {
  const files = tree !== null ? buildFileRows(tree) : [];
  const hasDocs = files.some((f) => f.node.kind === "file");
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const [importOpen, setImportOpen] = useState(false);
  const [importFiles, setImportFiles] = useState<File[]>([]);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [roundOpen, setRoundOpen] = useState(false);
  const [roundName, setRoundName] = useState("");
  const [selectedDocs, setSelectedDocs] = useState<Set<number>>(new Set());
  const [creatingRound, setCreatingRound] = useState(false);
  const [roundError, setRoundError] = useState<string | null>(null);

  useEffect(() => {
    if (roundOpen && tree !== null) {
      setSelectedDocs(new Set(tree.nodes.filter((n) => n.kind === "file").map((n) => n.id)));
    }
  }, [roundOpen, tree]);

  const docFiles = useMemo(
    () => (tree !== null ? tree.nodes.filter((n) => n.kind === "file") : []),
    [tree],
  );

  const closeImportDialog = (): void => {
    if (importing) return;
    setImportOpen(false);
    setImportFiles([]);
    setImportError(null);
  };

  const onImportFilesPicked = (event: ChangeEvent<HTMLInputElement>): void => {
    setImportError(null);
    const picked = event.target.files;
    setImportFiles(picked !== null ? Array.from(picked) : []);
    event.target.value = "";
  };

  const handleImport = async (): Promise<void> => {
    if (importFiles.length === 0) return;
    setImportError(null);
    setImporting(true);
    try {
      await api.uploadMarkdown(projectId, importFiles);
      setImportOpen(false);
      setImportFiles([]);
      setImportError(null);
      onTreeChanged();
    } catch (err) {
      setImportError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setImporting(false);
    }
  };

  const toggleDoc = (docId: number, checked: boolean): void => {
    const next = new Set(selectedDocs);
    if (checked) next.add(docId);
    else next.delete(docId);
    setSelectedDocs(next);
  };

  const handleCreateRound = async (): Promise<void> => {
    setRoundError(null);
    setCreatingRound(true);
    try {
      const created = await api.createRound({
        project_id: projectId,
        doc_ids: [...selectedDocs].sort(),
        name: roundName.trim() === "" ? null : roundName.trim(),
      });
      setRoundOpen(false);
      setRoundName("");
      onSelectRound(created.id);
      onRoundsChanged();
    } catch (err) {
      setRoundError(err instanceof ApiError ? err.detail : (err as Error).message);
    } finally {
      setCreatingRound(false);
    }
  };

  const toggleDir = (dirId: number): void => {
    const next = new Set(collapsed);
    if (next.has(dirId)) next.delete(dirId);
    else next.add(dirId);
    setCollapsed(next);
  };

  const fileNodes = tree !== null ? files.filter((f) => f.node.kind === "file") : [];
  const resourceCount = fileNodes.length;

  return (
    <div className={cn("flex h-full w-72 flex-col border-r bg-background", className)}>
      <div className="flex h-12 shrink-0 items-center justify-between border-b px-3">
        <span className="text-sm font-semibold">Resources</span>
        {!hasDocs && (
          <Button size="sm" variant="outline" onClick={() => setImportOpen(true)}>
            <Plus className="mr-1 h-3 w-3" />
            Import
          </Button>
        )}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {treeError !== null && <InlineError message={treeError} />}
        {tree === null && treeError === null && <EmptyHint>Loading resources…</EmptyHint>}
        {tree !== null && resourceCount === 0 && (
          <div className="space-y-3 px-1 py-2">
            <EmptyHint>
              No resources imported yet. This project starts empty — upload Markdown files from your browser to
              begin.
            </EmptyHint>
            <Button size="sm" onClick={() => setImportOpen(true)}>
              Import Markdown files
            </Button>
          </div>
        )}
        {resourceCount > 0 && (
          <ul className="space-y-0.5">
            {visibleRows(files, collapsed).map(({ node, depth }) => {
              if (node.kind === "dir") {
                const isCollapsed = collapsed.has(node.id);
                return (
                  <li key={node.id}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-1 rounded px-2 py-1 text-sm text-muted-foreground hover:bg-muted"
                      style={{ paddingLeft: `${depth * 14 + 8}px` }}
                      onClick={() => toggleDir(node.id)}
                    >
                      {isCollapsed ? (
                        <ChevronRight className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5" />
                      )}
                      {isCollapsed ? (
                        <Folder className="h-3.5 w-3.5" />
                      ) : (
                        <FolderOpen className="h-3.5 w-3.5" />
                      )}
                      <span className="truncate">{node.name}</span>
                    </button>
                  </li>
                );
              }
              const active = node.id === activeDocId;
              return (
                <li key={node.id}>
                  <button
                    type="button"
                    data-testid={`doc-row-${node.name}`}
                    className={`flex w-full items-center gap-1 rounded px-2 py-1 text-sm hover:bg-muted ${
                      active ? "bg-muted font-medium" : ""
                    }`}
                    style={{ paddingLeft: `${depth * 14 + 8}px` }}
                    onClick={() => onOpenDoc(node.id)}
                  >
                    <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{node.name}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <Separator />

      <div className="flex h-10 shrink-0 items-center justify-between px-3">
        <span className="text-sm font-semibold">Rounds</span>
        <Button size="sm" variant="outline" disabled={resourceCount === 0} onClick={() => setRoundOpen(true)}>
          <Plus className="mr-1 h-3 w-3" />
          New round
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {roundsError !== null && <InlineError message={roundsError} />}
        {rounds === null && roundsError === null && <EmptyHint>Loading rounds…</EmptyHint>}
        {rounds !== null && rounds.length === 0 && (
          <EmptyHint>
            {resourceCount === 0
              ? "Import resources before starting a round."
              : "No rounds yet — start a round over a set of docs."}
          </EmptyHint>
        )}
        <ul className="space-y-1">
          {rounds?.map((round) => {
            const active = round.id === activeRoundId;
            return (
              <li key={round.id}>
                <button
                  type="button"
                  data-testid={`round-row-${round.id}`}
                  className={`w-full rounded-md border px-2 py-1.5 text-left hover:bg-muted ${
                    active ? "border-primary/40 bg-muted" : "border-transparent"
                  }`}
                  onClick={() => onSelectRound(round.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium">{round.name}</span>
                    <Badge variant={round.stage === "reading" ? "secondary" : "outline"}>
                      {round.stage}
                    </Badge>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{round.doc_count} doc{round.doc_count === 1 ? "" : "s"}</span>
                    {round.dump_id !== null && <span>· dump</span>}
                    {round.report_id !== null && <span>· report</span>}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <Dialog open={importOpen} onOpenChange={(open) => { if (!open) closeImportDialog(); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import Markdown files</DialogTitle>
            <DialogDescription>
              Upload Markdown files from your browser (.md or .markdown). They are snapshotted into app
              storage once; resources become read-only here.
            </DialogDescription>
          </DialogHeader>
          {importError !== null && <InlineError message={importError} />}
          <div className="space-y-2">
            <input
              ref={fileInputRef}
              data-testid="import-file-input"
              type="file"
              accept=".md,.markdown"
              multiple
              className="hidden"
              onChange={onImportFilesPicked}
            />
            <Button
              variant="outline"
              disabled={importing}
              onClick={() => fileInputRef.current?.click()}
            >
              Choose files…
            </Button>
            {importFiles.length > 0 && (
              <div className="rounded-md border px-3 py-2">
                <p className="text-xs font-medium text-muted-foreground">
                  {importFiles.length} file{importFiles.length === 1 ? "" : "s"} selected
                </p>
                <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                  {importFiles.map((file, index) => (
                    <li key={`${file.name}-${index}`} className="truncate font-mono">
                      {file.name}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" disabled={importing} onClick={closeImportDialog}>
              Cancel
            </Button>
            <Button disabled={importFiles.length === 0 || importing} onClick={() => void handleImport()}>
              {importing ? "Importing…" : "Import"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={roundOpen} onOpenChange={setRoundOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New reading round</DialogTitle>
            <DialogDescription>
              Pick the doc set for this round. The human and the AI read this set together; the round ends in a
              curated dump and one generated report.
            </DialogDescription>
          </DialogHeader>
          {roundError !== null && <InlineError message={roundError} />}
          <div className="space-y-1.5">
            <Label htmlFor="round-name">Round name (optional)</Label>
            <Input
              id="round-name"
              placeholder="e.g. Round on market briefings"
              value={roundName}
              onChange={(e) => setRoundName(e.target.value)}
            />
          </div>
          <Separator />
          <div className="max-h-56 space-y-1 overflow-y-auto pr-1">
            {docFiles.length === 0 && <EmptyHint>No resources to pick — import Markdown files first.</EmptyHint>}
            {docFiles.map((doc) => (
              <label
                key={doc.id}
                className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted"
              >
                <Checkbox
                  checked={selectedDocs.has(doc.id)}
                  onCheckedChange={(checked) => toggleDoc(doc.id, checked === true)}
                />
                <span className="truncate">{doc.path}</span>
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRoundOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={selectedDocs.size === 0 || creatingRound}
              onClick={() => void handleCreateRound()}
            >
              {creatingRound ? "Creating…" : "Create round"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
