from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_enforce_resource_logical_path_uniqueness"
down_revision = "0002_create_resources"
branch_labels = None
depends_on = None

INDEX_NAME = "ux_resources_project_logical_path"
DUPLICATE_LOGICAL_PATHS_MESSAGE = (
    "Cannot enforce resource logical-path uniqueness because duplicate logical paths already "
    "exist within at least one project. Remove duplicates or recreate the local database "
    "before running this migration."
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "resources" not in inspector.get_table_names():
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("resources")}
    if INDEX_NAME in existing_indexes:
        return

    duplicate_row = bind.execute(
        sa.text(
            """
            SELECT project_id, logical_path
            FROM resources
            GROUP BY project_id, logical_path
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_row is not None:
        raise RuntimeError(DUPLICATE_LOGICAL_PATHS_MESSAGE)

    op.create_index(INDEX_NAME, "resources", ["project_id", "logical_path"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "resources" not in inspector.get_table_names():
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("resources")}
    if INDEX_NAME in existing_indexes:
        op.drop_index(INDEX_NAME, table_name="resources")
