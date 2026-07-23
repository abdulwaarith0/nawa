import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import User

_PHONE_RE = re.compile(r"^\+?\d{6,15}$")


async def get_user_by_identifier_db(
    *, identifier: str, session: AsyncSession | None = None
) -> User | None:
    """Content-sniffed lookup: '@' -> email, phone syntax -> phone, else username."""
    if "@" in identifier:
        column = User.email
    elif _PHONE_RE.match(identifier):
        column = User.phone
    else:
        column = User.username

    with observe_db(operation="read", table="users", method="get_user_by_identifier_db") as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(User).where(column == identifier))
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            obs.success = False
            return None
