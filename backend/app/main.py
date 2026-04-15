"""FastAPI application entry point with lifespan management."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging, request_context
from app.exceptions.handlers import register_exception_handlers
from app.routers import health, sessions
from app.services.session_manager import session_manager
from app.services.vlm_service import vlm_service

# Configure logging first
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: startup and shutdown events."""
    # Startup
    logger.info("Starting AeroScriptAI backend...")
    logger.info(f"LM Studio target: {settings.lm_studio_base_url}")
    logger.info(f"Model: {settings.model_name}")

    # Verify LM Studio is reachable
    is_healthy = await vlm_service.health_check()
    if is_healthy:
        logger.info("LM Studio is reachable")
    else:
        logger.warning("LM Studio is not reachable at startup. Backend will retry on first request.")

    # Start session cleanup task
    session_manager.start_cleanup_task()

    logger.info("AeroScriptAI backend ready")

    yield

    # Shutdown
    logger.info("Shutting down AeroScriptAI backend...")
    await session_manager.stop_cleanup_task()
    await vlm_service.close()
    logger.info("Shutdown complete")


# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AeroScriptAI Backend",
    description="Air drawing sketch recognition with local VLM via LM Studio",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the configured frontend origin plus any localhost port (dev convenience)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with endpoint, status, latency, and request ID."""
    import time
    request_id = request.headers.get("X-Request-ID", None)

    with request_context(request_id):
        start = time.perf_counter()
        try:
            response = await call_next(request)
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                f"{request.method} {request.url.path} → {response.status_code} ({latency_ms:.1f}ms)",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "latency_ms": round(latency_ms, 1),
                    }
                },
            )
            return response
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error(
                f"{request.method} {request.url.path} → 500 ({latency_ms:.1f}ms)",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": 500,
                        "latency_ms": round(latency_ms, 1),
                    }
                },
            )
            raise


# Register exception handlers
register_exception_handlers(app)

# Register routers
app.include_router(health.router)
app.include_router(sessions.router)
