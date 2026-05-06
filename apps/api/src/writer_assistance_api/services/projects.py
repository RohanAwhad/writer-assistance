from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from writer_assistance_api.db import get_session
from writer_assistance_api.models import Project
from writer_assistance_api.schemas.projects import CreateProjectRequest, ProjectResponse


class ProjectsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_projects(self) -> list[ProjectResponse]:
        projects = self._session.scalars(select(Project).order_by(Project.created_at.desc())).all()
        return [ProjectResponse.model_validate(project) for project in projects]

    def create_project(self, payload: CreateProjectRequest) -> ProjectResponse:
        timestamp = datetime.now(UTC)
        project = Project(
            id=str(uuid4()),
            title=payload.title,
            created_at=timestamp,
            updated_at=timestamp,
        )

        self._session.add(project)
        self._session.commit()
        self._session.refresh(project)

        return ProjectResponse.model_validate(project)


def get_projects_service(
    session: Annotated[Session, Depends(get_session)],
) -> ProjectsService:
    return ProjectsService(session)
