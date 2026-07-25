import uuid

from fastapi import APIRouter

from nawa_api.contracts.iam import Permission
from nawa_api.middleware.audit import audited
from nawa_api.middleware.iam import require_permission
from nawa_api.services.membership_requests.approve_membership_request import (
    approve_membership_request,
)
from nawa_api.services.membership_requests.list_membership_requests import (
    list_membership_requests,
)
from nawa_api.services.membership_requests.reject_membership_request import (
    reject_membership_request,
)
from nawa_api.utils.envelope import ok

router = APIRouter(tags=["membership_requests"])


@router.get("/admin/access-requests")
async def list_access_requests_route(status: str | None = None, limit: int = 20, offset: int = 0):
    await require_permission(Permission.IAM_MANAGE)
    return ok(await list_membership_requests(status=status, limit=limit, offset=offset))


@router.post("/admin/access-requests/{request_id}/approve")
@audited(action="admin.access_request.approve", target_type="membership_request")
async def approve_access_request_route(request_id: uuid.UUID):
    session = await require_permission(Permission.IAM_MANAGE)
    return ok(
        await approve_membership_request(
            request_id=request_id, reviewer_user_id=uuid.UUID(session.sub)
        )
    )


@router.post("/admin/access-requests/{request_id}/reject")
@audited(action="admin.access_request.reject", target_type="membership_request")
async def reject_access_request_route(request_id: uuid.UUID):
    session = await require_permission(Permission.IAM_MANAGE)
    return ok(
        await reject_membership_request(
            request_id=request_id, reviewer_user_id=uuid.UUID(session.sub)
        )
    )
