"""UC-18-equivalent failure behavior at the API boundary (R-074, spec SD-16).

A real app (no FakeAI override) with the provider env stripped: an AI call for a
project whose selected provider is unconfigured fails fast with a 503 ConfigError
naming the missing env var, and never falls back to the other provider. All
offline — the failure happens at client build time, before any transport call.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.deps import _ai_clients
from app.main import create_app
from tests.conftest import imported_project

PROVIDER_ENV_NAMES = (
    "ANTHROPIC_VERTEX_PROJECT_ID",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
    "GOOGLE_VERTEX_LOCATION",
    "VERTEX_LOCATION",
    "VERTEX_ACCESS_TOKEN",
    "ANTHROPIC_BASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
)


@pytest.fixture
def unconfigured_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    for name in PROVIDER_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    _ai_clients.clear()
    app = create_app(db_path=str(tmp_path / "uc18.db"))
    with TestClient(app) as client:
        yield client


def test_deepseek_selected_missing_key_fails_503_naming_var(
    unconfigured_client: TestClient, sample_tree: Path
) -> None:
    project_id, files = imported_project(unconfigured_client, sample_tree)
    assert (
        unconfigured_client.get(f"/api/v1/projects/{project_id}").json()["ai_provider"]
        == "deepseek"
    )
    response = unconfigured_client.post(
        f"/api/v1/resources/{files['alpha.md']}/lens-proposals", json={}
    )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "DEEPSEEK_API_KEY" in detail
    assert "ANTHROPIC" not in detail


def test_vertex_selected_missing_env_fails_503_naming_vertex_vars(
    unconfigured_client: TestClient, sample_tree: Path
) -> None:
    project_id, files = imported_project(unconfigured_client, sample_tree)
    switched = unconfigured_client.put(
        f"/api/v1/projects/{project_id}/provider", json={"provider": "vertex"}
    )
    assert switched.status_code == 200
    response = unconfigured_client.post(
        f"/api/v1/resources/{files['alpha.md']}/lens-proposals", json={}
    )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "ANTHROPIC_VERTEX_PROJECT_ID" in detail
    assert "DEEPSEEK_API_KEY" not in detail


def test_missing_entity_is_404_not_503(
    unconfigured_client: TestClient, sample_tree: Path
) -> None:
    _project_id, _files = imported_project(unconfigured_client, sample_tree)
    response = unconfigured_client.post("/api/v1/resources/999999/lens-proposals", json={})
    assert response.status_code == 404
