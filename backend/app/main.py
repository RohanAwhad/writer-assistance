"""FastAPI application factory (R-001): /api/v1 routers, lifespan, error mapping."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import db
from app.api import projects, reports, rounds
from app.errors import ApiError

DEFAULT_DB_PATH = "data/writer-assistance.db"
ENV_DB_PATH = "WRITER_ASSISTANCE_DB"


def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(os.environ.get(ENV_DB_PATH, DEFAULT_DB_PATH))


def create_app(db_path: str | Path | None = None) -> FastAPI:
    resolved = _resolve_db_path(db_path)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        conn = db.connect(resolved)
        try:
            db.init_schema(conn)
        finally:
            conn.close()
        yield

    app = FastAPI(title="writer-assistance backend", lifespan=lifespan)
    app.state.writer_db_path = resolved
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(rounds.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")

    @app.exception_handler(ApiError)
    def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    return app


app = create_app()
