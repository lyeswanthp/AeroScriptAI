"""Session and recognition endpoints."""

import json
import logging
import re
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from app.config import settings
from app.exceptions import ImageValidationError, SessionNotFoundError
from app.models.requests import DrawingSubmission, FollowUpMessage
from app.models.responses import ModelsResponse, RecognitionResponse, SessionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Sessions"])


# ── SSE helper ───────────────────────────────────────────────────────────────

async def _sse_stream(
    image_b64: str,
    prompt: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Call the VLM and yield Server-Sent Events.

    Event sequence:
      data: {"type": "confidence", "level": "high|medium|low|unknown"}
      data: {"type": "token", "content": "..."}   <- repeated
      data: [DONE]
    """
    from app.services.vlm_service import vlm_service

    buffer = ""
    confidence_sent = False

    async for token in vlm_service.recognize(image_b64, prompt):
        if not confidence_sent:
            buffer += token
            match = re.search(r"\[CONFIDENCE:(\w+)\]", buffer, re.IGNORECASE)
            if match:
                level = match.group(1).lower()
                if level not in ("high", "medium", "low"):
                    level = "unknown"
                yield f"data: {json.dumps({'type': 'confidence', 'level': level})}\n\n"
                remaining = re.sub(
                    r"\[CONFIDENCE:\w+\]\s*", "", buffer, flags=re.IGNORECASE
                ).strip()
                if remaining:
                    yield f"data: {json.dumps({'type': 'token', 'content': remaining})}\n\n"
                buffer = ""
                confidence_sent = True
            elif len(buffer) > 100:
                # No confidence tag found in first 100 chars — give up waiting
                yield f"data: {json.dumps({'type': 'confidence', 'level': 'unknown'})}\n\n"
                yield f"data: {json.dumps({'type': 'token', 'content': buffer})}\n\n"
                buffer = ""
                confidence_sent = True
        else:
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    # Flush remaining buffer if confidence never arrived
    if not confidence_sent:
        if buffer:
            match = re.search(r"\[CONFIDENCE:(\w+)\]", buffer, re.IGNORECASE)
            level = (
                match.group(1).lower()
                if match and match.group(1).lower() in ("high", "medium", "low")
                else "unknown"
            )
            yield f"data: {json.dumps({'type': 'confidence', 'level': level})}\n\n"
            remaining = re.sub(
                r"\[CONFIDENCE:\w+\]\s*", "", buffer, flags=re.IGNORECASE
            ).strip()
            if remaining:
                yield f"data: {json.dumps({'type': 'token', 'content': remaining})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'confidence', 'level': 'unknown'})}\n\n"

    yield "data: [DONE]\n\n"


def _sse_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _sse_stream_saving(
    image_b64: str,
    prompt: list[dict],
    session_id: str,
) -> AsyncGenerator[str, None]:
    """
    Wrap _sse_stream and persist the full assistant response to session history
    after the stream completes, so follow-up questions have full context.
    """
    from app.services.session_manager import session_manager

    collected: list[str] = []
    async for chunk in _sse_stream(image_b64, prompt):
        if chunk != "data: [DONE]\n\n":
            try:
                data = json.loads(chunk[6:].strip())
                if data.get("type") == "token":
                    collected.append(data["content"])
            except Exception:
                pass
        yield chunk

    from app.services.response_cleaner import build_final_response
    full_response = "".join(collected).strip()
    if full_response:
        full_response = build_final_response(full_response)
        session_manager.add_to_history(session_id, "assistant", full_response)


# ── Recognition ──────────────────────────────────────────────────────────────

@router.post("/recognize", response_model=RecognitionResponse)
async def recognize_drawing(submission: DrawingSubmission) -> RecognitionResponse:
    """
    Submit a drawing for recognition. Returns full response (non-streaming).
    Creates a new session or continues an existing one.
    """
    from app.services.preprocess import preprocess_image
    from app.services.prompt_engine import prompt_engine
    from app.services.session_manager import session_manager
    from app.services.vlm_service import vlm_service

    try:
        processed_b64 = preprocess_image(submission.base64_image)
    except ImageValidationError:
        raise

    if submission.session_id:
        session = session_manager.get_session(submission.session_id)
        session_manager.set_mode(submission.session_id, submission.mode)
        # Refresh stored image
        session_manager.add_to_history(
            submission.session_id, "user", "I drew this sketch", image_data=processed_b64
        )
        session_id = submission.session_id
    else:
        session_id = session_manager.create_session(
            submission.mode, image_data=processed_b64
        )
        session = session_manager.get_session(session_id)
        session_manager.add_to_history(session_id, "user", "I drew this sketch")

    prompt = prompt_engine.assemble_prompt(
        mode=submission.mode,
        user_message="What did I draw? Describe it briefly.",
        history=session_manager.get_history(session_id),
    )

    full_parts: list[str] = []
    async for token in vlm_service.recognize(processed_b64, prompt):
        full_parts.append(token)

    response_text = "".join(full_parts)
    confidence = prompt_engine.parse_confidence(response_text)
    response_text = prompt_engine.strip_confidence_tag(response_text)

    from app.services.response_cleaner import build_final_response
    response_text = build_final_response(response_text)

    session_manager.add_to_history(session_id, "assistant", response_text)

    return RecognitionResponse(
        recognized_text=response_text,
        confidence_hint=confidence,
        session_id=session_id,
        is_final=True,
    )


@router.get("/recognize/stream/{session_id}")
async def recognize_stream(session_id: str) -> StreamingResponse:
    """
    SSE: stream recognition for the image stored in the session.
    Call POST /api/recognize first to create the session with image_data.
    """
    from app.services.prompt_engine import prompt_engine
    from app.services.session_manager import session_manager

    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.image_data:
        raise HTTPException(
            status_code=400,
            detail="No image in session. Submit via POST /api/recognize first.",
        )

    prompt = prompt_engine.assemble_prompt(
        mode=session.mode,
        user_message="What did I draw? Describe it briefly.",
        history=session_manager.get_history(session_id),
    )

    return _sse_response(_sse_stream(session.image_data, prompt))


@router.post("/recognize/stream")
async def recognize_drawing_stream(submission: DrawingSubmission) -> StreamingResponse:
    """
    Submit a drawing and receive a streaming SSE recognition response.

    Event sequence:
      data: {"type": "session", "session_id": "..."}      <- first, capture this
      data: {"type": "confidence", "level": "high|..."}
      data: {"type": "token", "content": "..."}           <- repeated
      data: [DONE]

    The assistant response is saved to session history after the stream ends,
    so follow-up questions have full context.
    """
    from app.services.preprocess import preprocess_image
    from app.services.prompt_engine import prompt_engine
    from app.services.session_manager import session_manager

    try:
        processed_b64 = preprocess_image(submission.base64_image)
    except ImageValidationError:
        raise

    if submission.session_id:
        session_manager.get_session(submission.session_id)  # raises 404 if missing
        session_manager.set_mode(submission.session_id, submission.mode)
        session_manager.add_to_history(
            submission.session_id, "user", "I drew this sketch", image_data=processed_b64
        )
        session_id = submission.session_id
    else:
        session_id = session_manager.create_session(
            submission.mode, image_data=processed_b64
        )
        session_manager.add_to_history(session_id, "user", "I drew this sketch")

    prompt = prompt_engine.assemble_prompt(
        mode=submission.mode,
        user_message="What did I draw? Describe it briefly.",
        history=session_manager.get_history(session_id),
    )

    async def _stream() -> AsyncGenerator[str, None]:
        # Emit session ID first so the frontend can capture it
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
        # Stream VLM response and save assistant turn to history when done
        async for chunk in _sse_stream_saving(processed_b64, prompt, session_id):
            yield chunk

    return _sse_response(_stream())


# ── Follow-up ─────────────────────────────────────────────────────────────────

@router.post("/followup", response_model=RecognitionResponse)
async def followup(message: FollowUpMessage) -> RecognitionResponse:
    """Submit a follow-up question in an existing session (non-streaming)."""
    from app.services.prompt_engine import prompt_engine
    from app.services.session_manager import session_manager
    from app.services.vlm_service import vlm_service

    session = session_manager.get_session(message.session_id)

    if not session.image_data:
        raise HTTPException(
            status_code=400,
            detail="Session has no image. Submit a drawing first.",
        )

    session_manager.add_to_history(message.session_id, "user", message.text)

    prompt = prompt_engine.assemble_prompt(
        mode=session.mode,
        user_message=message.text,
        history=session_manager.get_history(message.session_id),
    )

    full_parts: list[str] = []
    async for token in vlm_service.recognize(session.image_data, prompt):
        full_parts.append(token)

    response_text = "".join(full_parts)
    confidence = prompt_engine.parse_confidence(response_text)
    response_text = prompt_engine.strip_confidence_tag(response_text)

    from app.services.response_cleaner import build_final_response
    response_text = build_final_response(response_text)

    session_manager.add_to_history(message.session_id, "assistant", response_text)

    return RecognitionResponse(
        recognized_text=response_text,
        confidence_hint=confidence,
        session_id=message.session_id,
        is_final=True,
    )


@router.get("/followup/stream/{session_id}")
async def followup_stream(
    session_id: str,
    text: str = Query(..., min_length=1, max_length=1000, description="Follow-up question"),
) -> StreamingResponse:
    """SSE: stream a follow-up answer for the given session."""
    from app.services.prompt_engine import prompt_engine
    from app.services.session_manager import session_manager

    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.image_data:
        raise HTTPException(
            status_code=400,
            detail="Session has no image. Submit a drawing first.",
        )

    session_manager.add_to_history(session_id, "user", text)

    prompt = prompt_engine.assemble_prompt(
        mode=session.mode,
        user_message=text,
        history=session_manager.get_history(session_id),
    )

    return _sse_response(_sse_stream_saving(session.image_data, prompt, session_id))


# ── Session management ────────────────────────────────────────────────────────

@router.delete("/session/{session_id}", status_code=204)
async def delete_session(session_id: str) -> Response:
    """Delete a session. 204 on success, 404 if not found."""
    from app.services.session_manager import session_manager

    try:
        session_manager.clear_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    return Response(status_code=204)


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get session metadata."""
    from app.services.session_manager import session_manager

    session = session_manager.get_session(session_id)
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
    )


# ── Models ────────────────────────────────────────────────────────────────────

@router.get("/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """List models available in LM Studio."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.lm_studio_base_url}/v1/models")
            response.raise_for_status()
            data = response.json()
            models = [m["id"] for m in data.get("data", [])]
    except Exception:
        models = []

    return ModelsResponse(models=models)
