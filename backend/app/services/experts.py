"""Expert runs and their notes (F4/F5, R-021/R-022): AI notes per doc x lens,
reviewed by the human, mergeable into the round's dump pool with provenance.
"""

import sqlite3

from app.ai.client import AIClient
from app.db import iter_rows, now_utc
from app.errors import BadRequestError, ConflictError, NotFoundError
from app.schemas import (
    DumpEntryOut,
    ExpertNoteOut,
    ExpertNoteState,
    ExpertRunOut,
    ExpertRunsOut,
)
from app.services import rounds as rounds_service
from app.services.resources import require_file_doc

_FINAL_STATES = ("accepted", "discarded", "merged-with-edits")


def _note_out(conn: sqlite3.Connection, note_id: int) -> ExpertNoteOut:
    row = conn.execute(
        """SELECT en.id, en.expert_run_id, en.content, en.edited_content, en.review_state,
                  en.position,
                  EXISTS(SELECT 1 FROM notes_dump_entries e
                         WHERE e.expert_note_id = en.id) AS merged
           FROM expert_notes en WHERE en.id = ?""",
        (note_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"expert note {note_id} not found")
    return ExpertNoteOut(
        id=int(row["id"]),
        expert_run_id=int(row["expert_run_id"]),
        content=str(row["content"]),
        edited_content=row["edited_content"],
        review_state=row["review_state"],
        merged=int(row["merged"]) == 1,
        position=int(row["position"]),
    )


def _run_out(conn: sqlite3.Connection, run_id: int) -> ExpertRunOut:
    run = conn.execute(
        """SELECT r.id, r.round_id, r.doc_id, r.lens_proposal_id, r.lens_title,
                  n.path AS doc_path, lp.rationale AS lens_rationale
           FROM expert_runs r
           JOIN resource_nodes n ON n.id = r.doc_id
           JOIN lens_proposals lp ON lp.id = r.lens_proposal_id
           WHERE r.id = ?""",
        (run_id,),
    ).fetchone()
    if run is None:
        raise NotFoundError(f"expert run {run_id} not found")
    notes = [
        _note_out(conn, int(row["id"]))
        for row in iter_rows(
            conn,
            """SELECT id FROM expert_notes
               WHERE expert_run_id = ? ORDER BY position""",
            (run_id,),
        )
    ]
    return ExpertRunOut(
        id=int(run["id"]),
        round_id=int(run["round_id"]),
        doc_id=int(run["doc_id"]),
        doc_path=str(run["doc_path"]),
        lens_proposal_id=int(run["lens_proposal_id"]),
        lens_rationale=str(run["lens_rationale"]),
        lens_title=str(run["lens_title"]),
        notes=notes,
    )


def run_experts(
    conn: sqlite3.Connection,
    ai: AIClient,
    round_id: int,
    lens_proposal_ids: list[int],
) -> ExpertRunsOut:
    rounds_service.require_round_reading(conn, round_id)
    ts = now_utc()
    created_run_ids: list[int] = []
    for proposal_id in dict.fromkeys(lens_proposal_ids):
        proposal = conn.execute(
            """SELECT lp.id, lp.doc_id, lp.title, lp.status
               FROM lens_proposals lp WHERE lp.id = ?""",
            (proposal_id,),
        ).fetchone()
        if proposal is None:
            raise NotFoundError(f"lens proposal {proposal_id} not found")
        doc_id = int(proposal["doc_id"])
        lens_title = str(proposal["title"])
        if str(proposal["status"]) != "selected":
            raise ConflictError(
                f"lens proposal {proposal_id} is '{proposal['status']}'; "
                "select it before running experts"
            )
        in_round = conn.execute(
            "SELECT 1 FROM round_docs WHERE round_id = ? AND node_id = ?",
            (round_id, doc_id),
        ).fetchone()
        if in_round is None:
            raise ConflictError(
                f"lens proposal {proposal_id} targets a doc that is not in the round's doc set"
            )
        duplicate = conn.execute(
            """SELECT id FROM expert_runs
               WHERE round_id = ? AND doc_id = ? AND lens_title = ?""",
            (round_id, doc_id, lens_title),
        ).fetchone()
        if duplicate is not None:
            raise ConflictError(
                f"expert for lens '{lens_title}' already ran on this doc in this round"
            )
        doc = require_file_doc(conn, doc_id)
        drafts = ai.expert_notes(str(doc["path"]), str(doc["content"]), lens_title)
        inserted_run = conn.execute(
            """INSERT INTO expert_runs (round_id, doc_id, lens_proposal_id, lens_title, created_at)
               VALUES (?, ?, ?, ?, ?) RETURNING id""",
            (round_id, doc_id, proposal_id, lens_title, ts),
        ).fetchone()
        if inserted_run is None:
            raise RuntimeError("expert run insert returned no row")
        run_id = int(inserted_run["id"])
        created_run_ids.append(run_id)
        for position, draft in enumerate(drafts):
            conn.execute(
                """INSERT INTO expert_notes
                   (expert_run_id, content, review_state, position, created_at)
                   VALUES (?, ?, 'pending', ?, ?)""",
                (run_id, draft.content, position, ts),
            )
    conn.commit()
    runs = [_run_out(conn, run_id) for run_id in created_run_ids]
    return ExpertRunsOut(expert_runs=runs)


def get_expert_run_notes(conn: sqlite3.Connection, run_id: int) -> ExpertRunOut:
    return _run_out(conn, run_id)


def list_round_expert_runs(conn: sqlite3.Connection, round_id: int) -> ExpertRunsOut:
    """The round's expert runs with lens/doc info and notes, for re-review after reload."""
    rounds_service.require_round(conn, round_id)
    rows = list(
        iter_rows(
            conn,
            "SELECT id FROM expert_runs WHERE round_id = ? ORDER BY id",
            (round_id,),
        )
    )
    return ExpertRunsOut(expert_runs=[_run_out(conn, int(row["id"])) for row in rows])


def _require_reviewable(conn: sqlite3.Connection, note_id: int) -> tuple[sqlite3.Row, sqlite3.Row]:
    note = conn.execute(
        """SELECT en.id, en.expert_run_id, en.content, en.edited_content, en.review_state
           FROM expert_notes en WHERE en.id = ?""",
        (note_id,),
    ).fetchone()
    if note is None:
        raise NotFoundError(f"expert note {note_id} not found")
    run = conn.execute(
        "SELECT id, round_id, doc_id FROM expert_runs WHERE id = ?",
        (int(note["expert_run_id"]),),
    ).fetchone()
    if run is None:
        raise RuntimeError(f"expert run for note {note_id} missing")
    rounds_service.require_round_reading(conn, int(run["round_id"]))
    return note, run


def update_expert_note(
    conn: sqlite3.Connection,
    note_id: int,
    review_state: ExpertNoteState,
    content: str | None,
) -> ExpertNoteOut:
    note, _run = _require_reviewable(conn, note_id)
    current = str(note["review_state"])
    if current == "discarded":
        raise ConflictError("a discarded expert note cannot be reviewed further")
    if review_state == "merged-with-edits":
        if content is None and note["edited_content"] is None:
            raise BadRequestError("merged-with-edits requires edited content (content field)")
        edits = content if content is not None else note["edited_content"]
        conn.execute(
            "UPDATE expert_notes SET review_state = ?, edited_content = ? WHERE id = ?",
            (review_state, edits, note_id),
        )
    elif review_state == "pending":
        if current != "pending":
            raise ConflictError("a reviewed expert note cannot be reopened")
        conn.execute(
            "UPDATE expert_notes SET review_state = ? WHERE id = ?",
            (review_state, note_id),
        )
    else:
        if current in _FINAL_STATES and current != review_state:
            raise ConflictError(f"expert note is '{current}'; its review state is final")
        conn.execute(
            "UPDATE expert_notes SET review_state = ? WHERE id = ?",
            (review_state, note_id),
        )
    conn.commit()
    return _note_out(conn, note_id)


def merge_expert_note(
    conn: sqlite3.Connection,
    note_id: int,
    content: str | None,
) -> DumpEntryOut:
    note, run = _require_reviewable(conn, note_id)
    current = str(note["review_state"])
    if current == "discarded":
        raise ConflictError("a discarded expert note cannot be merged")
    already = conn.execute(
        """SELECT 1 FROM notes_dump_entries
           WHERE expert_note_id = ? AND kind = 'ai-thought'""",
        (note_id,),
    ).fetchone()
    if already is not None:
        raise ConflictError("expert note is already merged into the dump pool")
    edited = content if content is not None else note["edited_content"]
    if content is not None:
        conn.execute(
            """UPDATE expert_notes
               SET review_state = 'merged-with-edits', edited_content = ?
               WHERE id = ?""",
            (content, note_id),
        )
        merged_text = content
    elif current == "merged-with-edits" and edited is not None:
        merged_text = str(edited)
    else:
        conn.execute(
            "UPDATE expert_notes SET review_state = 'accepted' WHERE id = ?",
            (note_id,),
        )
        merged_text = str(note["content"])
    entry = rounds_service.attach_entry(
        conn,
        int(run["round_id"]),
        kind="ai-thought",
        content=merged_text,
        doc_id=int(run["doc_id"]),
        expert_note_id=note_id,
    )
    conn.commit()
    return entry
