"""Human annotations against doc snapshots (F2, R-012): never written to files."""

import sqlite3

from app.db import fetch_one, iter_rows, now_utc
from app.errors import BadRequestError, NotFoundError
from app.schemas import AnnotationOut, AnnotationUpdate, HighlightCreate, NoteCreate
from app.services.resources import require_file_doc


def _validate_range(start_offset: int, end_offset: int, snapshot_len: int, what: str) -> None:
    if start_offset >= end_offset:
        raise BadRequestError(f"{what}: start_offset must be less than end_offset")
    if end_offset > snapshot_len:
        raise BadRequestError(
            f"{what}: range end {end_offset} exceeds document length {snapshot_len}"
        )


def _annotation_out(conn: sqlite3.Connection, annotation_id: int) -> AnnotationOut:
    row = conn.execute(
        """SELECT id, doc_id, kind, start_offset, end_offset, content, created_at, updated_at
           FROM annotations WHERE id = ?""",
        (annotation_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"annotation {annotation_id} not found")
    return AnnotationOut(
        id=int(row["id"]),
        doc_id=int(row["doc_id"]),
        kind=row["kind"],
        start_offset=int(row["start_offset"]) if row["start_offset"] is not None else None,
        end_offset=int(row["end_offset"]) if row["end_offset"] is not None else None,
        content=row["content"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_highlight(conn: sqlite3.Connection, doc_id: int, req: HighlightCreate) -> AnnotationOut:
    doc = require_file_doc(conn, doc_id)
    _validate_range(req.start_offset, req.end_offset, len(str(doc["content"])), "highlight")
    ts = now_utc()
    inserted = conn.execute(
        """INSERT INTO annotations
           (doc_id, kind, start_offset, end_offset, content, created_at, updated_at)
           VALUES (?, 'highlight', ?, ?, ?, ?, ?) RETURNING id""",
        (doc_id, req.start_offset, req.end_offset, req.content, ts, ts),
    ).fetchone()
    if inserted is None:
        raise RuntimeError("annotation insert returned no row")
    conn.commit()
    return _annotation_out(conn, int(inserted["id"]))


def create_note(conn: sqlite3.Connection, doc_id: int, req: NoteCreate) -> AnnotationOut:
    doc = require_file_doc(conn, doc_id)
    snapshot_len = len(str(doc["content"]))
    if req.start_offset is not None and req.end_offset is not None:
        _validate_range(req.start_offset, req.end_offset, snapshot_len, "note anchor")
    ts = now_utc()
    inserted = conn.execute(
        """INSERT INTO annotations
           (doc_id, kind, start_offset, end_offset, content, created_at, updated_at)
           VALUES (?, 'note', ?, ?, ?, ?, ?) RETURNING id""",
        (doc_id, req.start_offset, req.end_offset, req.content, ts, ts),
    ).fetchone()
    if inserted is None:
        raise RuntimeError("annotation insert returned no row")
    conn.commit()
    return _annotation_out(conn, int(inserted["id"]))


def list_annotations(conn: sqlite3.Connection, doc_id: int) -> list[AnnotationOut]:
    """All annotations (highlights + notes, incl. note-only rows) of a doc snapshot."""
    require_file_doc(conn, doc_id)
    rows = list(
        iter_rows(
            conn,
            """SELECT id FROM annotations
               WHERE doc_id = ?
               ORDER BY start_offset IS NULL, start_offset, created_at, id""",
            (doc_id,),
        )
    )
    return [_annotation_out(conn, int(row["id"])) for row in rows]


def _require_annotation(conn: sqlite3.Connection, annotation_id: int) -> sqlite3.Row:
    row = fetch_one(conn, "SELECT * FROM annotations WHERE id = ?", (annotation_id,))
    if row is None:
        raise NotFoundError(f"annotation {annotation_id} not found")
    return row


def update_annotation(
    conn: sqlite3.Connection, annotation_id: int, req: AnnotationUpdate
) -> AnnotationOut:
    annotation = _require_annotation(conn, annotation_id)
    kind = str(annotation["kind"])
    doc = require_file_doc(conn, int(annotation["doc_id"]))
    snapshot_len = len(str(doc["content"]))
    start = req.start_offset if req.start_offset is not None else int(annotation["start_offset"])
    end = req.end_offset if req.end_offset is not None else int(annotation["end_offset"])
    if kind == "highlight":
        _validate_range(start, end, snapshot_len, "highlight")
    elif req.start_offset is not None and req.end_offset is not None:
        _validate_range(start, end, snapshot_len, "note anchor")
    content = req.content if req.content is not None else annotation["content"]
    if kind == "note" and content is None:
        raise BadRequestError("note requires content")
    ts = now_utc()
    conn.execute(
        """UPDATE annotations
           SET start_offset = ?, end_offset = ?, content = ?, updated_at = ?
           WHERE id = ?""",
        (start, end, content, ts, annotation_id),
    )
    conn.commit()
    return _annotation_out(conn, annotation_id)


def delete_annotation(conn: sqlite3.Connection, annotation_id: int) -> None:
    _require_annotation(conn, annotation_id)
    conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
    conn.commit()
