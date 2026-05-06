from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from writer_assistance_api.schemas.analysis_runs import (
    AcceptAnalysisSuggestionResponse,
    AnalysisRunDetailResponse,
    CreateAnalysisRunRequest,
    SuggestionEnvelope,
)
from writer_assistance_api.services.analysis_runs import (
    AnalysisRunsService,
    get_analysis_runs_service,
    process_analysis_run_in_background,
)

router = APIRouter(tags=["analysis-runs"])


@router.post("/projects/{project_id}/analysis-runs", status_code=status.HTTP_202_ACCEPTED)
def create_analysis_run(
    request: Request,
    background_tasks: BackgroundTasks,
    project_id: str,
    payload: CreateAnalysisRunRequest,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AnalysisRunDetailResponse:
    queued_run = service.create_analysis_run(project_id, payload)
    background_tasks.add_task(process_analysis_run_in_background, request.app, queued_run.id)
    return queued_run


@router.get("/analysis-runs/{analysis_run_id}")
def get_analysis_run(
    analysis_run_id: str,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AnalysisRunDetailResponse:
    return service.get_analysis_run(analysis_run_id)


@router.get("/resources/{resource_id}/analysis-runs/latest")
def get_latest_analysis_run_for_resource(
    resource_id: str,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AnalysisRunDetailResponse:
    return service.get_latest_analysis_run_for_resource(resource_id)


@router.post("/analysis-runs/{analysis_run_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_analysis_run(
    request: Request,
    background_tasks: BackgroundTasks,
    analysis_run_id: str,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AnalysisRunDetailResponse:
    queued_run = service.retry_analysis_run(analysis_run_id)
    background_tasks.add_task(process_analysis_run_in_background, request.app, queued_run.id)
    return queued_run


@router.post("/analysis-runs/{analysis_run_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_analysis_run(
    analysis_run_id: str,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AnalysisRunDetailResponse:
    return service.cancel_analysis_run(analysis_run_id)


@router.post("/analysis-suggestions/{suggestion_id}/accept", status_code=status.HTTP_201_CREATED)
def accept_suggestion(
    suggestion_id: str,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> AcceptAnalysisSuggestionResponse:
    return service.accept_suggestion(suggestion_id)


@router.post("/analysis-suggestions/{suggestion_id}/discard")
def discard_suggestion(
    suggestion_id: str,
    service: Annotated[AnalysisRunsService, Depends(get_analysis_runs_service)],
) -> SuggestionEnvelope:
    return service.discard_suggestion(suggestion_id)
