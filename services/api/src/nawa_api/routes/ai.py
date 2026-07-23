"""AI admin + demo routes (05-ai-infrastructure.md §7, §9.5)."""

import asyncio
import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from nawa_api.ai import gateway
from nawa_api.ai.types import LLMRequest, Tier
from nawa_api.contracts.errors import ApiError
from nawa_api.contracts.iam import Permission
from nawa_api.middleware.iam import require_permission
from nawa_api.runtime.redis import get_redis
from nawa_api.services.ai_calls.list_ai_calls import list_ai_calls
from nawa_api.utils.envelope import ok
from nawa_api.utils.publish_event import publish_event

router = APIRouter(tags=["ai"])


@router.get("/admin/ai-calls")
async def list_ai_calls_route(
    task: str | None = None,
    provider: str | None = None,
    status: str | None = None,
    cycle: str | None = None,
    limit: int = 100,
):
    await require_permission(Permission.ADMIN_AI_CALLS_READ)
    return ok(
        await list_ai_calls(
            task=task, provider=provider, status=status, cycle=cycle, limit=min(limit, 100)
        )
    )


class EchoStreamInput(BaseModel):
    text: str
    thread_id: str | None = None


@router.post("/ai/echo-stream")
async def echo_stream_route(body: EchoStreamInput):
    """Thin demo of the SSE plumbing (§9.5): the gateway streams through the
    Redis pub/sub channel events:assistant:<thread_id>, and this endpoint relays
    the frames. The real assistant endpoint (slice 07) reuses this path."""
    await require_permission(Permission.AI_STREAM)
    thread_id = body.thread_id or str(uuid.uuid4())
    channel = f"events:assistant:{thread_id}"
    request = LLMRequest(
        task="assistant.echo",
        prompt_version="v1",
        tier=Tier.SMALL,
        system="Echo the user's message back.",
        messages=[{"role": "user", "content": body.text}],
    )

    async def produce() -> None:
        try:
            async for event in gateway.stream(request, pii_safe=True):
                await publish_event(channel, event.model_dump(mode="json"))
        except ApiError as exc:
            await publish_event(channel, {"type": "error", "code": str(exc.code)})

    async def relay():
        pubsub = get_redis().pubsub()
        await pubsub.subscribe(channel)
        producer = asyncio.create_task(produce())  # subscribed first, so no frames are lost
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if message is None:
                    yield ": keep-alive\n\n"  # heartbeat
                    continue
                data = message["data"]
                event_type = json.loads(data).get("type", "delta")
                yield f"event: {event_type}\ndata: {data}\n\n"
                if event_type in ("done", "error"):
                    break
        finally:
            producer.cancel()
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return StreamingResponse(relay(), media_type="text/event-stream")
