"""Project lifecycle and resource-tree import (F1, R-010, OQ-01).

Import snapshots the Markdown tree into SQLite once; after that the app never
reads the import path again (read-only invariant R-011/R-012).
"""

import os
import sqlite3
from pathlib import Path

from app.db import fetch_one, iter_rows, now_utc
from app.errors import BadRequestError, ConflictError, NotFoundError
from app.schemas import (
    ImportResult,
    ProjectDetail,
    ProjectOut,
    TreeNodeOut,
    TreeOut,
)

_PROJECT_COLS = "id, name, ai_provider, created_at, updated_at"


def _require_project_row(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row:
    row = fetch_one(conn, f"SELECT {_PROJECT_COLS} FROM projects WHERE id = ?", (project_id,))
    if row is None:
        raise NotFoundError(f"project {project_id} not found")
    return row


def get_ai_provider(conn: sqlite3.Connection, project_id: int) -> str:
    """The project's stored ai_provider value ('vertex'|'deepseek'; SD-20/R-071)."""
    row = fetch_one(conn, "SELECT ai_provider FROM projects WHERE id = ?", (project_id,))
    if row is None:
        raise NotFoundError(f"project {project_id} not found")
    return str(row["ai_provider"])


def _project_out(conn: sqlite3.Connection, project_id: int) -> ProjectOut:
    row = fetch_one(conn, f"SELECT {_PROJECT_COLS} FROM projects WHERE id = ?", (project_id,))
    if row is None:
        raise NotFoundError(f"project {project_id} not found")
    return ProjectOut(
        id=int(row["id"]),
        name=str(row["name"]),
        ai_provider=str(row["ai_provider"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_project(conn: sqlite3.Connection, name: str) -> ProjectOut:
    ts = now_utc()
    row = conn.execute(
        """INSERT INTO projects (name, created_at, updated_at)
           VALUES (?, ?, ?) RETURNING id, name, ai_provider, created_at, updated_at""",
        (name, ts, ts),
    ).fetchone()
    if row is None:
        raise RuntimeError("project insert returned no row")
    conn.commit()
    return ProjectOut(
        id=int(row["id"]),
        name=str(row["name"]),
        ai_provider=str(row["ai_provider"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_projects(conn: sqlite3.Connection) -> list[ProjectOut]:
    projects = [
        ProjectOut(
            id=int(row["id"]),
            name=str(row["name"]),
            ai_provider=str(row["ai_provider"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in iter_rows(conn, f"SELECT {_PROJECT_COLS} FROM projects ORDER BY id")
    ]
    return projects


def get_project(conn: sqlite3.Connection, project_id: int) -> ProjectDetail:
    _require_project_row(conn, project_id)
    row = conn.execute(
        """SELECT p.id, p.name, p.ai_provider, p.created_at, p.updated_at,
                  (SELECT COUNT(*) FROM resource_nodes n
                   WHERE n.project_id = p.id AND n.is_dir = 0) AS resource_count,
                  (SELECT COUNT(*) FROM reading_rounds r WHERE r.project_id = p.id) AS round_count
           FROM projects p WHERE p.id = ?""",
        (project_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"project {project_id} not found")
    return ProjectDetail(
        id=int(row["id"]),
        name=str(row["name"]),
        ai_provider=str(row["ai_provider"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        resource_count=int(row["resource_count"]),
        round_count=int(row["round_count"]),
    )


def rename_project(conn: sqlite3.Connection, project_id: int, name: str) -> ProjectOut:
    _require_project_row(conn, project_id)
    ts = now_utc()
    conn.execute(
        "UPDATE projects SET name = ?, updated_at = ? WHERE id = ?",
        (name, ts, project_id),
    )
    conn.commit()
    return _project_out(conn, project_id)


def set_project_provider(conn: sqlite3.Connection, project_id: int, provider: str) -> ProjectOut:
    """Persist the project's selected AI provider (R-071); fresh default 'deepseek'."""
    _require_project_row(conn, project_id)
    ts = now_utc()
    conn.execute(
        "UPDATE projects SET ai_provider = ?, updated_at = ? WHERE id = ?",
        (provider, ts, project_id),
    )
    conn.commit()
    return _project_out(conn, project_id)


def delete_project(conn: sqlite3.Connection, project_id: int) -> None:
    _require_project_row(conn, project_id)
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()


def _collect_markdown_files(root: Path) -> list[Path]:
    """Markdown files under root; dot-entries and non-.md files are skipped."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for filename in sorted(filenames):
            if filename.startswith(".") or not filename.lower().endswith(".md"):
                continue
            found.append(Path(dirpath) / filename)
    return found


def _insert_dir_chain(
    conn: sqlite3.Connection,
    project_id: int,
    project_root: Path,
    file_path: Path,
) -> int | None:
    """Insert resource_nodes rows for each ancestor directory of a file path.

    Returns the id of the innermost (file-parent) directory node, or None for
    files directly under the project root.
    """
    parent_id: int | None = None
    relative = file_path.parent.relative_to(project_root)
    parts = relative.parts
    for index, part in enumerate(parts):
        rel_path = str(Path(*parts[: index + 1]))
        row = conn.execute(
            "SELECT id FROM resource_nodes WHERE project_id = ? AND path = ?",
            (project_id, rel_path),
        ).fetchone()
        if row is None:
            inserted = conn.execute(
                """INSERT INTO resource_nodes (project_id, parent_id, name, path, is_dir)
                   VALUES (?, ?, ?, ?, 1) RETURNING id""",
                (project_id, parent_id, part, rel_path),
            ).fetchone()
            if inserted is None:
                raise RuntimeError("directory node insert returned no row")
            parent_id = int(inserted["id"])
        else:
            parent_id = int(row["id"])
    return parent_id


def import_tree(conn: sqlite3.Connection, project_id: int, import_path: str) -> ImportResult:
    _require_project_row(conn, project_id)
    root = Path(import_path)
    if not root.is_dir():
        raise BadRequestError(f"import path is not a directory: {import_path}")
    existing = conn.execute(
        "SELECT COUNT(*) AS n FROM resource_nodes WHERE project_id = ? AND is_dir = 0",
        (project_id,),
    ).fetchone()
    if existing is not None and int(existing["n"]) > 0:
        raise ConflictError("project already has imported resources")
    files = _collect_markdown_files(root)
    if not files:
        raise BadRequestError(f"no Markdown files found under {import_path}")
    ts = now_utc()
    for file_path in files:
        parent_id = _insert_dir_chain(conn, project_id, root, file_path)
        rel_path = file_path.relative_to(root).as_posix()
        content = file_path.read_text(encoding="utf-8")
        inserted = conn.execute(
            """INSERT INTO resource_nodes (project_id, parent_id, name, path, is_dir)
               VALUES (?, ?, ?, ?, 0) RETURNING id""",
            (project_id, parent_id, file_path.name, rel_path),
        ).fetchone()
        if inserted is None:
            raise RuntimeError("file node insert returned no row")
        node_id = int(inserted["id"])
        conn.execute(
            "INSERT INTO resource_docs (node_id, content, imported_at) VALUES (?, ?, ?)",
            (node_id, content, ts),
        )
    conn.commit()
    return ImportResult(project_id=project_id, imported_files=len(files))


def get_tree(conn: sqlite3.Connection, project_id: int) -> TreeOut:
    _require_project_row(conn, project_id)
    nodes = [
        TreeNodeOut(
            id=int(row["id"]),
            parent_id=int(row["parent_id"]) if row["parent_id"] is not None else None,
            name=str(row["name"]),
            path=str(row["path"]),
            kind="dir" if int(row["is_dir"]) == 1 else "file",
        )
        for row in iter_rows(
            conn,
            """SELECT id, parent_id, name, path, is_dir FROM resource_nodes
               WHERE project_id = ? ORDER BY path""",
            (project_id,),
        )
    ]
    return TreeOut(project_id=project_id, nodes=nodes)
