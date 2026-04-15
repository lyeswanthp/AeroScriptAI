"""Pydantic response models."""

from pydantic import BaseModel
from datetime import datetime


class RecognitionResponse(BaseModel):
    """Full recognition response (non-streaming)."""

    recognized_text: str
    confidence_hint: str  # "high", "medium", or "low"
    session_id: str
    is_final: bool = True


class StreamChunk(BaseModel):
    """A single token in a streaming response."""

    token: str
    is_final: bool = False


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # "healthy" or "unhealthy"
    model: str
    lm_studio_status: str
    uptime_seconds: float


class SessionResponse(BaseModel):
    """Response when a new session is created."""

    session_id: str
    created_at: datetime


class ModelsResponse(BaseModel):
    """Available models list."""

    models: list[str]


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str | None = None
    code: str
