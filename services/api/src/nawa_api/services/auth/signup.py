from nawa_api.contracts.auth import SignupInput
from nawa_api.contracts.errors import ERR_CONFLICT, ERR_INVALID_FIELDS
from nawa_api.contracts.iam import MEMBERS_GROUP_NAME
from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db.users.get_user_by_email_db import get_user_by_email_db
from nawa_api.services.auth.establish_session import establish_session, new_device_id
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.password import hash_password


async def signup(body: SignupInput, *, bearer: bool, device_id: str | None = None) -> dict:
    existing = await get_user_by_email_db(email=body.email)
    if existing is not None:
        raise ERR_CONFLICT

    username = body.username or body.email.split("@")[0]
    user = await create_user_db(
        email=body.email,
        username=username,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        language=body.language,
        phone=body.phone,
    )
    if user is None:
        raise ERR_CONFLICT  # unique collision on username/phone, or degraded write

    members = await get_group_by_name_db(name=MEMBERS_GROUP_NAME)
    if members is None:
        raise ERR_INVALID_FIELDS
    await add_group_member_db(group_id=members.id, user_id=user.id)

    await invalidate_cache_keys("services:iam:list_iam_users:*")
    return await establish_session(user, device_id=device_id or new_device_id(), bearer=bearer)
