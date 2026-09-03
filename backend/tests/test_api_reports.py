"""API tests: report lifecycle, blocks, tone samples, critique, export (F7..F11);
view-mode read path (R-060, R-061, F12)."""

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from tests.conftest import (
    PARAGRAPHS,
    FakeAI,
    Harness,
    direct_db,
    full_round_to_report,
    imported_project,
)


def _fake(client: TestClient) -> FakeAI:
    fake = cast(Any, client.app).state.fake_ai
    assert isinstance(fake, FakeAI)
    return fake


def _generated_report(client: TestClient, sample_tree: Path) -> dict[str, int]:
    project_id, files = imported_project(client, sample_tree)
    return full_round_to_report(client, project_id, [files["alpha.md"]])


def _report_blocks(client: TestClient, report_id: int) -> list[dict[str, Any]]:
    body = client.get(f"/api/v1/reports/{report_id}").json()
    return cast(list[dict[str, Any]], body["blocks"])


def test_generate_returns_blocks_and_persists(client: TestClient, sample_tree: Path) -> None:
    ids = _generated_report(client, sample_tree)
    report_id = ids["report_id"]
    fetched = client.get(f"/api/v1/reports/{report_id}")
    assert fetched.status_code == 200
    report = fetched.json()
    assert report["round_id"] == ids["round_id"]
    assert [block["content"] for block in report["blocks"]] == PARAGRAPHS
    assert [block["position"] for block in report["blocks"]] == [0, 1, 2]


def test_generation_input_is_the_curated_dump_only(client: TestClient, sample_tree: Path) -> None:
    _generated_report(client, sample_tree)
    dump_text = _fake(client).calls[-1][1][0]
    assert "A quoted snippet." in dump_text
    assert "Merged expert thought, lightly edited." in dump_text
    assert "My own thought about the reading." in dump_text
    assert "alpha.md" in dump_text
    assert "[snippet]" in dump_text and "[ai-thought]" in dump_text


def test_block_manual_edit_persists(client: TestClient, sample_tree: Path) -> None:
    ids = _generated_report(client, sample_tree)
    report_id = ids["report_id"]
    first_block = _report_blocks(client, report_id)[0]
    edited = client.put(
        f"/api/v1/blocks/{first_block['id']}",
        json={"content": "My rewritten opening paragraph."},
    )
    assert edited.status_code == 200
    assert edited.json()["content"] == "My rewritten opening paragraph."
    assert edited.json()["updated_at"] != first_block["updated_at"]

    persisted = _report_blocks(client, report_id)
    assert persisted[0]["content"] == "My rewritten opening paragraph."
    assert persisted[1]["content"] == PARAGRAPHS[1]
    assert client.put("/api/v1/blocks/999999", json={"content": "x"}).status_code == 404
    assert (
        client.put(f"/api/v1/blocks/{first_block['id']}", json={"content": ""}).status_code == 422
    )


def test_tone_samples_five_and_no_auto_replace(client: TestClient, sample_tree: Path) -> None:
    ids = _generated_report(client, sample_tree)
    report_id = ids["report_id"]
    blocks = _report_blocks(client, report_id)
    target = blocks[1]
    before = target["content"]
    before_updated_at = target["updated_at"]

    response = client.post(f"/api/v1/blocks/{target['id']}/tone-samples", json={})
    assert response.status_code == 200
    samples = response.json()["samples"]
    assert len(samples) == 5
    assert len({s["tone"] for s in samples}) == 5

    call = _fake(client).calls[-1]
    assert call[0] == "tone_samples"
    block_arg, context_arg = call[1]
    assert block_arg == before
    assert blocks[0]["content"] in context_arg

    after = _report_blocks(client, report_id)
    assert after[1]["content"] == before
    assert after[1]["updated_at"] == before_updated_at


def test_critique_returns_text_without_editing(client: TestClient, sample_tree: Path) -> None:
    ids = _generated_report(client, sample_tree)
    report_id = ids["report_id"]
    blocks = _report_blocks(client, report_id)
    target = blocks[2]
    before = target["content"]
    before_updated_at = target["updated_at"]

    response = client.post(f"/api/v1/blocks/{target['id']}/critique", json={})
    assert response.status_code == 200
    critique = response.json()["critique"]
    assert len(critique) > 20

    call = _fake(client).calls[-1]
    assert call[0] == "critique"
    block_arg, context_arg = call[1]
    assert block_arg == before
    assert blocks[0]["content"] in context_arg

    after = _report_blocks(client, report_id)
    assert after[2]["content"] == before
    assert after[2]["updated_at"] == before_updated_at


def test_critique_and_tone_use_other_blocks_as_context(
    client: TestClient, sample_tree: Path
) -> None:
    ids = _generated_report(client, sample_tree)
    report_id = ids["report_id"]
    blocks = _report_blocks(client, report_id)
    target = blocks[0]
    client.post(f"/api/v1/blocks/{target['id']}/tone-samples", json={})
    tone_call = _fake(client).calls[-1]
    assert blocks[1]["content"] in tone_call[1][1]
    assert blocks[2]["content"] in tone_call[1][1]
    client.post(f"/api/v1/blocks/{target['id']}/critique", json={})
    critique_call = _fake(client).calls[-1]
    assert blocks[1]["content"] in critique_call[1][1]


