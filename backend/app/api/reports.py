"""Report, block, tone-sample, and critique routes (F7..F11; spec §6)."""

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from app.deps import AiDep, DbDep
from app.schemas import (
    BlockUpdate,
    CritiqueOut,
    ReportBlockOut,
    ReportDeleteRequest,
    ReportOut,
    ToneSamplesOut,
)
from app.services import reports

router = APIRouter(tags=["reports"])


@router.post("/rounds/{round_id}/generate-report", response_model=ReportOut, status_code=201)
def generate_report(db: DbDep, ai: AiDep, round_id: int) -> ReportOut:
    return reports.generate_report(db, ai, round_id)


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(db: DbDep, report_id: int) -> ReportOut:
    return reports.get_report(db, report_id)


@router.get("/reports/{report_id}/export.md", response_class=PlainTextResponse)
def export_report_markdown(db: DbDep, report_id: int) -> PlainTextResponse:
    body = reports.export_markdown(db, report_id)
    return PlainTextResponse(
        body,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="report-{report_id}.md"'},
    )


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(db: DbDep, report_id: int, body: ReportDeleteRequest) -> Response:
    reports.delete_report(db, report_id, body.confirm)
    return Response(status_code=204)


@router.put("/blocks/{block_id}", response_model=ReportBlockOut)
def update_block(db: DbDep, block_id: int, body: BlockUpdate) -> ReportBlockOut:
    return reports.update_block(db, block_id, body.content)


@router.post("/blocks/{block_id}/tone-samples", response_model=ToneSamplesOut)
def tone_samples(db: DbDep, ai: AiDep, block_id: int) -> ToneSamplesOut:
    return reports.tone_samples_for_block(db, ai, block_id)


@router.post("/blocks/{block_id}/critique", response_model=CritiqueOut)
def critique(db: DbDep, ai: AiDep, block_id: int) -> CritiqueOut:
    return reports.critique_for_block(db, ai, block_id)
