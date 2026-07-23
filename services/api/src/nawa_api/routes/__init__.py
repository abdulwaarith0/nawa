"""Router registration. Each router is mounted under /api/v1."""

from fastapi import FastAPI

_API_PREFIX = "/api/v1"


def register_routers(app: FastAPI) -> None:
    from nawa_api.routes import ai, audit, auth, events, iam, site_config

    app.include_router(auth.router, prefix=_API_PREFIX)
    app.include_router(iam.router, prefix=_API_PREFIX)
    app.include_router(site_config.router, prefix=_API_PREFIX)
    app.include_router(audit.router, prefix=_API_PREFIX)
    app.include_router(events.router, prefix=_API_PREFIX)
    app.include_router(ai.router, prefix=_API_PREFIX)
