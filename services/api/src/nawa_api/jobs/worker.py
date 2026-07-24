"""arq worker settings. Queue lives under the `jobs:` namespace so
cache-invalidation globs (services:*) can never touch job state."""

from arq import cron
from arq.connections import RedisSettings

from nawa_api.jobs.dedup_scan import dedup_scan
from nawa_api.jobs.embed_application import embed_application
from nawa_api.jobs.embed_resource import embed_resource
from nawa_api.jobs.export_shortlist import export_shortlist
from nawa_api.jobs.hidden_gem_scan import hidden_gem_scan
from nawa_api.jobs.normalize_applications import normalize_application
from nawa_api.jobs.purge_audit_logs import purge_audit_logs
from nawa_api.jobs.score_applications import score_application
from nawa_api.jobs.score_cycle import score_cycle
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
    functions = [
        purge_audit_logs,
        embed_resource,
        normalize_application,
        score_application,
        score_cycle,
        embed_application,
        dedup_scan,
        hidden_gem_scan,
        export_shortlist,
        _noop,
    ]
    cron_jobs = [cron(purge_audit_logs, hour=3, minute=0)]
