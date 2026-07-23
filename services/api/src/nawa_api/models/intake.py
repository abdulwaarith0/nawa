"""Intake domain: rubrics, applications, scorecards, dedup, decisions."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nawa_api.models.base import Base


class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    name_ar: Mapped[str | None]
    name_en: Mapped[str | None]
    criteria: Mapped[list] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default="draft")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("program_id", "version"),
        CheckConstraint("name_ar IS NOT NULL OR name_en IS NOT NULL", name="name"),
        CheckConstraint("status IN ('draft','active','retired')", name="status"),
        Index(
            "uq_rubrics_program_active",
            "program_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


class ApplicationUpload(Base):
    __tablename__ = "application_uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_cycles.id", ondelete="RESTRICT"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(nullable=False)
    file_name: Mapped[str] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    row_count: Mapped[int | None]
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (Index("ix_application_uploads_cycle", "cycle_id", "created_at"),)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_cycles.id", ondelete="RESTRICT"), nullable=False
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="SET NULL")
    )
    source_upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_uploads.id", ondelete="SET NULL")
    )
    applicant_name: Mapped[str] = mapped_column(nullable=False)
    applicant_email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    source_language: Mapped[str] = mapped_column(nullable=False)
    original_answers: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_extra: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    normalized: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    title: Mapped[str | None]
    summary: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default="submitted")
    ai_total_score: Mapped[float | None]
    submitted_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    normalized_at: Mapped[datetime | None]
    scored_at: Mapped[datetime | None]
    decided_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("source_language IN ('ar','en','fr')", name="source_language"),
        CheckConstraint(
            "status IN ('submitted','normalized','normalize_failed','scored',"
            "'shortlisted','waitlisted','decided')",
            name="status",
        ),
        Index(
            "ix_applications_cycle_status_score",
            "cycle_id",
            "status",
            "ai_total_score",
            "submitted_at",
        ),
        Index("ix_applications_cycle_submitted", "cycle_id", "submitted_at"),
        Index("ix_applications_email", "applicant_email"),
    )


class ApplicationDocument(Base):
    __tablename__ = "application_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(nullable=False)
    file_name: Mapped[str] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(nullable=False, server_default="attachment")
    extracted_text: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("application_id", "storage_key"),
        CheckConstraint(
            "kind IN ('attachment','cv','deck','extracted_text')",
            name="kind",
        ),
    )


class Scorecard(Base):
    __tablename__ = "scorecards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    rubric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubrics.id", ondelete="RESTRICT"), nullable=False
    )
    rubric_version: Mapped[int] = mapped_column(nullable=False)
    prompt_version: Mapped[str] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    total_score: Mapped[float] = mapped_column(nullable=False)
    confidence: Mapped[float | None]
    rationale_ar: Mapped[str | None]
    rationale_en: Mapped[str | None]
    hidden_gem: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    hidden_gem_reason_ar: Mapped[str | None]
    hidden_gem_reason_en: Mapped[str | None]
    model: Mapped[str | None]
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_calls.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default="generated")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("application_id", "rubric_id", "source"),
        CheckConstraint("source IN ('ai','human')", name="source"),
        CheckConstraint("status IN ('generated','reviewed','final')", name="status"),
        Index("ix_scorecards_application", "application_id", "created_at"),
    )


class ScorecardCriterion(Base):
    __tablename__ = "scorecard_criteria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    scorecard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scorecards.id", ondelete="CASCADE"), nullable=False
    )
    criterion_key: Mapped[str] = mapped_column(nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    weight: Mapped[float] = mapped_column(nullable=False)
    rationale_ar: Mapped[str | None]
    rationale_en: Mapped[str | None]
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (UniqueConstraint("scorecard_id", "criterion_key"),)


class DedupMatch(Base):
    __tablename__ = "dedup_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    matched_application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    similarity: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default="pending")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("application_id", "matched_application_id"),
        CheckConstraint("application_id <> matched_application_id", name="distinct"),
        CheckConstraint("status IN ('pending','confirmed','dismissed')", name="status"),
        Index("ix_dedup_matches_application", "application_id", "similarity"),
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    decided_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(nullable=False)
    previous_value: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    new_value: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    reason: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "decision IN ('shortlist','waitlist','advance','reject','accept','override_score')",
            name="decision",
        ),
        Index("ix_decisions_application", "application_id", "created_at"),
    )
