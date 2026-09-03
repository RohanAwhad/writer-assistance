"""Stage-gate tests: reading -> editing flip per round (R-042, SD-9, OQ-05)."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import (
    full_round_to_report,
    imported_project,
    make_round,
    select_and_run_experts,
)


def test_generate_flips_round_to_editing(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    ids = full_round_to_report(client, project_id, [files["alpha.md"]])
    round_id = ids["round_id"]
    detail = client.get(f"/api/v1/rounds/{round_id}").json()
    assert detail["stage"] == "editing"
    assert detail["report_id"] == ids["report_id"]
    assert detail["dump_id"] is not None


def test_generation_is_one_shot_per_round(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    ids = full_round_to_report(client, project_id, [files["alpha.md"]])
    second = client.post(f"/api/v1/rounds/{ids['round_id']}/generate-report", json={})
    assert second.status_code == 409
    assert "one-shot" in second.json()["detail"]


def test_reading_actions_closed_after_flip(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    round_id = make_round(client, project_id, [alpha_id])
    run_id = select_and_run_experts(client, round_id, alpha_id)
    notes = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"]
    note_id = int(notes[0]["id"])
    client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={"entries": [{"kind": "human-thought", "content": "Thought."}]},
    )
    client.post(f"/api/v1/rounds/{round_id}/generate-report", json={})

    assert client.get(f"/api/v1/rounds/{round_id}").json()["stage"] == "editing"
    experts = client.post(f"/api/v1/rounds/{round_id}/experts", json={"lens_proposal_ids": [1]})
    assert experts.status_code == 409
    dump_save = client.post(
        f"/api/v1/rounds/{round_id}/dump",
        json={"entries": [{"kind": "human-thought", "content": "More."}]},
    )
    assert dump_save.status_code == 409
    review = client.patch(f"/api/v1/expert-notes/{note_id}", json={"review_state": "discarded"})
    assert review.status_code == 409
    merge = client.post(f"/api/v1/expert-notes/{note_id}/merge", json={})
    assert merge.status_code == 409
    assert client.post(f"/api/v1/rounds/{round_id}/generate-report", json={}).status_code == 409


def test_new_round_starts_reading_again(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id, beta_id = files["alpha.md"], files["beta.md"]
    first = full_round_to_report(client, project_id, [alpha_id])
    first_report = client.get(f"/api/v1/reports/{first['report_id']}").json()

    second_round = make_round(client, project_id, [beta_id])
    assert client.get(f"/api/v1/rounds/{second_round}").json()["stage"] == "reading"
    run_id = select_and_run_experts(client, second_round, beta_id)
    notes = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"]
    merged = client.post(f"/api/v1/expert-notes/{int(notes[0]['id'])}/merge", json={})
    assert merged.status_code == 201
    client.post(
        f"/api/v1/rounds/{second_round}/dump",
        json={"entries": [{"kind": "human-thought", "content": "Second round thought."}]},
    )
    second_report = client.post(f"/api/v1/rounds/{second_round}/generate-report", json={})
    assert second_report.status_code == 201

    first_report_after = client.get(f"/api/v1/reports/{first['report_id']}").json()
    assert first_report_after == first_report
    summaries = {s["id"]: s for s in client.get(f"/api/v1/rounds?project_id={project_id}").json()}
    assert summaries[first["round_id"]]["stage"] == "editing"
    assert summaries[second_round]["stage"] == "editing"
    assert summaries[second_round]["report_id"] != first["report_id"]


def test_generate_requires_saved_dump(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    round_id = make_round(client, project_id, [files["alpha.md"]])
    response = client.post(f"/api/v1/rounds/{round_id}/generate-report", json={})
    assert response.status_code == 400
    assert "dump" in response.json()["detail"]


def test_generate_requires_nonempty_dump(client: TestClient, sample_tree: Path) -> None:
    project_id, files = imported_project(client, sample_tree)
    round_id = make_round(client, project_id, [files["alpha.md"]])
    client.post(f"/api/v1/rounds/{round_id}/dump", json={"entries": []})
    response = client.post(f"/api/v1/rounds/{round_id}/generate-report", json={})
    assert response.status_code == 400
