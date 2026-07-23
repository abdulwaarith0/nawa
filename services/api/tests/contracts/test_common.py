import pytest
from pydantic import ValidationError

from nawa_api.contracts.common import (
    Envelope,
    PaginationQuery,
    is_email_syntax,
    is_phone_syntax,
)


def test_pagination_defaults():
    q = PaginationQuery()
    assert q.limit == 20
    assert q.cursor is None


def test_pagination_caps_limit_at_100():
    q = PaginationQuery(limit=500)
    assert q.limit == 100


def test_pagination_coerces_string_limit():
    q = PaginationQuery(limit="35")
    assert q.limit == 35


def test_pagination_rejects_below_one():
    q = PaginationQuery(limit=0)
    assert q.limit == 1


def test_envelope_model_shape():
    env = Envelope(code=200, message="OK", data={"a": 1})
    dumped = env.model_dump()
    assert dumped == {"code": 200, "message": "OK", "data": {"a": 1}}


def test_is_email_syntax():
    assert is_email_syntax("user@example.com") is True
    assert is_email_syntax("not-an-email") is False
    assert is_email_syntax("+97455512345") is False


def test_is_phone_syntax():
    assert is_phone_syntax("+97455512345") is True
    assert is_phone_syntax("55512345") is True
    assert is_phone_syntax("user@example.com") is False
    assert is_phone_syntax("abc") is False


def test_pagination_rejects_garbage_limit():
    with pytest.raises(ValidationError):
        PaginationQuery(limit="not-a-number")
