"""FastAPI application entrypoint.

The DI container is built once at startup (inside the lifespan context) and
torn down at shutdown — never at import time, and never as a module-level
singleton, per the architectural constraints.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.routes.analysis import router as analysis_router
from app.api.routes.review import router as review_router
from app.core.config import get_settings
from app.core.container import build_container
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    container = build_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        await container.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Site Cleanliness Analysis Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(analysis_router)
    app.include_router(review_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
