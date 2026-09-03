"""Reading rounds, the curated notes dump, and its pool (F6, R-030/R-031, OQ-02/03).

A dump's entries live in one of two states: attached (dump_id set, ordered)
or detached pool (dump_id NULL — entries dropped from the dump by a re-save,
awaiting re-attachment). Merged expert notes attach to the round's dump
immediately (the dump row is created on demand); saving the dump replaces its
entry set with the submitted ordered list and detaches unlisted entries.
"""

import sqlite3

from app.db import fetch_one, iter_rows, now_utc
from app.errors import BadRequestError, ConflictError, NotFoundError
from app.schemas import (
    DumpEntryOut,
    DumpOut,
    DumpSaveRequest,
    RoundDetailOut,
    RoundDocOut,
    RoundOut,
    RoundSummary,
)

_ROUND_COLS = "id, project_id, name, stage, created_at, updated_at"


def require_round(conn: sqlite3.Connection, round_id: int) -> sqlite3.Row:
    row = fetch_one(conn, f"SELECT {_ROUND_COLS} FROM reading_rounds WHERE id = ?", (round_id,))
    if row is None:
        raise NotFoundError(f"round {round_id} not found")
    return row


def require_round_reading(conn: sqlite3.Connection, round_id: int) -> sqlite3.Row:
    row = require_round(conn, round_id)
    if str(row["stage"]) != "reading":
        raise ConflictError(
            "round is in the 'editing' stage; its reading actions are closed (R-042)"
        )
    return row


