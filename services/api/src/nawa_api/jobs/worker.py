"""arq worker settings. Queue lives under the `jobs:` namespace so
cache-invalidation globs (services:*) can never touch job state."""

from arq import cron
from arq.connections import RedisSettings

from nawa_api.jobs.embed_resource import embed_resource
from nawa_api.jobs.purge_audit_logs import purge_audit_logs
from nawa_api.runtime.settings import get_settings

QUEUE_NAME = "jobs:default"


async def _noop(_ctx: dict) -> str:
    """A trivial enqueue-able job used to prove the worker wiring in tests."""
    return "ok"


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    redis_settings = _redis_settings()
    queue_name = QUEUE_NAME
    functions = [purge_audit_logs, embed_resource, _noop]
    cron_jobs = [cron(purge_audit_logs, hour=3, minute=0)]
