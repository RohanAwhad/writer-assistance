import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  Upload,
  Trash2,
  Sparkles,
  Plus,
  FileText,
  BookOpen,
  Check,
  X,
  Loader2,
} from "lucide-react";
import * as api from "@/lib/api";
import type { Resource, Lens, Note, ReportSummary } from "@/lib/api";
import SelectionPopup from "@/components/SelectionPopup";

export default function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const markdownRef = useRef<HTMLDivElement>(null);

  const [resources, setResources] = useState<Resource[]>([]);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(
    null
  );
  const [lenses, setLenses] = useState<Lens[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [generatingLenses, setGeneratingLenses] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [noteDialogOpen, setNoteDialogOpen] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState("");
  const [newNoteHighlight, setNewNoteHighlight] = useState("");
  const [loadingResources, setLoadingResources] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [reports, setReports] = useState<ReportSummary[]>([]);

  const pid = Number(projectId);

  const loadResources = useCallback(async () => {
    setLoadingResources(true);
    const data = await api.listResources(pid);
    setResources(data);
    setLoadingResources(false);
  }, [pid]);

  const loadNotes = useCallback(async () => {
    const data = await api.listNotes(pid);
    setNotes(data);
  }, [pid]);

  const loadReports = useCallback(async () => {
    const data = await api.listReports(pid);
    setReports(data);
  }, [pid]);

  useEffect(() => {
    loadResources();
    loadNotes();
    loadReports();
  }, [loadResources, loadNotes, loadReports]);

  const handleUpload = async (files: FileList | File[]) => {
    const arr = Array.from(files).filter((f) => f.name.endsWith(".md"));
    if (arr.length === 0) return;
    await api.uploadResources(pid, arr);
    loadResources();
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) handleUpload(e.target.files);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files) handleUpload(e.dataTransfer.files);
  };

  const handleDeleteResource = async (id: number) => {
    await api.deleteResource(id);
    if (selectedResource?.id === id) {
      setSelectedResource(null);
      setLenses([]);
    }
    loadResources();
  };

  const handleSelectResource = async (r: Resource) => {
    const full = await api.getResource(r.id);
    setSelectedResource(full);
    setLenses([]);
    loadLenses(r.id);
  };

  const handleGenerateLenses = async () => {
    if (!selectedResource) return;
    setGeneratingLenses(true);
    const generated = await api.generateLenses(selectedResource.id);
    setLenses(generated);
    setGeneratingLenses(false);
  };

  const loadLenses = useCallback(async (resourceId: number) => {
    const existing = await api.listLenses(resourceId);
    setLenses(existing);
  }, []);

  const handleAcceptLensNote = async (lens: Lens, noteIndex: number) => {
    await api.acceptLensNotes(pid, lens.id, [noteIndex]);
    loadNotes();
    if (selectedResource) loadLenses(selectedResource.id);
  };

  const handleDiscardLensNote = async (lens: Lens, noteIndex: number) => {
    await api.discardLensNotes(pid, lens.id, [noteIndex]);
    if (selectedResource) loadLenses(selectedResource.id);
  };

  const handleAddNote = async () => {
    if (!newNoteContent.trim()) return;
    await api.createNote(pid, {
      content: newNoteContent.trim(),
      note_type: "user",
      ...(newNoteHighlight && { highlight: newNoteHighlight }),
    });
    setNewNoteContent("");
    setNewNoteHighlight("");
    setNoteDialogOpen(false);
    loadNotes();
  };

  const handleSelectionNote = (text: string) => {
    setNewNoteHighlight(text);
    setNewNoteContent("");
    setNoteDialogOpen(true);
  };

  const handleDeleteNote = async (id: number) => {
    await api.deleteNote(id);
    loadNotes();
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    const report = await api.generateReport(pid);
    setGeneratingReport(false);
    navigate(`/projects/${pid}/report/${report.id}`);
  };

  return (
    <div className="flex h-full">
      {/* Left panel: Resources */}
      <div
        className="flex w-64 shrink-0 flex-col border-r"
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <div className="flex items-center justify-between border-b px-3 py-2">
          <h2 className="text-sm font-medium">Resources</h2>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="size-3.5" />
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".md"
            multiple
            className="hidden"
            onChange={handleFileInput}
          />
        </div>

        {dragging && (
          <div className="m-2 flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-primary/50 bg-primary/5 p-6 text-center">
            <Upload className="mb-2 size-5 text-primary/60" />
            <p className="text-xs text-muted-foreground">Drop .md files here</p>
          </div>
        )}

        <ScrollArea className="flex-1">
          <div className="flex flex-col gap-px p-1">
            {loadingResources ? (
              <p className="px-2 py-4 text-xs text-muted-foreground">
                Loading...
              </p>
            ) : resources.length === 0 ? (
              <div
                className="mx-1 mt-2 flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed border-muted-foreground/20 p-6 text-center transition-colors hover:border-muted-foreground/40"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="mb-2 size-5 opacity-40" />
                <p className="text-xs text-muted-foreground">
                  Click or drag .md files here
                </p>
              </div>
            ) : (
              resources.map((r) => (
                <div
                  key={r.id}
                  className={`group flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                    selectedResource?.id === r.id
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  }`}
                  onClick={() => handleSelectResource(r)}
                >
                  <FileText className="size-3.5 shrink-0" />
                  <span className="flex-1 truncate">{r.filename}</span>
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    className="opacity-0 group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteResource(r.id);
                    }}
                  >
                    <Trash2 className="size-3" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Center panel: Resource viewer + Lenses */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {selectedResource ? (
          <>
            <div className="flex shrink-0 items-center justify-between border-b px-4 py-2">
              <h2 className="text-sm font-medium">
                {selectedResource.filename}
              </h2>
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateLenses}
                disabled={generatingLenses}
              >
                {generatingLenses ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Sparkles className="size-3.5" />
                )}
                {generatingLenses
                  ? "Generating..."
                  : "Generate AI Perspectives"}
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <div className="relative max-w-3xl p-6" ref={markdownRef}>
                <SelectionPopup
                  containerRef={markdownRef}
                  onAddNote={handleSelectionNote}
                />
                <article className="markdown-body">
                  <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                    {selectedResource.content ?? ""}
                  </Markdown>
                </article>
              </div>

              {lenses.length > 0 && (
                <>
                  <Separator />
                  <div className="max-w-3xl p-6">
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
                      <Sparkles className="size-4" />
                      AI Expert Perspectives
                    </h3>
                    <Tabs defaultValue={String(lenses[0]?.id)}>
                      <TabsList>
                        {lenses.map((lens) => (
                          <TabsTrigger
                            key={lens.id}
                            value={String(lens.id)}
                          >
                            {lens.name}
                          </TabsTrigger>
                        ))}
                      </TabsList>
                      {lenses.map((lens) => (
                        <TabsContent key={lens.id} value={String(lens.id)}>
                          <div className="mt-3 space-y-1">
                            <p className="text-xs text-muted-foreground italic">
                              {lens.perspective}
                            </p>
                            <div className="mt-3 space-y-2">
                              {lens.notes.map((n, i) => (
                                <LensNoteCard
                                  key={i}
                                  note={n}
                                  onAdd={() =>
                                    handleAcceptLensNote(lens, i)
                                  }
                                  onDiscard={() =>
                                    handleDiscardLensNote(lens, i)
                                  }
                                />
                              ))}
                            </div>
                          </div>
                        </TabsContent>
                      ))}
                    </Tabs>
                  </div>
                </>
              )}

              {generatingLenses && (
                <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" />
                  Generating perspectives... (this may take a minute)
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
            <div className="text-center">
              <BookOpen className="mx-auto mb-2 size-8 opacity-30" />
              <p>Select a resource to view</p>
            </div>
          </div>
        )}
      </div>

      {/* Right panel: Notes */}
      <div className="flex w-72 shrink-0 flex-col border-l">
        <div className="flex items-center justify-between border-b px-3 py-2">
          <h2 className="text-sm font-medium">
            Notes{" "}
            <span className="text-muted-foreground">({notes.length})</span>
          </h2>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => {
              setNewNoteHighlight("");
              setNewNoteContent("");
              setNoteDialogOpen(true);
            }}
          >
            <Plus className="size-3.5" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col gap-2 p-2">
            {notes.length === 0 ? (
              <p className="px-1 py-4 text-xs text-muted-foreground">
                No notes yet. Highlight text in a document, add from AI lenses,
                or click + to add manually.
              </p>
            ) : (
              notes.map((note) => (
                <div
                  key={note.id}
                  className="group rounded-lg border p-2.5 text-xs"
                >
                  <div className="mb-1.5 flex items-start justify-between gap-1">
                    <Badge
                      variant={
                        note.note_type === "lens" ? "secondary" : "outline"
                      }
                    >
                      {note.note_type === "lens" ? "AI" : "You"}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      className="opacity-0 group-hover:opacity-100"
                      onClick={() => handleDeleteNote(note.id)}
                    >
                      <Trash2 className="size-3" />
                    </Button>
                  </div>
                  <p className="leading-relaxed">{note.content}</p>
                  {note.highlight && (
                    <p className="mt-1.5 border-l-2 border-primary/30 pl-2 text-muted-foreground italic">
                      "{note.highlight}"
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
        <div className="border-t p-2 space-y-2">
          {reports.length > 0 && (
            <div className="space-y-1">
              <p className="px-1 text-xs font-medium text-muted-foreground">Reports</p>
              {reports.map((r) => (
                <div
                  key={r.id}
                  className="group flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  onClick={() => navigate(`/projects/${pid}/report/${r.id}`)}
                >
                  <FileText className="size-3.5 shrink-0" />
                  <span className="flex-1 truncate">{r.title}</span>
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    className="opacity-0 group-hover:opacity-100"
                    onClick={async (e) => {
                      e.stopPropagation();
                      await api.deleteReport(r.id);
                      loadReports();
                    }}
                  >
                    <Trash2 className="size-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
          <Button
            className="w-full"
            onClick={handleGenerateReport}
            disabled={notes.length === 0 || generatingReport}
          >
            {generatingReport ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : null}
            {generatingReport ? "Generating..." : "Generate Report"}
          </Button>
        </div>
      </div>

      {/* Add Note Dialog */}
      <Dialog open={noteDialogOpen} onOpenChange={setNoteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Note</DialogTitle>
          </DialogHeader>
          {newNoteHighlight && (
            <div className="rounded-md bg-muted p-3">
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                Highlighted text
              </p>
              <p className="text-sm italic">"{newNoteHighlight}"</p>
            </div>
          )}
          <Textarea
            value={newNoteContent}
            onChange={(e) => setNewNoteContent(e.target.value)}
            placeholder="Write your thoughts about this..."
            rows={4}
            autoFocus
          />
          <DialogFooter>
            <Button
              onClick={handleAddNote}
              disabled={!newNoteContent.trim()}
            >
              Add Note
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function LensNoteCard({
  note,
  onAdd,
  onDiscard,
}: {
  note: { content: string; highlight: string; status: string };
  onAdd: () => void;
  onDiscard: () => void;
}) {
  if (note.status === "discarded") return null;

  const accepted = note.status === "accepted";

  return (
    <div className={`rounded-lg border p-3 text-sm ${accepted ? "opacity-50" : ""}`}>
      {note.highlight && (
        <p className="mb-2 border-l-2 border-primary/30 pl-2 text-xs text-muted-foreground italic">
          "{note.highlight}"
        </p>
      )}
      <p className="text-xs leading-relaxed">{note.content}</p>
      <div className="mt-2 flex gap-1">
        {accepted ? (
          <Badge variant="secondary">
            <Check className="size-3" />
            Added
          </Badge>
        ) : (
          <Button
            variant="outline"
            size="xs"
            onClick={onAdd}
          >
            <Plus className="size-3" />
            Add to Notes
          </Button>
        )}
        {!accepted && (
          <Button
            variant="ghost"
            size="xs"
            onClick={onDiscard}
          >
            <X className="size-3" />
            Discard
          </Button>
        )}
      </div>
    </div>
  );
}
