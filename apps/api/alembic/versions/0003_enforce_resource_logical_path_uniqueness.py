from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_enforce_resource_logical_path_uniqueness"
down_revision = "0002_create_resources"
branch_labels = None
depends_on = None

INDEX_NAME = "ux_resources_project_logical_path"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "resources" not in inspector.get_table_names():
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("resources")}
    if INDEX_NAME in existing_indexes:
        return

    op.create_index(INDEX_NAME, "resources", ["project_id", "logical_path"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "resources" not in inspector.get_table_names():
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("resources")}
    if INDEX_NAME in existing_indexes:
        op.drop_index(INDEX_NAME, table_name="resources")
