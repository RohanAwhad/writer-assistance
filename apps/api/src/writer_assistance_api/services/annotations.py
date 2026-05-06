from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from writer_assistance_api.db import get_session
from writer_assistance_api.models import Annotation, Project, Resource
from writer_assistance_api.schemas.annotations import (
    AnnotationResponse,
    CreateAnnotationRequest,
    QuoteAnchor,
    ResolutionStatus,
)


class AnnotationsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_annotation(self, project_id: str, payload: CreateAnnotationRequest) -> AnnotationResponse:
        project = self._session.scalar(select(Project).where(Project.id == project_id))
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        resource = self._session.scalar(
            select(Resource).where(Resource.id == payload.resource_id, Resource.project_id == project_id)
        )
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        body = payload.body.strip()
        if not body:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Annotation body is required")

        anchor = _validated_anchor(payload.anchor)
        now = datetime.now(UTC)
        annotation = Annotation(
            id=str(uuid4()),
            project_id=project_id,
            resource_id=resource.id,
            quote_text=anchor.quote_text,
            normalized_text=anchor.normalized_text,
            start_offset=anchor.start_offset,
            end_offset=anchor.end_offset,
            block_path=anchor.block_path,
            resolution_status=anchor.resolution_status,
            body=body,
            origin_type="user",
            provenance_source_id=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(annotation)
        self._session.commit()
        return _to_annotation_response(annotation)

    def list_annotations(self, resource_id: str) -> list[AnnotationResponse]:
        resource = self._session.get(Resource, resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        annotations = list(
            self._session.scalars(
                select(Annotation)
                .where(Annotation.resource_id == resource_id)
                .order_by(Annotation.created_at, Annotation.id)
            )
        )
        return [_to_annotation_response(annotation) for annotation in annotations]


def _to_annotation_response(annotation: Annotation) -> AnnotationResponse:
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


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _validated_anchor(anchor: QuoteAnchor) -> QuoteAnchor:
    trimmed_quote_text = anchor.quote_text.strip()
    if not trimmed_quote_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Quote anchor quoteText must contain non-whitespace text",
        )

    if trimmed_quote_text != anchor.quote_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Quote anchor quoteText must be trimmed",
        )

    if anchor.start_offset >= anchor.end_offset:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Quote anchor must satisfy startOffset < endOffset",
        )

    expected_normalized_text = _normalize_quote_text(trimmed_quote_text)
    if anchor.normalized_text != expected_normalized_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Quote anchor normalizedText must match quoteText",
        )

    return QuoteAnchor(
        quoteText=trimmed_quote_text,
        normalizedText=expected_normalized_text,
        startOffset=anchor.start_offset,
        endOffset=anchor.end_offset,
        blockPath=anchor.block_path,
        resolutionStatus=anchor.resolution_status,
    )


def _normalize_quote_text(quote_text: str) -> str:
    return " ".join(quote_text.split()).lower()


def get_annotations_service(
    session: Annotated[Session, Depends(get_session)],
) -> AnnotationsService:
    return AnnotationsService(session=session)
