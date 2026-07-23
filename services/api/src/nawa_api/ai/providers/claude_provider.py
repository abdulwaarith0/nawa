"""Default provider — Anthropic Claude (05-ai-infrastructure.md §3.2).

The ONLY module that imports `anthropic` (chat side). Offline CI never executes
it (mock is forced in ENVIRONMENT=test and get_provider lazy-imports this only
when a live provider is selected), so the whole adapter is `# pragma: no cover`.

SDK parameter shapes change — verify against the installed `anthropic` SDK on
integration; the caveats below are current as of 05-ai-infrastructure.md:
  * No sampling params on claude-opus-4-8 (temperature/top_p/top_k 400).
  * LARGE tier passes thinking={"type":"adaptive"}; SMALL omits thinking.
  * Own the retry policy in the gateway → construct the client with max_retries=0.
  * Check stop_reason BEFORE reading content: "refusal"→ERR_AI_REFUSED,
    "max_tokens"→ERR_AI_TRUNCATED (the gateway still logs the ai_calls row).
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

from pydantic import BaseModel

from nawa_api.ai.pricing import estimate_cost_usd
from nawa_api.ai.providers._structured import complete_structured_with_repair
from nawa_api.ai.providers.base import LLMProvider
from nawa_api.ai.types import DeltaEvent, DoneEvent, LLMRequest, LLMResponse, StreamEvent, Tier
from nawa_api.contracts.errors import (
    ERR_AI_NOT_CONFIGURED,
    ERR_AI_REFUSED,
    ERR_AI_TRUNCATED,
)
from nawa_api.runtime.settings import get_settings

_TIER_MODEL = {Tier.SMALL: "claude-haiku-4-5", Tier.LARGE: "claude-opus-4-8"}


class ClaudeProvider(LLMProvider):  # pragma: no cover - needs the SDK + a key
    name = "claude"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise ERR_AI_NOT_CONFIGURED
        import anthropic

        # max_retries=0: the gateway owns backoff so ai_calls sees every attempt.
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key, max_retries=0
        )

    def resolve_model(self, tier: Tier) -> str:
        return _TIER_MODEL[tier]

    def _thinking(self, tier: Tier) -> dict:
        return {"thinking": {"type": "adaptive"}} if tier is Tier.LARGE else {}

    def _system(self, req: LLMRequest) -> list[dict]:
        # Registry system texts are stable, so cache the prefix across a batch.
        return [{"type": "text", "text": req.system, "cache_control": {"type": "ephemeral"}}]

    def _text(self, message) -> str:
        return "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )

    def _to_response(self, req: LLMRequest, message, model: str, started: float) -> LLMResponse:
        if message.stop_reason == "refusal":
            raise ERR_AI_REFUSED
        if message.stop_reason == "max_tokens":
            raise ERR_AI_TRUNCATED
        usage = message.usage
        cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        tokens_in = usage.input_tokens + cached
        return LLMResponse(
            text=self._text(message),
            input_tokens=tokens_in,
            output_tokens=usage.output_tokens,
            cached_tokens=cached,
            model=model,
            provider=self.name,
            stop_reason=message.stop_reason,
            latency_ms=int((time.monotonic() - started) * 1000),
            cost_estimate=estimate_cost_usd(
                model, tokens_in=tokens_in, tokens_out=usage.output_tokens, tokens_cached=cached
            ),
            request_id=getattr(message, "id", None),
        )

    async def complete(self, req: LLMRequest) -> LLMResponse:
        model = self.resolve_model(req.tier)
        started = time.monotonic()
        message = await self._client.messages.create(
            model=model,
            system=self._system(req),
            messages=req.messages,
            max_tokens=req.max_tokens,
            stop_sequences=req.stop_sequences or [],
            **self._thinking(req.tier),
        )
        return self._to_response(req, message, model, started)

    async def complete_structured(
        self, req: LLMRequest, schema: type[BaseModel]
    ) -> tuple[BaseModel, LLMResponse]:
        model = self.resolve_model(req.tier)
        json_schema = schema.model_json_schema()
        json_schema["additionalProperties"] = False

        async def attempt(repair: list[dict]) -> tuple[str, LLMResponse]:
            started = time.monotonic()
            message = await self._client.messages.create(
                model=model,
                system=self._system(req),
                messages=[*req.messages, *repair],
                max_tokens=req.max_tokens,
                output_config={"format": {"type": "json_schema", "schema": json_schema}},
                **self._thinking(req.tier),
            )
            return self._text(message), self._to_response(req, message, model, started)

        return await complete_structured_with_repair(schema, attempt)

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamEvent]:
        model = self.resolve_model(req.tier)
        started = time.monotonic()
        async with self._client.messages.stream(
            model=model,
            system=self._system(req),
            messages=req.messages,
            max_tokens=req.max_tokens,
            **self._thinking(req.tier),
        ) as stream:
            async for text in stream.text_stream:
                yield DeltaEvent(text=text)
            final = await stream.get_final_message()
        yield DoneEvent(response=self._to_response(req, final, model, started))
