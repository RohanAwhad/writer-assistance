from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from writer_assistance_api.app import create_app
from writer_assistance_api.disk_storage import DiskStorage
from writer_assistance_api.models import Resource


def test_upload_markdown_resources_returns_public_fields_only(tmp_path) -> None:
    client = _create_client(tmp_path)
    project = _create_project(client)

    response = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            ("paths", (None, "research/zoning.md")),
            ("files", ("market.md", b"# Market\n\nDemand is rising.", "text/markdown")),
            ("files", ("zoning.md", b"# Zoning\n\nRules are changing.", "text/markdown")),
        ],
    )

    assert response.status_code == 201
    assert [item["logical_path"] for item in response.json()["resources"]] == [
        "research/market.md",
        "research/zoning.md",
    ]
    assert set(response.json()["resources"][0]) == {
        "id",
        "project_id",
        "logical_path",
        "original_filename",
        "content_hash",
        "upload_status",
        "created_at",
    }
    assert "storage_location" not in response.json()["resources"][0]


def test_upload_rejects_duplicate_logical_path_in_same_project(tmp_path) -> None:
    client = _create_client(tmp_path)
    project = _create_project(client)

    first_response = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            ("files", ("market.md", b"# Market\n\nOriginal content.", "text/markdown")),
        ],
    )

    assert first_response.status_code == 201

    first_resource = _stored_resources(client)[0]
    original_storage_path = Path(first_resource.storage_location)

    duplicate_response = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            ("files", ("market.md", b"# Market\n\nOverwritten content.", "text/markdown")),
        ],
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == _conflict_response(["research/market.md"])
    assert original_storage_path.read_bytes() == b"# Market\n\nOriginal content."
    assert [resource.logical_path for resource in _stored_resources(client)] == ["research/market.md"]


def test_upload_rejects_duplicate_logical_paths_within_batch(tmp_path) -> None:
    client = _create_client(tmp_path)
    project = _create_project(client)

    response = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            ("paths", (None, "research/market.md")),
            ("files", ("market-a.md", b"# Market A", "text/markdown")),
            ("files", ("market-b.md", b"# Market B", "text/markdown")),
        ],
    )

    assert response.status_code == 409
    assert response.json() == _conflict_response(["research/market.md"])
    assert _stored_resources(client) == []
    assert not any(path.is_file() for path in (tmp_path / "storage").rglob("*"))


def test_invalid_batch_does_not_leave_files_on_disk(tmp_path) -> None:
    client = _create_client(tmp_path)
    project = _create_project(client)

    response = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            ("paths", (None, "../secrets.md")),
            ("files", ("market.md", b"# Market", "text/markdown")),
            ("files", ("secrets.md", b"# Secrets", "text/markdown")),
        ],
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Logical path must point to a markdown file"}
    assert _stored_resources(client) == []
    assert not any(path.is_file() for path in (tmp_path / "storage").rglob("*"))


def test_failed_write_cleans_up_earlier_files(tmp_path) -> None:
    app = create_app(
        database_url="sqlite+pysqlite:///:memory:",
        storage_root=tmp_path / "storage",
    )
    app.state.storage = FailingDiskStorage(tmp_path / "storage")
    client = TestClient(app, raise_server_exceptions=False)
    project = _create_project(client)

    response = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            ("paths", (None, "research/zoning.md")),
            ("files", ("market.md", b"# Market", "text/markdown")),
            ("files", ("zoning.md", b"# Zoning", "text/markdown")),
        ],
    )

    assert response.status_code == 500
    assert _stored_resources(client) == []
    assert not any(path.is_file() for path in (tmp_path / "storage").rglob("*"))


class FailingDiskStorage:
    def __init__(self, root: Path) -> None:
        self._disk_storage = DiskStorage(root)
        self._write_attempts = 0

    def put_object(self, *, project_id: str, logical_path: str, content: bytes):
        self._write_attempts += 1
        if self._write_attempts == 2:
            raise OSError("disk full")
        return self._disk_storage.put_object(
            project_id=project_id,
            logical_path=logical_path,
            content=content,
        )

    def read_object(self, storage_path: str) -> bytes:
        return self._disk_storage.read_object(storage_path)

    def delete_object(self, storage_path: str) -> None:
        self._disk_storage.delete_object(storage_path)


def _create_client(tmp_path) -> TestClient:
    return TestClient(
        create_app(
            database_url="sqlite+pysqlite:///:memory:",
            storage_root=tmp_path / "storage",
        )
    )


def _create_project(client: TestClient) -> dict[str, str]:
    return client.post("/projects", json={"title": "Research Memo"}).json()


def _stored_resources(client: TestClient) -> list[Resource]:
    with client.app.state.session_factory() as session:
        return list(session.scalars(select(Resource).order_by(Resource.logical_path)))


def _conflict_response(paths: list[str]) -> dict[str, dict[str, object]]:
    return {
        "detail": {
            "code": "logical_path_conflict",
            "message": "Logical paths must be unique within a project",
            "paths": paths,
        }
    }
