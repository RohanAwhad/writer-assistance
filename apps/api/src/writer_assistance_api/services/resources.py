from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from writer_assistance_api.db import get_session
from writer_assistance_api.models import Project, Resource
from writer_assistance_api.schemas.resources import ResourceResponse
from writer_assistance_api.storage import StorageDriver


class ResourcesService:
    def __init__(self, session: Session, storage: StorageDriver) -> None:
        self._session = session
        self._storage = storage

    async def upload_resources(
        self,
        *,
        project_id: str,
        files: list[UploadFile],
        paths: list[str],
    ) -> list[ResourceResponse]:
        project = self._session.scalar(select(Project).where(Project.id == project_id))
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        if len(files) != len(paths):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each file must include a path")

        resources: list[Resource] = []

        for upload_file, raw_path in zip(files, paths, strict=True):
            logical_path = _normalize_logical_path(raw_path)
            content = await upload_file.read()
            stored_object = self._storage.put_object(
                project_id=project_id,
                logical_path=logical_path,
                content=content,
            )
            timestamp = datetime.now(UTC)
            resource = Resource(
                id=str(uuid4()),
                project_id=project_id,
                logical_path=logical_path,
                original_filename=upload_file.filename or PurePosixPath(logical_path).name,
                storage_location=stored_object.storage_path,
                content_hash=stored_object.content_hash,
                upload_status="uploaded",
                created_at=timestamp,
            )
            self._session.add(resource)
            resources.append(resource)

        self._session.commit()

        return [ResourceResponse.model_validate(resource) for resource in resources]


def _normalize_logical_path(logical_path: str) -> str:
    normalized = logical_path.replace("\\", "/").strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logical path is required")

    if normalized.startswith("/") or normalized.endswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logical path must point to a markdown file",
        )

    path = PurePosixPath(normalized)
    if any(part in {".", ".."} for part in path.parts) or path.suffix.lower() != ".md":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logical path must point to a markdown file",
        )

    return path.as_posix()


def get_resources_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> ResourcesService:
    storage = cast(StorageDriver, request.app.state.storage)
    return ResourcesService(session=session, storage=storage)
