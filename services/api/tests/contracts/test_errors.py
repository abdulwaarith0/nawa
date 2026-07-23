import pytest

from nawa_api.contracts.errors import (
    ERR_AI_BUDGET_EXCEEDED,
    ERR_AI_NOT_CONFIGURED,
    ERR_AI_UNAVAILABLE,
    ERR_CONFLICT,
    ERR_EMAIL_NOT_CONFIGURED,
    ERR_INTERNAL,
    ERR_INVALID_FIELDS,
    ERR_NOT_FOUND,
    ERR_RATE_LIMITED,
    ERR_SMS_NOT_CONFIGURED,
    ERR_STORAGE_NOT_CONFIGURED,
    ERR_UNAUTHENTICATED,
    ERR_UNAUTHORIZED,
    ApiError,
)


def test_api_error_is_raisable_and_carries_code_and_message():
    with pytest.raises(ApiError) as exc_info:
        raise ERR_NOT_FOUND
    assert exc_info.value.code == 404
    assert exc_info.value.message == "Not found"


def test_api_error_is_frozen():
    with pytest.raises(Exception):
        ERR_NOT_FOUND.code = 999


def test_sentinel_codes_match_http_semantics():
    assert ERR_INVALID_FIELDS.code == 400
    assert ERR_UNAUTHENTICATED.code == 401
    assert ERR_UNAUTHORIZED.code == 403
    assert ERR_NOT_FOUND.code == 404
    assert ERR_CONFLICT.code == 409
    assert ERR_RATE_LIMITED.code == 429
    assert ERR_INTERNAL.code == 500
    assert ERR_EMAIL_NOT_CONFIGURED.code == 503
    assert ERR_SMS_NOT_CONFIGURED.code == 503
    assert ERR_STORAGE_NOT_CONFIGURED.code == 503
    assert ERR_AI_NOT_CONFIGURED.code == 503
    assert ERR_AI_BUDGET_EXCEEDED.code == 429
    assert ERR_AI_UNAVAILABLE.code == 503


def test_sentinels_are_distinct_instances():
    codes = {
        id(e)
        for e in (
            ERR_INVALID_FIELDS,
            ERR_UNAUTHENTICATED,
            ERR_UNAUTHORIZED,
            ERR_NOT_FOUND,
        )
    }
    assert len(codes) == 4


def test_api_error_equality_by_value():
    assert ApiError(404, "Not found") == ApiError(404, "Not found")
    assert ApiError(404, "Not found") != ApiError(400, "Invalid fields")
