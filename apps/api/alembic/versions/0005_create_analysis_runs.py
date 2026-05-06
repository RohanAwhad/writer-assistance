from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_create_analysis_runs"
down_revision = "0004_create_annotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "analysis_runs" not in existing_tables:
        op.create_table(
            "analysis_runs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("resource_id", sa.String(), sa.ForeignKey("resources.id"), nullable=False),
            sa.Column("generation_state", sa.String(), nullable=False),
            sa.Column("requested_lenses", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_analysis_runs_project_id", "analysis_runs", ["project_id"])
        op.create_index("ix_analysis_runs_resource_id", "analysis_runs", ["resource_id"])

    if "analysis_run_lens_results" not in existing_tables:
        op.create_table(
            "analysis_run_lens_results",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("analysis_run_id", sa.String(), sa.ForeignKey("analysis_runs.id"), nullable=False),
            sa.Column("lens", sa.String(), nullable=False),
            sa.Column("generation_state", sa.String(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_analysis_run_lens_results_analysis_run_id",
            "analysis_run_lens_results",
            ["analysis_run_id"],
        )
        op.create_index(
            "ux_analysis_run_lens_results_run_lens",
            "analysis_run_lens_results",
            ["analysis_run_id", "lens"],
            unique=True,
        )

    if "analysis_suggestions" not in existing_tables:
        op.create_table(
            "analysis_suggestions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("analysis_run_id", sa.String(), sa.ForeignKey("analysis_runs.id"), nullable=False),
            sa.Column(
                "lens_result_id",
                sa.String(),
                sa.ForeignKey("analysis_run_lens_results.id"),
                nullable=False,
            ),
            sa.Column("lens", sa.String(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("quote_text", sa.Text(), nullable=False),
            sa.Column("normalized_text", sa.Text(), nullable=False),
            sa.Column("start_offset", sa.Integer(), nullable=False),
            sa.Column("end_offset", sa.Integer(), nullable=False),
            sa.Column("block_path", sa.JSON(), nullable=False),
            sa.Column("resolution_status", sa.String(), nullable=False),
            sa.Column("review_state", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_analysis_suggestions_analysis_run_id",
            "analysis_suggestions",
            ["analysis_run_id"],
        )
        op.create_index(
            "ix_analysis_suggestions_lens_result_id",
            "analysis_suggestions",
            ["lens_result_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "analysis_suggestions" in existing_tables:
        existing_indexes = {index["name"] for index in inspector.get_indexes("analysis_suggestions")}
        if "ix_analysis_suggestions_analysis_run_id" in existing_indexes:
            op.drop_index("ix_analysis_suggestions_analysis_run_id", table_name="analysis_suggestions")
        if "ix_analysis_suggestions_lens_result_id" in existing_indexes:
            op.drop_index("ix_analysis_suggestions_lens_result_id", table_name="analysis_suggestions")
        op.drop_table("analysis_suggestions")

    if "analysis_run_lens_results" in existing_tables:
        existing_indexes = {index["name"] for index in inspector.get_indexes("analysis_run_lens_results")}
        if "ix_analysis_run_lens_results_analysis_run_id" in existing_indexes:
            op.drop_index(
                "ix_analysis_run_lens_results_analysis_run_id",
                table_name="analysis_run_lens_results",
            )
        if "ux_analysis_run_lens_results_run_lens" in existing_indexes:
            op.drop_index("ux_analysis_run_lens_results_run_lens", table_name="analysis_run_lens_results")
        op.drop_table("analysis_run_lens_results")

    if "analysis_runs" in existing_tables:
        existing_indexes = {index["name"] for index in inspector.get_indexes("analysis_runs")}
        if "ix_analysis_runs_project_id" in existing_indexes:
            op.drop_index("ix_analysis_runs_project_id", table_name="analysis_runs")
        if "ix_analysis_runs_resource_id" in existing_indexes:
            op.drop_index("ix_analysis_runs_resource_id", table_name="analysis_runs")
        op.drop_table("analysis_runs")
