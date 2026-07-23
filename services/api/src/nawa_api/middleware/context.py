"""Pure-ASGI request middleware: request-id, token resolution, context vars,
cookie application, access logging, and the HTTP duration metric.

Implemented as pure ASGI (not BaseHTTPMiddleware) so the contextvars set here
propagate into the endpoint — BaseHTTPMiddleware runs the downstream app in a
separate task and would break that propagation.
"""

import http.cookies
import time
import uuid

from nawa_api.metrics.registry import http_request_duration_seconds
from nawa_api.utils.logger import get_logger
from nawa_api.utils.request_context import (
    CookieOp,
    logger_var,
    pending_cookies_var,
    request_id_var,
    session_var,
)
from nawa_api.utils.tokens import decode_session_jwt

_SKIP_LOG_PATHS = {"/healthz", "/readyz"}
_SESSION_COOKIE = "nw_session"


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> bytes | None:
    for key, value in headers:
        if key.lower() == name:
            return value
    return None


def _resolve_session(headers: list[tuple[bytes, bytes]]):
    # Bearer-first, then nw_session cookie fallback.
    auth = _header(headers, b"authorization")
    if auth:
        decoded = auth.decode("latin-1")
        if decoded.lower().startswith("bearer "):
            user = decode_session_jwt(decoded[7:].strip())
            if user is not None:
                return user
    cookie_header = _header(headers, b"cookie")
    if cookie_header:
        jar = http.cookies.SimpleCookie()
        try:
            jar.load(cookie_header.decode("latin-1"))
        except http.cookies.CookieError:
            return None
        morsel = jar.get(_SESSION_COOKIE)
        if morsel is not None:
            return decode_session_jwt(morsel.value)
    return None


def _render_set_cookie(op: CookieOp) -> bytes:
    if op.value is None:
        parts = [f"{op.name}=deleted", "Max-Age=0", "Expires=Thu, 01 Jan 1970 00:00:00 GMT"]
    else:
        parts = [f"{op.name}={op.value}"]
        if op.max_age is not None:
            parts.append(f"Max-Age={op.max_age}")
    parts.append(f"Path={op.path}")
    if op.http_only:
        parts.append("HttpOnly")
    parts.append(f"SameSite={op.same_site.capitalize()}")
    if op.secure:
        parts.append("Secure")
    return "; ".join(parts).encode("latin-1")


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        headers = scope.get("headers", [])

        incoming_id = _header(headers, b"x-request-id")
        request_id = incoming_id.decode("latin-1") if incoming_id else str(uuid.uuid4())

        session = _resolve_session(headers)
        request_id_var.set(request_id)
        session_var.set(session)
        pending_cookies_var.set([])
        logger_var.set(
            get_logger(
                request_id=request_id,
                method=scope.get("method"),
                route=path,
                user_id=session.sub if session else None,
            )
        )

        status_holder = {"code": 500}
        start = time.perf_counter()

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                raw_headers = list(message.get("headers", []))
                raw_headers.append((b"x-request-id", request_id.encode("latin-1")))
                for op in pending_cookies_var.get() or []:
                    raw_headers.append((b"set-cookie", _render_set_cookie(op)))
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            if path not in _SKIP_LOG_PATHS:
                duration = time.perf_counter() - start
                ip = scope.get("client", ("", 0))[0] or ""
                route = scope.get("path", path)
                http_request_duration_seconds.labels(
                    ip=ip,
                    method=scope.get("method", ""),
                    route=route,
                    status_code=str(status_holder["code"]),
                ).observe(duration)
                self._access_log(scope, status_holder["code"], duration, ip, request_id)

    @staticmethod
    def _access_log(scope, status: int, duration: float, ip: str, request_id: str) -> None:
        logger = get_logger(request_id=request_id)
        level = "error" if status >= 500 else ("warning" if status >= 400 else "info")
        getattr(logger, level)(
            "access",
            method=scope.get("method"),
            path=scope.get("path"),
            status=status,
            duration_ms=round(duration * 1000, 2),
            ip=ip,
        )
