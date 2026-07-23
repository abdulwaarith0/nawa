"""IAM user admin services: list/get with compiled effective perms, and
set_user_access (eager invalidation so revocations bite in seconds)."""

import uuid

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.db.iam.set_user_group_memberships_db import set_user_group_memberships_db
from nawa_api.db.users.get_user_by_id_db import get_user_by_id_db
from nawa_api.db.users.list_users_db import list_users_db
from nawa_api.db.users.update_user_db import update_user_db
from nawa_api.services.iam.resolve_effective_permissions import (
    get_query_key as effective_key,
)
from nawa_api.services.iam.resolve_effective_permissions import (
    resolve_effective_permissions,
)
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys


def _base_dto(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "language": user.language,
        "is_active": user.is_active,
        "attached_policy_ids": [str(p) for p in user.attached_policy_ids],
    }


async def list_iam_users(*, limit: int = 100) -> list[dict]:
    rows = await list_users_db(limit=limit)
    return [_base_dto(u) for u in rows]


async def get_iam_user(*, user_id: uuid.UUID) -> dict:
    user = await get_user_by_id_db(user_id=user_id)
    if user is None:
        raise ERR_NOT_FOUND
    dto = _base_dto(user)
    dto["effective"] = sorted(await resolve_effective_permissions(user_id=user.id))
    return dto


async def set_user_access(
    *,
    user_id: uuid.UUID,
    group_ids: list[uuid.UUID] | None = None,
    attached_policy_ids: list[uuid.UUID] | None = None,
) -> dict:
    user = await get_user_by_id_db(user_id=user_id)
    if user is None:
        raise ERR_NOT_FOUND

    if attached_policy_ids is not None:
        await update_user_db(user_id=user_id, attached_policy_ids=attached_policy_ids)
    if group_ids is not None:
        await set_user_group_memberships_db(user_id=user_id, group_ids=group_ids)

    # Eager invalidation of THIS user's effective key — revocation within seconds.
    await invalidate_cache_keys(
        effective_key(user_id=user_id),
        f"services:iam:get_iam_user:{user_id}",
        "services:iam:list_iam_users:*",
    )
    # Recompute fresh so the returned DTO reflects the new access immediately.
    return await get_iam_user(user_id=user_id)
