import asyncio
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from writer_assistance_api.app import create_app
from writer_assistance_api.db import create_engine_and_session_factory
from writer_assistance_api.disk_storage import DiskStorage
from writer_assistance_api.models import Resource
from writer_assistance_api.services.resources import ResourcesService


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


def test_duplicate_conflict_after_write_keeps_committed_file(tmp_path: Path) -> None:
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

    winner_storage_path = Path(_stored_resources(client)[0].storage_location)

    with client.app.state.session_factory() as session:
        service = RaceyResourcesService(session=session, storage=client.app.state.storage)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                service.upload_resources(
                    project_id=project["id"],
                    files=[_upload_file("market.md", b"# Market\n\nLosing content.")],
                    paths=["research/market.md"],
                )
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == _conflict_response(["research/market.md"])["detail"]
    assert winner_storage_path.read_bytes() == b"# Market\n\nOriginal content."
    assert {path for path in (tmp_path / "storage").rglob("*") if path.is_file()} == {winner_storage_path}


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


def test_after_write_failure_does_not_orphan_file(tmp_path: Path) -> None:
    app = create_app(
        database_url="sqlite+pysqlite:///:memory:",
        storage_root=tmp_path / "storage",
    )
    app.state.storage = AfterWriteFailingStorage(tmp_path / "storage")
    client = TestClient(app, raise_server_exceptions=False)
    project = _create_project(client)

    response = client.post(
        f"/projects/{project['id']}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            ("files", ("market.md", b"# Market", "text/markdown")),
        ],
    )

    assert response.status_code == 500
    assert _stored_resources(client) == []
    assert not any(path.is_file() for path in (tmp_path / "storage").rglob("*"))


def test_sqlite_startup_backfills_resource_uniqueness_for_legacy_database(tmp_path: Path) -> None:
    database_url = _create_legacy_sqlite_database(tmp_path / "legacy.db")

    app = create_app(database_url=database_url, storage_root=tmp_path / "storage")

    assert bool(_resource_index(database_url)["unique"]) is True
    app.state.engine.dispose()


def test_sqlite_startup_rejects_legacy_duplicates_before_index_creation(tmp_path: Path) -> None:
    database_url = _create_legacy_sqlite_database(
        tmp_path / "legacy-with-duplicates.db",
        duplicate_logical_paths=True,
    )

    with pytest.raises(RuntimeError, match="duplicate logical paths"):
        create_app(database_url=database_url, storage_root=tmp_path / "storage")


class FailingDiskStorage:
    def __init__(self, root: Path) -> None:
        self._disk_storage = DiskStorage(root)
        self._write_attempts = 0

    def prepare_object(self, *, project_id: str, logical_path: str, content: bytes):
        return self._disk_storage.prepare_object(
            project_id=project_id,
            logical_path=logical_path,
            content=content,
        )

    def put_object(self, *, project_id: str, logical_path: str, content: bytes, stored_object=None):
        self._write_attempts += 1
        if self._write_attempts == 2:
            raise OSError("disk full")
        return self._disk_storage.put_object(
            project_id=project_id,
            logical_path=logical_path,
            content=content,
            stored_object=stored_object,
        )

    def read_object(self, storage_path: str) -> bytes:
        return self._disk_storage.read_object(storage_path)

    def delete_object(self, storage_path: str) -> None:
        self._disk_storage.delete_object(storage_path)


class AfterWriteFailingStorage:
    def __init__(self, root: Path) -> None:
        self._disk_storage = DiskStorage(root)

    def prepare_object(self, *, project_id: str, logical_path: str, content: bytes):
        return self._disk_storage.prepare_object(
            project_id=project_id,
            logical_path=logical_path,
            content=content,
        )

    def put_object(self, *, project_id: str, logical_path: str, content: bytes, stored_object=None):
        self._disk_storage.put_object(
            project_id=project_id,
            logical_path=logical_path,
            content=content,
            stored_object=stored_object,
        )
        raise OSError("after write before return")

    def read_object(self, storage_path: str) -> bytes:
        return self._disk_storage.read_object(storage_path)

    def delete_object(self, storage_path: str) -> None:
        self._disk_storage.delete_object(storage_path)


