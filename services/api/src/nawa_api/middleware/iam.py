"""require_permission — the grep-able first line of every protected handler.

The JWT `perms` claim is never consulted here; it exists only for the web edge
tier. The live resolution (through the 30 s cache) is the authority.
"""

from nawa_api.contracts.auth import SessionUser
from nawa_api.contracts.errors import ERR_UNAUTHENTICATED, ERR_UNAUTHORIZED
from nawa_api.services.iam.resolve_effective_permissions import resolve_effective_permissions
from nawa_api.utils.request_context import get_session_user


async def require_permission(*perms: str) -> SessionUser:
    session = get_session_user()
    if session is None:
        raise ERR_UNAUTHENTICATED
    effective = await resolve_effective_permissions(user_id=session.sub)
    if not all(p in effective for p in perms):
        raise ERR_UNAUTHORIZED
    return session
