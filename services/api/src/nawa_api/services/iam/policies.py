"""IAM policy admin services (list/get/create/update/delete) with caching."""

import uuid

from pydantic import BaseModel

from nawa_api.contracts.errors import ERR_CONFLICT, ERR_NOT_FOUND
from nawa_api.db.iam.create_policy_db import create_policy_db
from nawa_api.db.iam.delete_policy_db import delete_policy_db
from nawa_api.db.iam.get_policy_by_id_db import get_policy_by_id_db
from nawa_api.db.iam.list_policies_db import list_policies_db
from nawa_api.db.iam.update_policy_db import update_policy_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys

CACHE_TTL_SECONDS = 300


class _PolicyList(BaseModel):
    items: list[dict]


def _dto(policy) -> dict:
    return {
        "id": str(policy.id),
        "name": policy.name,
        "description": policy.description,
        "statements": policy.statements,
        "managed": policy.managed,
    }


def list_query_key(*, q: str | None, limit: int) -> str:
    return f"services:iam:list_policies:{q or '*'}:{limit}"


def get_query_key(*, policy_id: uuid.UUID | str) -> str:
    return f"services:iam:get_policy:{policy_id}"


async def list_policies(*, q: str | None = None, limit: int = 100) -> list[dict]:
    key = list_query_key(q=q, limit=limit)
    cached = await redis_retrieve_key(key, _PolicyList)
    if cached is not None:
        return cached.items
    rows = await list_policies_db(limit=limit)
    items = [_dto(p) for p in rows]
    if items:
        await redis_update_key(key, _PolicyList(items=items), CACHE_TTL_SECONDS)
    return items


async def get_policy(*, policy_id: uuid.UUID) -> dict:
    policy = await get_policy_by_id_db(policy_id=policy_id)
    if policy is None:
        raise ERR_NOT_FOUND
    return _dto(policy)


async def create_policy(*, name: str, statements: list, description: str | None = None) -> dict:
    policy = await create_policy_db(name=name, statements=statements, description=description)
    if policy is None:
        raise ERR_CONFLICT
    await invalidate_cache_keys("services:iam:list_policies:*")
    return _dto(policy)


async def update_policy(
    *, policy_id: uuid.UUID, statements: list | None = None, description: str | None = None
) -> dict:
    policy = await get_policy_by_id_db(policy_id=policy_id)
    if policy is None:
        raise ERR_NOT_FOUND
    if policy.managed:
        raise ERR_CONFLICT  # managed builtins are immutable via the API
    fields = {}
    if statements is not None:
        fields["statements"] = statements
    if description is not None:
        fields["description"] = description
    if fields:
        await update_policy_db(policy_id=policy_id, **fields)
    await invalidate_cache_keys("services:iam:list_policies:*", get_query_key(policy_id=policy_id))
    return await get_policy(policy_id=policy_id)


async def delete_policy(*, policy_id: uuid.UUID) -> None:
    policy = await get_policy_by_id_db(policy_id=policy_id)
    if policy is None:
        raise ERR_NOT_FOUND
    if policy.managed:
        raise ERR_CONFLICT
    await delete_policy_db(policy_id=policy_id)
    await invalidate_cache_keys("services:iam:list_policies:*", get_query_key(policy_id=policy_id))
