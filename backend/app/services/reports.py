"""Report lifecycle: one-shot generation from the dump (F7..F11, R-040..R-043,
R-050..R-053, OQ-04/OQ-05), per-block editing and per-block AI assists.

Generation flips the round's stage reading -> editing (SD-9, R-042). The
flip is irreversible: with the report deleted, the round stays in 'editing',
so generation on the same round is refused (one-shot per round, OQ-05).
"""

import sqlite3

from app.ai.client import AIClient, ParagraphDraft
from app.db import fetch_one, iter_rows, now_utc
from app.errors import AIFormatError, BadRequestError, ConflictError, NotFoundError
from app.schemas import (
    CritiqueOut,
    ReportBlockOut,
    ReportOut,
    ToneSampleOut,
    ToneSamplesOut,
)
from app.services import rounds as rounds_service


def require_report(conn: sqlite3.Connection, report_id: int) -> sqlite3.Row:
    row = fetch_one(conn, "SELECT id, round_id, created_at FROM reports WHERE id = ?", (report_id,))
    if row is None:
        raise NotFoundError(f"report {report_id} not found")
    return row


def _block_links(conn: sqlite3.Connection, report_id: int) -> dict[int, list[int]]:
    links: dict[int, list[int]] = {}
    for row in iter_rows(
        conn,
        """SELECT block_id, entry_id FROM report_block_links
           WHERE block_id IN (SELECT id FROM report_blocks WHERE report_id = ?)
           ORDER BY entry_id""",
        (report_id,),
    ):
        links.setdefault(int(row["block_id"]), []).append(int(row["entry_id"]))
    return links


