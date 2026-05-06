from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[4] / "data" / "app.db"
DEFAULT_DATABASE_URL = f"sqlite+pysqlite:///{DEFAULT_DATABASE_PATH}"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL


def get_settings(*, database_url: str | None = None) -> Settings:
    if database_url is not None:
        return Settings(database_url=database_url)

    environment_database_url = os.getenv("WRITER_ASSISTANCE_DATABASE_URL")
    if environment_database_url is not None:
        return Settings(database_url=environment_database_url)

    return Settings(database_url=DEFAULT_DATABASE_URL)
