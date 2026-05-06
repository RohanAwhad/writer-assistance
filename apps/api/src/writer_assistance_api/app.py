from fastapi import FastAPI

from writer_assistance_api.config import get_settings
from writer_assistance_api.db import create_all_tables, create_engine_and_session_factory
from writer_assistance_api.routes.health import router as health_router
from writer_assistance_api.routes.projects import router as projects_router


def create_app(*, database_url: str | None = None) -> FastAPI:
    settings = get_settings(database_url=database_url)
    engine, session_factory = create_engine_and_session_factory(settings.database_url)

    if settings.database_url.startswith("sqlite"):
        create_all_tables(engine)

    app = FastAPI(title="Writer Assistance API")
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.include_router(health_router)
    app.include_router(projects_router)
    return app
