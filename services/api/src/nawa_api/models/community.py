"""Community domain: requests desk, opportunities board, mentorships."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nawa_api.models.base import Base


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    title_ar: Mapped[str | None]
    title_en: Mapped[str | None]
    details_ar: Mapped[str | None]
    details_en: Mapped[str | None]
    kind: Mapped[str] = mapped_column(nullable=False)
    skills_needed: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    duration_label: Mapped[str | None]
    source: Mapped[str] = mapped_column(nullable=False, server_default="member")
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default="draft")
    outcome: Mapped[str | None]
    outcome_note: Mapped[str | None]
    matched_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("title_ar IS NOT NULL OR title_en IS NOT NULL", name="title"),
        CheckConstraint(
            "kind IN ('talent','pilot','review','intro','funding','other')",
            name="kind",
        ),
        CheckConstraint("source IN ('member','assistant')", name="source"),
        CheckConstraint("status IN ('draft','open','matched','closed')", name="status"),
        CheckConstraint(
            "outcome IN ('fulfilled','partially','unfulfilled','withdrawn')",
            name="outcome",
        ),
        Index("ix_requests_status_created", "status", "created_at"),
        Index("ix_requests_profile", "profile_id", "created_at"),
        Index("ix_requests_skills", "skills_needed", postgresql_using="gin"),
    )


class RequestMatch(Base):
    __tablename__ = "request_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(nullable=False)
    rationale_ar: Mapped[str | None]
    rationale_en: Mapped[str | None]
    matched_skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default="suggested")
    responded_at: Mapped[datetime | None]
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_calls.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("request_id", "profile_id"),
        CheckConstraint(
            "status IN ('suggested','notified','accepted','declined','expired')",
            name="status",
        ),
        Index("ix_request_matches_request", "request_id", "score"),
        Index("ix_request_matches_profile", "profile_id", "created_at"),
    )


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    posted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="SET NULL")
    )
    title_ar: Mapped[str | None]
    title_en: Mapped[str | None]
    description_ar: Mapped[str | None]
    description_en: Mapped[str | None]
    kind: Mapped[str] = mapped_column(nullable=False)
    org_name: Mapped[str | None]
    location: Mapped[str | None]
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    domains: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    ai_tagged: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_calls.id", ondelete="SET NULL")
    )
    deadline_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default="draft")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("title_ar IS NOT NULL OR title_en IS NOT NULL", name="title"),
        CheckConstraint(
            "kind IN ('internship','job','grant','pilot','speaking','other')",
            name="kind",
        ),
        CheckConstraint("status IN ('draft','open','matched','closed')", name="status"),
        Index("ix_opportunities_status_deadline", "status", "deadline_at", "created_at"),
        Index("ix_opportunities_tags", "tags", postgresql_using="gin"),
    )


class OpportunityMatch(Base):
    __tablename__ = "opportunity_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(nullable=False)
    rationale_ar: Mapped[str | None]
    rationale_en: Mapped[str | None]
    message: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default="suggested")
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_calls.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("opportunity_id", "profile_id"),
        CheckConstraint(
            "status IN ('suggested','notified','interested','applied','accepted','declined')",
            name="status",
        ),
        Index("ix_opportunity_matches_profile", "profile_id", "created_at"),
    )


class Mentorship(Base):
    __tablename__ = "mentorships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    mentor_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    mentee_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorts.id", ondelete="SET NULL")
    )
    matched_by: Mapped[str] = mapped_column(nullable=False, server_default="ai")
    score: Mapped[float | None]
    rationale_ar: Mapped[str | None]
    rationale_en: Mapped[str | None]
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_calls.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default="suggested")
    started_at: Mapped[datetime | None]
    ended_at: Mapped[datetime | None]
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("mentor_profile_id <> mentee_profile_id", name="distinct"),
        CheckConstraint("matched_by IN ('ai','staff','self')", name="matched_by"),
        CheckConstraint("status IN ('suggested','active','completed','ended')", name="status"),
        Index(
            "uq_mentorships_active_pair",
            "mentor_profile_id",
            "mentee_profile_id",
            unique=True,
            postgresql_where=text("status IN ('suggested','active')"),
        ),
        Index("ix_mentorships_mentor", "mentor_profile_id", "status"),
        Index("ix_mentorships_mentee", "mentee_profile_id", "status"),
    )
