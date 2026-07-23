"""AI admin + demo routes (05-ai-infrastructure.md §7)."""

from fastapi import APIRouter

from nawa_api.contracts.iam import Permission
from nawa_api.middleware.iam import require_permission
from nawa_api.services.ai_calls.list_ai_calls import list_ai_calls
from nawa_api.utils.envelope import ok

router = APIRouter(tags=["ai"])


@router.get("/admin/ai-calls")
async def list_ai_calls_route(
    task: str | None = None,
    provider: str | None = None,
    status: str | None = None,
    cycle: str | None = None,
    limit: int = 100,
):
    await require_permission(Permission.ADMIN_AI_CALLS_READ)
    return ok(
        await list_ai_calls(
            task=task, provider=provider, status=status, cycle=cycle, limit=min(limit, 100)
        )
    )
