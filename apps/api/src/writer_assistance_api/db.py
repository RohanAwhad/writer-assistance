from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from writer_assistance_api.models import Base


def create_engine_and_session_factory(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    engine_options: dict[str, Any] = {}

    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}

        if database_url.endswith(":memory:"):
            engine_options["poolclass"] = StaticPool

    engine = create_engine(database_url, **engine_options)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, session_factory


def create_all_tables(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)


def get_session(request: Request) -> Iterator[Session]:
    session_factory = cast(sessionmaker[Session], request.app.state.session_factory)
    with session_factory() as session:
        yield session
