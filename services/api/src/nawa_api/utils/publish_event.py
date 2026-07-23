"""Pub/sub publish helper — real-time is an enhancement, never a dependency.
Failures are caught and logged; a pub/sub outage must never fail the write
that triggered it."""

import json

from nawa_api.runtime.redis import get_redis
from nawa_api.utils.logger import get_logger


async def publish_event(channel: str, payload: dict) -> None:
    try:
        await get_redis().publish(channel, json.dumps(payload))
    except Exception:
        get_logger().warning("publish_event_failed", channel=channel)
