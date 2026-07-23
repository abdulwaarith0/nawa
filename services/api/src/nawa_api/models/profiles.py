"""founder_profiles — the data spine every module reads from and writes to."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Computed, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nawa_api.models.base import Base
from nawa_api.runtime.settings import get_settings

_EMBEDDINGS_DIMENSION = get_settings().embeddings_dimension

_SEARCH_TSV_EXPR = (
    "to_tsvector('simple'::regconfig, "
    "coalesce(display_name_ar,'') || ' ' || coalesce(display_name_en,'') || ' ' || "
    "coalesce(venture_name_ar,'') || ' ' || coalesce(venture_name_en,'') || ' ' || "
    "coalesce(headline_ar,'') || ' ' || coalesce(headline_en,'') || ' ' || "
    "coalesce(bio_ar,'') || ' ' || coalesce(bio_en,'') || ' ' || "
    # array_to_string() is STABLE (not IMMUTABLE) in Postgres, so a generated
    # column can't call it directly; immutable_array_to_string() is a thin
    # IMMUTABLE SQL wrapper created in the migration for exactly this use.
    "immutable_array_to_string(skills,' ') || ' ' || immutable_array_to_string(domains,' '))"
)


class FounderProfile(Base):
    __tablename__ = "founder_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    handle: Mapped[str] = mapped_column(unique=True, nullable=False)
    display_name_ar: Mapped[str | None]
    display_name_en: Mapped[str | None]
    headline_ar: Mapped[str | None]
    headline_en: Mapped[str | None]
    bio_ar: Mapped[str | None]
    bio_en: Mapped[str | None]
    venture_name_ar: Mapped[str | None]
    venture_name_en: Mapped[str | None]
    venture_summary_ar: Mapped[str | None]
    venture_summary_en: Mapped[str | None]
    sector: Mapped[str | None]
    country: Mapped[str | None]
    city: Mapped[str | None]
    website: Mapped[str | None]
    links: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    stage: Mapped[str] = mapped_column(nullable=False, server_default="idea")
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    domains: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    asks: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    is_mentor_eligible: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    kpi_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    kpi_snapshot_at: Mapped[datetime | None]
    is_public: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(_EMBEDDINGS_DIMENSION))
    embedding_model: Mapped[str | None]
    embedding_stale: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    search_tsv: Mapped[str] = mapped_column(TSVECTOR, Computed(_SEARCH_TSV_EXPR, persisted=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "display_name_ar IS NOT NULL OR display_name_en IS NOT NULL",
            name="display_name",
        ),
        CheckConstraint(
            "stage IN ('idea','prototype','pilot','revenue','growth')",
            name="stage",
        ),
        Index(
            "ix_founder_profiles_directory", "is_public", "updated_at"
        ),  # canonical sort: recently_active
        Index("ix_founder_profiles_skills", "skills", postgresql_using="gin"),
        Index("ix_founder_profiles_domains", "domains", postgresql_using="gin"),
        Index("ix_founder_profiles_country_sector", "country", "sector", "updated_at"),
        Index("ix_founder_profiles_search_tsv", "search_tsv", postgresql_using="gin"),
    )
