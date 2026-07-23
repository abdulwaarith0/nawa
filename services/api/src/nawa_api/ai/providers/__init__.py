"""Provider registry + selection (05-ai-infrastructure.md §3.4).

`get_provider()` resolves the active LLMProvider. In ENVIRONMENT=test the mock
is forced regardless of env, so a stray key in CI can never cause a live call.
Real providers are imported lazily so the vendor SDKs are only touched when a
live provider is actually selected.
"""

from __future__ import annotations

from nawa_api.ai.providers.base import LLMProvider
from nawa_api.ai.providers.mock_provider import MockLLMProvider
from nawa_api.contracts.errors import ERR_AI_NOT_CONFIGURED
from nawa_api.runtime.settings import get_settings

# "anthropic" is the settings default alias for the Claude provider.
_CLAUDE_NAMES = {"claude", "anthropic"}

_singletons: dict[str, LLMProvider] = {}


def _build(name: str) -> LLMProvider:
    if name == "mock":
        return MockLLMProvider()
    if name in _CLAUDE_NAMES:
        try:
            from nawa_api.ai.providers.claude_provider import ClaudeProvider
        except ImportError as exc:  # pragma: no cover - SDK not installed offline
            raise ERR_AI_NOT_CONFIGURED from exc
        return ClaudeProvider()
    if name == "openai":
        try:
            from nawa_api.ai.providers.openai_provider import OpenAIProvider
        except ImportError as exc:  # pragma: no cover - SDK not installed offline
            raise ERR_AI_NOT_CONFIGURED from exc
        return OpenAIProvider()
    raise ERR_AI_NOT_CONFIGURED


def get_provider(name: str | None = None) -> LLMProvider:
    settings = get_settings()
    resolved = "mock" if settings.environment == "test" else (name or settings.llm_default_provider)
    if resolved not in _singletons:
        _singletons[resolved] = _build(resolved)
    return _singletons[resolved]


def reset_provider_cache() -> None:
    """Test helper — drop cached provider singletons."""
    _singletons.clear()