class RaceyResourcesService(ResourcesService):
    def __init__(self, session, storage) -> None:
        super().__init__(session=session, storage=storage)
        self._conflict_checks = 0

    def _find_conflicting_paths(self, *, project_id: str, logical_paths: list[str]) -> list[str]:
        self._conflict_checks += 1
        if self._conflict_checks == 1:
            return []
        return super()._find_conflicting_paths(project_id=project_id, logical_paths=logical_paths)


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


def _upload_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


def _create_legacy_sqlite_database(
    database_path: Path,
    *,
    duplicate_logical_paths: bool = False,
) -> str:
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine, _ = create_engine_and_session_factory(database_url)
    timestamp = datetime.now(UTC).isoformat()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE projects (
                    id VARCHAR PRIMARY KEY NOT NULL,
                    title VARCHAR(120) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE resources (
                    id VARCHAR PRIMARY KEY NOT NULL,
                    project_id VARCHAR NOT NULL,
                    logical_path VARCHAR NOT NULL,
                    original_filename VARCHAR NOT NULL,
                    storage_location VARCHAR NOT NULL,
                    content_hash VARCHAR NOT NULL,
                    upload_status VARCHAR NOT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects (id)
                )
                """
            )
        )
        connection.execute(text("CREATE INDEX ix_resources_project_id ON resources (project_id)"))
        connection.execute(
            text(
                """
                INSERT INTO projects (id, title, created_at, updated_at)
                VALUES (:id, :title, :created_at, :updated_at)
                """
            ),
            {
                "id": "project-1",
                "title": "Legacy project",
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO resources (
                    id,
                    project_id,
                    logical_path,
                    original_filename,
                    storage_location,
                    content_hash,
                    upload_status,
                    created_at
                ) VALUES (
                    :id,
                    :project_id,
                    :logical_path,
                    :original_filename,
                    :storage_location,
                    :content_hash,
                    :upload_status,
                    :created_at
                )
                """
            ),
            {
                "id": "resource-1",
                "project_id": "project-1",
                "logical_path": "research/market.md",
                "original_filename": "market.md",
                "storage_location": "/tmp/market.md",
                "content_hash": "hash-1",
                "upload_status": "uploaded",
                "created_at": timestamp,
            },
        )
        if duplicate_logical_paths:
            connection.execute(
                text(
                    """
                    INSERT INTO resources (
                        id,
                        project_id,
                        logical_path,
                        original_filename,
                        storage_location,
                        content_hash,
                        upload_status,
                        created_at
                    ) VALUES (
                        :id,
                        :project_id,
                        :logical_path,
                        :original_filename,
                        :storage_location,
                        :content_hash,
                        :upload_status,
                        :created_at
                    )
                    """
                ),
                {
                    "id": "resource-2",
                    "project_id": "project-1",
                    "logical_path": "research/market.md",
                    "original_filename": "market-copy.md",
                    "storage_location": "/tmp/market-copy.md",
                    "content_hash": "hash-2",
                    "upload_status": "uploaded",
                    "created_at": timestamp,
                },
            )

    engine.dispose()
    return database_url


def _resource_index(database_url: str) -> dict[str, object]:
    engine, _ = create_engine_and_session_factory(database_url)
    try:
        return next(
            index
            for index in inspect(engine).get_indexes("resources")
            if index["name"] == "ux_resources_project_logical_path"
        )
    finally:
        engine.dispose()


def _conflict_response(paths: list[str]) -> dict[str, dict[str, object]]:
    return {
        "detail": {
            "code": "logical_path_conflict",
            "message": "Logical paths must be unique within a project",
            "paths": paths,
        }
    }
