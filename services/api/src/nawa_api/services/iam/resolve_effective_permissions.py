"""Live effective-permission resolution — the API's authority.

Cache key `services:iam:effective:<user_id>`, TTL 30 s. Because the API
re-resolves per request through this short cache, revocations bite in seconds,
not at next sign-in. Inactive users compile to the empty set (deactivation
denies everything within 30 s). An empty set is a legitimate cacheable value
here — it is a computed result, not a degraded read.
"""

import uuid

from pydantic import BaseModel

from nawa_api.contracts.iam import compile_statements
from nawa_api.db.iam.list_groups_by_ids_db import list_groups_by_ids_db
from nawa_api.db.iam.list_policies_by_ids_db import list_policies_by_ids_db
from nawa_api.db.iam.list_user_group_ids_db import list_user_group_ids_db
from nawa_api.db.users.get_user_by_id_db import get_user_by_id_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 30


class _EffectiveCache(BaseModel):
    perms: list[str]


def get_query_key(*, user_id: uuid.UUID | str) -> str:
    return f"services:iam:effective:{user_id}"


async def resolve_effective_permissions(
    *, user_id: uuid.UUID | str, refresh_cache: bool = False
) -> set[str]:
    key = get_query_key(user_id=user_id)
    if not refresh_cache:
        cached = await redis_retrieve_key(key, _EffectiveCache)
        if cached is not None:
            return set(cached.perms)

    compiled = await _compile_for_user(user_id)
    await redis_update_key(key, _EffectiveCache(perms=sorted(compiled)), CACHE_TTL_SECONDS)
    return compiled


async def _compile_for_user(user_id: uuid.UUID | str) -> set[str]:
    uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    user = await get_user_by_id_db(user_id=uid)
    if user is None or not user.is_active:
        return set()

    group_ids = await list_user_group_ids_db(user_id=uid)
    groups = await list_groups_by_ids_db(group_ids=group_ids)

    policy_ids = set(user.attached_policy_ids)
    for group in groups:
        policy_ids.update(group.policy_ids)

    policies = await list_policies_by_ids_db(policy_ids=list(policy_ids))
    statements: list[dict] = []
    for policy in policies:
        statements.extend(policy.statements)
    for group in groups:
        statements.extend(group.inline_statements)

    try:
        return compile_statements(statements)
    except ValueError:
        # Malformed statement — fail closed (deny) rather than crash.
        return set()
