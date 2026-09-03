"""Round, expert-run, expert-note, and dump routes (F4..F6; spec §6)."""

from fastapi import APIRouter

from app.deps import AiDep, DbDep
from app.schemas import (
    DumpEntryOut,
    DumpOut,
    DumpSaveRequest,
    ExpertNoteMergeRequest,
    ExpertNoteOut,
    ExpertNoteUpdate,
    ExpertRunOut,
    ExpertRunRequest,
    ExpertRunsOut,
    RoundCreate,
    RoundDetailOut,
    RoundOut,
    RoundSummary,
)
from app.services import experts, rounds

router = APIRouter(tags=["rounds"])


@router.post("/rounds", response_model=RoundOut, status_code=201)
def create_round(db: DbDep, body: RoundCreate) -> RoundOut:
    return rounds.create_round(db, body.project_id, body.doc_ids, body.name)


@router.get("/rounds", response_model=list[RoundSummary])
def list_rounds(db: DbDep, project_id: int) -> list[RoundSummary]:
    return rounds.list_round_summaries(db, project_id)


@router.get("/rounds/{round_id}", response_model=RoundDetailOut)
def get_round(db: DbDep, round_id: int) -> RoundDetailOut:
    return rounds.round_detail(db, round_id)


@router.post("/rounds/{round_id}/experts", response_model=ExpertRunsOut, status_code=201)
def run_experts(db: DbDep, ai: AiDep, round_id: int, body: ExpertRunRequest) -> ExpertRunsOut:
    return experts.run_experts(db, ai, round_id, body.lens_proposal_ids)


@router.get("/expert-runs/{run_id}/notes", response_model=ExpertRunOut)
def get_expert_run_notes(db: DbDep, run_id: int) -> ExpertRunOut:
    return experts.get_expert_run_notes(db, run_id)


@router.get("/rounds/{round_id}/expert-runs", response_model=ExpertRunsOut)
def get_round_expert_runs(db: DbDep, round_id: int) -> ExpertRunsOut:
    return experts.list_round_expert_runs(db, round_id)


@router.patch("/expert-notes/{note_id}", response_model=ExpertNoteOut)
def update_expert_note(db: DbDep, note_id: int, body: ExpertNoteUpdate) -> ExpertNoteOut:
    return experts.update_expert_note(db, note_id, body.review_state, body.content)


@router.post("/expert-notes/{note_id}/merge", response_model=DumpEntryOut, status_code=201)
def merge_expert_note(db: DbDep, note_id: int, body: ExpertNoteMergeRequest) -> DumpEntryOut:
    return experts.merge_expert_note(db, note_id, body.content)


@router.get("/rounds/{round_id}/dump", response_model=DumpOut)
def get_dump(db: DbDep, round_id: int) -> DumpOut:
    return rounds.get_dump(db, round_id)


@router.post("/rounds/{round_id}/dump", response_model=DumpOut)
def save_dump(db: DbDep, round_id: int, body: DumpSaveRequest) -> DumpOut:
    return rounds.save_dump(db, round_id, body)
