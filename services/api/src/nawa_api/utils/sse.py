"""Shared SSE relay over a single Redis pub/sub channel. Real-time is an
enhancement, never a dependency (same philosophy as `publish_event.py`) — a
missed or dropped connection just means the next state read is stale until
reconnect, never a hard failure."""

from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

from nawa_api.runtime.redis import get_redis


async def _stream(channel: str, *, first_frame: str | None) -> AsyncIterator[str]:
    pubsub = get_redis().pubsub()
    try:
        if first_frame is not None:
            yield f"data: {first_frame}\n\n"
        await pubsub.subscribe(channel)
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=25.0)
            yield f"data: {msg['data']}\n\n" if msg else ": keep-alive\n\n"
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


def sse_response(channel: str, *, first_frame: str | None = None) -> StreamingResponse:
    """`first_frame`, when given, is sent before the subscribe — it lets a
    caller push the channel's current persisted state (e.g. a progress hash
    snapshot) so a client that connects after some events already fired
    still sees where things stand, since pub/sub itself has no history."""
    return StreamingResponse(
        _stream(channel, first_frame=first_frame), media_type="text/event-stream"
    )
