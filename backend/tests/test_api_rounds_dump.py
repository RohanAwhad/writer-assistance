"""API tests: rounds and dump curation (F6, R-030/R-031, OQ-03)."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import (
    Harness,
    direct_db,
    imported_project,
    make_round,
    select_and_run_experts,
)


def test_round_creation_and_doc_set(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id, chapter_id = files["alpha.md"], files["chapter.md"]
    response = client.post(
        "/api/v1/rounds",
        json={"project_id": project_id, "doc_ids": [chapter_id, alpha_id]},
    )
    assert response.status_code == 201
    round_id = int(response.json()["id"])
    assert response.json()["doc_ids"] == [chapter_id, alpha_id]
    assert response.json()["stage"] == "reading"

    detail = client.get(f"/api/v1/rounds/{round_id}")
    assert detail.status_code == 200
    assert [doc["path"] for doc in detail.json()["docs"]] == [
        "chapter.md",
        "alpha.md",
    ]
    assert detail.json()["dump_id"] is None
    assert detail.json()["report_id"] is None

    summaries = client.get(f"/api/v1/rounds?project_id={project_id}").json()
    assert len(summaries) == 1
    assert summaries[0]["doc_count"] == 2
    assert summaries[0]["stage"] == "reading"


def test_round_validation(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    bad = client.post("/api/v1/rounds", json={"project_id": project_id, "doc_ids": []})
    assert bad.status_code == 422
    unknown_doc = client.post(
        "/api/v1/rounds", json={"project_id": project_id, "doc_ids": [999999]}
    )
    assert unknown_doc.status_code == 400
    dupes = client.post(
        "/api/v1/rounds",
        json={"project_id": project_id, "doc_ids": [files["alpha.md"], files["alpha.md"]]},
    )
    assert dupes.status_code == 400
    assert (
        client.post("/api/v1/rounds", json={"project_id": 999, "doc_ids": [1]}).status_code == 404
    )
    assert client.get("/api/v1/rounds/999999").status_code == 404


def test_dump_save_reorders_and_replaces(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    round_id = make_round(client, project_id, [alpha_id])
    dump = client.get(f"/api/v1/rounds/{round_id}/dump")
    assert dump.status_code == 200
    assert dump.json()["saved"] is False
    assert dump.json()["entries"] == []

    body = {
        "entries": [
            {"kind": "snippet", "content": "Snippet A.", "doc_id": alpha_id},
            {"kind": "human-thought", "content": "Thought B."},
            {"kind": "highlight", "content": "Highlight C.", "doc_id": alpha_id},
        ]
    }
    saved = client.post(f"/api/v1/rounds/{round_id}/dump", json=body)
    assert saved.status_code == 200
    saved_body = saved.json()
    assert saved_body["saved"] is True
    assert [e["kind"] for e in saved_body["entries"]] == [
        "snippet",
        "human-thought",
        "highlight",
    ]
    assert [e["position"] for e in saved_body["entries"]] == [0, 1, 2]

    reshuffled = client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={
            "entries": [
                body["entries"][2],
                body["entries"][1],
                {"kind": "ai-thought", "content": "Thought D."},
            ]
        },
    )
    assert reshuffled.status_code == 200
    kinds = [e["kind"] for e in reshuffled.json()["entries"]]
    assert kinds == ["highlight", "human-thought", "ai-thought"]

    fetched = client.get(f"/api/v1/rounds/{round_id}/dump").json()
    assert [e["content"] for e in fetched["entries"]] == [
        "Highlight C.",
        "Thought B.",
        "Thought D.",
    ]


def test_dump_kind_validation(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    round_id = make_round(client, project_id, [alpha_id])

    missing_doc = client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={"entries": [{"kind": "snippet", "content": "x"}]},
    )
    assert missing_doc.status_code == 422

    foreign_doc = client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={"entries": [{"kind": "snippet", "content": "x", "doc_id": files["beta.md"]}]},
    )
    assert foreign_doc.status_code == 400
    assert "not part of the round's doc set" in foreign_doc.json()["detail"]


def test_merge_attaches_to_dump_immediately(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    round_id = make_round(client, project_id, [alpha_id])
    run_id = select_and_run_experts(client, round_id, alpha_id)
    notes = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"]
    first_note = int(notes[0]["id"])
    second_note = int(notes[1]["id"])
    first_entry = client.post(f"/api/v1/expert-notes/{first_note}/merge", json={}).json()
    assert first_entry["dump_id"] is not None

    second_entry = client.post(
        f"/api/v1/expert-notes/{second_note}/merge",
        json={"content": "Edited variant."},
    ).json()

    dump = client.get(f"/api/v1/rounds/{round_id}/dump").json()
    assert dump["saved"] is True
    assert [e["id"] for e in dump["entries"]] == [first_entry["id"], second_entry["id"]]
    assert [e["position"] for e in dump["entries"]] == [0, 1]
    assert [e["expert_note_id"] for e in dump["entries"]] == [first_note, second_note]


def test_pool_detach_and_reattach(harness: Harness, client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    round_id = make_round(client, project_id, [alpha_id])
    run_id = select_and_run_experts(client, round_id, alpha_id)
    notes = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"]
    note_id = int(notes[0]["id"])
    merged = client.post(f"/api/v1/expert-notes/{note_id}/merge", json={}).json()
    merged_id = int(merged["id"])

    saved = client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={
            "entries": [
                {
                    "id": merged_id,
                    "kind": "ai-thought",
                    "content": merged["content"],
                },
                {"kind": "human-thought", "content": "Free thought."},
            ]
        },
    )
    assert saved.status_code == 200
    assert [e["kind"] for e in saved.json()["entries"]] == ["ai-thought", "human-thought"]

    dropped = client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={"entries": [{"kind": "human-thought", "content": "Free thought."}]},
    )
    assert dropped.status_code == 200
    assert [e["id"] for e in dropped.json()["entries"]] != [merged_id]

    conn = direct_db(harness.db_path)
    row = conn.execute(
        "SELECT dump_id, position FROM notes_dump_entries WHERE id = ?", (merged_id,)
    ).fetchone()
    assert row is not None
    assert row["dump_id"] is None
    assert row["position"] is None

    reattached = client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={
            "entries": [
                {"kind": "human-thought", "content": "Free thought."},
                {"id": merged_id, "kind": "ai-thought", "content": merged["content"]},
            ]
        },
    )
    assert reattached.status_code == 200
    assert [e["id"] for e in reattached.json()["entries"]][1] == merged_id
    conn.close()


def test_dump_unknown_entry_id_rejected(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    round_id = make_round(client, project_id, [files["alpha.md"]])
    response = client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={"entries": [{"id": 999999, "kind": "human-thought", "content": "x"}]},
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"]
