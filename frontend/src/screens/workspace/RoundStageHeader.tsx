import { BookOpen, FileText, ListOrdered } from "lucide-react";
import type { RoundDetailOut, RoundSummary } from "../../api/types";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";

export type StageMode = "doc" | "curate" | "report";

interface RoundStageHeaderProps {
  round: RoundSummary | RoundDetailOut;
  mode: StageMode;
  curateAllowed: boolean;
  reportAllowed: boolean;
  onMode: (mode: StageMode) => void;
}

export default function RoundStageHeader({
  round,
  mode,
  curateAllowed,
  reportAllowed,
  onMode,
}: RoundStageHeaderProps) {
  const docCount = "doc_count" in round ? round.doc_count : round.docs.length;
  const reportId = round.report_id;
  const editing = round.stage === "editing";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-2.5">
      <div className="flex min-w-0 items-center gap-3">
        <span className="truncate text-sm font-semibold" data-testid="round-stage-name">
          {round.name}
        </span>
        <Badge variant={editing ? "outline" : "secondary"} data-testid="round-stage-badge">
          {round.stage}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {docCount} doc{docCount === 1 ? "" : "s"} in this round
        </span>
        {editing && (
          <span className="text-xs text-muted-foreground">
            {reportId !== null
              ? "report generated — this round is in editor mode"
              : "report deleted — generation is one-shot; start a new round for another"}
          </span>
        )}
        {!editing && reportId !== null && (
          <span className="text-xs text-muted-foreground">a report already exists</span>
        )}
      </div>
      <div className="flex items-center gap-1.5">
        <Button
          size="sm"
          variant={mode === "doc" ? "default" : "ghost"}
          onClick={() => onMode("doc")}
        >
          <BookOpen className="mr-1 h-3 w-3" />
          Read & annotate
        </Button>
        <Button
          size="sm"
          variant={mode === "curate" ? "default" : "ghost"}
          disabled={!curateAllowed}
          title={
            !curateAllowed
              ? editing
                ? "this round is in the editing stage; curation is closed (R-042)"
                : "no dump to curate yet"
              : undefined
          }
          onClick={() => onMode("curate")}
        >
          <ListOrdered className="mr-1 h-3 w-3" />
          Curate dump
        </Button>
        <Button
          size="sm"
          variant={mode === "report" ? "default" : "ghost"}
          disabled={!reportAllowed}
          title={!reportAllowed ? "no report for this round yet" : undefined}
          onClick={() => onMode("report")}
        >
          <FileText className="mr-1 h-3 w-3" />
          Report
        </Button>
      </div>
    </div>
  );
}
