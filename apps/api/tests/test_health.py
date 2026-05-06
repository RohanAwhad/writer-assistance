from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from writer_assistance_api.app import create_app


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
