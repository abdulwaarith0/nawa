"""Reports & KPI domain: kpi definitions/entries, check-ins, reports, anomalies."""

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nawa_api.models.base import Base


class KpiDefinition(Base):
    __tablename__ = "kpi_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    key: Mapped[str] = mapped_column(nullable=False)
    name_ar: Mapped[str | None]
    name_en: Mapped[str | None]
    unit: Mapped[str | None]
    direction: Mapped[str] = mapped_column(nullable=False, server_default="up_good")
    value_type: Mapped[str] = mapped_column(nullable=False, server_default="number")
    aggregation: Mapped[str] = mapped_column(nullable=False, server_default="last")
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE")
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("name_ar IS NOT NULL OR name_en IS NOT NULL", name="name"),
        CheckConstraint("direction IN ('up_good','down_good')", name="direction"),
        CheckConstraint(
            "value_type IN ('number','currency','percent','count')",
            name="value_type",
        ),
        CheckConstraint("aggregation IN ('last','sum','avg')", name="aggregation"),
        Index(
            "uq_kpi_definitions_global_key",
            "key",
            unique=True,
            postgresql_where=text("program_id IS NULL"),
        ),
        UniqueConstraint("program_id", "key"),
    )


class KpiEntry(Base):
    __tablename__ = "kpi_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    kpi_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kpi_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False, server_default="check_in")
    check_in_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("check_ins.id", ondelete="SET NULL")
    )
    confirmed_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("profile_id", "kpi_definition_id", "period_start"),
        CheckConstraint("source IN ('check_in','manual','import')", name="source"),
        Index(
            "ix_kpi_entries_profile_def_period",
            "profile_id",
            "kpi_definition_id",
            "period_start",
        ),
        Index("ix_kpi_entries_def_period", "kpi_definition_id", "period_start"),
    )


class CheckIn(Base):
    __tablename__ = "check_ins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_cycles.id", ondelete="SET NULL")
    )
    period_start: Mapped[date] = mapped_column(nullable=False)
    channel: Mapped[str] = mapped_column(nullable=False, server_default="conversational")
    language: Mapped[str] = mapped_column(nullable=False, server_default="ar")
    status: Mapped[str] = mapped_column(nullable=False, server_default="scheduled")
    transcript: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    summary_ar: Mapped[str | None]
    summary_en: Mapped[str | None]
    submitted_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("profile_id", "period_start"),
        CheckConstraint("channel IN ('conversational','form')", name="channel"),
        CheckConstraint("language IN ('ar','en')", name="language"),
        CheckConstraint(
            "status IN ('scheduled','in_progress','submitted','missed')",
            name="status",
        ),
        Index("ix_check_ins_status_period", "status", "period_start"),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    kind: Mapped[str] = mapped_column(nullable=False)
    subject_type: Mapped[str] = mapped_column(nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    period_start: Mapped[date] = mapped_column(nullable=False)
    period_end: Mapped[date] = mapped_column(nullable=False)
    template_key: Mapped[str | None]
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    rendered_ar: Mapped[str | None]
    rendered_en: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, server_default="draft")
    generated_by: Mapped[str] = mapped_column(nullable=False, server_default="ai")
    export_key: Mapped[str | None]
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_calls.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("kind", "subject_type", "subject_id", "period_start"),
        CheckConstraint(
            "kind IN ('founder_monthly','cycle_outcome','impact',"
            "'internship_evaluation','portfolio')",
            name="kind",
        ),
        CheckConstraint(
            "subject_type IN ('profile','cycle','program','portfolio')",
            name="subject_type",
        ),
        CheckConstraint("status IN ('draft','review','final')", name="status"),
        CheckConstraint("generated_by IN ('ai','human')", name="generated_by"),
        Index("ix_reports_subject", "subject_type", "subject_id", "period_start"),
        Index("ix_reports_status_created", "status", "created_at"),
    )


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("founder_profiles.id", ondelete="CASCADE"), nullable=False
    )
    kpi_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kpi_definitions.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(nullable=False)
    window_start: Mapped[date] = mapped_column(nullable=False)
    window_end: Mapped[date] = mapped_column(nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    dedupe_key: Mapped[str] = mapped_column(unique=True, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default="open")
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None]
    detected_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "kind IN ('runway','churn_spike','growth_stall','stalled_milestone',"
            "'missing_check_in')",
            name="kind",
        ),
        CheckConstraint("severity IN ('info','warning','critical')", name="severity"),
        CheckConstraint(
            "status IN ('open','acknowledged','resolved','dismissed')",
            name="status",
        ),
        Index(
            "uq_anomalies_open_per_kind",
            "profile_id",
            "kind",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index("ix_anomalies_status_severity", "status", "severity", "detected_at"),
        Index("ix_anomalies_profile", "profile_id", "detected_at"),
    )
