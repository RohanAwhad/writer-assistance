"""API tests: project CRUD, tree import, resource reads (F1, R-010/R-011)."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import ALPHA_CONTENT, imported_project


def test_project_crud_flow(client: TestClient, sample_tree: Path) -> None:
    response = client.post("/api/v1/projects", json={"name": "Book notes"})
    assert response.status_code == 201
    project_id = int(response.json()["id"])

    listed = client.get("/api/v1/projects").json()
    assert any(p["id"] == project_id for p in listed)

    detail = client.get(f"/api/v1/projects/{project_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Book notes"
    assert detail.json()["resource_count"] == 0

    renamed = client.put(f"/api/v1/projects/{project_id}", json={"name": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"

    deleted = client.delete(f"/api/v1/projects/{project_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/projects/{project_id}").status_code == 404


def test_project_validation(client: TestClient) -> None:
    assert client.post("/api/v1/projects", json={"name": ""}).status_code == 422
    assert client.get("/api/v1/projects/999").status_code == 404
    assert client.put("/api/v1/projects/999", json={"name": "x"}).status_code == 404


def test_import_snapshots_markdown_tree(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    assert set(files) == {"alpha.md", "beta.md", "sub/chapter.md"}
    tree = client.get(f"/api/v1/projects/{project_id}/tree").json()["nodes"]
    dirs = [n["path"] for n in tree if n["kind"] == "dir"]
    assert dirs == ["sub"]
    alpha_node = next(n for n in tree if n["path"] == "alpha.md")
    assert alpha_node["kind"] == "file"
    assert alpha_node["parent_id"] is None
    chapter_node = next(n for n in tree if n["path"] == "sub/chapter.md")
    sub_dir = next(n for n in tree if n["path"] == "sub")
    assert chapter_node["parent_id"] == sub_dir["id"]


def test_import_errors(client: TestClient, sample_tree: Path, tmp_path: Path) -> None:
    project_id, _ = imported_project(client, sample_tree)
    missing_dir = tmp_path / "does-not-exist"
    response = client.post(f"/api/v1/projects/{project_id}/import", json={"path": str(missing_dir)})
    assert response.status_code == 400
    assert "not a directory" in response.json()["detail"]

    second = client.post(f"/api/v1/projects/{project_id}/import", json={"path": str(sample_tree)})
    assert second.status_code == 409

    no_md = tmp_path / "plain"
    no_md.mkdir()
    (no_md / "readme.txt").write_text("no md here", encoding="utf-8")
    fresh = client.post("/api/v1/projects", json={"name": "Empty project"})
    fresh_id = int(fresh.json()["id"])
    response = client.post(f"/api/v1/projects/{fresh_id}/import", json={"path": str(no_md)})
    assert response.status_code == 400
    assert "no Markdown files" in response.json()["detail"]

    assert client.post("/api/v1/projects/999/import", json={"path": "/tmp"}).status_code == 404


def test_resource_content_equals_snapshot(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    resource = client.get(f"/api/v1/resources/{files['alpha.md']}")
    assert resource.status_code == 200
    body = resource.json()
    assert body["content"] == ALPHA_CONTENT
    assert body["path"] == "alpha.md"
    assert body["project_id"] == project_id
    assert client.get("/api/v1/resources/999999").status_code == 404


def test_delete_project_cascades(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    round_response = client.post(
        "/api/v1/rounds",
        json={"project_id": project_id, "doc_ids": [files["alpha.md"], files["beta.md"]]},
    )
    assert round_response.status_code == 201
    round_id = int(round_response.json()["id"])
    assert client.delete(f"/api/v1/projects/{project_id}").status_code == 204
    assert client.get(f"/api/v1/rounds/{round_id}").status_code == 404
    assert client.get(f"/api/v1/resources/{files['alpha.md']}").status_code == 404
