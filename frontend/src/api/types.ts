export type IsoDatetime = string;

export interface ProjectOut {
  id: number;
  name: string;
  created_at: IsoDatetime;
  updated_at: IsoDatetime;
}

export interface ProjectDetail extends ProjectOut {
  resource_count: number;
  round_count: number;
}

export interface ImportResult {
  project_id: number;
  imported_files: number;
}

export type NodeKind = "dir" | "file";

export interface TreeNodeOut {
  id: number;
  parent_id: number | null;
  name: string;
  path: string;
  kind: NodeKind;
}

export interface TreeOut {
  project_id: number;
  nodes: TreeNodeOut[];
}

export interface ResourceOut {
  id: number;
  project_id: number;
  path: string;
  content: string;
  imported_at: IsoDatetime;
}

export type AnnotationKind = "highlight" | "note";

export interface AnnotationOut {
  id: number;
  doc_id: number;
  kind: AnnotationKind;
  start_offset: number | null;
  end_offset: number | null;
  content: string | null;
  created_at: IsoDatetime;
  updated_at: IsoDatetime;
}

export type LensProposalStatus = "proposed" | "selected" | "skipped";

export interface LensProposalOut {
  id: number;
  doc_id: number;
  title: string;
  rationale: string;
  status: LensProposalStatus;
  created_at: IsoDatetime;
}

export type RoundStage = "reading" | "editing";

export interface RoundOut {
  id: number;
  project_id: number;
  name: string;
  stage: RoundStage;
  doc_ids: number[];
  created_at: IsoDatetime;
  updated_at: IsoDatetime;
}

export interface RoundDocOut {
  id: number;
  path: string;
}

export interface RoundDetailOut {
  id: number;
  project_id: number;
  name: string;
  stage: RoundStage;
  created_at: IsoDatetime;
  updated_at: IsoDatetime;
  docs: RoundDocOut[];
  dump_id: number | null;
  report_id: number | null;
}

export interface RoundSummary {
  id: number;
  project_id: number;
  name: string;
  stage: RoundStage;
  doc_count: number;
  created_at: IsoDatetime;
  dump_id: number | null;
  report_id: number | null;
}

export type ExpertNoteState = "pending" | "accepted" | "discarded" | "merged-with-edits";

export interface ExpertNoteOut {
  id: number;
  expert_run_id: number;
  content: string;
  edited_content: string | null;
  review_state: ExpertNoteState;
  merged: boolean;
  position: number;
}

export interface ExpertRunOut {
  id: number;
  round_id: number;
  doc_id: number;
  doc_path: string;
  lens_proposal_id: number;
  lens_rationale: string;
  lens_title: string;
  notes: ExpertNoteOut[];
}

export interface ExpertRunsOut {
  expert_runs: ExpertRunOut[];
}

export type DumpEntryKind = "snippet" | "highlight" | "human-thought" | "ai-thought";

export interface DumpEntryOut {
  id: number;
  round_id: number;
  dump_id: number | null;
  kind: DumpEntryKind;
  content: string;
  doc_id: number | null;
  doc_path: string | null;
  expert_note_id: number | null;
  position: number | null;
  created_at: IsoDatetime;
}

export interface DumpOut {
  round_id: number;
  dump_id: number | null;
  saved: boolean;
  entries: DumpEntryOut[];
}

export interface DumpEntryIn {
  id?: number | null;
  kind: DumpEntryKind;
  content: string;
  doc_id?: number | null;
}

export interface ReportBlockOut {
  id: number;
  report_id: number;
  position: number;
  content: string;
  source_entry_ids: number[];
  created_at: IsoDatetime;
  updated_at: IsoDatetime;
}

export interface ReportOut {
  id: number;
  round_id: number;
  created_at: IsoDatetime;
  blocks: ReportBlockOut[];
}

export interface ToneSampleOut {
  tone: string;
  text: string;
}

export interface ToneSamplesOut {
  samples: ToneSampleOut[];
}

export interface CritiqueOut {
  critique: string;
}
