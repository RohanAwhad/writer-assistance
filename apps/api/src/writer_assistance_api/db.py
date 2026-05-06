from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

from fastapi import Request
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from writer_assistance_api.models import Base

RESOURCE_LOGICAL_PATH_INDEX_NAME = "ux_resources_project_logical_path"
SQLITE_DUPLICATE_LOGICAL_PATHS_MESSAGE = (
    "SQLite resources table contains duplicate logical paths. "
    "Remove duplicates or recreate the local database before continuing."
)


def create_engine_and_session_factory(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    engine_options: dict[str, Any] = {}

    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
        database_path = make_url(database_url).database

        if database_path is not None and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        if database_url.endswith(":memory:"):
            engine_options["poolclass"] = StaticPool

    engine = create_engine(database_url, **engine_options)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, session_factory


def create_all_tables(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)


def ensure_sqlite_resource_logical_path_uniqueness(engine: Engine) -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "resources" not in inspector.get_table_names():
            return

        existing_indexes = {index["name"] for index in inspector.get_indexes("resources")}
        if RESOURCE_LOGICAL_PATH_INDEX_NAME in existing_indexes:
            return

        duplicate_row = connection.execute(
            text(
                """
                SELECT project_id, logical_path
                FROM resources
                GROUP BY project_id, logical_path
                HAVING COUNT(*) > 1
                LIMIT 1
                """
            )
        ).first()
        if duplicate_row is not None:
            raise RuntimeError(SQLITE_DUPLICATE_LOGICAL_PATHS_MESSAGE)

        connection.execute(
            text(
                "CREATE UNIQUE INDEX ux_resources_project_logical_path "
                "ON resources (project_id, logical_path)"
            )
        )


def get_session(request: Request) -> Iterator[Session]:
    session_factory = cast(sessionmaker[Session], request.app.state.session_factory)
    with session_factory() as session:
        yield session
