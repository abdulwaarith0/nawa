"""Redis fixed-window rate limiter. Degrades open on Redis errors (availability
over strictness for non-monetary actions)."""

from dataclasses import dataclass

from nawa_api.runtime.redis import get_redis
from nawa_api.utils.logger import get_logger


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int


async def consume(
    *, scope: str, identifier: str, limit: int, window_seconds: int = 60
) -> RateLimitResult:
    key = f"rl:{scope}:{identifier}"
    redis = get_redis()
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        ttl = await redis.ttl(key)
    except Exception:
        get_logger().warning("rate_limit_degraded_open", scope=scope)
        return RateLimitResult(allowed=True, limit=limit, remaining=limit, reset_seconds=0)
    return RateLimitResult(
        allowed=count <= limit,
        limit=limit,
        remaining=max(limit - count, 0),
        reset_seconds=max(ttl, 0),
    )
