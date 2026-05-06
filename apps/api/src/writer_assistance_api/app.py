from fastapi import FastAPI

from writer_assistance_api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Writer Assistance API")
    app.include_router(health_router)
    return app
