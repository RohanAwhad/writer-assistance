from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from writer_assistance_api.schemas.projects import CreateProjectRequest, ProjectResponse
from writer_assistance_api.services.projects import ProjectsService, get_projects_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(
    service: Annotated[ProjectsService, Depends(get_projects_service)],
) -> dict[str, list[ProjectResponse]]:
    return {"projects": service.list_projects()}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: CreateProjectRequest,
    service: Annotated[ProjectsService, Depends(get_projects_service)],
) -> ProjectResponse:
    return service.create_project(payload)
