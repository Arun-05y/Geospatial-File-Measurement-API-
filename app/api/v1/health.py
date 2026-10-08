"""Health check endpoint."""

from fastapi import APIRouter
from app.config import settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health/", response_model=HealthResponse, summary="Service health check")
async def health_check():
    """Returns application health status and version."""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        app=settings.APP_NAME,
    )
