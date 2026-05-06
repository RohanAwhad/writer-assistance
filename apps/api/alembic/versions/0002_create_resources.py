from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_create_resources"
down_revision = "0001_create_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "resources" in inspector.get_table_names():
        return

    op.create_table(
        "resources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("logical_path", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("storage_location", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("upload_status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resources_project_id", "resources", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_resources_project_id", table_name="resources")
    op.drop_table("resources")
