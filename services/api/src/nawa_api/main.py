"""API entrypoint. Runs the boot guard before the app factory, then bootstraps
dependencies via the lifespan handler on startup."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

import nawa_api  # noqa: F401  (Windows event-loop policy)
from nawa_api.runtime.app_factory import create_app
from nawa_api.runtime.boot_guard import assert_production_config
from nawa_api.runtime.bootstrap import bootstrap


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    await bootstrap()
    yield


assert_production_config()

app = create_app()
app.router.lifespan_context = _lifespan
