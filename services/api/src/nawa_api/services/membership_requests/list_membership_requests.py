from nawa_api.db.membership_requests.list_membership_requests_db import (
    list_membership_requests_db,
)
from nawa_api.services.membership_requests._dto import membership_request_dto


async def list_membership_requests(
    *, status: str | None = None, limit: int | None = None, offset: int | None = None
) -> list[dict]:
    rows = await list_membership_requests_db(status=status, limit=limit, offset=offset)
    return [membership_request_dto(r) for r in rows]
