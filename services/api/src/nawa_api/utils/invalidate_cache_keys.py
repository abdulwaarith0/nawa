"""The one shared cache-invalidation helper. Every write service invalidates
through this. Globs expand via SCAN — `KEYS` is banned repo-wide."""

from nawa_api.runtime.redis import get_redis


async def invalidate_cache_keys(*patterns: str) -> None:
    """Delete exact keys and glob patterns. Globs expand via SCAN, never KEYS."""
    redis = get_redis()
    keys: list[str] = [p for p in patterns if "*" not in p]
    for pattern in (p for p in patterns if "*" in p):
        cursor = 0
        while True:
            cursor, batch = await redis.scan(cursor=cursor, match=pattern, count=250)
            keys.extend(k if isinstance(k, str) else k.decode() for k in batch)
            if cursor == 0:
                break
    for i in range(0, len(keys), 500):
        chunk = keys[i : i + 500]
        if chunk:
            await redis.delete(*chunk)
