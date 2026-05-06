from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from writer_assistance_api.app import create_app


def test_create_and_list_annotations_persist_quote_anchor_for_resource(tmp_path: Path) -> None:
    client = _create_client(tmp_path)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    payload = {
        "resource_id": resource["id"],
        "body": "Use this as supporting evidence in the summary.",
        "anchor": {
            "quoteText": "Demand is rising.",
            "normalizedText": "demand is rising.",
            "startOffset": 0,
            "endOffset": 17,
            "blockPath": ["paragraph", "1"],
            "resolutionStatus": "exact",
        },
    }

    create_response = client.post(f"/projects/{project['id']}/annotations", json=payload)

    assert create_response.status_code == 201
    created_annotation = create_response.json()
    assert created_annotation["project_id"] == project["id"]
    assert created_annotation["resource_id"] == resource["id"]
    assert created_annotation["body"] == payload["body"]
    assert created_annotation["origin_type"] == "user"
    assert created_annotation["provenance_source_id"] is None
    assert created_annotation["anchor"] == payload["anchor"]

    with client.app.state.session_factory() as session:
        stored_row = session.execute(
            text(
                """
                SELECT
                    project_id,
                    resource_id,
                    quote_text,
                    normalized_text,
                    start_offset,
                    end_offset,
                    json_extract(block_path, '$[0]') AS block_path_0,
                    json_extract(block_path, '$[1]') AS block_path_1,
                    resolution_status,
                    body,
                    origin_type,
                    provenance_source_id
                FROM annotations
                """
            )
        ).mappings().one()

    assert stored_row["project_id"] == project["id"]
    assert stored_row["resource_id"] == resource["id"]
    assert stored_row["quote_text"] == "Demand is rising."
    assert stored_row["normalized_text"] == "demand is rising."
    assert stored_row["start_offset"] == 0
    assert stored_row["end_offset"] == 17
    assert stored_row["block_path_0"] == "paragraph"
    assert stored_row["block_path_1"] == "1"
    assert stored_row["resolution_status"] == "exact"
    assert stored_row["body"] == payload["body"]
    assert stored_row["origin_type"] == "user"
    assert stored_row["provenance_source_id"] is None

    list_response = client.get(f"/resources/{resource['id']}/annotations")

    assert list_response.status_code == 200
    assert list_response.json() == {"annotations": [created_annotation]}


def test_create_annotation_rejects_invalid_anchor_offsets(tmp_path: Path) -> None:
    client = _create_client(tmp_path)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    response = client.post(
        f"/projects/{project['id']}/annotations",
        json={
            "resource_id": resource["id"],
            "body": "Broken anchor.",
            "anchor": {
                "quoteText": "Demand is rising.",
                "normalizedText": "demand is rising.",
                "startOffset": 7,
                "endOffset": 7,
                "blockPath": ["paragraph", "1"],
                "resolutionStatus": "exact",
            },
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Quote anchor must satisfy startOffset < endOffset"}

    with client.app.state.session_factory() as session:
        assert session.execute(text("SELECT COUNT(*) FROM annotations")).scalar_one() == 0


def test_create_annotation_rejects_noncanonical_normalized_text(tmp_path: Path) -> None:
    client = _create_client(tmp_path)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    response = client.post(
        f"/projects/{project['id']}/annotations",
        json={
            "resource_id": resource["id"],
            "body": "Broken normalization.",
            "anchor": {
                "quoteText": "Demand is rising.",
                "normalizedText": "client-supplied",
                "startOffset": 0,
                "endOffset": 17,
                "blockPath": ["paragraph", "1"],
                "resolutionStatus": "exact",
            },
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Quote anchor normalizedText must match quoteText"}

    with client.app.state.session_factory() as session:
        assert session.execute(text("SELECT COUNT(*) FROM annotations")).scalar_one() == 0


def test_create_annotation_rejects_untrimmed_quote_text(tmp_path: Path) -> None:
    client = _create_client(tmp_path)
    project = _create_project(client)
    resource = _upload_resource(client, project_id=project["id"])

    response = client.post(
        f"/projects/{project['id']}/annotations",
        json={
            "resource_id": resource["id"],
            "body": "Broken whitespace.",
            "anchor": {
                "quoteText": "  Demand is rising.  ",
                "normalizedText": "demand is rising.",
                "startOffset": 2,
                "endOffset": 19,
                "blockPath": ["paragraph", "1"],
                "resolutionStatus": "exact",
            },
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Quote anchor quoteText must be trimmed"}

    with client.app.state.session_factory() as session:
        assert session.execute(text("SELECT COUNT(*) FROM annotations")).scalar_one() == 0


def _create_client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            database_url="sqlite+pysqlite:///:memory:",
            storage_root=tmp_path / "storage",
        )
    )


def _create_project(client: TestClient) -> dict[str, str]:
    return client.post("/projects", json={"title": "Research Memo"}).json()


def _upload_resource(client: TestClient, *, project_id: str) -> dict[str, str]:
    response = client.post(
        f"/projects/{project_id}/resources/upload",
        files=[
            ("paths", (None, "research/market.md")),
            ("files", ("market.md", b"# Market\n\nDemand is rising.", "text/markdown")),
        ],
    )

    assert response.status_code == 201
    return response.json()["resources"][0]
