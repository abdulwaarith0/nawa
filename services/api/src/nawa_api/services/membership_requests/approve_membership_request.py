"""Approve a pending membership request: create the real `User` (mirrors
signup.py's Members group assignment), mark the request approved, then reuse
the existing password-reset mechanism verbatim so the applicant gets a real
settable code — no separate invite/email system."""

import secrets
import uuid
from datetime import UTC, datetime

from nawa_api.contracts.auth import ForgotPasswordInput
from nawa_api.contracts.errors import ERR_CONFLICT, ERR_INVALID_FIELDS, ERR_NOT_FOUND
from nawa_api.contracts.iam import MEMBERS_GROUP_NAME
from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.membership_requests.get_membership_request_db import get_membership_request_db
from nawa_api.db.membership_requests.update_membership_request_status_db import (
    update_membership_request_status_db,
)
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db.users.get_user_by_email_db import get_user_by_email_db
from nawa_api.services.auth.password_reset import forgot_password
from nawa_api.services.membership_requests._dto import membership_request_dto
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.password import hash_password


async def approve_membership_request(*, request_id: uuid.UUID, reviewer_user_id: uuid.UUID) -> dict:
    request = await get_membership_request_db(request_id=request_id)
    if request is None:
        raise ERR_NOT_FOUND
    if request.status != "pending":
        raise ERR_CONFLICT  # already reviewed

    if await get_user_by_email_db(email=request.email) is not None:
        raise ERR_CONFLICT  # email already has an account

    username = request.email.split("@")[0]
    # Unguessable placeholder — the applicant never sees or types this; they
    # set their real password via the password-reset code sent below.
    user = await create_user_db(
        email=request.email,
        username=username,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        full_name=request.full_name,
    )
    if user is None:
        raise ERR_CONFLICT  # unique collision on username, or degraded write

    members = await get_group_by_name_db(name=MEMBERS_GROUP_NAME)
    if members is None:
        raise ERR_INVALID_FIELDS
    await add_group_member_db(group_id=members.id, user_id=user.id)

    await update_membership_request_status_db(
        request_id=request_id,
        status="approved",
        reviewed_by_user_id=reviewer_user_id,
        reviewed_at=datetime.now(UTC),
    )
    await forgot_password(ForgotPasswordInput(identifier=request.email))
    await invalidate_cache_keys("services:iam:list_iam_users:*")

    approved = await get_membership_request_db(request_id=request_id)
    return membership_request_dto(approved)
