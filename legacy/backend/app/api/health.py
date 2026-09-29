"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Liveness check and system information."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.app_env,
        database="connected",
    )
