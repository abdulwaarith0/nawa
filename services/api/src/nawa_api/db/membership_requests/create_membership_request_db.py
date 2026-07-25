from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import MembershipRequest
from nawa_api.utils.logger import get_logger


async def create_membership_request_db(
    *,
    full_name: str,
    email: str,
    organization: str | None = None,
    reason: str | None = None,
    session: AsyncSession | None = None,
) -> MembershipRequest | None:
    with observe_db(
        operation="write", table="membership_requests", method="create_membership_request_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = MembershipRequest(
                    full_name=full_name,
                    email=email,
                    organization=organization,
                    reason=reason,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_membership_request_db", exc_info=True)
            obs.success = False
            return None
