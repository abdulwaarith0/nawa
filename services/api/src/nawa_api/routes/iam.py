import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from nawa_api.contracts.iam import PERMISSION_META, Permission
from nawa_api.middleware.audit import audited
from nawa_api.middleware.iam import require_permission
from nawa_api.services.iam import groups as groups_service
from nawa_api.services.iam import policies as policies_service
from nawa_api.services.iam import users as users_service
from nawa_api.utils.envelope import created, ok

router = APIRouter(prefix="/iam", tags=["iam"])


class CreatePolicyInput(BaseModel):
    name: str
    statements: list = []
    description: str | None = None


class UpdatePolicyInput(BaseModel):
    statements: list | None = None
    description: str | None = None


class CreateGroupInput(BaseModel):
    name: str
    policy_ids: list[uuid.UUID] = []
    description: str | None = None


class UpdateGroupInput(BaseModel):
    policy_ids: list[uuid.UUID] | None = None
    description: str | None = None


class SetUserAccessInput(BaseModel):
    group_ids: list[uuid.UUID] | None = None
    attached_policy_ids: list[uuid.UUID] | None = None


@router.get("/permissions")
async def list_permissions_route():
    await require_permission(Permission.IAM_MANAGE)
    return ok({"permissions": PERMISSION_META})


@router.get("/policies")
async def list_policies_route(q: str | None = None, limit: int = 100):
    await require_permission(Permission.IAM_MANAGE)
    return ok(await policies_service.list_policies(q=q, limit=min(limit, 100)))


@router.post("/policies", status_code=201)
@audited(action="iam.policy.create", target_type="iam_policy", capture_body=True)
async def create_policy_route(body: CreatePolicyInput):
    await require_permission(Permission.IAM_MANAGE)
    return created(
        await policies_service.create_policy(
            name=body.name, statements=body.statements, description=body.description
        )
    )


@router.get("/policies/{policy_id}")
async def get_policy_route(policy_id: uuid.UUID):
    await require_permission(Permission.IAM_MANAGE)
    return ok(await policies_service.get_policy(policy_id=policy_id))


@router.patch("/policies/{policy_id}")
@audited(action="iam.policy.update", target_type="iam_policy")
async def update_policy_route(policy_id: uuid.UUID, body: UpdatePolicyInput):
    await require_permission(Permission.IAM_MANAGE)
    return ok(
        await policies_service.update_policy(
            policy_id=policy_id, statements=body.statements, description=body.description
        )
    )


@router.delete("/policies/{policy_id}")
@audited(action="iam.policy.delete", target_type="iam_policy")
async def delete_policy_route(policy_id: uuid.UUID):
    await require_permission(Permission.IAM_MANAGE)
    await policies_service.delete_policy(policy_id=policy_id)
    return ok(None)


@router.get("/groups")
async def list_groups_route(q: str | None = None, limit: int = 100):
    await require_permission(Permission.IAM_MANAGE)
    return ok(await groups_service.list_groups(q=q, limit=min(limit, 100)))


@router.post("/groups", status_code=201)
@audited(action="iam.group.create", target_type="iam_group", capture_body=True)
async def create_group_route(body: CreateGroupInput):
    await require_permission(Permission.IAM_MANAGE)
    return created(
        await groups_service.create_group(
            name=body.name, policy_ids=body.policy_ids, description=body.description
        )
    )


@router.get("/groups/{group_id}")
async def get_group_route(group_id: uuid.UUID):
    await require_permission(Permission.IAM_MANAGE)
    return ok(await groups_service.get_group(group_id=group_id))


@router.patch("/groups/{group_id}")
@audited(action="iam.group.update", target_type="iam_group")
async def update_group_route(group_id: uuid.UUID, body: UpdateGroupInput):
    await require_permission(Permission.IAM_MANAGE)
    return ok(
        await groups_service.update_group(
            group_id=group_id, policy_ids=body.policy_ids, description=body.description
        )
    )


@router.delete("/groups/{group_id}")
@audited(action="iam.group.delete", target_type="iam_group")
async def delete_group_route(group_id: uuid.UUID):
    await require_permission(Permission.IAM_MANAGE)
    await groups_service.delete_group(group_id=group_id)
    return ok(None)


@router.get("/users")
async def list_users_route(limit: int = 100):
    await require_permission(Permission.IAM_MANAGE)
    return ok(await users_service.list_iam_users(limit=min(limit, 100)))


@router.get("/users/{user_id}")
async def get_user_route(user_id: uuid.UUID):
    await require_permission(Permission.IAM_MANAGE)
    return ok(await users_service.get_iam_user(user_id=user_id))


@router.put("/users/{user_id}/access")
@audited(action="iam.user.set_access", target_type="user", capture_body=True)
async def set_user_access_route(user_id: uuid.UUID, body: SetUserAccessInput):
    await require_permission(Permission.IAM_MANAGE)
    return ok(
        await users_service.set_user_access(
            user_id=user_id,
            group_ids=body.group_ids,
            attached_policy_ids=body.attached_policy_ids,
        )
    )
