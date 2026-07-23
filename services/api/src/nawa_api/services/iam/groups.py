"""IAM group admin services (list/get/create/update/delete) with caching."""

import uuid

from pydantic import BaseModel

from nawa_api.contracts.errors import ERR_CONFLICT, ERR_NOT_FOUND
from nawa_api.db.iam.create_group_db import create_group_db
from nawa_api.db.iam.delete_group_db import delete_group_db
from nawa_api.db.iam.get_group_by_id_db import get_group_by_id_db
from nawa_api.db.iam.list_groups_db import list_groups_db
from nawa_api.db.iam.update_group_db import update_group_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys

CACHE_TTL_SECONDS = 300


class _GroupList(BaseModel):
    items: list[dict]


def _dto(group) -> dict:
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "policy_ids": [str(p) for p in group.policy_ids],
        "inline_statements": group.inline_statements,
        "managed": group.managed,
    }


def list_query_key(*, q: str | None, limit: int) -> str:
    return f"services:iam:list_groups:{q or '*'}:{limit}"


def get_query_key(*, group_id: uuid.UUID | str) -> str:
    return f"services:iam:get_group:{group_id}"


async def list_groups(*, q: str | None = None, limit: int = 100) -> list[dict]:
    key = list_query_key(q=q, limit=limit)
    cached = await redis_retrieve_key(key, _GroupList)
    if cached is not None:
        return cached.items
    rows = await list_groups_db(limit=limit)
    items = [_dto(g) for g in rows]
    if items:
        await redis_update_key(key, _GroupList(items=items), CACHE_TTL_SECONDS)
    return items


async def get_group(*, group_id: uuid.UUID) -> dict:
    group = await get_group_by_id_db(group_id=group_id)
    if group is None:
        raise ERR_NOT_FOUND
    return _dto(group)


async def create_group(
    *, name: str, policy_ids: list[uuid.UUID] | None = None, description: str | None = None
) -> dict:
    group = await create_group_db(name=name, policy_ids=policy_ids or [], description=description)
    if group is None:
        raise ERR_CONFLICT
    await invalidate_cache_keys("services:iam:list_groups:*")
    return _dto(group)


async def update_group(
    *,
    group_id: uuid.UUID,
    policy_ids: list[uuid.UUID] | None = None,
    description: str | None = None,
) -> dict:
    group = await get_group_by_id_db(group_id=group_id)
    if group is None:
        raise ERR_NOT_FOUND
    if group.managed:
        raise ERR_CONFLICT
    fields = {}
    if policy_ids is not None:
        fields["policy_ids"] = policy_ids
    if description is not None:
        fields["description"] = description
    if fields:
        await update_group_db(group_id=group_id, **fields)
    await invalidate_cache_keys("services:iam:list_groups:*", get_query_key(group_id=group_id))
    return await get_group(group_id=group_id)


async def delete_group(*, group_id: uuid.UUID) -> None:
    group = await get_group_by_id_db(group_id=group_id)
    if group is None:
        raise ERR_NOT_FOUND
    if group.managed:
        raise ERR_CONFLICT
    await delete_group_db(group_id=group_id)
    await invalidate_cache_keys("services:iam:list_groups:*", get_query_key(group_id=group_id))
