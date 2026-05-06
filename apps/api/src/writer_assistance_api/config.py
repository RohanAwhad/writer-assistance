from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[4] / "data" / "app.db"
DEFAULT_DATABASE_URL = f"sqlite+pysqlite:///{DEFAULT_DATABASE_PATH}"
DEFAULT_STORAGE_ROOT = Path(__file__).resolve().parents[4] / "data" / "storage"
AiMode = Literal["live", "smoke"]


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    storage_root: Path = DEFAULT_STORAGE_ROOT
    ai_mode: AiMode = "live"
    anthropic_vertex_project_id: str | None = None
    cloud_ml_region: str | None = None


def get_settings(
    *,
    database_url: str | None = None,
    storage_root: Path | None = None,
) -> Settings:
    resolved_database_url = database_url
    if resolved_database_url is None:
        resolved_database_url = os.getenv("WRITER_ASSISTANCE_DATABASE_URL")
    if resolved_database_url is None:
        resolved_database_url = DEFAULT_DATABASE_URL

    resolved_storage_root = storage_root
    if resolved_storage_root is None:
        storage_root_env = os.getenv("WRITER_ASSISTANCE_STORAGE_ROOT")
        if storage_root_env is not None:
            resolved_storage_root = Path(storage_root_env)
    if resolved_storage_root is None:
        resolved_storage_root = DEFAULT_STORAGE_ROOT

    return Settings(
        database_url=resolved_database_url,
        storage_root=resolved_storage_root,
        ai_mode=_resolve_ai_mode(),
        anthropic_vertex_project_id=os.getenv("ANTHROPIC_VERTEX_PROJECT_ID"),
        cloud_ml_region=os.getenv("CLOUD_ML_REGION"),
    )


def _resolve_ai_mode() -> AiMode:
    raw_ai_mode = os.getenv("WRITER_ASSISTANCE_AI_MODE", "live").strip().lower()
    if raw_ai_mode == "live":
        return "live"
    if raw_ai_mode == "smoke":
        return "smoke"
    raise RuntimeError("WRITER_ASSISTANCE_AI_MODE must be either 'live' or 'smoke'")
