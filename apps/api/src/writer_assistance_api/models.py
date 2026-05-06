from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        Index("ux_resources_project_logical_path", "project_id", "logical_path", unique=True),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    logical_path: Mapped[str] = mapped_column(String)
    original_filename: Mapped[str] = mapped_column(String)
    storage_location: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String)
    upload_status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), index=True)
    quote_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int]
    end_offset: Mapped[int]
    block_path: Mapped[list[str]] = mapped_column(JSON)
    resolution_status: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    origin_type: Mapped[str] = mapped_column(String)
    provenance_source_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), index=True)
    lens_discovery_status: Mapped[str] = mapped_column(String)
    discovered_lenses: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    generation_state: Mapped[str] = mapped_column(String)
    requested_lenses: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AnalysisRunLensResult(Base):
    __tablename__ = "analysis_run_lens_results"
    __table_args__ = (
        Index("ux_analysis_run_lens_results_run_lens", "analysis_run_id", "lens", unique=True),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    lens: Mapped[str] = mapped_column(String)
    generation_state: Mapped[str] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AnalysisSuggestion(Base):
    __tablename__ = "analysis_suggestions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    lens_result_id: Mapped[str] = mapped_column(ForeignKey("analysis_run_lens_results.id"), index=True)
    lens: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    quote_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int]
    end_offset: Mapped[int]
    block_path: Mapped[list[str]] = mapped_column(JSON)
    resolution_status: Mapped[str] = mapped_column(String)
    review_state: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
