from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from writer_assistance_api.app import create_app
from writer_assistance_api.config import DEFAULT_DATABASE_PATH, get_settings
from writer_assistance_api.db import create_all_tables, create_engine_and_session_factory


def test_package_is_importable_via_uv_project_python() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    result = subprocess.run(
        ["uv", "run", "--project", "apps/api", "python", "-c", "import writer_assistance_api.main"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_health_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_default_database_url_uses_workspace_data_directory(monkeypatch) -> None:
    monkeypatch.delenv("WRITER_ASSISTANCE_DATABASE_URL", raising=False)
    expected_database_path = Path(__file__).resolve().parents[3] / "data" / "app.db"

    assert DEFAULT_DATABASE_PATH == expected_database_path
    assert get_settings().database_url == f"sqlite+pysqlite:///{expected_database_path}"


def test_sqlite_file_database_creates_parent_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "app.db"

    engine, _ = create_engine_and_session_factory(f"sqlite+pysqlite:///{database_path}")
    create_all_tables(engine)

    assert database_path.parent.exists()
    assert database_path.is_file()
