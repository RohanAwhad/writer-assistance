"""Provider-resolution unit tests (SD-20/SD-21, R-074): per-project mapping,
fresh + legacy defaults, per-provider lazy builds, no-fallback failure.

Offline: client construction never opens a connection; env is controlled via
monkeypatch so a configured provider resolves even while the other provider's
env is absent.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app import db
from app.ai import deepseek
from app.ai.vertex import VertexAIClient
from app.deps import get_ai_client_for_provider
from app.errors import ConfigError, NotFoundError
from app.services import projects

DEEPSEEK_MODEL = "deepseek-v4-flash"

VERTEX_ENV = {
    "ANTHROPIC_VERTEX_PROJECT_ID": "proj-123",
    "ANTHROPIC_MODEL": "claude-big",
    "ANTHROPIC_SMALL_FAST_MODEL": "claude-small",
    "GOOGLE_VERTEX_LOCATION": "us-east5",
    "VERTEX_ACCESS_TOKEN": "dummy-token",
}

ALL_PROVIDER_ENV = set(VERTEX_ENV) | {"DEEPSEEK_API_KEY", "DEEPSEEK_MODEL"}


@pytest.fixture(autouse=True)
def _isolated_env_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ALL_PROVIDER_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("app.deps._ai_clients", {})


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = db.connect(tmp_path / "resolution.db")
    db.init_schema(connection)
    yield connection
    connection.close()


def set_env(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_fresh_project_row_defaults_to_deepseek(conn: sqlite3.Connection) -> None:
    project = projects.create_project(conn, "Fresh")
    assert project.ai_provider == "deepseek"
    assert projects.get_ai_provider(conn, project.id) == "deepseek"


def test_set_project_provider_persists(conn: sqlite3.Connection) -> None:
    project = projects.create_project(conn, "Switchable")
    updated = projects.set_project_provider(conn, project.id, "vertex")
    assert updated.ai_provider == "vertex"
    assert updated.name == "Switchable"
    assert projects.get_ai_provider(conn, project.id) == "vertex"
    assert projects.get_project(conn, project.id).ai_provider == "vertex"
    assert projects.set_project_provider(conn, project.id, "deepseek").ai_provider == "deepseek"


def test_set_project_provider_missing_project_404(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError):
        projects.set_project_provider(conn, 99999, "vertex")
    with pytest.raises(NotFoundError):
        projects.get_ai_provider(conn, 99999)


def test_legacy_projects_rows_adopt_deepseek_on_schema_init(tmp_path: Path) -> None:
    connection = db.connect(tmp_path / "legacy.db")
    connection.execute(
        """CREATE TABLE projects (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT NOT NULL,
               created_at TEXT NOT NULL,
               updated_at TEXT NOT NULL
           )"""
    )
    ts = db.now_utc()
    connection.execute(
        "INSERT INTO projects (name, created_at, updated_at) VALUES ('Legacy', ?, ?)",
        (ts, ts),
    )
    connection.commit()
    db.init_schema(connection)
    legacy = projects.list_projects(connection)
    assert len(legacy) == 1
    assert legacy[0].name == "Legacy"
    assert legacy[0].ai_provider == "deepseek"
    db.init_schema(connection)
    assert projects.get_ai_provider(connection, legacy[0].id) == "deepseek"
    connection.close()


def test_resolver_builds_and_caches_per_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    set_env(monkeypatch, {"DEEPSEEK_API_KEY": "sk-test"})
    first = get_ai_client_for_provider("deepseek")
    assert isinstance(first, deepseek.DeepSeekAIClient)
    assert get_ai_client_for_provider("deepseek") is first


def test_deepseek_project_configured_while_vertex_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_env(monkeypatch, {"DEEPSEEK_API_KEY": "sk-test"})
    client = get_ai_client_for_provider("deepseek")
    assert isinstance(client, deepseek.DeepSeekAIClient)
    with pytest.raises(ConfigError) as excinfo:
        get_ai_client_for_provider("vertex")
    assert "ANTHROPIC_VERTEX_PROJECT_ID" in str(excinfo.value)


def test_vertex_project_unaffected_by_missing_deepseek_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_env(monkeypatch, VERTEX_ENV)
    client = get_ai_client_for_provider("vertex")
    assert isinstance(client, VertexAIClient)
    with pytest.raises(ConfigError) as excinfo:
        get_ai_client_for_provider("deepseek")
    assert "DEEPSEEK_API_KEY" in str(excinfo.value)
    assert "ANTHROPIC" not in str(excinfo.value)


def test_missing_selected_env_raises_config_error_with_no_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ConfigError) as excinfo:
        get_ai_client_for_provider("deepseek")
    assert "DEEPSEEK_API_KEY" in str(excinfo.value)
    with pytest.raises(ConfigError) as vertex_exc:
        get_ai_client_for_provider("vertex")
    assert "ANTHROPIC_VERTEX_PROJECT_ID" in str(vertex_exc.value)
    assert "DEEPSEEK_API_KEY" not in str(vertex_exc.value)


def test_unknown_provider_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        get_ai_client_for_provider("gemini")
