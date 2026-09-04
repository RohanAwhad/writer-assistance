"""Transport-failure mapping at the API boundary (R-074 parenthetical; M1Fn-02).

Provider transports that raise — anthropic SDK exceptions on vertex, raw httpx
network exceptions on deepseek — surface as 502 AIError responses naming the
failure instead of uncaught 500s, while config errors (missing env) stay 503
and entity errors stay 404 (M1Fn-01 precedence untouched). All offline: the
transport layers are monkeypatched to raise before any network I/O.
"""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import httpx2
import pytest
from anthropic import APIConnectionError, APIError, AuthenticationError
from fastapi.testclient import TestClient

from app.ai import deepseek, vertex
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

DUMMY_VERTEX_ENV = {
    "ANTHROPIC_VERTEX_PROJECT_ID": "proj-test",
    "ANTHROPIC_MODEL": "model-big",
    "ANTHROPIC_SMALL_FAST_MODEL": "model-small",
    "GOOGLE_VERTEX_LOCATION": "us-east5",
    "VERTEX_ACCESS_TOKEN": "dummy-token",
}

DUMMY_DEEPSEEK_ENV = {
    "DEEPSEEK_API_KEY": "sk-test",
    "DEEPSEEK_MODEL": "deepseek-test",
}


@pytest.fixture
def configured_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    for name in PROVIDER_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    _ai_clients.clear()
    app = create_app(db_path=str(tmp_path / "transport.db"))
    with TestClient(app) as client:
        yield client


def _set_env(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def _patch_vertex_sdk(monkeypatch: pytest.MonkeyPatch, error: APIError) -> None:
    """Replace app.ai.vertex.AnthropicVertex with a stand-in raising ``error``."""

    class _Messages:
        def create(self, **kwargs: object) -> object:
            raise error

    class _Client:
        def __init__(self, **kwargs: object) -> None:
            self.messages = _Messages()

    monkeypatch.setattr(vertex, "AnthropicVertex", _Client)


def _patch_deepseek_transport(monkeypatch: pytest.MonkeyPatch, error: httpx.HTTPError) -> None:
    """Replace deepseek's httpx.Client with a stand-in whose post raises ``error``.

    HTTPError stays the real class: the chat boundary's ``except httpx.HTTPError``
    is evaluated lazily against the module's httpx name.
    """

    class _Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            raise error

    monkeypatch.setattr(
        deepseek, "httpx", SimpleNamespace(Client=_Client, HTTPError=httpx.HTTPError)
    )


def _patch_deepseek_transport_response(
    monkeypatch: pytest.MonkeyPatch, response: httpx.Response
) -> None:
    """Replace deepseek's httpx.Client with a stand-in whose post returns ``response``."""

    class _Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            return response

    monkeypatch.setattr(
        deepseek, "httpx", SimpleNamespace(Client=_Client, HTTPError=httpx.HTTPError)
    )


def test_vertex_sdk_connection_error_maps_to_502(
    configured_client: TestClient,
    sample_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, DUMMY_VERTEX_ENV)
    _patch_vertex_sdk(
        monkeypatch,
        APIConnectionError(
            message="connection failed test",
            request=httpx2.Request("POST", "https://api.anthropic.com"),
        ),
    )
    project_id, files = imported_project(configured_client, sample_tree)
    switched = configured_client.put(
        f"/api/v1/projects/{project_id}/provider", json={"provider": "vertex"}
    )
    assert switched.status_code == 200
    response = configured_client.post(
        f"/api/v1/resources/{files['alpha.md']}/lens-proposals", json={}
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "vertex AI call failed" in detail
    assert "connection failed test" in detail


def test_vertex_sdk_status_error_maps_to_502(
    configured_client: TestClient,
    sample_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, DUMMY_VERTEX_ENV)
    request = httpx2.Request("POST", "https://api.anthropic.com")
    _patch_vertex_sdk(
        monkeypatch,
        AuthenticationError(
            message="401 unauthorized test",
            response=httpx2.Response(401, request=request),
            body=None,
        ),
    )
    project_id, files = imported_project(configured_client, sample_tree)
    switched = configured_client.put(
        f"/api/v1/projects/{project_id}/provider", json={"provider": "vertex"}
    )
    assert switched.status_code == 200
    response = configured_client.post(
        f"/api/v1/resources/{files['alpha.md']}/lens-proposals", json={}
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "vertex AI call failed" in detail
    assert "401 unauthorized test" in detail


def test_deepseek_httpx_connect_error_maps_to_502(
    configured_client: TestClient,
    sample_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, DUMMY_DEEPSEEK_ENV)
    _patch_deepseek_transport(
        monkeypatch,
        httpx.ConnectError(
            "connection refused test", request=httpx.Request("POST", "https://api.deepseek.com")
        ),
    )
    project_id, files = imported_project(configured_client, sample_tree)
    response = configured_client.post(
        f"/api/v1/resources/{files['alpha.md']}/lens-proposals", json={}
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "deepseek API request failed" in detail
    assert "connection refused test" in detail


def test_deepseek_httpx_timeout_maps_to_502(
    configured_client: TestClient,
    sample_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, DUMMY_DEEPSEEK_ENV)
    _patch_deepseek_transport(
        monkeypatch,
        httpx.ReadTimeout(
            "timed out test", request=httpx.Request("POST", "https://api.deepseek.com")
        ),
    )
    project_id, files = imported_project(configured_client, sample_tree)
    response = configured_client.post(
        f"/api/v1/resources/{files['alpha.md']}/lens-proposals", json={}
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "deepseek API request failed" in detail
    assert "timed out test" in detail


def test_deepseek_non_json_body_maps_to_502(
    configured_client: TestClient,
    sample_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, DUMMY_DEEPSEEK_ENV)
    _patch_deepseek_transport_response(monkeypatch, httpx.Response(200, content=b"not json"))
    project_id, files = imported_project(configured_client, sample_tree)
    response = configured_client.post(
        f"/api/v1/resources/{files['alpha.md']}/lens-proposals", json={}
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "deepseek API response is not valid JSON" in detail
    assert "not json" in detail