def _blocks(conn: sqlite3.Connection, report_id: int) -> list[ReportBlockOut]:
    links = _block_links(conn, report_id)
    blocks: list[ReportBlockOut] = []
    for row in iter_rows(
        conn,
        """SELECT id, report_id, position, content, created_at, updated_at
           FROM report_blocks WHERE report_id = ? ORDER BY position""",
        (report_id,),
    ):
        block_id = int(row["id"])
        blocks.append(
            ReportBlockOut(
                id=block_id,
                report_id=int(row["report_id"]),
                position=int(row["position"]),
                content=str(row["content"]),
                source_entry_ids=links.get(block_id, []),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return blocks


def get_report(conn: sqlite3.Connection, report_id: int) -> ReportOut:
    row = require_report(conn, report_id)
    return ReportOut(
        id=int(row["id"]),
        round_id=int(row["round_id"]),
        created_at=row["created_at"],
        blocks=_blocks(conn, report_id),
    )


def _require_entries(conn: sqlite3.Connection, round_id: int, dump_id: int) -> set[int]:
    rows = list(
        iter_rows(
            conn,
            "SELECT id FROM notes_dump_entries WHERE dump_id = ?",
            (dump_id,),
        )
    )
    if not rows:
        raise BadRequestError("round dump is empty; curate and save entries first")
    return {int(row["id"]) for row in rows}


def generate_report(conn: sqlite3.Connection, ai: AIClient, round_id: int) -> ReportOut:
    round_row = rounds_service.require_round(conn, round_id)
    if str(round_row["stage"]) != "reading":
        raise ConflictError(
            "round is in the 'editing' stage; generation is one-shot per round — "
            "start a new round for another report"
        )
    dump_row = conn.execute("SELECT id FROM notes_dumps WHERE round_id = ?", (round_id,)).fetchone()
    if dump_row is None:
        raise BadRequestError("round has no saved dump; curate and save entries first")
    valid_entry_ids = _require_entries(conn, round_id, int(dump_row["id"]))
    dump_text = rounds_service.dump_input_text(conn, round_id)
    paragraphs = ai.generate_report(dump_text)
    if not paragraphs:
        raise AIFormatError("report generation produced no paragraphs")
    ts = now_utc()
    inserted = conn.execute(
        """INSERT INTO reports (round_id, created_at) VALUES (?, ?) RETURNING id""",
        (round_id, ts),
    ).fetchone()
    if inserted is None:
        raise RuntimeError("report insert returned no row")
    report_id = int(inserted["id"])
    for position, draft in enumerate(paragraphs):
        _insert_block(conn, report_id, position, draft, valid_entry_ids, ts)
    conn.execute(
        "UPDATE reading_rounds SET stage = 'editing', updated_at = ? WHERE id = ?",
        (ts, round_id),
    )
    conn.commit()
    return get_report(conn, report_id)


def _insert_block(
    conn: sqlite3.Connection,
    report_id: int,
    position: int,
    draft: ParagraphDraft,
    valid_entry_ids: set[int],
    ts: str,
) -> None:
    inserted = conn.execute(
        """INSERT INTO report_blocks (report_id, content, position, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?) RETURNING id""",
        (report_id, draft.text, position, ts, ts),
    ).fetchone()
    if inserted is None:
        raise RuntimeError("report block insert returned no row")
    block_id = int(inserted["id"])
    for entry_id in dict.fromkeys(draft.source_entry_ids):
        if entry_id in valid_entry_ids:
            conn.execute(
                """INSERT INTO report_block_links (block_id, entry_id)
                   VALUES (?, ?) ON CONFLICT DO NOTHING""",
                (block_id, entry_id),
            )


def delete_report(conn: sqlite3.Connection, report_id: int, confirm: bool) -> None:
    if not confirm:
        raise BadRequestError("deleting a report requires an explicit confirm=true payload")
    require_report(conn, report_id)
    conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()


def export_markdown(conn: sqlite3.Connection, report_id: int) -> str:
    require_report(conn, report_id)
    blocks = _blocks(conn, report_id)
    return "\n\n".join(block.content for block in blocks) + "\n"


def _block_row(conn: sqlite3.Connection, block_id: int) -> sqlite3.Row:
    row = fetch_one(
        conn,
        """SELECT id, report_id, content, position, created_at, updated_at
           FROM report_blocks WHERE id = ?""",
        (block_id,),
    )
    if row is None:
        raise NotFoundError(f"report block {block_id} not found")
    return row


def _block_out(conn: sqlite3.Connection, block_id: int) -> ReportBlockOut:
    row = _block_row(conn, block_id)
    links = _block_links(conn, int(row["report_id"]))
    return ReportBlockOut(
        id=int(row["id"]),
        report_id=int(row["report_id"]),
        position=int(row["position"]),
        content=str(row["content"]),
        source_entry_ids=links.get(block_id, []),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def update_block(conn: sqlite3.Connection, block_id: int, content: str) -> ReportBlockOut:
    _block_row(conn, block_id)
    ts = now_utc()
    conn.execute(
        "UPDATE report_blocks SET content = ?, updated_at = ? WHERE id = ?",
        (content, ts, block_id),
    )
    conn.commit()
    return _block_out(conn, block_id)


def block_and_report_context(conn: sqlite3.Connection, block_id: int) -> tuple[str, str]:
    """(target block content, numbered report context of the other blocks)."""
    row = _block_row(conn, block_id)
    target = str(row["content"])
    context_lines = [
        f"{index}. {str(r['content'])}"
        for index, r in enumerate(
            iter_rows(
                conn,
                """SELECT content FROM report_blocks
                   WHERE report_id = ? AND id != ?
                   ORDER BY position""",
                (int(row["report_id"]), block_id),
            ),
            start=1,
        )
    ]
    return target, "\n".join(context_lines)


def tone_samples_for_block(conn: sqlite3.Connection, ai: AIClient, block_id: int) -> ToneSamplesOut:
    block, context = block_and_report_context(conn, block_id)
    samples = ai.tone_samples(block, context)
    return ToneSamplesOut(
        samples=[ToneSampleOut(tone=sample.tone, text=sample.text) for sample in samples]
    )


def critique_for_block(conn: sqlite3.Connection, ai: AIClient, block_id: int) -> CritiqueOut:
    block, context = block_and_report_context(conn, block_id)
    return CritiqueOut(critique=ai.critique(block, context))
