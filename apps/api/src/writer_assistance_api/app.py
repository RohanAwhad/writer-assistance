from pathlib import Path

from fastapi import FastAPI

from writer_assistance_api.config import get_settings
from writer_assistance_api.db import (
    create_all_tables,
    create_engine_and_session_factory,
    ensure_sqlite_resource_logical_path_uniqueness,
)
from writer_assistance_api.disk_storage import DiskStorage
from writer_assistance_api.routes.health import router as health_router
from writer_assistance_api.routes.projects import router as projects_router
from writer_assistance_api.routes.resources import router as resources_router

DEFAULT_STORAGE_ROOT = Path(__file__).resolve().parents[4] / "data" / "storage"


def create_app(*, database_url: str | None = None, storage_root: Path | None = None) -> FastAPI:
    settings = get_settings(database_url=database_url)
    engine, session_factory = create_engine_and_session_factory(settings.database_url)
    resolved_storage_root = storage_root or DEFAULT_STORAGE_ROOT
    resolved_storage_root.mkdir(parents=True, exist_ok=True)

    if settings.database_url.startswith("sqlite"):
        create_all_tables(engine)
        ensure_sqlite_resource_logical_path_uniqueness(engine)

    app = FastAPI(title="Writer Assistance API")
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.storage = DiskStorage(resolved_storage_root)

    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(resources_router)
    return app