def test_export_markdown(client: TestClient, sample_tree: Path) -> None:
    ids = _generated_report(client, sample_tree)
    report_id = ids["report_id"]
    response = client.get(f"/api/v1/reports/{report_id}/export.md")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    body = response.text
    for paragraph in PARAGRAPHS:
        assert paragraph in body
    assert body.strip().endswith(PARAGRAPHS[-1])


def test_delete_report_requires_confirm(client: TestClient, sample_tree: Path) -> None:
    ids = _generated_report(client, sample_tree)
    report_id = ids["report_id"]
    round_id = ids["round_id"]

    refused = client.request("DELETE", f"/api/v1/reports/{report_id}", json={"confirm": False})
    assert refused.status_code == 400
    assert "confirm" in refused.json()["detail"]
    assert client.get(f"/api/v1/reports/{report_id}").status_code == 200

    missing_body = client.request("DELETE", f"/api/v1/reports/{report_id}")
    assert missing_body.status_code == 422

    deleted = client.request("DELETE", f"/api/v1/reports/{report_id}", json={"confirm": True})
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/reports/{report_id}").status_code == 404

    detail = client.get(f"/api/v1/rounds/{round_id}").json()
    assert detail["stage"] == "editing"
    assert detail["report_id"] is None
    assert detail["dump_id"] is not None

    regenerate = client.post(f"/api/v1/rounds/{round_id}/generate-report", json={})
    assert regenerate.status_code == 409
    assert (
        client.request("DELETE", "/api/v1/reports/999999", json={"confirm": True}).status_code
        == 404
    )


def _round_report_state(
    harness: Harness, report_id: int, round_id: int
) -> tuple[
    tuple[object, ...],
    tuple[tuple[object, ...], ...],
    tuple[object, ...],
]:
    """Canonical (report row, block rows, round row) snapshot from the DB."""
    conn = direct_db(harness.db_path)
    report = conn.execute(
        "SELECT id, round_id, created_at FROM reports WHERE id = ?",
        (report_id,),
    ).fetchone()
    blocks = conn.execute(
        """SELECT id, report_id, position, content, created_at, updated_at
           FROM report_blocks WHERE report_id = ? ORDER BY position""",
        (report_id,),
    ).fetchall()
    round_row = conn.execute(
        "SELECT stage, updated_at FROM reading_rounds WHERE id = ?",
        (round_id,),
    ).fetchone()
    conn.close()
    assert report is not None and round_row is not None
    return tuple(report), tuple(tuple(block) for block in blocks), tuple(round_row)


def test_view_mode_read_path_returns_saved_blocks_and_mutates_nothing(
    harness: Harness, client: TestClient, sample_tree: Path
) -> None:
    ids = _generated_report(client, sample_tree)
    report_id, round_id = ids["report_id"], ids["round_id"]
    before = _round_report_state(harness, report_id, round_id)
    saved_block_ids = [row[0] for row in before[1]]
    assert len(saved_block_ids) == 3

    fetched = client.get(f"/api/v1/reports/{report_id}")
    assert fetched.status_code == 200
    report = fetched.json()
    assert report["id"] == report_id
    assert report["round_id"] == round_id
    assert [block["id"] for block in report["blocks"]] == saved_block_ids
    assert [block["content"] for block in report["blocks"]] == PARAGRAPHS
    assert [block["position"] for block in report["blocks"]] == [0, 1, 2]

    exported = client.get(f"/api/v1/reports/{report_id}/export.md")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert exported.text == "\n\n".join(PARAGRAPHS) + "\n"

    detail = client.get(f"/api/v1/rounds/{round_id}")
    assert detail.status_code == 200
    assert detail.json()["stage"] == "editing"
    assert detail.json()["report_id"] == report_id

    assert _round_report_state(harness, report_id, round_id) == before


def test_view_mode_read_path_returns_edited_rows_and_mutates_nothing(
    harness: Harness, client: TestClient, sample_tree: Path
) -> None:
    ids = _generated_report(client, sample_tree)
    report_id, round_id = ids["report_id"], ids["round_id"]
    edited_content = "My rewritten opening paragraph."
    edited = client.put(
        f"/api/v1/blocks/{_report_blocks(client, report_id)[0]['id']}",
        json={"content": edited_content},
    )
    assert edited.status_code == 200
    expected_contents = [edited_content, PARAGRAPHS[1], PARAGRAPHS[2]]
    saved = _round_report_state(harness, report_id, round_id)

    fetched = client.get(f"/api/v1/reports/{report_id}")
    assert fetched.status_code == 200
    blocks = fetched.json()["blocks"]
    assert [block["content"] for block in blocks] == expected_contents
    assert blocks[0]["updated_at"] == edited.json()["updated_at"]

    exported = client.get(f"/api/v1/reports/{report_id}/export.md")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert exported.text == "\n\n".join(expected_contents) + "\n"

    detail = client.get(f"/api/v1/rounds/{round_id}")
    assert detail.status_code == 200
    assert detail.json()["stage"] == "editing"
    assert detail.json()["report_id"] == report_id

    assert _round_report_state(harness, report_id, round_id) == saved
