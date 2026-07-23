"""SSE endpoint. Subscribes to the caller's own notifications channel only
(events:notifications:<user_id>). This channel name is a cross-slice contract."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from nawa_api.contracts.errors import ERR_UNAUTHENTICATED
from nawa_api.runtime.redis import get_redis
from nawa_api.utils.request_context import get_session_user

router = APIRouter(tags=["events"])


@router.get("/events")
async def events_route():
    session = get_session_user()
    if session is None:
        raise ERR_UNAUTHENTICATED
    channel = f"events:notifications:{session.sub}"

    async def stream():
        pubsub = get_redis().pubsub()
        try:
            await pubsub.subscribe(channel)
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=25.0)
                yield f"data: {msg['data']}\n\n" if msg else ": keep-alive\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return StreamingResponse(stream(), media_type="text/event-stream")
