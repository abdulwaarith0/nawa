"""The FastAPI app factory: middleware order, exception handlers, health,
metrics, and the /api/v1 routers."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.exceptions import HTTPException as StarletteHTTPException

from nawa_api.contracts.errors import ERR_INTERNAL, ERR_INVALID_FIELDS, ERR_RATE_LIMITED, ApiError
from nawa_api.middleware.context import RequestContextMiddleware
from nawa_api.middleware.rate_limit import RateLimitMiddleware
from nawa_api.runtime.health import check_readiness
from nawa_api.runtime.settings import get_settings
from nawa_api.utils.logger import get_logger
from nawa_api.utils.request_context import rate_limit_retry_after_var


def _envelope_response(code: int, message: str, data=None, *, headers=None) -> JSONResponse:
    return JSONResponse(
        status_code=code, content={"code": code, "message": message, "data": data}, headers=headers
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="NAWA API", version="1.0.0")

    # --- Exception handlers (map everything to the envelope) ---
    @app.exception_handler(ApiError)
    async def _api_error_handler(_request: Request, err: ApiError) -> JSONResponse:
        headers = None
        if err == ERR_RATE_LIMITED:
            retry_after = rate_limit_retry_after_var.get()
            if retry_after is not None:
                headers = {"Retry-After": str(retry_after)}
                rate_limit_retry_after_var.set(None)
        return _envelope_response(err.code, err.message, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Field names only — never values.
        fields = sorted({".".join(str(p) for p in e.get("loc", [])[1:]) for e in exc.errors()})
        message = f"{ERR_INVALID_FIELDS.message}: {', '.join(f for f in fields if f)}".rstrip(": ")
        return _envelope_response(ERR_INVALID_FIELDS.code, message)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Unmatched routes (404) and method-not-allowed (405) arrive here.
        message = exc.detail if isinstance(exc.detail, str) else "Not found"
        return _envelope_response(exc.status_code, message)

    @app.exception_handler(Exception)
    async def _unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        get_logger().error("unhandled_exception", exc_info=True)
        return _envelope_response(ERR_INTERNAL.code, ERR_INTERNAL.message)

    # --- Health probes (no deps in the access log path) ---
    @app.get("/healthz")
    async def _healthz() -> JSONResponse:
        return JSONResponse(status_code=200, content={"status": "ok"})

    @app.get("/readyz")
    async def _readyz() -> JSONResponse:
        ok, failing = await check_readiness()
        if ok:
            return JSONResponse(status_code=200, content={"status": "ready"})
        get_logger().warning("readiness_failed", dependency=failing)
        return JSONResponse(status_code=503, content={"status": "not_ready", "dependency": failing})

    # --- Metrics (public, no JWT) ---
    @app.get("/api/v1/metrics")
    async def _metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # --- Routers (mounted under /api/v1) ---
    from nawa_api.routes import register_routers

    register_routers(app)

    # --- Middleware (last-added runs outermost) ---
    # Innermost: rate limiting (so 429s still pass back through CORS).
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Client",
            "X-Device-Id",
            "X-Request-Id",
        ],
    )
    # Outermost: request context / logging / metrics.
    app.add_middleware(RequestContextMiddleware)

    return app
