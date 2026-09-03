"""Resource reads: tree access and the content snapshot (F1/F2, R-011)."""

import sqlite3

from app.db import fetch_one, iter_rows
from app.errors import NotFoundError
from app.schemas import ResourceOut


def require_file_doc(conn: sqlite3.Connection, node_id: int) -> sqlite3.Row:
    """File node + its snapshot row; directories and missing nodes are 404s."""
    row = fetch_one(
        conn,
        """SELECT n.id, n.project_id, n.name, n.path, d.content, d.imported_at
           FROM resource_nodes n
           JOIN resource_docs d ON d.node_id = n.id
           WHERE n.id = ?""",
        (node_id,),
    )
    if row is None:
        raise NotFoundError(f"resource {node_id} not found")
    return row


def get_resource(conn: sqlite3.Connection, node_id: int) -> ResourceOut:
    row = require_file_doc(conn, node_id)
    return ResourceOut(
        id=int(row["id"]),
        project_id=int(row["project_id"]),
        path=str(row["path"]),
        content=str(row["content"]),
        imported_at=row["imported_at"],
    )


def resource_paths(conn: sqlite3.Connection, project_id: int) -> dict[int, str]:
    return {
        int(row["id"]): str(row["path"])
        for row in iter_rows(
            conn,
            """SELECT id, path FROM resource_nodes
               WHERE project_id = ? AND is_dir = 0""",
            (project_id,),
        )
    }
