"""AI bookkeeping: the ai_calls ledger, and the applications embedding side-table."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from nawa_api.models.base import Base
from nawa_api.runtime.settings import get_settings

_EMBEDDINGS_DIMENSION = get_settings().embeddings_dimension


class AiCall(Base):
    __tablename__ = "ai_calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(nullable=False)
    tier: Mapped[str | None]
    prompt_hash: Mapped[str] = mapped_column(nullable=False)
    prompt_version: Mapped[str] = mapped_column(nullable=False)
    tokens_in: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    tokens_out: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    tokens_cached: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    cost_estimate: Mapped[float] = mapped_column(nullable=False, server_default=text("0"))
    latency_ms: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(nullable=False)
    error_code: Mapped[str | None]
    request_id: Mapped[str | None]
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("program_cycles.id", ondelete="SET NULL")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    subject_type: Mapped[str | None]
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('ok','error')", name="status"),
        Index("ix_ai_calls_task_created", "task", "created_at"),
        Index("ix_ai_calls_created", "created_at"),
    )


class ApplicationEmbedding(Base):
    __tablename__ = "application_embeddings"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(_EMBEDDINGS_DIMENSION), nullable=False)
    embedding_model: Mapped[str] = mapped_column(nullable=False)
    source_hash: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
