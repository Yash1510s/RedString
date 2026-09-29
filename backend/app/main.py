"""Main FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.config import settings
from app.db import init_db
from app.models import db_models as _db_models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle management."""
    # Startup actions: ensure database schema exists
    await init_db()
    yield
    # Shutdown actions


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend service for RedString (OSINT Investigation Copilot)",
    docs_url="/docs" if settings.app_debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS restriction as required by spec section 13
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# API Routers
app.include_router(health_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Root redirect / ping."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
    }
