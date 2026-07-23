"""Shared bounded structured-output repair loop (05-ai-infrastructure.md §3.2/§3.3).

Both real providers route complete_structured through this so they get identical
semantics: validate the returned JSON against the Pydantic model; on a
ValidationError append a repair turn quoting the errors and retry up to
STRUCTURED_REPAIR_RETRIES; after the final failure raise ERR_AI_MALFORMED_OUTPUT
(never return a half-parsed object downstream).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel, ValidationError

from nawa_api.ai.types import LLMResponse
from nawa_api.contracts.errors import ERR_AI_MALFORMED_OUTPUT

STRUCTURED_REPAIR_RETRIES = 2


async def complete_structured_with_repair[T: BaseModel](
    schema: type[T],
    attempt: Callable[[list[dict]], Awaitable[tuple[str, LLMResponse]]],
) -> tuple[T, LLMResponse]:
    """`attempt(repair_messages)` performs one provider call (with any repair
    turns appended) and returns (raw_json_text, LLMResponse)."""
    repair_messages: list[dict] = []
    for _ in range(STRUCTURED_REPAIR_RETRIES + 1):
        raw, response = await attempt(repair_messages)
        try:
            return schema.model_validate_json(raw), response
        except ValidationError as exc:
            repair_messages = [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        "The previous response failed schema validation with these errors:\n"
                        f"{exc}\nReturn ONLY corrected JSON that satisfies the schema."
                    ),
                },
            ]
    raise ERR_AI_MALFORMED_OUTPUT
