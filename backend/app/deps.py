"""Shared FastAPI dependencies (db connection, per-project AI client resolution).

Provider resolution per SD-21: an AI endpoint's entity id (resource, round, or
report block) maps to the project it belongs to, and the project's stored
``ai_provider`` value selects the client (R-071). Clients are built lazily and
cached per provider (today's singleton generalized per provider); a provider is
only built when a project selects it, so an unconfigured provider can never
break calls for projects on the other one — its ConfigError (503) surfaces
unchanged through the app's ApiError handler (R-074).
"""

import sqlite3
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Request

from app import db
from app.ai.client import AIClient
from app.ai.deepseek import build_ai_client as build_deepseek_client
from app.ai.vertex import build_ai_client as build_vertex_client
from app.errors import NotFoundError
from app.services import projects as projects_service
from app.services import reports as reports_service
from app.services import resources as resources_service
from app.services import rounds as rounds_service


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.writer_db_path)
    try:
        yield conn
    finally:
        conn.close()


DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


def get_ai_client_for_provider(provider: str) -> AIClient:
    """Cached client for a provider; built lazily from the process env.

    A build-time ConfigError for the selected provider's missing env var (e.g.
    DEEPSEEK_API_KEY) propagates to the caller as a 503 — there is no fallback
    path to the other provider (R-074).
    """
    if provider not in _ai_clients:
        builder = _PROVIDER_BUILDERS.get(provider)
        if builder is None:
            raise ValueError(f"unknown AI provider: {provider}")
        _ai_clients[provider] = builder()
    return _ai_clients[provider]


def _ai_client_for_project(db: sqlite3.Connection, project_id: int) -> AIClient:
    return get_ai_client_for_provider(projects_service.get_ai_provider(db, project_id))


def get_ai_client_for_resource(db: DbDep, resource_id: int) -> AIClient:
    """The client for the project the resource (file doc) belongs to."""
    doc = resources_service.require_file_doc(db, resource_id)
    return _ai_client_for_project(db, int(doc["project_id"]))


def get_ai_client_for_round(db: DbDep, round_id: int) -> AIClient:
    """The client for the project the reading round belongs to."""
    round_row = rounds_service.require_round(db, round_id)
    return _ai_client_for_project(db, int(round_row["project_id"]))


def get_ai_client_for_block(db: DbDep, block_id: int) -> AIClient:
    """The client for the project owning the report block (block -> report -> round)."""
    row = db.execute("SELECT report_id FROM report_blocks WHERE id = ?", (block_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"report block {block_id} not found")
    report = reports_service.require_report(db, int(row["report_id"]))
    round_row = rounds_service.require_round(db, int(report["round_id"]))
    return _ai_client_for_project(db, int(round_row["project_id"]))


_ai_clients: dict[str, AIClient] = {}

_PROVIDER_BUILDERS: dict[str, Callable[[], AIClient]] = {
    "vertex": build_vertex_client,
    "deepseek": build_deepseek_client,
}


ResourceAiDep = Annotated[AIClient, Depends(get_ai_client_for_resource)]
RoundAiDep = Annotated[AIClient, Depends(get_ai_client_for_round)]
BlockAiDep = Annotated[AIClient, Depends(get_ai_client_for_block)]
