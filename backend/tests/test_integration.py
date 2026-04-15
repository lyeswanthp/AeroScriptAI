"""
Integration tests — real HTTP calls to the FastAPI app via ASGI transport.
LM Studio is mocked so tests run without the external server.
"""

import base64
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image, ImageDraw

from app.main import app
from app.services.vlm_service import vlm_service as _vlm


# ── Shared fixtures & helpers ─────────────────────────────────────────────────

MOCK_TOKENS = ["[CONFIDENCE:high]", " This appears", " to be", " a circle."]


def _make_sketch_b64(width: int = 200, height: int = 200) -> str:
    """White background + black circle outline — valid non-blank sketch."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([40, 40, 160, 160], outline=(0, 0, 0), width=5)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


SKETCH_B64 = _make_sketch_b64()


async def _mock_recognize(image_b64, messages, stream=True):
    """Async generator that simulates VLM streaming with confidence tag."""
    for token in MOCK_TOKENS:
        yield token


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_sessions():
    """Clear all session state between tests."""
    from app.services.session_manager import session_manager
    yield
    session_manager._sessions.clear()


@pytest.fixture
def mock_vlm():
    """Patch vlm_service.recognize to return deterministic tokens."""
    with patch.object(_vlm, "recognize", new=_mock_recognize):
        yield


def _mock_httpx_lm_studio(models: list[str] | None = None):
    """Return a patched httpx.AsyncClient that simulates LM Studio's /v1/models."""
    if models is None:
        models = ["llava-llama-3-8b-v1_1"]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": [{"id": m} for m in models]}
    mock_resp.raise_for_status = MagicMock()

    mock_instance = AsyncMock()
    mock_instance.__aenter__.return_value = mock_instance
    mock_instance.__aexit__.return_value = False
    mock_instance.get.return_value = mock_resp

    return MagicMock(return_value=mock_instance)


# ── POST /api/recognize ───────────────────────────────────────────────────────

class TestRecognize:
    async def test_creates_session_and_returns_response(self, client, mock_vlm):
        resp = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "OBJECT"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["confidence_hint"] == "high"
        assert data["is_final"] is True
        assert "[CONFIDENCE:" not in data["recognized_text"]

    async def test_confidence_stripped_from_text(self, client, mock_vlm):
        resp = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "FREE"},
        )
        assert "[CONFIDENCE:" not in resp.json()["recognized_text"]

    async def test_continues_existing_session(self, client, mock_vlm):
        r1 = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "FREE"},
        )
        sid = r1.json()["session_id"]

        r2 = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "OBJECT", "session_id": sid},
        )
        assert r2.status_code == 200
        assert r2.json()["session_id"] == sid

    async def test_blank_canvas_returns_400(self, client):
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        blank = base64.b64encode(buf.getvalue()).decode()

        resp = await client.post(
            "/api/recognize",
            json={"base64_image": blank, "mode": "FREE"},
        )
        assert resp.status_code == 400

    async def test_invalid_base64_returns_400(self, client):
        resp = await client.post(
            "/api/recognize",
            json={"base64_image": "not!!valid!!base64", "mode": "FREE"},
        )
        assert resp.status_code == 400

    async def test_missing_body_returns_422(self, client):
        resp = await client.post("/api/recognize", json={})
        assert resp.status_code == 422


# ── GET /api/recognize/stream/{session_id} ────────────────────────────────────

class TestRecognizeStream:
    async def test_sse_event_sequence(self, client, mock_vlm):
        # Create session with image first
        r = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "OBJECT"},
        )
        sid = r.json()["session_id"]

        events = []
        async with client.stream("GET", f"/api/recognize/stream/{sid}") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    payload = line[6:]
                    events.append(payload)
                    if payload == "[DONE]":
                        break

        assert events, "No SSE events received"
        assert events[-1] == "[DONE]"

        # First event must be confidence
        first = json.loads(events[0])
        assert first["type"] == "confidence"
        assert first["level"] in ("high", "medium", "low", "unknown")

        # At least one token
        token_events = [json.loads(e) for e in events[:-1] if e != "[DONE]"]
        assert any(e["type"] == "token" for e in token_events)

    async def test_unknown_session_returns_404(self, client):
        resp = await client.get("/api/recognize/stream/no-such-session")
        assert resp.status_code == 404


# ── POST /api/followup ────────────────────────────────────────────────────────

