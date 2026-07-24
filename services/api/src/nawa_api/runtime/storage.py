"""Object storage — the ONE client for MinIO/S3 (04-platform-foundation.md's
"standard object-storage pipeline", first actually implemented here for
06-intake-copilot.md's export). Mirrors the AI-provider pattern exactly:
`ENVIRONMENT=test` forces an in-memory mock so the whole test suite runs
offline — no real bucket is ever touched by a test, same reasoning as
`ai/providers/get_provider()` forcing MockLLMProvider.

boto3 is sync; calls are pushed through `asyncio.to_thread` rather than
pulling in an extra async-S3 dependency, matching the pattern already used
for the alembic migration runner in tests/conftest.py.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from nawa_api.contracts.errors import ERR_STORAGE_NOT_CONFIGURED
from nawa_api.runtime.settings import get_settings


class ObjectStorageProvider(Protocol):
    async def put_object(self, key: str, data: bytes, *, content_type: str) -> None: ...

    async def presign_get_url(self, key: str, *, expires_seconds: int) -> str: ...


class MockObjectStorageProvider:
    """In-memory, deterministic — what the whole test suite runs against."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put_object(self, key: str, data: bytes, *, content_type: str) -> None:
        self._objects[key] = data

    async def presign_get_url(self, key: str, *, expires_seconds: int) -> str:
        return f"mock://storage/{key}?expires={expires_seconds}"

    def get_object(self, key: str) -> bytes | None:
        """Test-only accessor — real providers have no equivalent (the
        presigned URL IS the read path)."""
        return self._objects.get(key)


class S3ObjectStorageProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not (
            settings.s3_endpoint
            and settings.s3_access_key
            and settings.s3_secret_key
            and settings.s3_bucket
        ):
            raise ERR_STORAGE_NOT_CONFIGURED
        import boto3  # pragma: no cover - real client, offline-untestable

        self._bucket = settings.s3_bucket  # pragma: no cover
        self._client = boto3.client(  # pragma: no cover
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    async def put_object(
        self, key: str, data: bytes, *, content_type: str
    ) -> None:  # pragma: no cover - real client, offline-untestable
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def presign_get_url(
        self, key: str, *, expires_seconds: int
    ) -> str:  # pragma: no cover - real client, offline-untestable
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )


_singleton: ObjectStorageProvider | None = None


def get_storage_provider() -> ObjectStorageProvider:
    global _singleton
    if _singleton is None:
        settings = get_settings()
        _singleton = (
            MockObjectStorageProvider()
            if settings.environment == "test"
            else S3ObjectStorageProvider()
        )
    return _singleton


def reset_storage_provider_cache() -> None:
    global _singleton
    _singleton = None
