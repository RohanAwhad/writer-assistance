import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Download,
  Palette,
  MessageSquareWarning,
  Check,
  Loader2,
} from "lucide-react";
import * as api from "@/lib/api";
import type { Report, ReportBlock, ToneVariation, Critique } from "@/lib/api";

export default function ReportEditor() {
  const { projectId, reportId } = useParams<{
    projectId: string;
    reportId: string;
  }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingBlockId, setEditingBlockId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");

  // Tone variations
  const [toneDialogOpen, setToneDialogOpen] = useState(false);
  const [toneBlockId, setToneBlockId] = useState<number | null>(null);
  const [toneVariations, setToneVariations] = useState<ToneVariation[]>([]);
  const [loadingTones, setLoadingTones] = useState(false);

  // Critique
  const [critiqueDialogOpen, setCritiqueDialogOpen] = useState(false);
  const [critique, setCritique] = useState<Critique | null>(null);
  const [loadingCritique, setLoadingCritique] = useState(false);

  const rid = Number(reportId);

  const loadReport = useCallback(async () => {
    setLoading(true);
    const data = await api.getReport(rid);
    setReport(data);
    setLoading(false);
  }, [rid]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleBlockClick = (block: ReportBlock) => {
    setEditingBlockId(block.id);
    setEditContent(block.content);
  };

  const handleSaveBlock = async () => {
    if (editingBlockId === null) return;
    await api.updateBlock(rid, editingBlockId, editContent);
    setEditingBlockId(null);
    loadReport();
  };

  const handleCancelEdit = () => {
    setEditingBlockId(null);
    setEditContent("");
  };

  const handleToneVariations = async (blockId: number) => {
    setToneBlockId(blockId);
    setToneDialogOpen(true);
    setLoadingTones(true);
    setToneVariations([]);
    const variations = await api.getToneVariations(rid, blockId);
    setToneVariations(variations);
    setLoadingTones(false);
  };

  const handleSelectTone = async (variation: ToneVariation) => {
    if (toneBlockId === null) return;
    await api.updateBlock(rid, toneBlockId, variation.content);
    setToneDialogOpen(false);
    loadReport();
  };

  const handleCritique = async (blockId: number) => {
    setCritiqueDialogOpen(true);
    setLoadingCritique(true);
    setCritique(null);
    const data = await api.getCritique(rid, blockId);
    setCritique(data);
    setLoadingCritique(false);
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading report...
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Report not found.
      </div>
    );
  }

  const sortedBlocks = [...report.blocks].sort(
    (a, b) => a.position - b.position
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b px-4 py-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(`/projects/${projectId}`)}
        >
          <ArrowLeft className="size-3.5" />
          Back to Workspace
        </Button>
        <Separator orientation="vertical" className="h-5" />
        <h1 className="flex-1 text-sm font-medium">{report.title}</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => api.exportReport(rid)}
        >
          <Download className="size-3.5" />
          Export Markdown
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-2xl space-y-4 p-6">
          {sortedBlocks.map((block) => (
            <div key={block.id} className="group relative">
              {editingBlockId === block.id ? (
                <div className="space-y-2">
                  <Textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="min-h-24"
                  />
                  <div className="flex gap-1">
                    <Button size="xs" onClick={handleSaveBlock}>
                      <Check className="size-3" />
                      Save
                    </Button>
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={handleCancelEdit}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div
                  className="cursor-pointer rounded-lg border border-transparent p-3 transition-colors hover:border-border hover:bg-muted/30"
                  onClick={() => handleBlockClick(block)}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {block.content}
                  </p>
                  <div className="mt-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <Button
                      variant="outline"
                      size="xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToneVariations(block.id);
                      }}
                    >
                      <Palette className="size-3" />
                      Tone Variations
                    </Button>
                    <Button
                      variant="outline"
                      size="xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCritique(block.id);
                      }}
                    >
                      <MessageSquareWarning className="size-3" />
                      Challenge Argument
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Tone Variations Dialog */}
      <Dialog open={toneDialogOpen} onOpenChange={setToneDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Tone Variations</DialogTitle>
          </DialogHeader>
          {loadingTones ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Generating variations...
            </div>
          ) : (
            <div className="max-h-80 space-y-3 overflow-y-auto">
              {toneVariations.map((v, i) => (
                <div
                  key={i}
                  className="cursor-pointer rounded-lg border p-3 transition-colors hover:bg-muted/50"
                  onClick={() => handleSelectTone(v)}
                >
                  <Badge variant="secondary" className="mb-2">
                    {v.tone_name}
                  </Badge>
                  <p className="text-xs leading-relaxed">{v.content}</p>
                </div>
              ))}
            </div>
          )}
          <DialogFooter showCloseButton />
        </DialogContent>
      </Dialog>

      {/* Critique Dialog */}
      <Dialog open={critiqueDialogOpen} onOpenChange={setCritiqueDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Challenge Argument</DialogTitle>
          </DialogHeader>
          {loadingCritique ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Analyzing argument...
            </div>
          ) : critique ? (
            <div className="max-h-96 space-y-4 overflow-y-auto">
              <div>
                <h4 className="mb-1 text-xs font-medium text-muted-foreground">
                  Critique
                </h4>
                <p className="text-sm leading-relaxed">{critique.critique}</p>
              </div>
              {critique.suggestions.length > 0 && (
                <div>
                  <h4 className="mb-1 text-xs font-medium text-muted-foreground">
                    Suggestions
                  </h4>
                  <ul className="list-inside list-disc space-y-1 text-sm">
                    {critique.suggestions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
              {critique.questions.length > 0 && (
                <div>
                  <h4 className="mb-1 text-xs font-medium text-muted-foreground">
                    Probing Questions
                  </h4>
                  <ul className="list-inside list-disc space-y-1 text-sm">
                    {critique.questions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
          <DialogFooter showCloseButton />
        </DialogContent>
      </Dialog>
    </div>
  );
}
