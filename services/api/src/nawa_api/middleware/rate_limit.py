"""Pure-ASGI rate-limit middleware (innermost, so 429s still carry CORS headers).

Default scope rl:api:<ip> at 100/min. Auth overrides: login/signup 10/min,
forgot/reset 5/min per IP. Bypassed when site_config.rate_limiting_enabled
is false (the e2e switch). Over limit → the ERR_RATE_LIMITED envelope with
Retry-After and X-RateLimit-* headers.
"""

import json

from nawa_api.contracts.errors import ERR_RATE_LIMITED
from nawa_api.services.rate_limit.consume import consume
from nawa_api.services.site_config.get_site_config import get_flag

_DEFAULT_LIMIT = 100
_AUTH_STRICT_PATHS = ("/api/v1/auth/forgot-password", "/api/v1/auth/reset-password")
_AUTH_PATHS = ("/api/v1/auth/login", "/api/v1/auth/signup")


def _scope_and_limit(path: str) -> tuple[str, int]:
    if path in _AUTH_STRICT_PATHS:
        return "auth", 5
    if path in _AUTH_PATHS:
        return "auth", 10
    return "api", _DEFAULT_LIMIT


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in ("/healthz", "/readyz", "/api/v1/metrics"):
            await self.app(scope, receive, send)
            return

        if not await get_flag("rate_limiting_enabled", True):
            await self.app(scope, receive, send)
            return

        ip = scope.get("client", ("", 0))[0] or "unknown"
        rl_scope, limit = _scope_and_limit(path)
        result = await consume(scope=rl_scope, identifier=ip, limit=limit)

        rate_headers = [
            (b"x-ratelimit-limit", str(result.limit).encode()),
            (b"x-ratelimit-remaining", str(result.remaining).encode()),
            (b"x-ratelimit-reset", str(result.reset_seconds).encode()),
        ]

        if not result.allowed:
            body = json.dumps(
                {"code": ERR_RATE_LIMITED.code, "message": ERR_RATE_LIMITED.message, "data": None}
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": ERR_RATE_LIMITED.code,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"retry-after", str(result.reset_seconds).encode()),
                        *rate_headers,
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(rate_headers)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, wrapped_send)
