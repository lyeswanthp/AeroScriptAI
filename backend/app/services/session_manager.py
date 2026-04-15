"""Session management with in-memory storage and TTL cleanup."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.config import settings
from app.exceptions import SessionNotFoundError, SessionLimitExceededError
from app.models.modes import Mode

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Holds all state for a single conversation session."""

    session_id: str
    mode: Mode
    created_at: datetime
    last_activity: datetime
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    image_data: str | None = None  # base64 image for follow-up context


class SessionManager:
    """
    In-memory session store with TTL-based cleanup.
    Manages conversation history and session lifecycle.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._cleanup_task: asyncio.Task | None = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start_cleanup_task(self) -> None:
        """Start the background TTL cleanup loop."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup loop."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Session cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        """Periodically delete expired sessions."""
        while True:
            await asyncio.sleep(60)
            try:
                expired = self._get_expired_sessions()
                for sid in expired:
                    del self._sessions[sid]
                    logger.debug(f"Cleaned up expired session: {sid}")
                if expired:
                    logger.info(f"Cleaned up {len(expired)} expired sessions")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error during session cleanup")

    def _get_expired_sessions(self) -> list[str]:
        """Return session IDs that have exceeded their TTL."""
        threshold = datetime.now() - timedelta(minutes=settings.session_ttl_minutes)
        return [
            sid
            for sid, session in self._sessions.items()
            if session.last_activity < threshold
        ]

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create_session(self, mode: Mode, image_data: str | None = None) -> str:
        """Create a new session and return its ID."""
        if len(self._sessions) >= settings.session_max_count:
            raise SessionLimitExceededError()

        session_id = str(uuid.uuid4())
        now = datetime.now()
        self._sessions[session_id] = SessionData(
            session_id=session_id,
            mode=mode,
            created_at=now,
            last_activity=now,
            image_data=image_data,
        )
        logger.info(f"Created session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> SessionData:
        """Get a session by ID. Raises SessionNotFoundError if not found."""
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def add_to_history(
        self,
        session_id: str,
        role: str,
        content: str,
        image_data: str | None = None,
    ) -> None:
        """Append a message to the conversation history."""
        session = self.get_session(session_id)
        session.conversation_history.append({"role": role, "content": content})
        session.last_activity = datetime.now()
        if image_data:
            session.image_data = image_data

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        """Return the conversation history for a session."""
        session = self.get_session(session_id)
        return session.conversation_history

    def set_mode(self, session_id: str, mode: Mode) -> None:
        """Update the mode for a session."""
        session = self.get_session(session_id)
        session.mode = mode
        session.last_activity = datetime.now()

    def clear_session(self, session_id: str) -> None:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
        else:
            raise SessionNotFoundError(session_id)

    def get_active_count(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)


# Singleton instance
session_manager = SessionManager()
