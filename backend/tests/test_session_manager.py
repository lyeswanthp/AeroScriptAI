"""Unit tests for the session manager."""

import pytest
import asyncio

from app.services.session_manager import SessionManager, SessionData
from app.exceptions import SessionNotFoundError, SessionLimitExceededError


@pytest.fixture
def manager():
    """Fresh session manager for each test."""
    m = SessionManager()
    yield m
    # Cancel cleanup task if running
    if m._cleanup_task:
        m._cleanup_task.cancel()


class TestSessionCreation:
    def test_create_session_returns_id(self, manager):
        sid = manager.create_session("FREE")
        assert isinstance(sid, str)
        assert len(sid) == 36  # UUID format

    def test_create_session_stores_data(self, manager):
        sid = manager.create_session("OBJECT")
        session = manager.get_session(sid)
        assert session.session_id == sid
        assert session.mode == "OBJECT"

    def test_duplicate_id_not_created(self, manager):
        sid1 = manager.create_session("FREE")
        sid2 = manager.create_session("FREE")
        assert sid1 != sid2


class TestSessionRetrieval:
    def test_get_existing_session(self, manager):
        sid = manager.create_session("FREE")
        session = manager.get_session(sid)
        assert session.session_id == sid

    def test_get_nonexistent_raises(self, manager):
        with pytest.raises(SessionNotFoundError):
            manager.get_session("nonexistent-id")


class TestHistory:
    def test_add_to_history(self, manager):
        sid = manager.create_session("FREE")
        manager.add_to_history(sid, "user", "I drew a cat")
        history = manager.get_history(sid)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "I drew a cat"

    def test_multiple_messages(self, manager):
        sid = manager.create_session("FREE")
        manager.add_to_history(sid, "user", "Question 1")
        manager.add_to_history(sid, "assistant", "Answer 1")
        manager.add_to_history(sid, "user", "Follow up")
        history = manager.get_history(sid)
        assert len(history) == 3
        assert history[1]["role"] == "assistant"


class TestModeUpdate:
    def test_set_mode(self, manager):
        sid = manager.create_session("FREE")
        manager.set_mode(sid, "MATH")
        session = manager.get_session(sid)
        assert session.mode == "MATH"


class TestClearSession:
    def test_clear_existing(self, manager):
        sid = manager.create_session("FREE")
        manager.clear_session(sid)
        with pytest.raises(SessionNotFoundError):
            manager.get_session(sid)

    def test_clear_nonexistent_raises(self, manager):
        with pytest.raises(SessionNotFoundError):
            manager.clear_session("nonexistent")


class TestActiveCount:
    def test_count_increases(self, manager):
        manager.create_session("FREE")
        manager.create_session("FREE")
        manager.create_session("FREE")
        assert manager.get_active_count() == 3

    def test_count_decreases_after_clear(self, manager):
        sid = manager.create_session("FREE")
        manager.create_session("FREE")
        manager.clear_session(sid)
        assert manager.get_active_count() == 1


class TestTTL:
    def test_expired_sessions_detected(self, manager):
        import time
        sid = manager.create_session("FREE")
        # Manually backdate last_activity
        from datetime import datetime, timedelta
        manager._sessions[sid].last_activity = datetime.now() - timedelta(minutes=60)
        expired = manager._get_expired_sessions()
        assert sid in expired

    def test_active_sessions_not_expired(self, manager):
        sid = manager.create_session("FREE")
        expired = manager._get_expired_sessions()
        assert sid not in expired


class TestSessionLimit:
    def test_exceed_limit_raises(self):
        # Create manager with very low limit
        from app.config import settings
        original_limit = settings.session_max_count
        settings.session_max_count = 2

        m = SessionManager()
        m.create_session("FREE")
        m.create_session("FREE")

        with pytest.raises(SessionLimitExceededError):
            m.create_session("FREE")

        settings.session_max_count = original_limit
