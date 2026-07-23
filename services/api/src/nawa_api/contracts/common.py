"""Shared contract primitives: the envelope model, pagination, id/slug params,
and the email/phone syntax validators shared with the password-reset channel rule.
"""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?\d{6,15}$")


def is_email_syntax(value: str) -> bool:
    return bool(_EMAIL_RE.match(value))


def is_phone_syntax(value: str) -> bool:
    return bool(_PHONE_RE.match(value))


class Envelope(BaseModel):
    code: int
    message: str
    data: Any = None


class PaginationQuery(BaseModel):
    limit: int = Field(default=20)
    cursor: str | None = None  # reserved for later keyset pagination

    @field_validator("limit", mode="after")
    @classmethod
    def _clamp_limit(cls, v: int) -> int:
        return max(1, min(v, 100))


class IdParam(BaseModel):
    id: str


class SlugParam(BaseModel):
    slug: str
