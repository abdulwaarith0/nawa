"""Batch scoring fan-out with progress (06-intake-copilot.md §3.3).

Fans `score_application` out over every normalized-but-unscored application in
a cycle (or, with `rescore=True`, every already-scored one — used after a
rubric version bump per §3.4; `create_scorecard_db`'s
`(application_id, rubric_id, source)` uniqueness means a re-score only ever
collides with itself, never with the prior version's scorecard, since the
active rubric has a new id by then).

Progress lives in Redis — a `{total, done, failed}` hash plus a pub/sub event
per application — so the console can show a live bar without polling the
database. `list_applications_db` caps at 100 rows per call, so the full target
set is paged into memory *before* any scoring starts (scoring flips an
application's status, so paging the same live-filtered query mid-run would
skip or duplicate rows).

A cycle-level essential-task budget stop (120% ceiling, same cap
`gateway`/`budget.enforce_budget` uses per call) halts the fan-out between
applications rather than letting every remaining one individually 429 through
the gateway: the progress hash records `stopped_reason` and the untouched
applications stay exactly where they were — `normalized` and retriable,
never dropped, never auto-rejected — per the same contract a single scoring
failure already has.
"""

from __future__ import annotations

import uuid

from nawa_api.ai import budget
from nawa_api.db.intake.get_active_rubric_db import get_active_rubric_db
from nawa_api.db.intake.list_applications_db import list_applications_db
from nawa_api.db.programs.get_program_cycle_db import get_program_cycle_db
from nawa_api.jobs.score_applications import score_application
from nawa_api.models.intake import Application
from nawa_api.runtime.redis import get_redis
from nawa_api.runtime.settings import get_settings
from nawa_api.utils.publish_event import publish_event

_PAGE_SIZE = 100
_MAX_PAGES = 200  # sanity bound, far above any real cycle size
PROGRESS_TTL_SECONDS = 24 * 3600


def progress_key(cycle_id: uuid.UUID) -> str:
    return f"jobs:intake:score:{cycle_id}:progress"


def progress_channel(cycle_id: uuid.UUID) -> str:
    return f"events:intake:score:{cycle_id}"


async def _list_all_target_applications(cycle_id: uuid.UUID, status: str) -> list[Application]:
    applications: list[Application] = []
    offset = 0
    for _ in range(_MAX_PAGES):
        page = await list_applications_db(
            cycle_id=cycle_id, status=status, limit=_PAGE_SIZE, offset=offset
        )
        applications.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return applications


async def _budget_exhausted(cycle_id: uuid.UUID) -> bool:
    cap = get_settings().ai_cycle_budget_usd * budget.ESSENTIAL_CEILING
    return await budget.get_spend(cycle_id) >= cap


async def _abort(key: str, reason: str) -> dict:
    redis = get_redis()
    await redis.delete(key)
    await redis.hset(key, mapping={"total": 0, "done": 0, "failed": 0, "stopped_reason": reason})
    await redis.expire(key, PROGRESS_TTL_SECONDS)
    return {"total": 0, "done": 0, "failed": 0, "stopped_reason": reason}


async def score_cycle(
    _ctx: dict | None = None, cycle_id: str | uuid.UUID = "", *, rescore: bool = False
) -> dict:
    cid = uuid.UUID(str(cycle_id))
    redis = get_redis()
    key = progress_key(cid)

    cycle = await get_program_cycle_db(cycle_id=cid)
    if cycle is None:
        return await _abort(key, "cycle_not_found")

    rubric = await get_active_rubric_db(program_id=cycle.program_id)
    if rubric is None:
        return await _abort(key, "no_active_rubric")

    target_status = "scored" if rescore else "normalized"
    applications = await _list_all_target_applications(cid, target_status)

    await redis.delete(key)
    await redis.hset(key, mapping={"total": len(applications), "done": 0, "failed": 0})
    await redis.expire(key, PROGRESS_TTL_SECONDS)

    stopped_reason: str | None = None
    for application in applications:
        if await _budget_exhausted(cid):
            stopped_reason = "budget_exceeded"
            break
        result = await score_application(
            application_id=str(application.id), rubric_id=str(rubric.id), cycle_id=cid
        )
        field = "done" if result == "scored" else "failed"
        await redis.hincrby(key, field, 1)
        await publish_event(
            progress_channel(cid),
            {"type": "progress", "application_id": str(application.id), "status": result},
        )

    if stopped_reason is not None:
        await redis.hset(key, "stopped_reason", stopped_reason)
        await publish_event(progress_channel(cid), {"type": "stopped", "reason": stopped_reason})

    counts = await redis.hgetall(key)
    return {
        "total": int(counts.get("total", 0)),
        "done": int(counts.get("done", 0)),
        "failed": int(counts.get("failed", 0)),
        "stopped_reason": counts.get("stopped_reason"),
    }
