"""FastAPI application factory (R-001): /api/v1 routers, lifespan, error mapping.

INT-006 wiring (SD-24): the gate is off by default; the module-level ``app``
below resolves AUTH_API_KEY from the environment after load_dotenv and passes it
in, so uvicorn runs are gated exactly when the key is present. Static serving of
the built SPA (R-076) mounts when the dist directory exists at creation.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from app import auth, db
from app.api import projects, reports, rounds
from app.errors import ApiError

load_dotenv(override=True)

DEFAULT_DB_PATH = "data/writer-assistance.db"
ENV_DB_PATH = "WRITER_ASSISTANCE_DB"
ENV_AUTH_KEY = "AUTH_API_KEY"
_SPA_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_SPA_FALLBACK_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(os.environ.get(ENV_DB_PATH, DEFAULT_DB_PATH))


def _env_auth_key() -> str | None:
    """AUTH_API_KEY from the environment; empty/unset means gate off (SD-24)."""
    key = os.environ.get(ENV_AUTH_KEY)
    return key if key else None


def _resolve_static_dir(static_dir: str | Path | None) -> Path | None:
    """The dist directory to serve, or None when absent (R-076, SD-25).

    An explicit ``static_dir`` that is not a directory means no mount, keeping
    test factories hermetic; the default is ``<backend>/../frontend/dist``.
    """
    if static_dir is not None:
        candidate = Path(static_dir)
    else:
        candidate = _SPA_DIST
    return candidate if candidate.is_dir() else None


def _install_spa_fallback(app: FastAPI, static_dir: Path) -> None:
    """Serve the built SPA (R-076): files on disk, else index.html for GET.

    Registered last, so real /api/v1 routes win; /api/* paths that reach the
    fallback (unknown API routes) keep the JSON 404 of a gate-passing request
    and are never swallowed by index.html. Non-GET unknown paths also 404, as
    they do without a static mount.
    """

    @app.api_route("/{full_path:path}", methods=_SPA_FALLBACK_METHODS, include_in_schema=False)
    def spa_fallback(request: Request, full_path: str) -> Response:
        if request.method != "GET":
            raise HTTPException(status_code=404)
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        root = static_dir.resolve()
        candidate = (root / full_path).resolve()
        if not candidate.is_relative_to(root):
            raise HTTPException(status_code=404)
        if candidate.is_file():
            return FileResponse(candidate)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404)


def create_app(
    db_path: str | Path | None = None,
    *,
    auth_key: str | None = None,
    static_dir: str | Path | None = None,
) -> FastAPI:
    resolved = _resolve_db_path(db_path)
    resolved_static = _resolve_static_dir(static_dir)

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
    if auth_key:
        auth.install_gate(app, auth_key)
    if resolved_static is not None:
        _install_spa_fallback(app, resolved_static)

    @app.exception_handler(ApiError)
    def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    return app


app = create_app(auth_key=_env_auth_key())
