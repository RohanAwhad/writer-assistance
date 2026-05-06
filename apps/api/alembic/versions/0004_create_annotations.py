from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_create_annotations"
down_revision = "0003_enforce_resource_logical_path_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "annotations" in inspector.get_table_names():
        return

    op.create_table(
        "annotations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("resource_id", sa.String(), sa.ForeignKey("resources.id"), nullable=False),
        sa.Column("quote_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("block_path", sa.JSON(), nullable=False),
        sa.Column("resolution_status", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("origin_type", sa.String(), nullable=False),
        sa.Column("provenance_source_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_annotations_project_id", "annotations", ["project_id"])
    op.create_index("ix_annotations_resource_id", "annotations", ["resource_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "annotations" not in inspector.get_table_names():
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("annotations")}
    if "ix_annotations_project_id" in existing_indexes:
        op.drop_index("ix_annotations_project_id", table_name="annotations")
    if "ix_annotations_resource_id" in existing_indexes:
        op.drop_index("ix_annotations_resource_id", table_name="annotations")
    op.drop_table("annotations")
