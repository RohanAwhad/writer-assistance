"""Shared fixtures: offline test app with a fake AI client (spec SD-16)."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.client import (
    ExpertNoteDraft,
    LensDraft,
    ParagraphDraft,
    ToneSampleDraft,
)
from app.deps import get_ai_client
from app.main import create_app

ALPHA_CONTENT = (
    "Alpha opening line.\n\n"
    "A second paragraph that contains a phrase worth highlighting.\n\n"
    "Third paragraph with more detail.\n"
)
BETA_CONTENT = "Beta file with some text.\n\nAnd a second paragraph.\n"
CHAPTER_CONTENT = "# Chapter\n\nSubdirectory document content for the round.\n"
MARKER = "phrase worth highlighting"
PARAGRAPHS = [
    "Report opening paragraph.",
    "Report body paragraph with substance.",
    "Report closing paragraph.",
]


class FakeAI:
    """AIClient fake: canned outputs, records every call for payload assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.lens_drafts = [
            LensDraft("Financial", "Finance reading of the document."),
            LensDraft("Political", "Political science reading of the document."),
            LensDraft("Software engineering", "Engineering reading of the document."),
        ]
        self.note_drafts = [
            ExpertNoteDraft("Expert observation one."),
            ExpertNoteDraft("Expert observation two."),
            ExpertNoteDraft("Expert observation three."),
        ]
        self.paragraphs = [ParagraphDraft(p) for p in PARAGRAPHS]
        self.tones = [
            ToneSampleDraft("confident", "Confident tone sample text."),
            ToneSampleDraft("conversational", "Conversational tone sample text."),
            ToneSampleDraft("urgent", "Urgent tone sample text."),
            ToneSampleDraft("measured", "Measured tone sample text."),
            ToneSampleDraft("vivid", "Vivid tone sample text."),
        ]
        self.critique_text = (
            "The paragraph asserts causation without evidence; a counter-argument "
            "is that correlation alone is shown."
        )

    def propose_lenses(self, doc_path: str, doc_content: str) -> list[LensDraft]:
        self.calls.append(("propose_lenses", (doc_path, doc_content)))
        return list(self.lens_drafts)

    def expert_notes(
        self, doc_path: str, doc_content: str, lens_title: str
    ) -> list[ExpertNoteDraft]:
        self.calls.append(("expert_notes", (doc_path, doc_content, lens_title)))
        return list(self.note_drafts)

    def generate_report(self, dump_text: str) -> list[ParagraphDraft]:
        self.calls.append(("generate_report", (dump_text,)))
        return list(self.paragraphs)

    def tone_samples(self, block: str, report_context: str) -> list[ToneSampleDraft]:
        self.calls.append(("tone_samples", (block, report_context)))
        return list(self.tones)

    def critique(self, block: str, report_context: str) -> str:
        self.calls.append(("critique", (block, report_context)))
        return self.critique_text


class Harness(NamedTuple):
    app: FastAPI
    fake: FakeAI
    db_path: Path


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    root = tmp_path / "library"
    root.mkdir()
    (root / "alpha.md").write_text(ALPHA_CONTENT, encoding="utf-8")
    (root / "beta.md").write_text(BETA_CONTENT, encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "chapter.md").write_text(CHAPTER_CONTENT, encoding="utf-8")
    (root / "sub" / "ignore.txt").write_text("not markdown", encoding="utf-8")
    (root / ".hidden.md").write_text("hidden", encoding="utf-8")
    (root / ".dotdir").mkdir()
    (root / ".dotdir" / "inside.md").write_text("hidden dir", encoding="utf-8")
    (root / "emptydir").mkdir()
    return root


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    fake = FakeAI()
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.dependency_overrides[get_ai_client] = lambda: fake
    app.state.fake_ai = fake
    return Harness(app=app, fake=fake, db_path=tmp_path / "test.db")


@pytest.fixture
def client(harness: Harness) -> Iterator[TestClient]:
    with TestClient(harness.app) as c:
        yield c


def imported_project(
    client: TestClient, root: Path, name: str = "Project"
) -> tuple[int, dict[str, int]]:
    """Create a project, import the tree, return (project_id, path -> node id)."""
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 201, response.text
    project_id = int(response.json()["id"])
    response = client.post(f"/api/v1/projects/{project_id}/import", json={"path": str(root)})
    assert response.status_code == 201, response.text
    tree = client.get(f"/api/v1/projects/{project_id}/tree").json()["nodes"]
    files = {node["path"]: int(node["id"]) for node in tree if node["kind"] == "file"}
    return project_id, files


def make_round(client: TestClient, project_id: int, doc_ids: list[int]) -> int:
    response = client.post(
        "/api/v1/rounds",
        json={"project_id": project_id, "doc_ids": doc_ids},
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def select_and_run_experts(
    client: TestClient, round_id: int, doc_id: int, proposal_index: int = 0
) -> int:
    """Propose lenses on doc_id, select one, run it in the round; returns run id."""
    response = client.post(f"/api/v1/resources/{doc_id}/lens-proposals", json={})
    assert response.status_code == 201, response.text
    proposals = response.json()
    proposal_id = int(proposals[proposal_index]["id"])
    response = client.patch(f"/api/v1/lens-proposals/{proposal_id}", json={"status": "selected"})
    assert response.status_code == 200, response.text
    response = client.post(
        f"/api/v1/rounds/{round_id}/experts",
        json={"lens_proposal_ids": [proposal_id]},
    )
    assert response.status_code == 201, response.text
    return int(response.json()["expert_runs"][0]["id"])


def full_round_to_report(client: TestClient, project_id: int, doc_ids: list[int]) -> dict[str, int]:
    """Drive a round through dump save + generate; returns ids for later asserts."""
    round_id = make_round(client, project_id, doc_ids)
    first_doc = doc_ids[0]
    run_id = select_and_run_experts(client, round_id, first_doc)
    notes = client.get(f"/api/v1/expert-runs/{run_id}/notes").json()["notes"]
    first_note_id = int(notes[0]["id"])
    merged = client.post(
        f"/api/v1/expert-notes/{first_note_id}/merge",
        json={"content": "Merged expert thought, lightly edited."},
    )
    assert merged.status_code == 201, merged.text
    pool_entry_id = int(merged.json()["id"])
    dump_body = {
        "entries": [
            {"kind": "snippet", "content": "A quoted snippet.", "doc_id": first_doc},
            {
                "id": pool_entry_id,
                "kind": "ai-thought",
                "content": "Merged expert thought, lightly edited.",
            },
            {"kind": "human-thought", "content": "My own thought about the reading."},
        ]
    }
    response = client.post(f"/api/v1/rounds/{round_id}/dump", json=dump_body)
    assert response.status_code == 200, response.text
    response = client.post(f"/api/v1/rounds/{round_id}/generate-report", json={})
    assert response.status_code == 201, response.text
    report = response.json()
    return {
        "round_id": round_id,
        "run_id": run_id,
        "report_id": int(report["id"]),
        "pool_entry_id": pool_entry_id,
    }


def direct_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
