from fastapi.testclient import TestClient

from writer_assistance_api.app import create_app


def test_create_and_list_projects() -> None:
    client = TestClient(create_app(database_url="sqlite+pysqlite:///:memory:"))

    create_response = client.post("/projects", json={"title": "Municipal Housing Brief"})
    assert create_response.status_code == 201

    list_response = client.get("/projects")
    assert list_response.status_code == 200
    assert list_response.json()["projects"][0]["title"] == "Municipal Housing Brief"
