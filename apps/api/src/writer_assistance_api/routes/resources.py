from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from writer_assistance_api.schemas.resources import ResourceContentResponse, ResourceResponse
from writer_assistance_api.services.resources import ResourcesService, get_resources_service

router = APIRouter(tags=["resources"])


@router.get("/projects/{project_id}/resources")
def list_resources(
    project_id: str,
    service: Annotated[ResourcesService, Depends(get_resources_service)],
) -> dict[str, list[ResourceResponse]]:
    return {"resources": service.list_resources(project_id)}


@router.get("/resources/{resource_id}/content")
def get_resource_content(
    resource_id: str,
    service: Annotated[ResourcesService, Depends(get_resources_service)],
) -> ResourceContentResponse:
    return service.get_resource_content(resource_id)


@router.post("/projects/{project_id}/resources/upload", status_code=status.HTTP_201_CREATED)
async def upload_resources(
    project_id: str,
    files: Annotated[list[UploadFile], File(...)],
    paths: Annotated[list[str], Form(...)],
    service: Annotated[ResourcesService, Depends(get_resources_service)],
) -> dict[str, list[ResourceResponse]]:
    return {"resources": await service.upload_resources(project_id=project_id, files=files, paths=paths)}
