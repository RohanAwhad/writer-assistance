"""Read-only invariant for imported resource snapshots (R-011/R-012, §11.1).

Drives a full reading -> annotate -> (mocked AI) -> report -> edit -> assist
path, then asserts every imported snapshot is byte-identical via both the API
and a direct DB helper.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import (
    ALPHA_CONTENT,
    BETA_CONTENT,
    CHAPTER_CONTENT,
    MARKER,
    Harness,
    direct_db,
    full_round_to_report,
    imported_project,
)


def _resource_contents(client: TestClient, doc_ids: list[int]) -> dict[int, str]:
    return {
        doc_id: client.get(f"/api/v1/resources/{doc_id}").json()["content"] for doc_id in doc_ids
    }


def test_snapshot_byte_identical_through_full_flow(
    harness: Harness, client: TestClient, sample_tree: Path
) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id, beta_id, chapter_id = (
        files["alpha.md"],
        files["beta.md"],
        files["sub/chapter.md"],
    )
    expected = {
        alpha_id: ALPHA_CONTENT,
        beta_id: BETA_CONTENT,
        chapter_id: CHAPTER_CONTENT,
    }
    initial = _resource_contents(client, [alpha_id, beta_id, chapter_id])
    assert initial == expected

    start, end = ALPHA_CONTENT.index(MARKER), ALPHA_CONTENT.index(MARKER) + len(MARKER)
    client.post(
        f"/api/v1/resources/{alpha_id}/highlights",
        json={"start_offset": start, "end_offset": end, "content": "attached note"},
    )
    client.post(f"/api/v1/resources/{alpha_id}/notes", json={"content": "Free note."})

    ids = full_round_to_report(client, project_id, [alpha_id, beta_id])
    report_id = ids["report_id"]

    blocks = client.get(f"/api/v1/reports/{report_id}").json()["blocks"]
    for block in blocks:
        assert (
            client.put(
                f"/api/v1/blocks/{block['id']}", json={"content": "Edited by hand."}
            ).status_code
            == 200
        )
        tone = client.post(f"/api/v1/blocks/{block['id']}/tone-samples", json={})
        assert tone.status_code == 200
        critique = client.post(f"/api/v1/blocks/{block['id']}/critique", json={})
        assert critique.status_code == 200

    client.get(f"/api/v1/reports/{report_id}/export.md")

    after_api = _resource_contents(client, [alpha_id, beta_id, chapter_id])
    assert after_api == expected == initial

    conn = direct_db(harness.db_path)
    rows = conn.execute(
        """SELECT d.content FROM resource_docs d
           JOIN resource_nodes n ON n.id = d.node_id
           WHERE n.project_id = ? ORDER BY n.path""",
        (project_id,),
    ).fetchall()
    stored = sorted(str(row["content"]) for row in rows)
    assert stored == sorted(expected.values())
    assert len(rows) == 3
    conn.close()


def test_direct_db_still_holds_snapshot_after_annotations(
    harness: Harness, client: TestClient, sample_tree: Path
) -> None:
    project_id, files = imported_project(client, sample_tree)
    alpha_id = files["alpha.md"]
    client.post(
        f"/api/v1/resources/{alpha_id}/highlights",
        json={"start_offset": 0, "end_offset": 5},
    )
    client.post(f"/api/v1/resources/{alpha_id}/notes", json={"content": "x"})
    conn = direct_db(harness.db_path)
    original = conn.execute(
        """SELECT d.content FROM resource_docs d
           JOIN resource_nodes n ON n.id = d.node_id
           WHERE n.project_id = ? AND n.path = 'alpha.md'""",
        (project_id,),
    ).fetchone()
    assert original is not None
    assert str(original["content"]) == ALPHA_CONTENT
    conn.close()
