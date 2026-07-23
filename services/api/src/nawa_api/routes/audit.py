from fastapi import APIRouter

from nawa_api.contracts.iam import Permission
from nawa_api.middleware.iam import require_permission
from nawa_api.services.audit.list_audit_logs import list_audit_logs
from nawa_api.utils.envelope import ok

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
async def list_audit_logs_route(
    actor: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    limit: int = 100,
):
    await require_permission(Permission.AUDIT_READ)
    return ok(
        await list_audit_logs(
            actor=actor, action=action, target_type=target_type, limit=min(limit, 100)
        )
    )
