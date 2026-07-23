import importlib

import pytest


def _reload_settings():
    from nawa_api.runtime import settings as settings_module

    importlib.reload(settings_module)
    return settings_module


def test_read_env_blank_falls_back_to_none(monkeypatch):
    from nawa_api.runtime.settings import read_env

    monkeypatch.setenv("NAWA_TEST_BLANK", "   ")
    assert read_env("NAWA_TEST_BLANK") is None
    assert read_env("NAWA_TEST_BLANK", "fallback") == "fallback"


def test_read_env_missing_uses_fallback(monkeypatch):
    from nawa_api.runtime.settings import read_env

    monkeypatch.delenv("NAWA_TEST_MISSING", raising=False)
    assert read_env("NAWA_TEST_MISSING", "fallback") == "fallback"


def test_read_env_present_value_returned(monkeypatch):
    from nawa_api.runtime.settings import read_env

    monkeypatch.setenv("NAWA_TEST_PRESENT", "hello")
    assert read_env("NAWA_TEST_PRESENT") == "hello"


def test_read_int_env_blank_falls_back(monkeypatch):
    from nawa_api.runtime.settings import read_int_env

    monkeypatch.setenv("NAWA_TEST_INT_BLANK", "")
    assert read_int_env("NAWA_TEST_INT_BLANK", 42) == 42


def test_read_int_env_garbage_falls_back(monkeypatch):
    from nawa_api.runtime.settings import read_int_env

    monkeypatch.setenv("NAWA_TEST_INT_GARBAGE", "not-a-number")
    assert read_int_env("NAWA_TEST_INT_GARBAGE", 42) == 42


def test_read_int_env_zero_is_a_live_value(monkeypatch):
    from nawa_api.runtime.settings import read_int_env

    monkeypatch.setenv("NAWA_TEST_INT_ZERO", "0")
    assert read_int_env("NAWA_TEST_INT_ZERO", 42) == 0


def test_read_int_env_missing_falls_back(monkeypatch):
    from nawa_api.runtime.settings import read_int_env

    monkeypatch.delenv("NAWA_TEST_INT_MISSING", raising=False)
    assert read_int_env("NAWA_TEST_INT_MISSING", 7) == 7


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("EMBEDDINGS_DIMENSION", raising=False)
    settings_module = _reload_settings()
    settings = settings_module.get_settings()

    assert settings.environment == "development"
    assert settings.database_url == ("postgresql+asyncpg://nawa:nawa@localhost:5433/nawa_dev")
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.embeddings_dimension == 1536
    assert settings.access_ttl_seconds == 900
    assert settings.refresh_ttl_seconds == 60 * 24 * 3600
    assert settings.session_ttl_seconds == 7 * 24 * 3600


def test_settings_reads_overrides(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EMBEDDINGS_DIMENSION", "768")
    settings_module = _reload_settings()
    settings = settings_module.get_settings()

    assert settings.environment == "production"
    assert settings.embeddings_dimension == 768
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("EMBEDDINGS_DIMENSION", raising=False)
    _reload_settings()


def test_settings_is_frozen(monkeypatch):
    settings_module = _reload_settings()
    settings = settings_module.get_settings()
    with pytest.raises(Exception):
        settings.environment = "hacked"


def test_only_settings_module_reads_os_environ():
    """Conformance test: no other nawa_api module touches os.environ directly."""
    import pathlib
    import re

    src_root = pathlib.Path(__file__).parent.parent.parent / "src" / "nawa_api"
    offenders = []
    for path in src_root.rglob("*.py"):
        if path.name == "settings.py":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"os\.environ", text):
            offenders.append(str(path))
    assert offenders == []
