"""Per-request state via contextvars.

The request middleware resolves the token once, sets these vars, runs the
handler, then applies any queued cookie ops to the outgoing response. Leaf
code anywhere in the stack reads them with zero parameter-threading. Handlers
never touch the cookie jar directly — they queue ops here.
"""

from contextvars import ContextVar
from dataclasses import dataclass

from nawa_api.contracts.auth import SessionUser
from nawa_api.runtime.settings import get_settings
from nawa_api.utils.logger import get_logger as _root_logger

SESSION_COOKIE_NAME = "nw_session"
REFRESH_COOKIE_NAME = "nw_refresh"
_REFRESH_COOKIE_PATH = "/api/v1/auth"


@dataclass
class CookieOp:
    name: str
    value: str | None  # None means delete
    max_age: int | None = None
    path: str = "/"
    http_only: bool = True
    same_site: str = "lax"
    secure: bool = False


request_id_var: ContextVar[str | None] = ContextVar("request_id_var", default=None)
session_var: ContextVar[SessionUser | None] = ContextVar("session_var", default=None)
logger_var: ContextVar[object | None] = ContextVar("logger_var", default=None)
pending_cookies_var: ContextVar[list[CookieOp] | None] = ContextVar(
    "pending_cookies_var", default=None
)
# Set immediately before `raise ERR_RATE_LIMITED` by any caller holding a
# `RateLimitResult`, so the app-level ApiError handler can attach a
# Retry-After header without every raise site needing to build its own
# Response (10-testing-validation.md / 06-intake-copilot.md DoD #12).
rate_limit_retry_after_var: ContextVar[int | None] = ContextVar(
    "rate_limit_retry_after_var", default=None
)


def get_session_user() -> SessionUser | None:
    return session_var.get()


def get_logger():
    bound = logger_var.get()
    return bound if bound is not None else _root_logger()


def _queue(op: CookieOp) -> None:
    ops = pending_cookies_var.get()
    if ops is None:
        ops = []
        pending_cookies_var.set(ops)
    ops.append(op)


def _secure() -> bool:
    return get_settings().environment == "production"


def issue_session_cookie(jwt: str) -> None:
    _queue(
        CookieOp(
            name=SESSION_COOKIE_NAME,
            value=jwt,
            max_age=get_settings().session_ttl_seconds,
            path="/",
            same_site="lax",
            secure=_secure(),
        )
    )


def issue_refresh_cookie(token: str) -> None:
    _queue(
        CookieOp(
            name=REFRESH_COOKIE_NAME,
            value=token,
            max_age=get_settings().refresh_ttl_seconds,
            path=_REFRESH_COOKIE_PATH,
            same_site="lax",
            secure=_secure(),
        )
    )


def revoke_session_cookie() -> None:
    _queue(CookieOp(name=SESSION_COOKIE_NAME, value=None, path="/", secure=_secure()))
    _queue(
        CookieOp(name=REFRESH_COOKIE_NAME, value=None, path=_REFRESH_COOKIE_PATH, secure=_secure())
    )
