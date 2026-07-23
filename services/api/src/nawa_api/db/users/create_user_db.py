from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import User
from nawa_api.utils.logger import get_logger


async def create_user_db(
    *,
    email: str,
    username: str,
    password_hash: str,
    full_name: str,
    language: str = "ar",
    phone: str | None = None,
    session: AsyncSession | None = None,
) -> User | None:
    with observe_db(operation="write", table="users", method="create_user_db") as obs:
        try:
            async with use_session(session) as s:
                user = User(
                    email=email,
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    language=language,
                    phone=phone,
                )
                s.add(user)
                await s.flush()
                await s.refresh(user)
            obs.success = True
            return user
        except Exception:
            get_logger().warning("db_error", method="create_user_db", exc_info=True)
            obs.success = False
            return None
