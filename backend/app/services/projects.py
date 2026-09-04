"""Project lifecycle and resource import (F1, R-010, R-079..R-081, OQ-01).

Import snapshots browser-uploaded Markdown files into SQLite once; uploads land
flat at the project root (SD-28) and the snapshot is immutable (read-only
invariant R-011/R-012). The backend never reads a server filesystem path to
import resources (R-079).
"""

import sqlite3

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


_MARKDOWN_EXTENSIONS = (".md", ".markdown")


def _check_upload_name(name: str) -> None:
    """Per-part name grammar (SD-30): .md/.markdown, plain basename.

    A failing name raises BadRequestError naming the offending file, rejecting
    the whole request (all-or-nothing).
    """
    lowered = name.lower()
    if not lowered.endswith(_MARKDOWN_EXTENSIONS):
        raise BadRequestError(f"unsupported file type: {name}")
    if "/" in name or "\\" in name:
        raise BadRequestError(f"file name must not contain path separators: {name}")
    if name.startswith("."):
        raise BadRequestError(f"file name must not start with a dot: {name}")


def import_uploads(
    conn: sqlite3.Connection, project_id: int, uploads: list[tuple[str, bytes]]
) -> ImportResult:
    """Snapshot accepted browser-uploaded files into the project (R-079..R-081).

    Each part is (filename, raw bytes) as received from the multipart body.
    Every part must pass the SD-30 grammar before anything is written; on any
    failure nothing persists. Accepted files are stored byte-for-byte (decoded
    as UTF-8) as file nodes with ``path == filename`` at the project root
    (SD-28), flat — no directory nodes are created.
    """
    _require_project_row(conn, project_id)
    existing = conn.execute(
        "SELECT COUNT(*) AS n FROM resource_nodes WHERE project_id = ? AND is_dir = 0",
        (project_id,),
    ).fetchone()
    if existing is not None and int(existing["n"]) > 0:
        raise ConflictError("project already has imported resources")
    decoded: list[tuple[str, str]] = []
    for name, raw in uploads:
        _check_upload_name(name)
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise BadRequestError(f"file is not valid UTF-8: {name}") from None
        if any(existing_name == name for existing_name, _ in decoded):
            raise ConflictError(f"duplicate file name in import: {name}")
        decoded.append((name, content))
    ts = now_utc()
    for name, content in decoded:
        inserted = conn.execute(
            """INSERT INTO resource_nodes (project_id, parent_id, name, path, is_dir)
               VALUES (?, NULL, ?, ?, 0) RETURNING id""",
            (project_id, name, name),
        ).fetchone()
        if inserted is None:
            raise RuntimeError("file node insert returned no row")
        conn.execute(
            "INSERT INTO resource_docs (node_id, content, imported_at) VALUES (?, ?, ?)",
            (int(inserted["id"]), content, ts),
        )
    conn.commit()
    return ImportResult(project_id=project_id, imported_files=len(decoded))


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
