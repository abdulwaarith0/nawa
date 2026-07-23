"""The ONLY module in nawa_api permitted to read os.environ.

Every other module imports `get_settings()` from here. Enforced by a
conformance test (tests/runtime/test_settings.py) that greps the source
tree for `os.environ` outside this file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def read_env(name: str, fallback: str | None = None) -> str | None:
    value = os.environ.get(name)
    return fallback if value is None or value.strip() == "" else value


def read_int_env(name: str, fallback: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return fallback
    try:
        return int(raw)
    except ValueError:
        return fallback


def read_float_env(name: str, fallback: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    redis_url: str
    jwt_secret: str
    web_origin: str
    api_internal_url: str

    s3_endpoint: str | None
    s3_access_key: str | None
    s3_secret_key: str | None
    s3_bucket: str | None

    anthropic_api_key: str | None
    openai_api_key: str | None
    llm_default_provider: str
    embeddings_provider: str
    embeddings_dimension: int
    ai_cycle_budget_usd: float

    access_ttl_seconds: int
    refresh_ttl_seconds: int
    session_ttl_seconds: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        environment=read_env("ENVIRONMENT", "development"),
        database_url=read_env(
            "DATABASE_URL",
            "postgresql+asyncpg://nawa:nawa@localhost:5433/nawa_dev",
        ),
        redis_url=read_env("REDIS_URL", "redis://localhost:6379/0"),
        jwt_secret=read_env("JWT_SECRET", "") or "",
        web_origin=read_env("WEB_ORIGIN", "http://localhost:3000"),
        api_internal_url=read_env("API_INTERNAL_URL", "http://localhost:8000"),
        s3_endpoint=read_env("S3_ENDPOINT"),
        s3_access_key=read_env("S3_ACCESS_KEY"),
        s3_secret_key=read_env("S3_SECRET_KEY"),
        s3_bucket=read_env("S3_BUCKET"),
        anthropic_api_key=read_env("ANTHROPIC_API_KEY"),
        openai_api_key=read_env("OPENAI_API_KEY"),
        llm_default_provider=read_env("LLM_DEFAULT_PROVIDER", "anthropic"),
        embeddings_provider=read_env("EMBEDDINGS_PROVIDER", "openai"),
        embeddings_dimension=read_int_env("EMBEDDINGS_DIMENSION", 1536),
        ai_cycle_budget_usd=read_float_env("AI_CYCLE_BUDGET_USD", 50.0),
        access_ttl_seconds=read_int_env("ACCESS_TTL_SECONDS", 900),
        refresh_ttl_seconds=read_int_env("REFRESH_TTL_SECONDS", 60 * 24 * 3600),
        session_ttl_seconds=read_int_env("SESSION_TTL_SECONDS", 7 * 24 * 3600),
    )
