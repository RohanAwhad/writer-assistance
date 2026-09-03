"""API tests: lens proposals, expert runs, note review and merge (F3..F5)."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import imported_project, make_round, select_and_run_experts


def test_lens_proposal_lifecycle(client: TestClient, sample_tree: Path) -> None:
    _project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    response = client.post(f"/api/v1/resources/{alpha_id}/lens-proposals", json={})
    assert response.status_code == 201
    proposals = response.json()
    assert len(proposals) == 3
    assert {p["status"] for p in proposals} == {"proposed"}

    listed = client.get(f"/api/v1/resources/{alpha_id}/lens-proposals").json()
    assert len(listed) == 3

    selected = client.patch(
        f"/api/v1/lens-proposals/{proposals[0]['id']}", json={"status": "selected"}
    )
    assert selected.status_code == 200
    assert selected.json()["status"] == "selected"
    skipped = client.patch(
        f"/api/v1/lens-proposals/{proposals[1]['id']}", json={"status": "skipped"}
    )
    assert skipped.status_code == 200
    assert skipped.json()["status"] == "skipped"
    assert (
        client.patch(
            f"/api/v1/lens-proposals/{proposals[2]['id']}",
            json={"status": "proposed"},
        ).status_code
        == 422
    )
    assert (
        client.patch("/api/v1/lens-proposals/999999", json={"status": "selected"}).status_code
        == 404
    )

    re_proposed = client.post(f"/api/v1/resources/{alpha_id}/lens-proposals", json={})
    assert re_proposed.status_code == 201
    statuses_after = {
        p["status"] for p in client.get(f"/api/v1/resources/{alpha_id}/lens-proposals").json()
    }
    assert statuses_after == {"selected", "skipped", "proposed"}


def test_expert_run_and_note_review_flow(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    round_id = make_round(client, project_id, [files["alpha.md"], files["sub/chapter.md"]])
    alpha_id = files["alpha.md"]

    response = client.post(f"/api/v1/resources/{alpha_id}/lens-proposals", json={})
    proposals = response.json()
    first, second = proposals[0]["id"], proposals[1]["id"]
    client.patch(f"/api/v1/lens-proposals/{first}", json={"status": "selected"})
    client.patch(f"/api/v1/lens-proposals/{second}", json={"status": "skipped"})

    run = client.post(f"/api/v1/rounds/{round_id}/experts", json={"lens_proposal_ids": [first]})
    assert run.status_code == 201
    runs = run.json()["expert_runs"]
    assert len(runs) == 1
    run_id = int(runs[0]["id"])
    assert runs[0]["lens_title"] == "Financial"
    assert runs[0]["round_id"] == round_id
    assert runs[0]["doc_path"] == "alpha.md"
    assert [note["review_state"] for note in runs[0]["notes"]] == [
        "pending",
        "pending",
        "pending",
    ]

    fetched = client.get(f"/api/v1/expert-runs/{run_id}/notes")
    assert fetched.status_code == 200
    notes = fetched.json()["notes"]
    assert len(notes) == 3
    note_ids = [int(note["id"]) for note in notes]

    discarded = client.patch(
        f"/api/v1/expert-notes/{note_ids[0]}", json={"review_state": "discarded"}
    )
    assert discarded.status_code == 200
    assert discarded.json()["review_state"] == "discarded"

    edited = client.patch(
        f"/api/v1/expert-notes/{note_ids[1]}",
        json={"review_state": "merged-with-edits", "content": "Edited expert note."},
    )
    assert edited.status_code == 200
    assert edited.json()["edited_content"] == "Edited expert note."

    assert (
        client.patch(
            f"/api/v1/expert-notes/{note_ids[0]}", json={"review_state": "pending"}
        ).status_code
        == 409
    )
    again = client.patch(
        f"/api/v1/expert-notes/{note_ids[1]}",
        json={"review_state": "merged-with-edits"},
    )
    assert again.status_code == 200
    assert again.json()["edited_content"] == "Edited expert note."


def test_expert_run_gates(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    chapter_id = files["sub/chapter.md"]
    round_id = make_round(client, project_id, [alpha_id, chapter_id])

    proposals = client.post(f"/api/v1/resources/{alpha_id}/lens-proposals", json={}).json()
    unselected = proposals[0]["id"]
    run = client.post(
        f"/api/v1/rounds/{round_id}/experts",
        json={"lens_proposal_ids": [unselected]},
    )
    assert run.status_code == 409
    assert "select it before running" in run.json()["detail"]

    client.patch(f"/api/v1/lens-proposals/{unselected}", json={"status": "selected"})
    other_doc_proposals = client.post(
        f"/api/v1/resources/{files['beta.md']}/lens-proposals", json={}
    ).json()
    other_id = other_doc_proposals[0]["id"]
    client.patch(f"/api/v1/lens-proposals/{other_id}", json={"status": "selected"})
    run = client.post(
        f"/api/v1/rounds/{round_id}/experts",
        json={"lens_proposal_ids": [other_id]},
    )
    assert run.status_code == 409
    assert "not in the round's doc set" in run.json()["detail"]

    assert (
        client.post("/api/v1/rounds/999999/experts", json={"lens_proposal_ids": [1]}).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/rounds/{round_id}/experts", json={"lens_proposal_ids": [999999]}
        ).status_code
        == 404
    )


def test_duplicate_expert_run_rejected(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    round_id = make_round(client, project_id, [files["alpha.md"]])
    select_and_run_experts(client, round_id, files["alpha.md"])
    proposal_id = int(
        client.get(f"/api/v1/resources/{files['alpha.md']}/lens-proposals").json()[0]["id"]
    )
    second = client.post(
        f"/api/v1/rounds/{round_id}/experts",
        json={"lens_proposal_ids": [proposal_id]},
    )
    assert second.status_code == 409
    assert "already ran" in second.json()["detail"]


def test_merge_creates_pool_entry_with_provenance(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    round_id = make_round(client, project_id, [files["alpha.md"]])
    run_id = select_and_run_experts(client, round_id, files["alpha.md"])
    notes = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"]
    note_id = int(notes[0]["id"])

    merged = client.post(f"/api/v1/expert-notes/{note_id}/merge", json={})
    assert merged.status_code == 201
    entry = merged.json()
    assert entry["kind"] == "ai-thought"
    assert entry["content"] == notes[0]["content"]
    assert entry["expert_note_id"] == note_id
    assert entry["doc_id"] == files["alpha.md"]
    assert entry["dump_id"] is not None
    assert entry["doc_path"] == "alpha.md"
    assert entry["position"] == 0

    reviewed = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"]
    assert reviewed[0]["review_state"] == "accepted"

    duplicate = client.post(f"/api/v1/expert-notes/{note_id}/merge", json={})
    assert duplicate.status_code == 409


def test_merge_with_edits_and_discard_gates(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    round_id = make_round(client, project_id, [files["alpha.md"]])
    run_id = select_and_run_experts(client, round_id, files["alpha.md"])
    notes = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"]
    first_id, second_id = int(notes[0]["id"]), int(notes[1]["id"])

    edited = client.post(
        f"/api/v1/expert-notes/{first_id}/merge",
        json={"content": "Merged with human edits."},
    )
    assert edited.status_code == 201
    assert edited.json()["content"] == "Merged with human edits."
    state = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"][0]
    assert state["review_state"] == "merged-with-edits"
    assert state["edited_content"] == "Merged with human edits."

    client.patch(f"/api/v1/expert-notes/{second_id}", json={"review_state": "discarded"})
    rejected = client.post(f"/api/v1/expert-notes/{second_id}/merge", json={})
    assert rejected.status_code == 409
