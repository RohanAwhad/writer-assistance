from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from writer_assistance_api.schemas.annotations import AnnotationResponse, CreateAnnotationRequest
from writer_assistance_api.services.annotations import AnnotationsService, get_annotations_service

router = APIRouter(tags=["annotations"])


@router.post("/projects/{project_id}/annotations", status_code=status.HTTP_201_CREATED)
def create_annotation(
    project_id: str,
    payload: CreateAnnotationRequest,
    service: Annotated[AnnotationsService, Depends(get_annotations_service)],
) -> AnnotationResponse:
    return service.create_annotation(project_id, payload)


@router.get("/resources/{resource_id}/annotations")
def list_annotations(
    resource_id: str,
    service: Annotated[AnnotationsService, Depends(get_annotations_service)],
) -> dict[str, list[AnnotationResponse]]:
    return {"annotations": service.list_annotations(resource_id)}
