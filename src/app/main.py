"""ASGI app factory and lifespan management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import auth, items, ws
from app.ws import ConnectionHub


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    yield
    from app.db import engine

    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "prod" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(items.router)
    app.include_router(ws.router)

    # One hub per app instance (asyncio primitives are event-loop-bound).
    app.state.hub = ConnectionHub()

    import time
    start_time = time.monotonic()

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str | float | int]:
        hub = getattr(app.state, "hub", None)
        active_rooms = len(hub.room_count()) if hub else 0
        return {
            "status": "ok",
            "env": settings.app_env,
            "version": "1.0.0",
            "uptime_seconds": round(time.monotonic() - start_time, 2),
            "active_ws_rooms": active_rooms,
        }

    return app


app = create_app()
