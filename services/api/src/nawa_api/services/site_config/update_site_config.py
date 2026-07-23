import uuid

from nawa_api.db.site_config.upsert_site_config_db import upsert_site_config_db
from nawa_api.services.site_config.get_site_config import get_query_key
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys


async def update_site_config(*, key: str, value, updated_by: uuid.UUID | None = None) -> bool:
    ok = await upsert_site_config_db(key=key, value=value, updated_by=updated_by)
    if ok:
        await invalidate_cache_keys(get_query_key())
    return ok
