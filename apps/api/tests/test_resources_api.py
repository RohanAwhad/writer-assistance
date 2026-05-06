from fastapi.testclient import TestClient

from writer_assistance_api.app import create_app


def test_upload_markdown_resources_with_logical_paths(tmp_path) -> None:
    client = TestClient(
        create_app(
            database_url="sqlite+pysqlite:///:memory:",
            storage_root=tmp_path / "storage",
        )
    )

    project = client.post("/projects", json={"title": "Research Memo"}).json()

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
