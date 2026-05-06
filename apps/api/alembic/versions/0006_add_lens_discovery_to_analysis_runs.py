from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "0006_add_lens_discovery_to_analysis_runs"
down_revision = "0005_create_analysis_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "analysis_runs" not in existing_tables:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("analysis_runs")}
    if "lens_discovery_status" not in existing_columns:
        op.add_column(
            "analysis_runs",
            sa.Column(
                "lens_discovery_status",
                sa.String(),
                nullable=False,
                server_default="succeeded",
            ),
        )
    if "discovered_lenses" not in existing_columns:
        op.add_column(
            "analysis_runs",
            sa.Column(
                "discovered_lenses",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            ),
        )

    rows = bind.execute(
        sa.text(
            """
            SELECT id, requested_lenses
            FROM analysis_runs
            """
        )
    ).mappings()
    for row in rows:
        requested_lenses = _coerce_requested_lenses(row["requested_lenses"])
        discovered_lenses = [
            {
                "name": lens,
                "description": "Imported from an earlier fixed-lens analysis run.",
            }
            for lens in requested_lenses
        ]
        bind.execute(
            sa.text(
                """
                UPDATE analysis_runs
                SET lens_discovery_status = :lens_discovery_status,
                    discovered_lenses = :discovered_lenses
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "lens_discovery_status": "succeeded",
                "discovered_lenses": json.dumps(discovered_lenses),
            },
        )

    with op.batch_alter_table("analysis_runs") as batch_op:
        batch_op.alter_column(
            "lens_discovery_status",
            existing_type=sa.String(),
            existing_nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "discovered_lenses",
            existing_type=sa.JSON(),
            existing_nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "analysis_runs" not in existing_tables:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("analysis_runs")}
    if "discovered_lenses" in existing_columns:
        op.drop_column("analysis_runs", "discovered_lenses")
    if "lens_discovery_status" in existing_columns:
        op.drop_column("analysis_runs", "lens_discovery_status")


def _coerce_requested_lenses(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        decoded = json.loads(value)
        if not isinstance(decoded, list):
            raise ValueError("requested_lenses must decode to a JSON list")
        return [str(item) for item in decoded]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise TypeError("requested_lenses must be stored as a list or JSON string")
