"""INT-006 auth-gate + static-serving API tests (R-075/R-076; spec §11.1).

Two app-instance shapes per SD-24: gate-off (plain ``create_app()``) and gate-on
(``create_app(auth_key=...)``). All instances here pass an explicit ``static_dir``
so the rows are hermetic regardless of whether frontend/dist exists in the repo.
"""

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import SESSION_COOKIE, SESSION_TTL_SECONDS, make_session_value
from app.main import create_app

KEY = "test-gate-key"
UNAUTHENTICATED = "authentication required"
DIST_INDEX = "<!doctype html><html><body>SPA index</body></html>\n"
DIST_ASSET = b"export const app = 1;\n"


def make_app(
    tmp_path: Path,
    *,
    auth_key: str | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    return create_app(
        db_path=str(tmp_path / "test.db"),
        auth_key=auth_key,
        static_dir=str(static_dir) if static_dir is not None else str(tmp_path / "absent"),
    )


@pytest.fixture
def gate_client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(make_app(tmp_path, auth_key=KEY)) as client:
        yield client


@pytest.fixture
def open_client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(make_app(tmp_path)) as client:
        yield client


@pytest.fixture
def dist_dir(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(DIST_INDEX, encoding="utf-8")
    (dist / "assets" / "app-abc123.js").write_bytes(DIST_ASSET)
    return dist


def login(client: TestClient, key: str = KEY) -> None:
    response = client.post("/login", data={"key": key}, follow_redirects=False)
    assert response.status_code == 302, response.text
    assert response.headers["location"] == "/"


def with_cookie_header(value: str) -> dict[str, str]:
    return {"cookie": f"{SESSION_COOKIE}={value}"}


# --- R-075 gate-on rows ---------------------------------------------------------


def test_login_page_served_when_gate_on(gate_client: TestClient) -> None:
    response = gate_client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert '<form method="post" action="/login">' in body
    assert 'name="key"' in body
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in body


def test_wrong_key_401_no_cookie_no_session(gate_client: TestClient) -> None:
    response = gate_client.post("/login", data={"key": "wrong-key"}, follow_redirects=False)
    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    assert "login-error" in response.text
    assert gate_client.get("/api/v1/projects").status_code == 401


def test_right_key_sets_cookie_and_redirects(gate_client: TestClient) -> None:
    response = gate_client.post("/login", data={"key": KEY}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"
    cookie = response.headers["set-cookie"].lower()
    assert "wa_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "secure" not in cookie
    assert f"max-age={SESSION_TTL_SECONDS}" in cookie


def test_api_without_session_401_json(gate_client: TestClient) -> None:
    response = gate_client.get("/api/v1/projects")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": UNAUTHENTICATED}


def test_api_with_session_200(gate_client: TestClient) -> None:
    assert gate_client.get("/api/v1/projects").status_code == 401
    login(gate_client)
    assert gate_client.get("/api/v1/projects").status_code == 200


def test_non_api_paths_without_session_redirect_to_login(gate_client: TestClient) -> None:
    for path in ("/", "/assets/app-abc123.js", "/some/deep/spa/route"):
        response = gate_client.get(path, follow_redirects=False)
        assert response.status_code == 302, path
        assert response.headers["location"] == "/login", path


def test_login_page_redirects_when_session_valid(gate_client: TestClient) -> None:
    login(gate_client)
    response = gate_client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_cookie_secure_when_x_forwarded_proto_https(gate_client: TestClient) -> None:
    response = gate_client.post(
        "/login",
        data={"key": KEY},
        headers={"X-Forwarded-Proto": "https"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "secure" in response.headers["set-cookie"].lower()


def test_tampered_cookie_rejected(gate_client: TestClient) -> None:
    value = make_session_value(KEY)
    tampered = value[:-2] + ("0" if value[-2] != "0" else "1") + value[-1]
    response = gate_client.get("/api/v1/projects", headers=with_cookie_header(tampered))
    assert response.status_code == 401


def test_expired_cookie_rejected(gate_client: TestClient) -> None:
    expired = make_session_value(KEY, now=int(time.time()) - SESSION_TTL_SECONDS - 60)
    response = gate_client.get("/api/v1/projects", headers=with_cookie_header(expired))
    assert response.status_code == 401


def test_logout_clears_session(gate_client: TestClient) -> None:
    login(gate_client)
    response = gate_client.post("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"
    assert gate_client.get("/api/v1/projects").status_code == 401


def test_rotated_key_invalidates_cookie(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path, auth_key=KEY + "-rotated")) as rotated:
        response = rotated.get(
            "/api/v1/projects", headers=with_cookie_header(make_session_value(KEY))
        )
        assert response.status_code == 401


def test_empty_auth_key_is_gate_off(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path, auth_key="")) as client:
        assert client.get("/api/v1/projects").status_code == 200
        assert client.get("/login").status_code == 404


# --- R-075 gate-off rows --------------------------------------------------------


def test_gate_off_exposes_no_login_surface(open_client: TestClient) -> None:
    assert open_client.get("/login").status_code == 404
    assert open_client.post("/login", data={"key": KEY}).status_code == 404
    assert open_client.post("/logout").status_code == 404
    assert open_client.get("/api/v1/projects").status_code == 200


# --- R-076 static-serving rows --------------------------------------------------


def test_static_serving_index_asset_fallback(tmp_path: Path, dist_dir: Path) -> None:
    with TestClient(make_app(tmp_path, auth_key=KEY, static_dir=dist_dir)) as client:
        login(client)
        index = client.get("/")
        assert index.status_code == 200
        assert index.text == DIST_INDEX
        asset = client.get("/assets/app-abc123.js")
        assert asset.status_code == 200
        assert asset.content == DIST_ASSET
        deep = client.get("/workspace/1/some/route")
        assert deep.status_code == 200
        assert deep.text == DIST_INDEX


def test_unknown_api_route_404_json_not_index(tmp_path: Path, dist_dir: Path) -> None:
    with TestClient(make_app(tmp_path, auth_key=KEY, static_dir=dist_dir)) as client:
        login(client)
        response = client.get("/api/v1/does-not-exist")
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Not Found"}
        assert DIST_INDEX not in response.text


def test_static_paths_sit_behind_gate(tmp_path: Path, dist_dir: Path) -> None:
    with TestClient(make_app(tmp_path, auth_key=KEY, static_dir=dist_dir)) as client:
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/login"
        assert client.get("/assets/app-abc123.js", follow_redirects=False).status_code == 302


def test_path_traversal_outside_dist_404(tmp_path: Path, dist_dir: Path) -> None:
    with TestClient(make_app(tmp_path, auth_key=KEY, static_dir=dist_dir)) as client:
        login(client)
        response = client.get("/assets/%2e%2e/%2e%2e/%2e%2e/etc/passwd")
        assert response.status_code == 404


def test_no_dist_dir_serves_api_only(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path, auth_key=KEY)) as client:
        login(client)
        assert client.get("/api/v1/projects").status_code == 200
        assert client.get("/").status_code == 404
        assert client.get("/some/deep/route").status_code == 404
