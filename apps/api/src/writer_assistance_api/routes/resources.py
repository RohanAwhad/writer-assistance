from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from writer_assistance_api.schemas.resources import ResourceResponse
from writer_assistance_api.services.resources import ResourcesService, get_resources_service

router = APIRouter(tags=["resources"])


@router.post("/projects/{project_id}/resources/upload", status_code=status.HTTP_201_CREATED)
async def upload_resources(
    project_id: str,
    files: Annotated[list[UploadFile], File(...)],
    paths: Annotated[list[str], Form(...)],
    service: Annotated[ResourcesService, Depends(get_resources_service)],
) -> dict[str, list[ResourceResponse]]:
    return {"resources": await service.upload_resources(project_id=project_id, files=files, paths=paths)}
