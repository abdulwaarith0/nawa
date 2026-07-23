"""Programs & cohorts — program-agnostic configuration layer."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nawa_api.models.base import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    name_ar: Mapped[str | None]
    name_en: Mapped[str | None]
    description_ar: Mapped[str | None]
    description_en: Mapped[str | None]
    kind: Mapped[str] = mapped_column(nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("name_ar IS NOT NULL OR name_en IS NOT NULL", name="name"),
        CheckConstraint(
            "kind IN ('competition','accelerator','incubation',"
            "'research_translation','residency','internship')",
            name="kind",
        ),
    )


class ProgramCycle(Base):
    __tablename__ = "program_cycles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False
    )
    slug: Mapped[str] = mapped_column(nullable=False)
    name_ar: Mapped[str | None]
    name_en: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default="draft")
    opens_at: Mapped[datetime | None]
    closes_at: Mapped[datetime | None]
    starts_at: Mapped[datetime | None]
    ends_at: Mapped[datetime | None]
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("program_id", "slug"),
        CheckConstraint("name_ar IS NOT NULL OR name_en IS NOT NULL", name="name"),
        CheckConstraint(
            "status IN ('draft','applications_open','screening','active','completed','archived')",
            name="status",
        ),
        Index(
            "ix_program_cycles_program_status",
            "program_id",
            "status",
            "opens_at",  # canonical sort: opens_desc
        ),
    )


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_cycles.id", ondelete="RESTRICT"), nullable=False
    )
    name_ar: Mapped[str | None]
    name_en: Mapped[str | None]
    program_manager_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(nullable=False)
    ends_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("name_ar IS NOT NULL OR name_en IS NOT NULL", name="name"),
        Index("ix_cohorts_cycle", "cycle_id", "starts_at"),
    )


class CohortMember(Base):
    __tablename__ = "cohort_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(nullable=False, server_default="participant")
    status: Mapped[str] = mapped_column(nullable=False, server_default="active")
    joined_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    left_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("cohort_id", "profile_id"),
        CheckConstraint("role IN ('participant','mentor')", name="role"),
        CheckConstraint("status IN ('active','graduated','withdrawn')", name="status"),
        Index("ix_cohort_members_profile", "profile_id", "joined_at"),
    )
