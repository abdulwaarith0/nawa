from nawa_api.ai.providers import get_provider, reset_provider_cache
from nawa_api.ai.providers.mock_provider import MockLLMProvider


def test_test_env_forces_mock_regardless_of_name():
    # conftest sets ENVIRONMENT=test, so even asking for claude yields the mock.
    assert isinstance(get_provider("claude"), MockLLMProvider)
    assert isinstance(get_provider(), MockLLMProvider)


def test_provider_is_cached_as_singleton():
    reset_provider_cache()
    first = get_provider()
    second = get_provider()
    assert first is second


def test_reset_cache_rebuilds():
    first = get_provider()
    reset_provider_cache()
    second = get_provider()
    assert first is not second
