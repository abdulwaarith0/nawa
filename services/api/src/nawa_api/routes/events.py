"""SSE endpoint. Subscribes to the caller's own notifications channel only
(events:notifications:<user_id>). This channel name is a cross-slice contract."""

from fastapi import APIRouter

from nawa_api.contracts.errors import ERR_UNAUTHENTICATED
from nawa_api.utils.request_context import get_session_user
from nawa_api.utils.sse import sse_response

router = APIRouter(tags=["events"])


@router.get("/events")
async def events_route():
    session = get_session_user()
    if session is None:
        raise ERR_UNAUTHENTICATED
    return sse_response(f"events:notifications:{session.sub}")
