"""Swappable provider — OpenAI (05-ai-infrastructure.md §3.3).

The ONLY module that imports `openai` (chat side). Model ids come from
OPENAI_MODEL_SMALL / OPENAI_MODEL_LARGE (that vendor's catalog churns too), never
hard-coded. Structured output goes through the SDK's JSON-schema response format
with the same Pydantic-validation + bounded-repair loop as Claude. Offline CI
never executes this, so the whole adapter is `# pragma: no cover`.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

from pydantic import BaseModel

from nawa_api.ai.pricing import estimate_cost_usd
from nawa_api.ai.providers._structured import complete_structured_with_repair
from nawa_api.ai.providers.base import LLMProvider
from nawa_api.ai.types import DeltaEvent, DoneEvent, LLMRequest, LLMResponse, StreamEvent, Tier
from nawa_api.contracts.errors import ERR_AI_NOT_CONFIGURED, ERR_AI_TRUNCATED
from nawa_api.runtime.settings import get_settings


class OpenAIProvider(LLMProvider):  # pragma: no cover - needs the SDK + a key
    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        if not (settings.openai_api_key and settings.openai_model_small):
            raise ERR_AI_NOT_CONFIGURED
        import openai

        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key, max_retries=0)
        self._model_small = settings.openai_model_small
        self._model_large = settings.openai_model_large or settings.openai_model_small

    def resolve_model(self, tier: Tier) -> str:
        return self._model_large if tier is Tier.LARGE else self._model_small

    def _messages(self, req: LLMRequest, extra: list[dict]) -> list[dict]:
        return [{"role": "system", "content": req.system}, *req.messages, *extra]

    def _to_response(self, model: str, completion, started: float) -> LLMResponse:
        choice = completion.choices[0]
        if choice.finish_reason == "length":
            raise ERR_AI_TRUNCATED
        usage = completion.usage
        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            model=model,
            provider=self.name,
            stop_reason=choice.finish_reason,
            latency_ms=int((time.monotonic() - started) * 1000),
            cost_estimate=estimate_cost_usd(
                model, tokens_in=usage.prompt_tokens, tokens_out=usage.completion_tokens
            ),
            request_id=getattr(completion, "id", None),
        )

    async def complete(self, req: LLMRequest) -> LLMResponse:
        model = self.resolve_model(req.tier)
        started = time.monotonic()
        completion = await self._client.chat.completions.create(
            model=model,
            messages=self._messages(req, []),
            max_tokens=req.max_tokens,
            stop=req.stop_sequences or None,
        )
        return self._to_response(model, completion, started)

    async def complete_structured(
        self, req: LLMRequest, schema: type[BaseModel]
    ) -> tuple[BaseModel, LLMResponse]:
        model = self.resolve_model(req.tier)
        json_schema = schema.model_json_schema()
        json_schema["additionalProperties"] = False
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": json_schema, "strict": True},
        }

        async def attempt(repair: list[dict]) -> tuple[str, LLMResponse]:
            started = time.monotonic()
            completion = await self._client.chat.completions.create(
                model=model,
                messages=self._messages(req, repair),
                max_tokens=req.max_tokens,
                response_format=response_format,
            )
            response = self._to_response(model, completion, started)
            return response.text, response

        return await complete_structured_with_repair(schema, attempt)

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamEvent]:
        model = self.resolve_model(req.tier)
        started = time.monotonic()
        text_parts: list[str] = []
        prompt_tokens = completion_tokens = 0
        finish = "stop"
        stream = await self._client.chat.completions.create(
            model=model,
            messages=self._messages(req, []),
            max_tokens=req.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if chunk.usage is not None:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if chunk.choices[0].finish_reason:
                finish = chunk.choices[0].finish_reason
            if delta:
                text_parts.append(delta)
                yield DeltaEvent(text=delta)
        yield DoneEvent(
            response=LLMResponse(
                text="".join(text_parts),
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                model=model,
                provider=self.name,
                stop_reason=finish,
                latency_ms=int((time.monotonic() - started) * 1000),
                cost_estimate=estimate_cost_usd(
                    model, tokens_in=prompt_tokens, tokens_out=completion_tokens
                ),
            )
        )
