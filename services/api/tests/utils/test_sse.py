import pytest

from nawa_api.utils import sse as sse_module
from nawa_api.utils.sse import sse_response


class _FakePubSub:
    def __init__(self, messages):
        self.subscribed = None
        self.unsubscribed = False
        self._messages = list(messages)

    async def subscribe(self, channel):
        self.subscribed = channel

    async def get_message(self, ignore_subscribe_messages=True, timeout=25.0):
        return self._messages.pop(0) if self._messages else None

    async def unsubscribe(self, channel):
        self.unsubscribed = True

    async def aclose(self):
        pass


class _FakeRedis:
    def __init__(self, pubsub):
        self._pubsub = pubsub

    def pubsub(self):
        return self._pubsub


@pytest.mark.asyncio
async def test_sse_response_emits_first_frame_before_subscribing(monkeypatch):
    fake = _FakePubSub([{"data": '{"t":"tick"}'}, None])
    monkeypatch.setattr(sse_module, "get_redis", lambda: _FakeRedis(fake))

    response = sse_response("events:test:chan", first_frame='{"snapshot":true}')

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
        if len(chunks) >= 3:
            break

    assert chunks[0] == 'data: {"snapshot":true}\n\n'
    assert any('data: {"t":"tick"}' in c for c in chunks)
    assert any(": keep-alive" in c for c in chunks)
    assert fake.subscribed == "events:test:chan"


@pytest.mark.asyncio
async def test_sse_response_without_first_frame_subscribes_immediately(monkeypatch):
    fake = _FakePubSub([None])
    monkeypatch.setattr(sse_module, "get_redis", lambda: _FakeRedis(fake))

    response = sse_response("events:test:chan2")

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
        break

    assert chunks[0] == ": keep-alive\n\n"
    assert fake.subscribed == "events:test:chan2"
