"""Pydantic request models."""

from pydantic import BaseModel, Field
from app.models.modes import Mode


class DrawingSubmission(BaseModel):
    """Submission of a drawing for recognition."""

    base64_image: str = Field(..., description="Base64-encoded PNG or JPEG image of the drawing")
    mode: Mode = Field(default="FREE", description="Sketch type: OBJECT, GEOGRAPHY, MATH, TEXT, or FREE")
    session_id: str | None = Field(default=None, description="Existing session ID to continue conversation, or None for new session")


class FollowUpMessage(BaseModel):
    """Follow-up question in an existing conversation."""

    session_id: str = Field(..., description="Session ID from a prior recognition call")
    text: str = Field(..., min_length=1, max_length=1000, description="Follow-up question or message")
