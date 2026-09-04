"""SQLite persistence: schema (spec §4) and connection helpers."""

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ai_provider TEXT NOT NULL DEFAULT 'deepseek'
        CHECK (ai_provider IN ('vertex', 'deepseek')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES resource_nodes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    is_dir INTEGER NOT NULL,
    UNIQUE (project_id, path)
);

CREATE TABLE IF NOT EXISTS resource_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL UNIQUE REFERENCES resource_nodes(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES resource_nodes(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('highlight', 'note')),
    start_offset INTEGER,
    end_offset INTEGER,
    content TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reading_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'reading'
        CHECK (stage IN ('reading', 'editing')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS round_docs (
    round_id INTEGER NOT NULL REFERENCES reading_rounds(id) ON DELETE CASCADE,
    node_id INTEGER NOT NULL REFERENCES resource_nodes(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    PRIMARY KEY (round_id, node_id)
);

CREATE TABLE IF NOT EXISTS lens_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES resource_nodes(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed', 'selected', 'skipped')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expert_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL REFERENCES reading_rounds(id) ON DELETE CASCADE,
    doc_id INTEGER NOT NULL REFERENCES resource_nodes(id) ON DELETE CASCADE,
    lens_proposal_id INTEGER NOT NULL REFERENCES lens_proposals(id) ON DELETE CASCADE,
    lens_title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (round_id, doc_id, lens_title)
);

CREATE TABLE IF NOT EXISTS expert_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expert_run_id INTEGER NOT NULL REFERENCES expert_runs(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    edited_content TEXT,
    review_state TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_state IN ('pending', 'accepted', 'discarded', 'merged-with-edits')),
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes_dumps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL UNIQUE REFERENCES reading_rounds(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes_dump_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dump_id INTEGER REFERENCES notes_dumps(id) ON DELETE CASCADE,
    round_id INTEGER NOT NULL REFERENCES reading_rounds(id) ON DELETE CASCADE,
    kind TEXT NOT NULL
        CHECK (kind IN ('snippet', 'highlight', 'human-thought', 'ai-thought')),
    content TEXT NOT NULL,
    doc_id INTEGER REFERENCES resource_nodes(id) ON DELETE SET NULL,
    expert_note_id INTEGER REFERENCES expert_notes(id) ON DELETE SET NULL,
    position INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL UNIQUE REFERENCES reading_rounds(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_block_links (
    block_id INTEGER NOT NULL REFERENCES report_blocks(id) ON DELETE CASCADE,
    entry_id INTEGER NOT NULL REFERENCES notes_dump_entries(id) ON DELETE CASCADE,
    PRIMARY KEY (block_id, entry_id)
);

CREATE INDEX IF NOT EXISTS idx_nodes_project ON resource_nodes (project_id);
CREATE INDEX IF NOT EXISTS idx_annotations_doc ON annotations (doc_id);
CREATE INDEX IF NOT EXISTS idx_proposals_doc ON lens_proposals (doc_id);
CREATE INDEX IF NOT EXISTS idx_runs_round ON expert_runs (round_id);
CREATE INDEX IF NOT EXISTS idx_notes_run ON expert_notes (expert_run_id);
CREATE INDEX IF NOT EXISTS idx_entries_dump ON notes_dump_entries (dump_id);
CREATE INDEX IF NOT EXISTS idx_entries_round ON notes_dump_entries (round_id);
CREATE INDEX IF NOT EXISTS idx_blocks_report ON report_blocks (report_id);
"""


def now_utc() -> str:
    """ISO-8601 UTC timestamp string used for every persisted timestamp."""
    return datetime.now(UTC).isoformat(timespec="microseconds")


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    migrate_legacy_projects(conn)
    conn.commit()


def migrate_legacy_projects(conn: sqlite3.Connection) -> None:
    """Add projects.ai_provider to pre-INT-007 databases (SD-20).

    ``CREATE TABLE IF NOT EXISTS`` leaves existing projects tables untouched, so
    legacy rows get the column here with its DEFAULT 'deepseek' — they read back
    as 'deepseek' (the fresh-project default) without data loss.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(projects)")}
    if "ai_provider" not in columns:
        conn.execute("ALTER TABLE projects ADD COLUMN ai_provider TEXT NOT NULL DEFAULT 'deepseek'")


def fetch_one(
    conn: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()
) -> sqlite3.Row | None:
    """Fetch one row (or None) with a statically typed Row result."""
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return None
    return cast(sqlite3.Row, row)


def iter_rows(
    conn: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()
) -> Iterator[sqlite3.Row]:
    cursor = conn.execute(sql, params)
    yield from cursor
