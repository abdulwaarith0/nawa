from types import SimpleNamespace

import pytest

from nawa_api.contracts.errors import ApiError
from nawa_api.runtime import storage as storage_mod
from nawa_api.runtime.storage import (
    MockObjectStorageProvider,
    S3ObjectStorageProvider,
    get_storage_provider,
    reset_storage_provider_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_storage_provider_cache()
    yield
    reset_storage_provider_cache()


def test_get_storage_provider_returns_mock_in_test_env():
    provider = get_storage_provider()
    assert isinstance(provider, MockObjectStorageProvider)


def test_get_storage_provider_is_a_singleton():
    a = get_storage_provider()
    b = get_storage_provider()
    assert a is b


def test_reset_storage_provider_cache_clears_the_singleton():
    a = get_storage_provider()
    reset_storage_provider_cache()
    b = get_storage_provider()
    assert a is not b


async def test_mock_provider_put_and_presign_round_trip():
    provider = MockObjectStorageProvider()
    await provider.put_object("intake/exports/x.xlsx", b"hello", content_type="application/xlsx")
    assert provider.get_object("intake/exports/x.xlsx") == b"hello"
    url = await provider.presign_get_url("intake/exports/x.xlsx", expires_seconds=3600)
    assert "intake/exports/x.xlsx" in url


def test_mock_provider_get_object_returns_none_for_missing_key():
    provider = MockObjectStorageProvider()
    assert provider.get_object("does-not-exist") is None


def test_s3_provider_raises_when_unconfigured(monkeypatch):
    monkeypatch.setattr(
        storage_mod,
        "get_settings",
        lambda: SimpleNamespace(
            s3_endpoint=None, s3_access_key=None, s3_secret_key=None, s3_bucket=None
        ),
    )
    with pytest.raises(ApiError):
        S3ObjectStorageProvider()


def test_get_storage_provider_uses_s3_outside_test_env_and_still_fails_closed(monkeypatch):
    # No real S3 endpoint is configured anywhere in this process, so even
    # outside ENVIRONMENT=test, construction must fail closed rather than
    # silently reach for a real boto3 client.
    monkeypatch.setattr(
        storage_mod,
        "get_settings",
        lambda: SimpleNamespace(
            environment="production",
            s3_endpoint=None,
            s3_access_key=None,
            s3_secret_key=None,
            s3_bucket=None,
        ),
    )
    with pytest.raises(ApiError):
        get_storage_provider()
