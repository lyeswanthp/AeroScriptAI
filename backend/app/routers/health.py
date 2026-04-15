"""Health check endpoint."""

import logging
import time

import httpx
from fastapi import APIRouter

from app.exceptions import LMStudioUnavailableError
from app.models.responses import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])

# Module-level start time for uptime calculation
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check backend and LM Studio health.

    Returns model info, server status, and uptime.
    HTTP 200 if healthy, raises 503 if LM Studio is unreachable.
    """
    from app.config import settings

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.lm_studio_base_url}/v1/models")
            response.raise_for_status()
            models_data = response.json()
            available_models = [m["id"] for m in models_data.get("data", [])]
            model_loaded = settings.model_name in available_models
            lm_status = "connected" if model_loaded else "no_vision_model_loaded"
    except httpx.HTTPError as e:
        logger.warning(f"LM Studio health check failed: {e}")
        raise LMStudioUnavailableError(
            message="LM Studio is not reachable",
            detail=str(e),
        )

    return HealthResponse(
        status="healthy",
        model=settings.model_name,
        lm_studio_status=lm_status,
        uptime_seconds=time.time() - _start_time,
    )
