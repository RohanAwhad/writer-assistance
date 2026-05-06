from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from writer_assistance_api.db import get_session
from writer_assistance_api.models import Project, Resource
from writer_assistance_api.schemas.resources import ResourceContentResponse, ResourceResponse
from writer_assistance_api.storage import StorageDriver

LOGICAL_PATH_CONFLICT_CODE = "logical_path_conflict"
LOGICAL_PATH_CONFLICT_MESSAGE = "Logical paths must be unique within a project"


@dataclass(frozen=True)
class PendingUpload:
    logical_path: str
    original_filename: str
    content: bytes


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

        normalized_paths = [_normalize_logical_path(raw_path) for raw_path in paths]
        conflicting_paths = self._find_conflicting_paths(
            project_id=project_id,
            logical_paths=normalized_paths,
        )
        if conflicting_paths:
            raise _logical_path_conflict(conflicting_paths)

        pending_uploads = await _read_uploads(files=files, logical_paths=normalized_paths)
        written_storage_paths: list[str] = []
        resources: list[Resource] = []

        try:
            for pending_upload in pending_uploads:
                prepared_object = self._storage.prepare_object(
                    project_id=project_id,
                    logical_path=pending_upload.logical_path,
                    content=pending_upload.content,
                )
                written_storage_paths.append(prepared_object.storage_path)
                stored_object = self._storage.put_object(
                    project_id=project_id,
                    logical_path=pending_upload.logical_path,
                    content=pending_upload.content,
                    stored_object=prepared_object,
                )
                written_storage_paths[-1] = stored_object.storage_path
                resources.append(
                    Resource(
                        id=str(uuid4()),
                        project_id=project_id,
                        logical_path=pending_upload.logical_path,
                        original_filename=pending_upload.original_filename,
                        storage_location=stored_object.storage_path,
                        content_hash=stored_object.content_hash,
                        upload_status="uploaded",
                        created_at=datetime.now(UTC),
                    )
                )

            self._session.add_all(resources)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            self._cleanup_written_objects(written_storage_paths)
            if _is_logical_path_conflict_error(exc):
                conflicts_after_rollback = self._find_conflicting_paths(
                    project_id=project_id,
                    logical_paths=normalized_paths,
                )
                raise _logical_path_conflict(conflicts_after_rollback or normalized_paths) from exc
            raise
        except Exception:
            self._session.rollback()
            self._cleanup_written_objects(written_storage_paths)
            raise

        return [ResourceResponse.model_validate(resource) for resource in resources]

    def list_resources(self, project_id: str) -> list[ResourceResponse]:
        project = self._session.scalar(select(Project).where(Project.id == project_id))
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        resources = list(
            self._session.scalars(
                select(Resource).where(Resource.project_id == project_id).order_by(Resource.logical_path)
            )
        )
        return [ResourceResponse.model_validate(resource) for resource in resources]

    def get_resource_content(self, resource_id: str) -> ResourceContentResponse:
        resource = self._session.get(Resource, resource_id)
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        try:
            markdown = self._storage.read_object(resource.storage_location).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Resource content is not valid UTF-8 markdown",
            ) from exc
        return ResourceContentResponse(resource_id=resource.id, markdown=markdown)

    def _find_conflicting_paths(self, *, project_id: str, logical_paths: list[str]) -> list[str]:
        duplicate_paths = {
            logical_path for logical_path, count in Counter(logical_paths).items() if count > 1
        }
        existing_paths = set(
            self._session.scalars(
                select(Resource.logical_path).where(
                    Resource.project_id == project_id,
                    Resource.logical_path.in_(logical_paths),
                )
            )
        )
        return sorted(duplicate_paths | existing_paths)

    def _cleanup_written_objects(self, storage_paths: list[str]) -> None:
        for storage_path in reversed(storage_paths):
            try:
                self._storage.delete_object(storage_path)
            except OSError:
                continue


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


async def _read_uploads(*, files: list[UploadFile], logical_paths: list[str]) -> list[PendingUpload]:
    pending_uploads: list[PendingUpload] = []
    for upload_file, logical_path in zip(files, logical_paths, strict=True):
        pending_uploads.append(
            PendingUpload(
                logical_path=logical_path,
                original_filename=upload_file.filename or PurePosixPath(logical_path).name,
                content=await upload_file.read(),
            )
        )
    return pending_uploads


def _logical_path_conflict(paths: list[str]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": LOGICAL_PATH_CONFLICT_CODE,
            "message": LOGICAL_PATH_CONFLICT_MESSAGE,
            "paths": sorted(set(paths)),
        },
    )


def _is_logical_path_conflict_error(error: IntegrityError) -> bool:
    message = str(error.orig).lower()
    return "unique constraint failed: resources.project_id, resources.logical_path" in message or (
        "ux_resources_project_logical_path" in message
    )


def get_resources_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> ResourcesService:
    storage = cast(StorageDriver, request.app.state.storage)
    return ResourcesService(session=session, storage=storage)
