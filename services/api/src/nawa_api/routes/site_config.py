from fastapi import APIRouter
from pydantic import BaseModel

from nawa_api.contracts.iam import Permission
from nawa_api.middleware.audit import audited
from nawa_api.middleware.iam import require_permission
from nawa_api.services.site_config.get_site_config import get_public_site_config, get_site_config
from nawa_api.services.site_config.update_site_config import update_site_config
from nawa_api.utils.envelope import ok

router = APIRouter(tags=["site_config"])


class UpdateSiteConfigInput(BaseModel):
    key: str
    value: object


@router.get("/site-config")
async def public_site_config_route():
    # public projection — only the flags the web shell needs
    return ok(await get_public_site_config())


@router.get("/admin/site-config")
async def admin_site_config_route():
    await require_permission(Permission.ADMIN_MANAGE)
    return ok(await get_site_config())


@router.patch("/admin/site-config")
@audited(action="admin.site_config.update", target_type="site_config", capture_body=True)
async def update_site_config_route(body: UpdateSiteConfigInput):
    session = await require_permission(Permission.ADMIN_MANAGE)
    import uuid

    await update_site_config(key=body.key, value=body.value, updated_by=uuid.UUID(session.sub))
    return ok(await get_site_config(refresh_cache=True))
