import pytest


def test_main_module_builds_app():
    import nawa_api.main as main

    assert main.app is not None
    assert main.app.title == "NAWA API"


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent(monkeypatch):
    import nawa_api.runtime.bootstrap as bootstrap_module

    calls = {"connect_pg": 0, "connect_redis": 0, "seed": 0}

    async def _pg():
        calls["connect_pg"] += 1

    async def _redis():
        calls["connect_redis"] += 1

    async def _seed(*_a, **_k):
        calls["seed"] += 1

    monkeypatch.setattr(bootstrap_module, "connect_postgres", _pg)
    monkeypatch.setattr(bootstrap_module, "connect_redis", _redis)
    monkeypatch.setattr(bootstrap_module, "seed_defaults", _seed)
    monkeypatch.setattr(bootstrap_module, "_booted", False)

    await bootstrap_module.bootstrap()
    await bootstrap_module.bootstrap()  # second call is a no-op (guarded)

    assert calls == {"connect_pg": 1, "connect_redis": 1, "seed": 1}


@pytest.mark.asyncio
async def test_bootstrap_seed_failure_is_non_fatal(monkeypatch):
    import nawa_api.runtime.bootstrap as bootstrap_module

    async def _ok():
        return None

    async def _boom(*_a, **_k):
        raise RuntimeError("seed exploded")

    monkeypatch.setattr(bootstrap_module, "connect_postgres", _ok)
    monkeypatch.setattr(bootstrap_module, "connect_redis", _ok)
    monkeypatch.setattr(bootstrap_module, "seed_defaults", _boom)
    monkeypatch.setattr(bootstrap_module, "_booted", False)

    # Must not raise — a seed hiccup is loud but non-fatal.
    await bootstrap_module.bootstrap()