def require_project(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row:
    row = fetch_one(conn, "SELECT id FROM projects WHERE id = ?", (project_id,))
    if row is None:
        raise NotFoundError(f"project {project_id} not found")
    return row


def _round_out(conn: sqlite3.Connection, round_id: int) -> RoundOut:
    row = require_round(conn, round_id)
    doc_ids = [
        int(r["node_id"])
        for r in iter_rows(
            conn,
            "SELECT node_id FROM round_docs WHERE round_id = ? ORDER BY position",
            (round_id,),
        )
    ]
    return RoundOut(
        id=int(row["id"]),
        project_id=int(row["project_id"]),
        name=str(row["name"]),
        stage=row["stage"],
        doc_ids=doc_ids,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_round(
    conn: sqlite3.Connection,
    project_id: int,
    doc_ids: list[int],
    name: str | None,
) -> RoundOut:
    require_project(conn, project_id)
    ordered: list[int] = list(dict.fromkeys(doc_ids))
    if len(ordered) != len(doc_ids):
        raise BadRequestError("doc_ids contains duplicates")
    placeholders = ",".join("?" for _ in ordered)
    if not ordered:
        raise BadRequestError("a round needs at least one doc")
    found: set[int] = set()
    for row in conn.execute(
        f"""SELECT id FROM resource_nodes
            WHERE project_id = ? AND is_dir = 0 AND id IN ({placeholders})""",
        (project_id, *ordered),
    ):
        found.add(int(row["id"]))
    missing = [doc_id for doc_id in ordered if doc_id not in found]
    if missing:
        raise BadRequestError(
            f"doc_ids not found among project resources: {', '.join(str(i) for i in missing)}"
        )
    ts = now_utc()
    count_row = conn.execute(
        "SELECT COUNT(*) AS n FROM reading_rounds WHERE project_id = ?", (project_id,)
    ).fetchone()
    count = int(count_row["n"]) if count_row is not None else 0
    round_name = name if name is not None else f"Round {count + 1}"
    inserted = conn.execute(
        """INSERT INTO reading_rounds (project_id, name, stage, created_at, updated_at)
           VALUES (?, ?, 'reading', ?, ?) RETURNING id""",
        (project_id, round_name, ts, ts),
    ).fetchone()
    if inserted is None:
        raise RuntimeError("round insert returned no row")
    round_id = int(inserted["id"])
    for position, doc_id in enumerate(ordered):
        conn.execute(
            "INSERT INTO round_docs (round_id, node_id, position) VALUES (?, ?, ?)",
            (round_id, doc_id, position),
        )
    conn.commit()
    return _round_out(conn, round_id)


def list_round_summaries(conn: sqlite3.Connection, project_id: int) -> list[RoundSummary]:
    require_project(conn, project_id)
    summaries: list[RoundSummary] = []
    for row in iter_rows(
        conn,
        """SELECT r.id, r.project_id, r.name, r.stage, r.created_at,
                  (SELECT COUNT(*) FROM round_docs rd WHERE rd.round_id = r.id) AS doc_count,
                  (SELECT d.id FROM notes_dumps d WHERE d.round_id = r.id) AS dump_id,
                  (SELECT p.id FROM reports p WHERE p.round_id = r.id) AS report_id
           FROM reading_rounds r
           WHERE r.project_id = ? ORDER BY r.id DESC""",
        (project_id,),
    ):
        summaries.append(
            RoundSummary(
                id=int(row["id"]),
                project_id=int(row["project_id"]),
                name=str(row["name"]),
                stage=row["stage"],
                doc_count=int(row["doc_count"]),
                created_at=row["created_at"],
                dump_id=int(row["dump_id"]) if row["dump_id"] is not None else None,
                report_id=int(row["report_id"]) if row["report_id"] is not None else None,
            )
        )
    return summaries


def round_detail(conn: sqlite3.Connection, round_id: int) -> RoundDetailOut:
    row = require_round(conn, round_id)
    docs = [
        RoundDocOut(id=int(r["node_id"]), path=str(r["path"]))
        for r in iter_rows(
            conn,
            """SELECT rd.node_id, n.path FROM round_docs rd
               JOIN resource_nodes n ON n.id = rd.node_id
               WHERE rd.round_id = ? ORDER BY rd.position""",
            (round_id,),
        )
    ]
    dump_row = conn.execute("SELECT id FROM notes_dumps WHERE round_id = ?", (round_id,)).fetchone()
    report_row = conn.execute("SELECT id FROM reports WHERE round_id = ?", (round_id,)).fetchone()
    return RoundDetailOut(
        id=int(row["id"]),
        project_id=int(row["project_id"]),
        name=str(row["name"]),
        stage=row["stage"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        docs=docs,
        dump_id=int(dump_row["id"]) if dump_row is not None else None,
        report_id=int(report_row["id"]) if report_row is not None else None,
    )


def get_entry_out(conn: sqlite3.Connection, entry_id: int) -> DumpEntryOut:
    row = conn.execute(
        """SELECT e.id, e.dump_id, e.round_id, e.kind, e.content, e.doc_id,
                  e.expert_note_id, e.position, e.created_at,
                  n.path AS doc_path
           FROM notes_dump_entries e
           LEFT JOIN resource_nodes n ON n.id = e.doc_id
           WHERE e.id = ?""",
        (entry_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"dump entry {entry_id} not found")
    return DumpEntryOut(
        id=int(row["id"]),
        round_id=int(row["round_id"]),
        dump_id=int(row["dump_id"]) if row["dump_id"] is not None else None,
        kind=row["kind"],
        content=str(row["content"]),
        doc_id=int(row["doc_id"]) if row["doc_id"] is not None else None,
        doc_path=row["doc_path"],
        expert_note_id=(int(row["expert_note_id"]) if row["expert_note_id"] is not None else None),
        position=int(row["position"]) if row["position"] is not None else None,
        created_at=row["created_at"],
    )


def _dump_entries(
    conn: sqlite3.Connection, round_id: int, dump_id: int | None
) -> list[DumpEntryOut]:
    if dump_id is not None:
        rows = list(
            iter_rows(
                conn,
                """SELECT e.id FROM notes_dump_entries e
                   WHERE e.dump_id = ? ORDER BY e.position""",
                (dump_id,),
            )
        )
    else:
        rows = list(
            iter_rows(
                conn,
                """SELECT e.id FROM notes_dump_entries e
                   WHERE e.round_id = ? AND e.dump_id IS NULL
                   ORDER BY e.id""",
                (round_id,),
            )
        )
    return [get_entry_out(conn, int(row["id"])) for row in rows]


def get_dump(conn: sqlite3.Connection, round_id: int) -> DumpOut:
    require_round(conn, round_id)
    dump_row = conn.execute("SELECT id FROM notes_dumps WHERE round_id = ?", (round_id,)).fetchone()
    dump_id = int(dump_row["id"]) if dump_row is not None else None
    return DumpOut(
        round_id=round_id,
        dump_id=dump_id,
        saved=dump_id is not None,
        entries=_dump_entries(conn, round_id, dump_id),
    )


def _require_round_doc(conn: sqlite3.Connection, round_id: int, doc_id: int) -> None:
    row = fetch_one(
        conn,
        "SELECT 1 FROM round_docs WHERE round_id = ? AND node_id = ?",
        (round_id, doc_id),
    )
    if row is None:
        raise BadRequestError(f"doc_id {doc_id} is not part of the round's doc set")


def _dump_id_or_create(conn: sqlite3.Connection, round_id: int, ts: str) -> int:
    dump_row = conn.execute("SELECT id FROM notes_dumps WHERE round_id = ?", (round_id,)).fetchone()
    if dump_row is not None:
        return int(dump_row["id"])
    inserted = conn.execute(
        """INSERT INTO notes_dumps (round_id, created_at, updated_at)
           VALUES (?, ?, ?) RETURNING id""",
        (round_id, ts, ts),
    ).fetchone()
    if inserted is None:
        raise RuntimeError("notes_dumps insert returned no row")
    return int(inserted["id"])


def attach_entry(
    conn: sqlite3.Connection,
    round_id: int,
    kind: str,
    content: str,
    doc_id: int | None,
    expert_note_id: int | None,
) -> DumpEntryOut:
    """Attach a new entry at the end of the round's dump (creating it if absent)."""
    ts = now_utc()
    dump_id = _dump_id_or_create(conn, round_id, ts)
    position_row = conn.execute(
        """SELECT COALESCE(MAX(position), -1) + 1 AS position
           FROM notes_dump_entries WHERE dump_id = ?""",
        (dump_id,),
    ).fetchone()
    position = int(position_row["position"]) if position_row is not None else 0
    inserted = conn.execute(
        """INSERT INTO notes_dump_entries
           (dump_id, round_id, kind, content, doc_id, expert_note_id, position, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
        (dump_id, round_id, kind, content, doc_id, expert_note_id, position, ts),
    ).fetchone()
    if inserted is None:
        raise RuntimeError("notes_dump_entries insert returned no row")
    conn.execute("UPDATE notes_dumps SET updated_at = ? WHERE id = ?", (ts, dump_id))
    return get_entry_out(conn, int(inserted["id"]))


def save_dump(conn: sqlite3.Connection, round_id: int, request: DumpSaveRequest) -> DumpOut:
    require_round_reading(conn, round_id)
    ts = now_utc()
    dump_id = _dump_id_or_create(conn, round_id, ts)

    given_ids = [entry.id for entry in request.entries if entry.id is not None]
    if len(set(given_ids)) != len(given_ids):
        raise BadRequestError("entries contains duplicate entry ids")

    previous = list(
        iter_rows(
            conn,
            "SELECT id, expert_note_id FROM notes_dump_entries WHERE dump_id = ?",
            (dump_id,),
        )
    )
    kept = set(given_ids)
    for row in previous:
        entry_id = int(row["id"])
        if entry_id in kept:
            continue
        if row["expert_note_id"] is not None:
            conn.execute(
                """UPDATE notes_dump_entries
                   SET dump_id = NULL, position = NULL WHERE id = ?""",
                (entry_id,),
            )
        else:
            conn.execute("DELETE FROM notes_dump_entries WHERE id = ?", (entry_id,))

    for position, entry in enumerate(request.entries):
        if entry.doc_id is not None:
            _require_round_doc(conn, round_id, entry.doc_id)
        if entry.id is not None:
            existing = conn.execute(
                "SELECT id, round_id, kind FROM notes_dump_entries WHERE id = ?",
                (entry.id,),
            ).fetchone()
            if existing is None:
                raise BadRequestError(f"dump entry {entry.id} not found")
            if int(existing["round_id"]) != round_id:
                raise BadRequestError(f"dump entry {entry.id} belongs to a different round")
            if str(existing["kind"]) != entry.kind:
                raise BadRequestError(
                    f"dump entry {entry.id} has kind '{existing['kind']}', not '{entry.kind}'"
                )
            conn.execute(
                """UPDATE notes_dump_entries
                   SET dump_id = ?, position = ?, content = ?, doc_id = ?
                   WHERE id = ?""",
                (dump_id, position, entry.content, entry.doc_id, entry.id),
            )
        else:
            conn.execute(
                """INSERT INTO notes_dump_entries
                   (dump_id, round_id, kind, content, doc_id, position, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (dump_id, round_id, entry.kind, entry.content, entry.doc_id, position, ts),
            )
    conn.execute("UPDATE notes_dumps SET updated_at = ? WHERE id = ?", (ts, dump_id))
    conn.commit()
    return DumpOut(
        round_id=round_id,
        dump_id=dump_id,
        saved=True,
        entries=_dump_entries(conn, round_id, dump_id),
    )


def dump_input_text(conn: sqlite3.Connection, round_id: int) -> str:
    """Rendered dump text: the sole input to report generation (R-040)."""
    dump_row = conn.execute("SELECT id FROM notes_dumps WHERE round_id = ?", (round_id,)).fetchone()
    if dump_row is None:
        raise BadRequestError("round has no saved dump; curate and save entries first")
    entries = _dump_entries(conn, round_id, int(dump_row["id"]))
    if not entries:
        raise BadRequestError("round dump is empty; curate and save entries first")
    lines: list[str] = []
    for index, entry in enumerate(entries, start=1):
        source = f" ({entry.doc_path})" if entry.doc_path else ""
        lines.append(f"{index}. [{entry.kind}]{source}\n{entry.content}")
    return "\n\n".join(lines)
