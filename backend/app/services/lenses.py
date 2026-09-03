"""Lens proposals per doc (F3, R-020, OQ-06: AI-proposed lenses only)."""

import sqlite3

from app.ai.client import AIClient
from app.db import iter_rows, now_utc
from app.errors import BadRequestError, NotFoundError
from app.schemas import LensProposalOut
from app.services.resources import require_file_doc


def _proposal_out(conn: sqlite3.Connection, proposal_id: int) -> LensProposalOut:
    row = conn.execute(
        """SELECT id, doc_id, title, rationale, status, created_at
           FROM lens_proposals WHERE id = ?""",
        (proposal_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"lens proposal {proposal_id} not found")
    return LensProposalOut(
        id=int(row["id"]),
        doc_id=int(row["doc_id"]),
        title=str(row["title"]),
        rationale=str(row["rationale"]),
        status=row["status"],
        created_at=row["created_at"],
    )


def propose_lenses(conn: sqlite3.Connection, ai: AIClient, doc_id: int) -> list[LensProposalOut]:
    doc = require_file_doc(conn, doc_id)
    drafts = ai.propose_lenses(str(doc["path"]), str(doc["content"]))
    ts = now_utc()
    conn.execute(
        "DELETE FROM lens_proposals WHERE doc_id = ? AND status = 'proposed'",
        (doc_id,),
    )
    ids: list[int] = []
    for draft in drafts:
        inserted = conn.execute(
            """INSERT INTO lens_proposals (doc_id, title, rationale, status, created_at)
               VALUES (?, ?, ?, 'proposed', ?) RETURNING id""",
            (doc_id, draft.title, draft.rationale, ts),
        ).fetchone()
        if inserted is None:
            raise RuntimeError("lens proposal insert returned no row")
        ids.append(int(inserted["id"]))
    conn.commit()
    return [_proposal_out(conn, proposal_id) for proposal_id in ids]


def list_lens_proposals(conn: sqlite3.Connection, doc_id: int) -> list[LensProposalOut]:
    require_file_doc(conn, doc_id)
    rows = list(
        iter_rows(
            conn,
            """SELECT id FROM lens_proposals WHERE doc_id = ? ORDER BY id""",
            (doc_id,),
        )
    )
    return [_proposal_out(conn, int(row["id"])) for row in rows]


def update_lens_proposal_status(
    conn: sqlite3.Connection, proposal_id: int, status: str
) -> LensProposalOut:
    row = conn.execute(
        "SELECT status FROM lens_proposals WHERE id = ?", (proposal_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"lens proposal {proposal_id} not found")
    if status == "proposed":
        raise BadRequestError("a lens proposal cannot be set back to 'proposed'")
    conn.execute(
        "UPDATE lens_proposals SET status = ? WHERE id = ?", (status, proposal_id)
    )
    conn.commit()
    return _proposal_out(conn, proposal_id)
