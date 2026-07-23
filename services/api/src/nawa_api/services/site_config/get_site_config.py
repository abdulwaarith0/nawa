"""Cached read of the whole site_config map (TTL 60 s)."""

from pydantic import BaseModel

from nawa_api.db.site_config.list_all_site_config_db import list_all_site_config_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 60

_PUBLIC_KEYS = {"maintenance_mode"}


class _SiteConfigCache(BaseModel):
    values: dict


def get_query_key() -> str:
    return "services:site_config:get_site_config"


async def get_site_config(*, refresh_cache: bool = False) -> dict:
    key = get_query_key()
    if not refresh_cache:
        cached = await redis_retrieve_key(key, _SiteConfigCache)
        if cached is not None:
            return cached.values
    values = await list_all_site_config_db()
    if values:
        await redis_update_key(key, _SiteConfigCache(values=values), CACHE_TTL_SECONDS)
    return values


async def get_flag(key: str, default: bool) -> bool:
    values = await get_site_config()
    raw = values.get(key, default)
    return bool(raw)


async def get_public_site_config() -> dict:
    values = await get_site_config()
    return {k: v for k, v in values.items() if k in _PUBLIC_KEYS}
