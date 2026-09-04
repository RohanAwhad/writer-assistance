"""API tests: project CRUD and browser-upload import (F1; R-079..R-081, SD-28..SD-30).

INT-008 contract: POST /api/v1/projects/{project_id}/import accepts multipart
file parts (field ``files``), snapshots accepted files byte-for-byte, flat at
the project root, and rejects the whole request when any part fails the SD-30
grammar — nothing persists on any rejection (all-or-nothing).
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import ALPHA_CONTENT, BETA_CONTENT, imported_project

MARKDOWN = "text/markdown"
GATE_KEY = "import-test-key"
CAP_DETAIL = "import upload exceeds the 10 MiB cap"


def parts(*files: tuple[str, bytes]) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", (name, content, MARKDOWN)) for name, content in files]


def _create_project(client: TestClient) -> int:
    response = client.post("/api/v1/projects", json={"name": "Upload project"})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _assert_no_files(client: TestClient, project_id: int) -> None:
    detail = client.get(f"/api/v1/projects/{project_id}")
    assert detail.status_code == 200
    assert detail.json()["resource_count"] == 0
    tree = client.get(f"/api/v1/projects/{project_id}/tree").json()["nodes"]
    assert tree == []


@pytest.fixture
def capped_client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(
        create_app(
            db_path=str(tmp_path / "cap.db"),
            static_dir=str(tmp_path / "absent"),
            import_cap_bytes=2048,
        )
    ) as client:
        yield client


@pytest.fixture
def gated_client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(
        create_app(
            db_path=str(tmp_path / "gated.db"),
            auth_key=GATE_KEY,
            static_dir=str(tmp_path / "absent"),
        )
    ) as client:
        yield client


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


def test_import_upload_success_round_trip_byte_fidelity(
    client: TestClient, sample_tree: Path
) -> None:
    alpha_bytes = ALPHA_CONTENT.encode("utf-8")
    beta_bytes = BETA_CONTENT.encode("utf-8")
    project_id, files = imported_project(client, sample_tree)
    assert set(files) == {"alpha.md", "beta.md", "chapter.md"}

    tree = client.get(f"/api/v1/projects/{project_id}/tree").json()["nodes"]
    assert [n["path"] for n in tree] == ["alpha.md", "beta.md", "chapter.md"]
    assert all(n["kind"] == "file" and n["parent_id"] is None for n in tree)

    for node_id, expected in (
        (files["alpha.md"], alpha_bytes),
        (files["beta.md"], beta_bytes),
    ):
        resource = client.get(f"/api/v1/resources/{node_id}")
        assert resource.status_code == 200
        body = resource.json()
        assert body["path"] in {"alpha.md", "beta.md"}
        assert body["project_id"] == project_id
        assert body["content"] == expected.decode("utf-8")
        assert body["content"].encode("utf-8") == expected


def test_import_upload_markdown_variants(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts(
            ("UPPER.MD", b"# Upper\n"),
            ("notes.markdown", b"Markdown extension notes.\n"),
        ),
    )
    assert response.status_code == 201, response.text
    assert response.json() == {"project_id": project_id, "imported_files": 2}
    files_map = {
        node["path"]: int(node["id"])
        for node in client.get(f"/api/v1/projects/{project_id}/tree").json()["nodes"]
    }
    assert set(files_map) == {"UPPER.MD", "notes.markdown"}
    served = client.get(f"/api/v1/resources/{files_map['notes.markdown']}").json()["content"]
    assert served == "Markdown extension notes.\n"


def test_import_rejects_bad_extension_nothing_persisted(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts(("notes.txt", b"not markdown")),
    )
    assert response.status_code == 400
    assert "notes.txt" in response.json()["detail"]
    _assert_no_files(client, project_id)


@pytest.mark.parametrize("bad_name", ["sub/alpha.md", "sub\\alpha.md"])
def test_import_rejects_path_separator_in_name_nothing_persisted(
    client: TestClient, bad_name: str
) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts((bad_name, b"# Nested\n")),
    )
    assert response.status_code == 400
    assert bad_name in response.json()["detail"]
    _assert_no_files(client, project_id)


def test_import_rejects_dot_leading_name_nothing_persisted(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts((".hidden.md", b"# Hidden\n")),
    )
    assert response.status_code == 400
    assert ".hidden.md" in response.json()["detail"]
    _assert_no_files(client, project_id)


def test_import_rejects_non_utf8_bytes_nothing_persisted(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts(("latin1.md", b"\xff\xfe\xfa")),
    )
    assert response.status_code == 400
    assert "latin1.md" in response.json()["detail"]
    _assert_no_files(client, project_id)


def test_import_rejects_mixed_batch_whole_nothing_persisted(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts(
            ("alpha.md", ALPHA_CONTENT.encode("utf-8")),
            ("break.txt", b"bad"),
        ),
    )
    assert response.status_code == 400
    assert "break.txt" in response.json()["detail"]
    _assert_no_files(client, project_id)


def test_import_accepts_empty_file(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts(("empty.md", b"")),
    )
    assert response.status_code == 201, response.text
    assert response.json() == {"project_id": project_id, "imported_files": 1}
    tree = client.get(f"/api/v1/projects/{project_id}/tree").json()["nodes"]
    resource = client.get(f"/api/v1/resources/{tree[0]['id']}")
    assert resource.json()["content"] == ""


def test_import_rejects_intra_request_duplicate_names_nothing_persisted(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts(
            ("dup.md", b"# One\n"),
            ("dup.md", b"# Two\n"),
        ),
    )
    assert response.status_code == 409
    assert "dup.md" in response.json()["detail"]
    _assert_no_files(client, project_id)


def test_second_import_409_and_snapshot_unchanged(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    before = client.get(f"/api/v1/projects/{project_id}/tree").json()["nodes"]
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts(("extra.md", b"# Extra\n")),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "project already has imported resources"
    assert client.get(f"/api/v1/projects/{project_id}/tree").json()["nodes"] == before
    assert client.get(f"/api/v1/projects/{project_id}").json()["resource_count"] == len(files)


def test_import_with_no_file_part_422(client: TestClient) -> None:
    project_id = _create_project(client)
    boundary = "----writer-assistance-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="unrelated"\r\n\r\n'
        "x\r\n"
        f"--{boundary}--\r\n"
    )
    response = client.post(
        f"/api/v1/projects/{project_id}/import",
        content=body,
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )
    assert response.status_code == 422
    _assert_no_files(client, project_id)


def test_import_over_cap_413_nothing_persisted(capped_client: TestClient) -> None:
    project_id = _create_project(capped_client)
    big = b"x" * 4096
    response = capped_client.post(
        f"/api/v1/projects/{project_id}/import", files=parts(("big.md", big))
    )
    assert response.status_code == 413
    assert response.json()["detail"] == CAP_DETAIL
    _assert_no_files(capped_client, project_id)
    small = capped_client.post(
        f"/api/v1/projects/{project_id}/import",
        files=parts(("small.md", b"# Fits\n")),
    )
    assert small.status_code == 201, small.text


def test_import_unknown_project_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects/999999/import",
        files=parts(("alpha.md", b"# Nope\n")),
    )
    assert response.status_code == 404


def test_import_gate_on_unauthenticated_upload_401(gated_client: TestClient) -> None:
    response = gated_client.post(
        "/api/v1/projects/1/import",
        files=parts(("alpha.md", ALPHA_CONTENT.encode("utf-8"))),
    )
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "authentication required"}


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
