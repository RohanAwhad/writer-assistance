"""Shared FastAPI dependencies (db connection, AI client)."""

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from app import db
from app.ai.client import AIClient
from app.ai.vertex import build_ai_client

_ai_client: AIClient | None = None


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.writer_db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_ai_client() -> AIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = build_ai_client()
    return _ai_client


DbDep = Annotated[sqlite3.Connection, Depends(get_db)]
AiDep = Annotated[AIClient, Depends(get_ai_client)]
