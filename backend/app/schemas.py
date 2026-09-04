"""Pydantic request/response models for the /api/v1 surface (spec §6)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ProjectId = int
NodeId = int
RoundId = int

AnnotationKind = Literal["highlight", "note"]
LensProposalStatus = Literal["proposed", "selected", "skipped"]
RoundStage = Literal["reading", "editing"]
ExpertNoteState = Literal["pending", "accepted", "discarded", "merged-with-edits"]
DumpEntryKind = Literal["snippet", "highlight", "human-thought", "ai-thought"]
AiProvider = Literal["vertex", "deepseek"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProviderUpdate(BaseModel):
    provider: AiProvider


class ProjectOut(BaseModel):
    id: ProjectId
    name: str
    ai_provider: AiProvider
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectOut):
    resource_count: int
    round_count: int


class ImportRequest(BaseModel):
    path: str


class ImportResult(BaseModel):
    project_id: ProjectId
    imported_files: int


class TreeNodeOut(BaseModel):
    id: NodeId
    parent_id: NodeId | None
    name: str
    path: str
    kind: Literal["dir", "file"]


class TreeOut(BaseModel):
    project_id: ProjectId
    nodes: list[TreeNodeOut]


class ResourceOut(BaseModel):
    id: NodeId
    project_id: ProjectId
    path: str
    content: str
    imported_at: datetime


class HighlightCreate(BaseModel):
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    content: str | None = Field(default=None, max_length=10000)


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _offsets_come_in_pairs(self) -> "NoteCreate":
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("start_offset and end_offset must be provided together")
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.start_offset >= self.end_offset
        ):
            raise ValueError("start_offset must be less than end_offset")
        return self


class AnnotationUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _offsets_come_in_pairs(self) -> "AnnotationUpdate":
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("start_offset and end_offset must be provided together")
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.start_offset >= self.end_offset
        ):
            raise ValueError("start_offset must be less than end_offset")
        return self


class AnnotationOut(BaseModel):
    id: int
    doc_id: NodeId
    kind: AnnotationKind
    start_offset: int | None
    end_offset: int | None
    content: str | None
    created_at: datetime
    updated_at: datetime


class LensProposalOut(BaseModel):
    id: int
    doc_id: NodeId
    title: str
    rationale: str
    status: LensProposalStatus
    created_at: datetime


class LensProposalsOut(BaseModel):
    lens_proposals: list[LensProposalOut]


class LensProposalStatusUpdate(BaseModel):
    status: Literal["selected", "skipped"]


class RoundCreate(BaseModel):
    project_id: ProjectId
    doc_ids: list[NodeId] = Field(min_length=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)


class RoundOut(BaseModel):
    id: RoundId
    project_id: ProjectId
    name: str
    stage: RoundStage
    doc_ids: list[NodeId]
    created_at: datetime
    updated_at: datetime


class RoundDocOut(BaseModel):
    id: NodeId
    path: str


class RoundSummary(BaseModel):
    id: RoundId
    project_id: ProjectId
    name: str
    stage: RoundStage
    doc_count: int
    created_at: datetime
    dump_id: int | None
    report_id: int | None


class RoundDetailOut(BaseModel):
    id: RoundId
    project_id: ProjectId
    name: str
    stage: RoundStage
    created_at: datetime
    updated_at: datetime
    docs: list[RoundDocOut]
    dump_id: int | None
    report_id: int | None


class ExpertRunRequest(BaseModel):
    lens_proposal_ids: list[int] = Field(min_length=1)


class ExpertNoteOut(BaseModel):
    id: int
    expert_run_id: int
    content: str
    edited_content: str | None
    review_state: ExpertNoteState
    merged: bool
    position: int


class ExpertRunOut(BaseModel):
    id: int
    round_id: RoundId
    doc_id: NodeId
    doc_path: str
    lens_proposal_id: int
    lens_rationale: str
    lens_title: str
    notes: list[ExpertNoteOut]


class ExpertRunsOut(BaseModel):
    expert_runs: list[ExpertRunOut]


class ExpertNoteUpdate(BaseModel):
    review_state: ExpertNoteState
    content: str | None = Field(default=None, min_length=1, max_length=20000)


class ExpertNoteMergeRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=20000)


class DumpEntryIn(BaseModel):
    id: int | None = None
    kind: DumpEntryKind
    content: str = Field(min_length=1, max_length=50000)
    doc_id: NodeId | None = None

    @model_validator(mode="after")
    def _source_doc_required_for_extracts(self) -> "DumpEntryIn":
        if self.kind in ("snippet", "highlight") and self.doc_id is None:
            raise ValueError("doc_id is required for snippet and highlight entries")
        return self


class DumpSaveRequest(BaseModel):
    entries: list[DumpEntryIn] = Field(max_length=1000)


class DumpEntryOut(BaseModel):
    id: int
    round_id: RoundId
    dump_id: int | None
    kind: DumpEntryKind
    content: str
    doc_id: NodeId | None
    doc_path: str | None
    expert_note_id: int | None
    position: int | None
    created_at: datetime


class DumpOut(BaseModel):
    round_id: RoundId
    dump_id: int | None
    saved: bool
    entries: list[DumpEntryOut]


class ReportBlockOut(BaseModel):
    id: int
    report_id: int
    position: int
    content: str
    source_entry_ids: list[int]
    created_at: datetime
    updated_at: datetime


class ReportOut(BaseModel):
    id: int
    round_id: RoundId
    created_at: datetime
    blocks: list[ReportBlockOut]


class BlockUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=50000)


class ToneSampleOut(BaseModel):
    tone: str
    text: str


class ToneSamplesOut(BaseModel):
    samples: list[ToneSampleOut]


class CritiqueOut(BaseModel):
    critique: str


class ReportDeleteRequest(BaseModel):
    confirm: bool