class TestFollowUp:
    async def test_followup_returns_response(self, client, mock_vlm):
        r = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "OBJECT"},
        )
        sid = r.json()["session_id"]

        fu = await client.post(
            "/api/followup",
            json={"session_id": sid, "text": "What color is it?"},
        )
        assert fu.status_code == 200
        data = fu.json()
        assert data["session_id"] == sid
        assert "[CONFIDENCE:" not in data["recognized_text"]

    async def test_followup_unknown_session_returns_404(self, client):
        resp = await client.post(
            "/api/followup",
            json={"session_id": "nonexistent", "text": "Hello?"},
        )
        assert resp.status_code == 404

    async def test_followup_empty_text_returns_422(self, client, mock_vlm):
        r = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "FREE"},
        )
        sid = r.json()["session_id"]
        resp = await client.post(
            "/api/followup", json={"session_id": sid, "text": ""}
        )
        assert resp.status_code == 422


# ── GET /api/followup/stream/{session_id} ─────────────────────────────────────

class TestFollowUpStream:
    async def test_sse_followup_format(self, client, mock_vlm):
        r = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "OBJECT"},
        )
        sid = r.json()["session_id"]

        events = []
        async with client.stream(
            "GET",
            f"/api/followup/stream/{sid}",
            params={"text": "Tell me more."},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    payload = line[6:]
                    events.append(payload)
                    if payload == "[DONE]":
                        break

        assert events[-1] == "[DONE]"
        first = json.loads(events[0])
        assert first["type"] == "confidence"

    async def test_followup_stream_missing_text_returns_422(self, client, mock_vlm):
        r = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "FREE"},
        )
        sid = r.json()["session_id"]
        resp = await client.get(f"/api/followup/stream/{sid}")
        assert resp.status_code == 422

    async def test_followup_stream_unknown_session_returns_404(self, client):
        resp = await client.get(
            "/api/followup/stream/bad-id", params={"text": "hello"}
        )
        assert resp.status_code == 404


# ── Session CRUD ──────────────────────────────────────────────────────────────

class TestSessionLifecycle:
    async def test_get_session_metadata(self, client, mock_vlm):
        r = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "MATH"},
        )
        sid = r.json()["session_id"]

        g = await client.get(f"/api/session/{sid}")
        assert g.status_code == 200
        data = g.json()
        assert data["session_id"] == sid
        assert "created_at" in data

    async def test_delete_returns_204(self, client, mock_vlm):
        r = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "FREE"},
        )
        sid = r.json()["session_id"]
        d = await client.delete(f"/api/session/{sid}")
        assert d.status_code == 204

    async def test_delete_nonexistent_returns_404(self, client):
        resp = await client.delete("/api/session/fake-id")
        assert resp.status_code == 404

    async def test_full_lifecycle(self, client, mock_vlm):
        """Create → followup → delete → 404."""
        # Create
        r = await client.post(
            "/api/recognize",
            json={"base64_image": SKETCH_B64, "mode": "OBJECT"},
        )
        sid = r.json()["session_id"]

        # Follow up
        fu = await client.post(
            "/api/followup", json={"session_id": sid, "text": "More details?"}
        )
        assert fu.status_code == 200

        # Delete
        assert (await client.delete(f"/api/session/{sid}")).status_code == 204

        # Gone
        assert (await client.get(f"/api/session/{sid}")).status_code == 404


# ── GET /health ───────────────────────────────────────────────────────────────

class TestHealth:
    async def test_health_ok_when_lm_studio_up(self, client):
        with patch("app.routers.health.httpx.AsyncClient", _mock_httpx_lm_studio()):
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data

    async def test_health_503_when_lm_studio_down(self, client):
        import httpx as _httpx

        broken = AsyncMock()
        broken.__aenter__.return_value = broken
        broken.__aexit__.return_value = False
        broken.get.side_effect = _httpx.ConnectError("refused")

        with patch("app.routers.health.httpx.AsyncClient", MagicMock(return_value=broken)):
            resp = await client.get("/health")
        assert resp.status_code == 503
        assert resp.json()["code"] == "LM_STUDIO_UNAVAILABLE"


# ── GET /api/models ───────────────────────────────────────────────────────────

class TestModels:
    async def test_returns_model_list(self, client):
        with patch(
            "app.routers.sessions.httpx.AsyncClient",
            _mock_httpx_lm_studio(["llava-llama-3-8b-v1_1", "mistral"]),
        ):
            resp = await client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "llava-llama-3-8b-v1_1" in data["models"]

    async def test_returns_empty_list_when_lm_studio_down(self, client):
        import httpx as _httpx

        broken = AsyncMock()
        broken.__aenter__.return_value = broken
        broken.__aexit__.return_value = False
        broken.get.side_effect = _httpx.ConnectError("refused")

        with patch(
            "app.routers.sessions.httpx.AsyncClient", MagicMock(return_value=broken)
        ):
            resp = await client.get("/api/models")
        assert resp.status_code == 200
        assert resp.json()["models"] == []
