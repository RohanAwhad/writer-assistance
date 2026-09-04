"""API tests: PUT /projects/{id}/provider + ai_provider payload surfacing (R-071, F13).

Provider switching and payload defaults run against the standard FakeAI harness
(no AI call is made by these endpoints); the legacy-row adoption test builds an
app over a pre-INT-007 database file.
"""

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app.main import create_app


def make_project(client: TestClient) -> int:
    response = client.post("/api/v1/projects", json={"name": "Provider test"})
    assert response.status_code == 201
    return int(response.json()["id"])


def test_fresh_project_payloads_surface_deepseek_default(client: TestClient) -> None:
    created = client.post("/api/v1/projects", json={"name": "Fresh"})
    assert created.status_code == 201
    body = created.json()
    project_id = int(body["id"])
    assert body["ai_provider"] == "deepseek"

    listed = client.get("/api/v1/projects").json()
    assert next(p for p in listed if p["id"] == project_id)["ai_provider"] == "deepseek"

    detail = client.get(f"/api/v1/projects/{project_id}").json()
    assert detail["ai_provider"] == "deepseek"


def test_put_provider_persists_and_returns_payload(client: TestClient) -> None:
    project_id = make_project(client)
    switched = client.put(
        f"/api/v1/projects/{project_id}/provider", json={"provider": "vertex"}
    )
    assert switched.status_code == 200
    assert switched.json()["ai_provider"] == "vertex"
    assert switched.json()["name"] == "Provider test"

    assert client.get(f"/api/v1/projects/{project_id}").json()["ai_provider"] == "vertex"
    listed = client.get("/api/v1/projects").json()
    assert next(p for p in listed if p["id"] == project_id)["ai_provider"] == "vertex"

    back = client.put(
        f"/api/v1/projects/{project_id}/provider", json={"provider": "deepseek"}
    )
    assert back.status_code == 200
    assert back.json()["ai_provider"] == "deepseek"


def test_put_provider_rejects_other_values(client: TestClient) -> None:
    project_id = make_project(client)
    for payload in (
        {"provider": "gemini"},
        {"provider": "DeepSeek"},
        {"provider": ""},
        {"provider": "vertex "},
        {},
    ):
        response = client.put(f"/api/v1/projects/{project_id}/provider", json=payload)
        assert response.status_code == 422, payload
    assert client.get(f"/api/v1/projects/{project_id}").json()["ai_provider"] == "deepseek"


def test_put_provider_unknown_project_is_404(client: TestClient) -> None:
    response = client.put("/api/v1/projects/999999/provider", json={"provider": "vertex"})
    assert response.status_code == 404


def test_rename_preserves_selected_provider(client: TestClient) -> None:
    project_id = make_project(client)
    client.put(f"/api/v1/projects/{project_id}/provider", json={"provider": "vertex"})
    renamed = client.put(f"/api/v1/projects/{project_id}", json={"name": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["ai_provider"] == "vertex"
    assert client.get(f"/api/v1/projects/{project_id}").json()["name"] == "Renamed"


def test_legacy_project_row_adopts_deepseek_and_can_switch(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """CREATE TABLE projects (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT NOT NULL,
               created_at TEXT NOT NULL,
               updated_at TEXT NOT NULL
           )"""
    )
    ts = db.now_utc()
    conn.execute(
        "INSERT INTO projects (name, created_at, updated_at) VALUES ('Legacy', ?, ?)",
        (ts, ts),
    )
    conn.commit()
    conn.close()

    app = create_app(db_path=str(db_path))
    with TestClient(app) as client:
        listed = client.get("/api/v1/projects").json()
        assert len(listed) == 1
        project_id = int(listed[0]["id"])
        assert listed[0]["name"] == "Legacy"
        assert listed[0]["ai_provider"] == "deepseek"
        assert client.get(f"/api/v1/projects/{project_id}").json()["ai_provider"] == "deepseek"

        switched = client.put(
            f"/api/v1/projects/{project_id}/provider", json={"provider": "vertex"}
        )
        assert switched.status_code == 200
        assert switched.json()["ai_provider"] == "vertex"
        assert client.get(f"/api/v1/projects/{project_id}").json()["ai_provider"] == "vertex"
