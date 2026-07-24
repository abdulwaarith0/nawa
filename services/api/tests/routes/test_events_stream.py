import pytest

from nawa_api.contracts.auth import SessionUser
from nawa_api.routes import events
from nawa_api.utils import request_context as rc
from nawa_api.utils import sse as sse_module


class _FakePubSub:
    def __init__(self):
        self.subscribed = None
        self._messages = [{"data": '{"t":"ping"}'}, None]

    async def subscribe(self, channel):
        self.subscribed = channel

    async def get_message(self, ignore_subscribe_messages=True, timeout=25.0):
        return self._messages.pop(0) if self._messages else None

    async def unsubscribe(self, channel):
        pass

    async def aclose(self):
        pass


class _FakeRedis:
    def __init__(self, pubsub):
        self._pubsub = pubsub

    def pubsub(self):
        return self._pubsub


@pytest.mark.asyncio
async def test_events_stream_yields_published_then_keepalive(monkeypatch):
    fake = _FakePubSub()
    monkeypatch.setattr(sse_module, "get_redis", lambda: _FakeRedis(fake))

    rc.session_var.set(SessionUser(sub="user-42", full_name="A", language="en", perms=[]))
    response = await events.events_route()

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
        if len(chunks) >= 2:
            break

    assert fake.subscribed == "events:notifications:user-42"
    assert any('data: {"t":"ping"}' in c for c in chunks)
    assert any(": keep-alive" in c for c in chunks)


@pytest.mark.asyncio
async def test_events_route_raises_without_session():
    from nawa_api.contracts.errors import ERR_UNAUTHENTICATED

    rc.session_var.set(None)
    with pytest.raises(type(ERR_UNAUTHENTICATED)):
        await events.events_route()
