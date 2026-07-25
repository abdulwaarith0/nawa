"""Public request-access intake. Non-enumerable: the response is identical
whether or not the email already belongs to a real account — callers must
never be able to tell the two cases apart."""

from nawa_api.contracts.auth import RequestAccessInput
from nawa_api.db.membership_requests.create_membership_request_db import (
    create_membership_request_db,
)
from nawa_api.db.users.get_user_by_email_db import get_user_by_email_db


async def submit_membership_request(body: RequestAccessInput) -> None:
    existing = await get_user_by_email_db(email=body.email)
    if existing is None:
        await create_membership_request_db(
            full_name=body.full_name,
            email=body.email,
            organization=body.organization,
            reason=body.reason,
        )
    # else: silently no-op — same response either way.
