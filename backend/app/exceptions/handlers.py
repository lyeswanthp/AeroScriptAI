"""FastAPI exception handlers."""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.exceptions import (
    AppException,
    LMStudioUnavailableError,
    ImageValidationError,
    SessionNotFoundError,
    SessionLimitExceededError,
    ModelBusyError,
    PreprocessingError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI app."""

    @app.exception_handler(LMStudioUnavailableError)
    async def lm_studio_unavailable(request, exc: LMStudioUnavailableError):
        logger.error(f"LM Studio unavailable: {exc.message}", extra={"detail": exc.detail})
        return JSONResponse(
            status_code=503,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )

    @app.exception_handler(ImageValidationError)
    async def image_validation_error(request, exc: ImageValidationError):
        logger.warning(f"Image validation failed: {exc.message}")
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )

    @app.exception_handler(SessionNotFoundError)
    async def session_not_found(request, exc: SessionNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )

    @app.exception_handler(SessionLimitExceededError)
    async def session_limit_exceeded(request, exc: SessionLimitExceededError):
        return JSONResponse(
            status_code=429,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )

    @app.exception_handler(ModelBusyError)
    async def model_busy(request, exc: ModelBusyError):
        return JSONResponse(
            status_code=503,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )

    @app.exception_handler(PreprocessingError)
    async def preprocessing_error(request, exc: PreprocessingError):
        logger.error(f"Preprocessing failed: {exc.message}")
        return JSONResponse(
            status_code=500,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )

    @app.exception_handler(AppException)
    async def generic_app_error(request, exc: AppException):
        logger.error(f"Unhandled app error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )
