import aiosqlite
import json
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "writer.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    path TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    perspective TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    resource_id INTEGER,
    lens_id INTEGER,
    content TEXT NOT NULL,
    note_type TEXT NOT NULL DEFAULT 'user',
    highlight TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE SET NULL,
    FOREIGN KEY (lens_id) REFERENCES lenses(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS report_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    block_type TEXT NOT NULL DEFAULT 'paragraph',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
);
"""


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def init_db() -> None:
    db = await get_db()
    await db.executescript(SCHEMA)
    await db.commit()
    await db.close()


async def fetch_all(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    result = [dict(row) for row in rows]
    await db.close()
    return result


async def fetch_one(query: str, params: tuple = ()) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute(query, params)
    row = await cursor.fetchone()
    result = dict(row) if row else None
    await db.close()
    return result


async def execute(query: str, params: tuple = ()) -> int:
    db = await get_db()
    cursor = await db.execute(query, params)
    await db.commit()
    last_id = cursor.lastrowid
    await db.close()
    return last_id


async def execute_many(query: str, params_list: list[tuple]) -> None:
    db = await get_db()
    await db.executemany(query, params_list)
    await db.commit()
    await db.close()
