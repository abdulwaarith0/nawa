"""Router registration. Each router is mounted under /api/v1."""

from fastapi import FastAPI

_API_PREFIX = "/api/v1"


def register_routers(app: FastAPI) -> None:
    from nawa_api.routes import (
        ai,
        audit,
        auth,
        community,
        events,
        iam,
        intake,
        journey,
        membership_requests,
        profiles,
        site_config,
    )

    app.include_router(auth.router, prefix=_API_PREFIX)
    app.include_router(iam.router, prefix=_API_PREFIX)
    app.include_router(membership_requests.router, prefix=_API_PREFIX)
    app.include_router(site_config.router, prefix=_API_PREFIX)
    app.include_router(audit.router, prefix=_API_PREFIX)
    app.include_router(events.router, prefix=_API_PREFIX)
    app.include_router(ai.router, prefix=_API_PREFIX)
    app.include_router(intake.router, prefix=_API_PREFIX)
    app.include_router(journey.router, prefix=_API_PREFIX)
    app.include_router(profiles.router, prefix=_API_PREFIX)
    app.include_router(community.router, prefix=_API_PREFIX)
