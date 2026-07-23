"""Idempotently upsert the builtin IAM policies and groups on every boot.

Loud but non-fatal: an exception here is logged and boot continues (it
self-heals next boot). Runs upsert-by-name so managed rows are pinned back to
the catalog even if they drifted in the DB.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.contracts.iam import BUILTIN_GROUPS, BUILTIN_POLICIES
from nawa_api.db.iam.get_policy_by_name_db import get_policy_by_name_db
from nawa_api.db.iam.upsert_group_by_name_db import upsert_group_by_name_db
from nawa_api.db.iam.upsert_policy_by_name_db import upsert_policy_by_name_db
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.logger import get_logger


async def seed_defaults(*, session: AsyncSession | None = None) -> None:
    for name, statements in BUILTIN_POLICIES.items():
        await upsert_policy_by_name_db(
            name=name, statements=statements, managed=True, session=session
        )

    for group_name, policy_name in BUILTIN_GROUPS.items():
        policy = await get_policy_by_name_db(name=policy_name, session=session)
        policy_ids = [policy.id] if policy is not None else []
        await upsert_group_by_name_db(
            name=group_name, policy_ids=policy_ids, managed=True, session=session
        )

    await invalidate_cache_keys("services:iam:list_policies:*", "services:iam:list_groups:*")
    get_logger().info("iam_seed_defaults_complete")
