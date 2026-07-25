import uuid
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import MembershipRequest
from nawa_api.utils.logger import get_logger


async def update_membership_request_status_db(
    *,
    request_id: uuid.UUID,
    session: AsyncSession | None = None,
    **fields: Any,
) -> bool:
    with observe_db(
        operation="write",
        table="membership_requests",
        method="update_membership_request_status_db",
    ) as obs:
        try:
            async with use_session(session) as s:
                result = await s.execute(
                    update(MembershipRequest)
                    .where(MembershipRequest.id == request_id)
                    .values(**fields)
                )
            obs.success = result.rowcount > 0
            return obs.success
        except Exception:
            get_logger().warning(
                "db_error", method="update_membership_request_status_db", exc_info=True
            )
            obs.success = False
            return False
