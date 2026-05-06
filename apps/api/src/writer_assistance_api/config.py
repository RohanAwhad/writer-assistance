from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[4] / "data" / "app.db"
DEFAULT_DATABASE_URL = f"sqlite+pysqlite:///{DEFAULT_DATABASE_PATH}"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    anthropic_vertex_project_id: str | None = None
    cloud_ml_region: str | None = None


def get_settings(*, database_url: str | None = None) -> Settings:
    resolved_database_url = database_url
    if resolved_database_url is None:
        resolved_database_url = os.getenv("WRITER_ASSISTANCE_DATABASE_URL")
    if resolved_database_url is None:
        resolved_database_url = DEFAULT_DATABASE_URL

    return Settings(
        database_url=resolved_database_url,
        anthropic_vertex_project_id=os.getenv("ANTHROPIC_VERTEX_PROJECT_ID"),
        cloud_ml_region=os.getenv("CLOUD_ML_REGION"),
    )
