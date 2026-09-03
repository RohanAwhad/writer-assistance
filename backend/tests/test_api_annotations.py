"""API tests: annotations against snapshots (F2, R-012)."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import ALPHA_CONTENT, MARKER, imported_project


def _alpha_offsets() -> tuple[int, int]:
    start = ALPHA_CONTENT.index(MARKER)
    return start, start + len(MARKER)


def test_highlight_and_note_lifecycle(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    start, end = _alpha_offsets()

    created = client.post(
        f"/api/v1/resources/{alpha_id}/highlights",
        json={"start_offset": start, "end_offset": end},
    )
    assert created.status_code == 201
    highlight = created.json()
    assert highlight["kind"] == "highlight"
    assert highlight["doc_id"] == alpha_id

    listed_doc = client.get(f"/api/v1/resources/{alpha_id}").json()
    assert listed_doc["content"] == ALPHA_CONTENT

    updated = client.put(
        f"/api/v1/annotations/{highlight['id']}",
        json={"content": "The phrase I care about."},
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "The phrase I care about."

    note = client.post(
        f"/api/v1/resources/{alpha_id}/notes",
        json={"content": "A thought about alpha.", "start_offset": start, "end_offset": end},
    )
    assert note.status_code == 201
    assert note.json()["kind"] == "note"
    assert note.json()["start_offset"] == start

    detached_note = client.post(
        f"/api/v1/resources/{alpha_id}/notes",
        json={"content": "Unanchored thought."},
    )
    assert detached_note.status_code == 201
    assert detached_note.json()["start_offset"] is None

    retitled = client.put(
        f"/api/v1/annotations/{note.json()['id']}", json={"content": "Edited thought."}
    )
    assert retitled.status_code == 200
    assert retitled.json()["content"] == "Edited thought."

    assert client.delete(f"/api/v1/annotations/{highlight['id']}").status_code == 204
    assert client.get(f"/api/v1/resources/{alpha_id}").json()["content"] == ALPHA_CONTENT
    assert client.delete(f"/api/v1/annotations/{note.json()['id']}").status_code == 204


def test_annotation_validation(client: TestClient, sample_tree: Path) -> None:
    _project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    start, end = _alpha_offsets()

    assert (
        client.post(
            f"/api/v1/resources/{alpha_id}/highlights",
            json={"start_offset": end, "end_offset": start},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/resources/{alpha_id}/highlights",
            json={"start_offset": start, "end_offset": len(ALPHA_CONTENT) + 5},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/resources/{alpha_id}/highlights",
            json={"start_offset": -1, "end_offset": 5},
        ).status_code
        == 422
    )
    assert (
        client.post(f"/api/v1/resources/{alpha_id}/notes", json={"content": ""}).status_code == 422
    )
    assert (
        client.post(
            f"/api/v1/resources/{alpha_id}/notes",
            json={"content": "x", "start_offset": start},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/resources/999999/highlights",
            json={"start_offset": 0, "end_offset": 1},
        ).status_code
        == 404
    )


def test_annotation_put_and_delete_errors(client: TestClient, sample_tree: Path) -> None:
    _project_id, files = imported_project(client, sample_tree)
    start, end = _alpha_offsets()
    created = client.post(
        f"/api/v1/resources/{files['alpha.md']}/highlights",
        json={"start_offset": start, "end_offset": end},
    ).json()
    annotation_id = int(created["id"])

    assert (
        client.put(
            f"/api/v1/annotations/{annotation_id}",
            json={"start_offset": 0},
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/v1/annotations/{annotation_id}",
            json={"start_offset": 1, "end_offset": len(ALPHA_CONTENT) + 3},
        ).status_code
        == 400
    )
    assert client.put("/api/v1/annotations/999999", json={"content": "x"}).status_code == 404
    assert client.delete("/api/v1/annotations/999999").status_code == 404
    assert client.put(f"/api/v1/annotations/{annotation_id}", json={}).status_code == 200


def test_annotation_never_touches_source_file(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    start, end = _alpha_offsets()
    client.post(
        f"/api/v1/resources/{alpha_id}/highlights",
        json={"start_offset": start, "end_offset": end},
    )
    client.post(f"/api/v1/resources/{alpha_id}/notes", json={"content": "note text"})
    disk_text = (sample_tree / "alpha.md").read_text(encoding="utf-8")
    assert disk_text == ALPHA_CONTENT
