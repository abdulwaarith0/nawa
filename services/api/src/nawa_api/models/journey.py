"""Journey domain: milestones, progress, RAG resources, assistant threads, digests."""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nawa_api.models.base import Base
from nawa_api.runtime.settings import get_settings

_EMBEDDINGS_DIMENSION = get_settings().embeddings_dimension


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False
    )
    program_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_cycles.id", ondelete="SET NULL")
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorts.id", ondelete="CASCADE")
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="SET NULL")
    )
    scope: Mapped[str] = mapped_column(nullable=False, server_default="template")
    sequence: Mapped[int] = mapped_column(nullable=False)
    title_ar: Mapped[str | None]
    title_en: Mapped[str | None]
    description_ar: Mapped[str | None]
    description_en: Mapped[str | None]
    due_offset_days: Mapped[int | None]
    due_date: Mapped[date | None]
    evidence_required: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("scope IN ('template','cohort')", name="scope"),
        CheckConstraint(
            "(scope = 'template' AND cohort_id IS NULL) OR "
            "(scope = 'cohort' AND cohort_id IS NOT NULL)",
            name="scope_shape",
        ),
        CheckConstraint("title_ar IS NOT NULL OR title_en IS NOT NULL", name="title"),
        Index(
            "uq_milestones_cohort_sequence",
            "cohort_id",
            "sequence",
            unique=True,
            postgresql_where=text("scope = 'cohort'"),
        ),
        Index(
            "uq_milestones_cohort_template",
            "cohort_id",
            "template_id",
            unique=True,
            postgresql_where=text("template_id IS NOT NULL"),
        ),
        Index("ix_milestones_cohort_sequence", "cohort_id", "sequence"),
        Index("ix_milestones_template_scope", "program_id", "program_cycle_id", "scope"),
    )


class MilestoneProgress(Base):
    __tablename__ = "milestone_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="CASCADE"), nullable=False
    )
    cohort_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohort_members.id", ondelete="CASCADE"), nullable=False
    )
    founder_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("founder_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default="not_started")
    note_ar: Mapped[str | None]
    note_en: Mapped[str | None]
    evidence_links: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("milestone_id", "cohort_member_id"),
        CheckConstraint(
            "status IN ('not_started','in_progress','submitted','blocked','done','waived')",
            name="status",
        ),
        Index("ix_milestone_progress_profile", "founder_profile_id", "status"),
        Index("ix_milestone_progress_member", "cohort_member_id", "status"),
        Index("ix_milestone_progress_status_updated", "status", "updated_at"),
    )


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title_ar: Mapped[str | None]
    title_en: Mapped[str | None]
    description_ar: Mapped[str | None]
    description_en: Mapped[str | None]
    kind: Mapped[str] = mapped_column(nullable=False)
    language: Mapped[str] = mapped_column(nullable=False, server_default="ar")
    steward_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    storage_key: Mapped[str | None]
    source_url: Mapped[str | None]
    content: Mapped[str | None]
    content_hash: Mapped[str | None]
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default="draft")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("title_ar IS NOT NULL OR title_en IS NOT NULL", name="title"),
        CheckConstraint(
            "kind IN ('handbook','lab_capability','mentor_bio','guide','faq','policy')",
            name="kind",
        ),
        CheckConstraint("language IN ('ar','en')", name="language"),
        CheckConstraint("status IN ('draft','processing','live','archived')", name="status"),
        Index("ix_resources_status_updated", "status", "updated_at"),
        Index("ix_resources_tags", "tags", postgresql_using="gin"),
    )


class ResourceChunk(Base):
    __tablename__ = "resource_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    token_count: Mapped[int] = mapped_column(nullable=False)
    heading_path: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    language: Mapped[str] = mapped_column(nullable=False, server_default="ar")
    chunk_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'")
    )
    source_hash: Mapped[str] = mapped_column(nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(_EMBEDDINGS_DIMENSION))
    embedding_model: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("resource_id", "chunk_index"),
        CheckConstraint("language IN ('ar','en')", name="language"),
    )


class AssistantThread(Base):
    __tablename__ = "assistant_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    founder_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="SET NULL")
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorts.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(nullable=False, server_default="assistant")
    language: Mapped[str] = mapped_column(nullable=False, server_default="ar")
    title: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("kind IN ('assistant','check_in')", name="kind"),
        CheckConstraint("language IN ('ar','en')", name="language"),
        CheckConstraint("status IN ('active','archived')", name="status"),
        Index("ix_assistant_threads_user", "user_id", "kind", "updated_at"),
    )


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_threads.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    language: Mapped[str] = mapped_column(nullable=False, server_default="ar")
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    confidence: Mapped[float | None]
    intent: Mapped[str | None]
    routed_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requests.id", ondelete="SET NULL")
    )
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_calls.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('user','assistant','system','route')", name="role"),
        CheckConstraint("language IN ('ar','en')", name="language"),
        CheckConstraint("intent IN ('informational','operational')", name="intent"),
        Index("ix_assistant_messages_thread", "thread_id", "created_at"),
    )


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    kind: Mapped[str] = mapped_column(nullable=False)
    scope_type: Mapped[str] = mapped_column(nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    period_start: Mapped[date] = mapped_column(nullable=False)
    period_end: Mapped[date] = mapped_column(nullable=False)
    stats: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    at_risk: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    upcoming: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    content_ar: Mapped[str | None]
    content_en: Mapped[str | None]
    generated_by: Mapped[str] = mapped_column(nullable=False, server_default="cron")
    status: Mapped[str] = mapped_column(nullable=False, server_default="draft")
    sent_at: Mapped[datetime | None]
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_calls.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("kind", "scope_type", "scope_id", "period_start"),
        CheckConstraint("kind IN ('program_manager','jury','cohort','supervisor')", name="kind"),
        CheckConstraint("scope_type IN ('cohort','cycle','program')", name="scope_type"),
        CheckConstraint("content_ar IS NOT NULL OR content_en IS NOT NULL", name="content"),
        CheckConstraint("generated_by IN ('cron','manual')", name="generated_by"),
        CheckConstraint("status IN ('draft','sent')", name="status"),
        Index("ix_digests_scope", "scope_type", "scope_id", "period_start"),
    )
