import uuid
from datetime import UTC, datetime

from nawa_api.contracts.errors import ERR_CONFLICT, ERR_NOT_FOUND
from nawa_api.db.membership_requests.get_membership_request_db import get_membership_request_db
from nawa_api.db.membership_requests.update_membership_request_status_db import (
    update_membership_request_status_db,
)
from nawa_api.services.membership_requests._dto import membership_request_dto


async def reject_membership_request(*, request_id: uuid.UUID, reviewer_user_id: uuid.UUID) -> dict:
    request = await get_membership_request_db(request_id=request_id)
    if request is None:
        raise ERR_NOT_FOUND
    if request.status != "pending":
        raise ERR_CONFLICT  # already reviewed

    await update_membership_request_status_db(
        request_id=request_id,
        status="rejected",
        reviewed_by_user_id=reviewer_user_id,
        reviewed_at=datetime.now(UTC),
    )
    rejected = await get_membership_request_db(request_id=request_id)
    return membership_request_dto(rejected)
