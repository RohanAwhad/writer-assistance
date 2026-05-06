from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from writer_assistance_api.ai.anthropic_vertex_client import AnthropicVertexAiClient
from writer_assistance_api.ai.client import AiClient, LensName, normalize_suggestion_drafts
from writer_assistance_api.config import Settings
from writer_assistance_api.db import get_session
from writer_assistance_api.models import (
    AnalysisRun,
    AnalysisRunLensResult,
    AnalysisSuggestion,
    Annotation,
    Project,
    Resource,
)
from writer_assistance_api.schemas.analysis_runs import (
    AcceptAnalysisSuggestionResponse,
    AnalysisLensGenerationState,
    AnalysisLensResultResponse,
    AnalysisRunDetailResponse,
    AnalysisRunGenerationState,
    AnalysisSuggestionResponse,
    CreateAnalysisRunRequest,
    SuggestionReviewState,
    SuggestionEnvelope,
)
from writer_assistance_api.schemas.annotations import AnnotationResponse, QuoteAnchor, ResolutionStatus
from writer_assistance_api.storage import StorageDriver


class AnalysisRunsService:
    def __init__(
        self,
        session: Session,
        storage: StorageDriver,
        ai_client: AiClient | None = None,
    ) -> None:
        self._session = session
        self._storage = storage
        self._ai_client = ai_client

    def create_analysis_run(
        self,
        project_id: str,
        payload: CreateAnalysisRunRequest,
    ) -> AnalysisRunDetailResponse:
        project = self._session.scalar(select(Project).where(Project.id == project_id))
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        resource = self._session.scalar(
            select(Resource).where(Resource.id == payload.resource_id, Resource.project_id == project_id)
        )
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        now = datetime.now(UTC)
        run = AnalysisRun(
            id=str(uuid4()),
            project_id=project_id,
            resource_id=resource.id,
            generation_state="queued",
            requested_lenses=list(payload.lenses),
            created_at=now,
            updated_at=now,
        )
        lens_results = [
            AnalysisRunLensResult(
                id=str(uuid4()),
                analysis_run_id=run.id,
                lens=lens,
                generation_state="queued",
                error_message=None,
                created_at=now,
                updated_at=now,
            )
            for lens in payload.lenses
        ]
        self._session.add(run)
        self._session.add_all(lens_results)
        self._session.commit()
        return self._serialize_run(run)

    def get_analysis_run(self, analysis_run_id: str) -> AnalysisRunDetailResponse:
        run = self._get_analysis_run_or_404(analysis_run_id)
        return self._serialize_run(run)

    def get_latest_analysis_run_for_resource(self, resource_id: str) -> AnalysisRunDetailResponse:
        resource = self._session.get(Resource, resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        latest_run = self._session.scalar(
            select(AnalysisRun)
            .where(AnalysisRun.resource_id == resource_id)
            .order_by(desc(AnalysisRun.created_at), desc(AnalysisRun.id))
            .limit(1)
        )
        if latest_run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
        return self._serialize_run(latest_run)

    def retry_analysis_run(self, analysis_run_id: str) -> AnalysisRunDetailResponse:
        run = self._get_analysis_run_or_404(analysis_run_id)
        all_lens_results = self._ordered_lens_results(run)
        failed_lens_results = [
            lens_result for lens_result in all_lens_results if lens_result.generation_state == "failed"
        ]
        if not failed_lens_results:
            return self._serialize_run(run)

        run.generation_state = "queued"
        run.updated_at = datetime.now(UTC)
        for lens_result in failed_lens_results:
            lens_result.generation_state = "queued"
            lens_result.error_message = None
            lens_result.updated_at = datetime.now(UTC)
        self._session.commit()
        return self._serialize_run(run)

    def cancel_analysis_run(self, analysis_run_id: str) -> AnalysisRunDetailResponse:
        run = self._get_analysis_run_or_404(analysis_run_id)
        all_lens_results = self._ordered_lens_results(run)
        cancellable_lens_results = [
            lens_result
            for lens_result in all_lens_results
            if lens_result.generation_state in {"queued", "running"}
        ]
        if not cancellable_lens_results:
            return self._serialize_run(run)

        now = datetime.now(UTC)
        for lens_result in cancellable_lens_results:
            lens_result.generation_state = "cancelled"
            lens_result.error_message = None
            lens_result.updated_at = now
        run.generation_state = _run_generation_state(all_lens_results)
        run.updated_at = now
        self._session.commit()
        return self._serialize_run(run)

    def process_analysis_run(self, analysis_run_id: str) -> None:
        run = self._get_analysis_run_or_404(analysis_run_id)
        resource = self._get_resource_for_run(run)
        all_lens_results = self._ordered_lens_results(run)
        lens_results_to_process = [
            lens_result for lens_result in all_lens_results if lens_result.generation_state == "queued"
        ]
        if not lens_results_to_process:
            return

        if self._ai_client is None:
            raise RuntimeError("AI client is required to process analysis runs")

        run.generation_state = "running"
        run.updated_at = datetime.now(UTC)
        for lens_result in lens_results_to_process:
            lens_result.generation_state = "running"
            lens_result.error_message = None
            lens_result.updated_at = datetime.now(UTC)
        self._session.commit()

        try:
            markdown = self._read_markdown_resource(resource)
        except Exception as exc:
            self._mark_processing_failure(
                run=run,
                lens_results=lens_results_to_process,
                all_lens_results=all_lens_results,
                message=str(exc) or exc.__class__.__name__,
            )
            return

        for lens_result in lens_results_to_process:
            self._session.refresh(run)
            self._session.refresh(lens_result)
            if lens_result.generation_state == "cancelled":
                continue
            try:
                raw_suggestions = self._ai_client.analyze_resource(
                    lens=cast(LensName, lens_result.lens),
                    markdown=markdown,
                    logical_path=resource.logical_path,
                )
                self._session.refresh(run)
                self._session.refresh(lens_result)
                if lens_result.generation_state == "cancelled":
                    continue
                suggestion_drafts = normalize_suggestion_drafts(raw_suggestions)
                suggestions = [
                    self._build_suggestion(
                        run_id=run.id,
                        lens_result=lens_result,
                        body=suggestion.body,
                        anchor=suggestion.anchor,
                    )
                    for suggestion in suggestion_drafts
                ]
                self._session.add_all(suggestions)
                lens_result.generation_state = "succeeded"
                lens_result.error_message = None
            except Exception as exc:
                self._session.refresh(run)
                self._session.refresh(lens_result)
                if lens_result.generation_state == "cancelled":
                    continue
                lens_result.generation_state = "failed"
                lens_result.error_message = str(exc) or exc.__class__.__name__
            lens_result.updated_at = datetime.now(UTC)
            run.generation_state = _run_generation_state(self._ordered_lens_results(run))
            run.updated_at = datetime.now(UTC)
            self._session.commit()

        self._session.refresh(run)
        run.generation_state = _run_generation_state(self._ordered_lens_results(run))
        run.updated_at = datetime.now(UTC)
        self._session.commit()

    def accept_suggestion(self, suggestion_id: str) -> AcceptAnalysisSuggestionResponse:
        suggestion = self._get_suggestion_or_404(suggestion_id)
        self._ensure_unreviewed(suggestion)
        run = self._get_analysis_run_or_404(suggestion.analysis_run_id)

        now = datetime.now(UTC)
        suggestion.review_state = "accepted"
        suggestion.updated_at = now
        annotation = Annotation(
            id=str(uuid4()),
            project_id=run.project_id,
            resource_id=run.resource_id,
            quote_text=suggestion.quote_text,
            normalized_text=suggestion.normalized_text,
            start_offset=suggestion.start_offset,
            end_offset=suggestion.end_offset,
            block_path=suggestion.block_path,
            resolution_status=suggestion.resolution_status,
            body=suggestion.body,
            origin_type="accepted_ai",
            provenance_source_id=suggestion.id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(annotation)
        self._session.commit()
        return AcceptAnalysisSuggestionResponse(
            suggestion=self._serialize_suggestion(suggestion),
            annotation=_serialize_annotation(annotation),
        )

    def discard_suggestion(self, suggestion_id: str) -> SuggestionEnvelope:
        suggestion = self._get_suggestion_or_404(suggestion_id)
        self._ensure_unreviewed(suggestion)
        suggestion.review_state = "discarded"
        suggestion.updated_at = datetime.now(UTC)
        self._session.commit()
        return SuggestionEnvelope(suggestion=self._serialize_suggestion(suggestion))

    def _mark_processing_failure(
        self,
        *,
        run: AnalysisRun,
        lens_results: Sequence[AnalysisRunLensResult],
        all_lens_results: Sequence[AnalysisRunLensResult],
        message: str,
    ) -> None:
        for lens_result in lens_results:
            lens_result.generation_state = "failed"
            lens_result.error_message = message
            lens_result.updated_at = datetime.now(UTC)
        run.generation_state = _run_generation_state(all_lens_results)
        run.updated_at = datetime.now(UTC)
        self._session.commit()

    def _build_suggestion(
        self,
        *,
        run_id: str,
        lens_result: AnalysisRunLensResult,
        body: str,
        anchor: QuoteAnchor,
    ) -> AnalysisSuggestion:
        canonical_anchor = _canonicalize_anchor(anchor)
        cleaned_body = body.strip()
        if not cleaned_body:
            raise ValueError("Suggestion body is required")
        now = datetime.now(UTC)
        return AnalysisSuggestion(
            id=str(uuid4()),
            analysis_run_id=run_id,
            lens_result_id=lens_result.id,
            lens=lens_result.lens,
            body=cleaned_body,
            quote_text=canonical_anchor.quote_text,
            normalized_text=canonical_anchor.normalized_text,
            start_offset=canonical_anchor.start_offset,
            end_offset=canonical_anchor.end_offset,
            block_path=canonical_anchor.block_path,
            resolution_status=canonical_anchor.resolution_status,
            review_state="unreviewed",
            created_at=now,
            updated_at=now,
        )

    def _serialize_run(self, run: AnalysisRun) -> AnalysisRunDetailResponse:
        ordered_lens_results = self._ordered_lens_results(run)
        suggestions = list(
            self._session.scalars(
                select(AnalysisSuggestion)
                .where(AnalysisSuggestion.analysis_run_id == run.id)
                .order_by(AnalysisSuggestion.created_at, AnalysisSuggestion.id)
            )
        )
        suggestions_by_lens_result: dict[str, list[AnalysisSuggestion]] = defaultdict(list)
        for suggestion in suggestions:
            suggestions_by_lens_result[suggestion.lens_result_id].append(suggestion)

        return AnalysisRunDetailResponse(
            id=run.id,
            project_id=run.project_id,
            resource_id=run.resource_id,
            generation_state=cast(AnalysisRunGenerationState, run.generation_state),
            lens_results=[
                AnalysisLensResultResponse(
                    id=lens_result.id,
                    lens=cast(LensName, lens_result.lens),
                    generation_state=cast(AnalysisLensGenerationState, lens_result.generation_state),
                    error_message=lens_result.error_message,
                    suggestions=[
                        self._serialize_suggestion(suggestion)
                        for suggestion in suggestions_by_lens_result.get(lens_result.id, [])
                    ],
                )
                for lens_result in ordered_lens_results
            ],
            created_at=_coerce_utc(run.created_at),
            updated_at=_coerce_utc(run.updated_at),
        )

    def _serialize_suggestion(self, suggestion: AnalysisSuggestion) -> AnalysisSuggestionResponse:
        return AnalysisSuggestionResponse(
            id=suggestion.id,
            analysis_run_id=suggestion.analysis_run_id,
            lens=cast(LensName, suggestion.lens),
            body=suggestion.body,
            review_state=cast(SuggestionReviewState, suggestion.review_state),
            created_at=_coerce_utc(suggestion.created_at),
            updated_at=_coerce_utc(suggestion.updated_at),
            anchor=QuoteAnchor(
                quoteText=suggestion.quote_text,
                normalizedText=suggestion.normalized_text,
                startOffset=suggestion.start_offset,
                endOffset=suggestion.end_offset,
                blockPath=suggestion.block_path,
                resolutionStatus=cast(ResolutionStatus, suggestion.resolution_status),
            ),
        )

    def _ordered_lens_results(self, run: AnalysisRun) -> list[AnalysisRunLensResult]:
        lens_results = list(
            self._session.scalars(
                select(AnalysisRunLensResult).where(AnalysisRunLensResult.analysis_run_id == run.id)
            )
        )
        lens_order = {lens: index for index, lens in enumerate(run.requested_lenses)}
        lens_results.sort(key=lambda lens_result: lens_order.get(lens_result.lens, len(lens_order)))
        return lens_results

    def _get_analysis_run_or_404(self, analysis_run_id: str) -> AnalysisRun:
        run = self._session.get(AnalysisRun, analysis_run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
        return run

    def _get_resource_for_run(self, run: AnalysisRun) -> Resource:
        resource = self._session.get(Resource, run.resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        return resource

    def _get_suggestion_or_404(self, suggestion_id: str) -> AnalysisSuggestion:
        suggestion = self._session.get(AnalysisSuggestion, suggestion_id)
        if suggestion is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        return suggestion

    def _ensure_unreviewed(self, suggestion: AnalysisSuggestion) -> None:
        if suggestion.review_state != "unreviewed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Suggestion has already been reviewed",
            )

    def _read_markdown_resource(self, resource: Resource) -> str:
        try:
            return self._storage.read_object(resource.storage_location).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Resource content is not valid UTF-8 markdown",
            ) from exc


def _run_generation_state(
    lens_results: Sequence[AnalysisRunLensResult],
) -> AnalysisRunGenerationState:
    states = {lens_result.generation_state for lens_result in lens_results}
    if "running" in states:
        return "running"
    if "queued" in states:
        return "queued"
    if states == {"succeeded"}:
        return "succeeded"
    if states == {"failed"}:
        return "failed"
    if states == {"cancelled"}:
        return "cancelled"
    return "completed_with_failures"


def _canonicalize_anchor(anchor: QuoteAnchor) -> QuoteAnchor:
    quote_text = anchor.quote_text.strip()
    if not quote_text:
        raise ValueError("Suggestion anchor quoteText must contain non-whitespace text")
    if anchor.start_offset >= anchor.end_offset:
        raise ValueError("Suggestion anchor must satisfy startOffset < endOffset")

    normalized_text = _normalize_quote_text(quote_text)
    return QuoteAnchor(
        quoteText=quote_text,
        normalizedText=normalized_text,
        startOffset=anchor.start_offset,
        endOffset=anchor.end_offset,
        blockPath=anchor.block_path,
        resolutionStatus=anchor.resolution_status,
    )


def _normalize_quote_text(quote_text: str) -> str:
    return " ".join(quote_text.split()).lower()


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _serialize_annotation(annotation: Annotation) -> AnnotationResponse:
    return AnnotationResponse(
        id=annotation.id,
        project_id=annotation.project_id,
        resource_id=annotation.resource_id,
        body=annotation.body,
        origin_type=annotation.origin_type,
        provenance_source_id=annotation.provenance_source_id,
        created_at=_coerce_utc(annotation.created_at),
        updated_at=_coerce_utc(annotation.updated_at),
        anchor=QuoteAnchor(
            quoteText=annotation.quote_text,
            normalizedText=annotation.normalized_text,
            startOffset=annotation.start_offset,
            endOffset=annotation.end_offset,
            blockPath=annotation.block_path,
            resolutionStatus=cast(ResolutionStatus, annotation.resolution_status),
        ),
    )


def get_analysis_runs_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> AnalysisRunsService:
    storage = cast(StorageDriver, request.app.state.storage)
    ai_client = cast(AiClient | None, getattr(request.app.state, "ai_client", None))
    return AnalysisRunsService(session=session, storage=storage, ai_client=ai_client)


def process_analysis_run_in_background(app: FastAPI, analysis_run_id: str) -> None:
    session_factory = cast(sessionmaker[Session], app.state.session_factory)
    storage = cast(StorageDriver, app.state.storage)
    ai_client = _get_or_create_ai_client(app)
    with session_factory() as session:
        service = AnalysisRunsService(session=session, storage=storage, ai_client=ai_client)
        service.process_analysis_run(analysis_run_id)


def _get_or_create_ai_client(app: FastAPI) -> AiClient:
    ai_client = cast(AiClient | None, getattr(app.state, "ai_client", None))
    if ai_client is not None:
        return ai_client

    settings = cast(Settings, app.state.settings)
    try:
        ai_client = AnthropicVertexAiClient.from_settings(settings)
    except Exception as exc:
        ai_client = _FailingAiClient(str(exc) or exc.__class__.__name__)
    app.state.ai_client = ai_client
    return ai_client


class _FailingAiClient:
    def __init__(self, message: str) -> None:
        self._message = message

    def analyze_resource(self, **_: Any) -> list[Any]:
        raise RuntimeError(self._message)
