# AeroScriptAI — Project Plan

## Overview

AeroScriptAI is an air-drawing recognition system where users draw in the air with hand gestures. A local VLM recognizes the sketch and explains it conversationally.

## The Three Layers

### Layer 1 — Hand Tracking & Canvas (Frontend — Person A)

**MediaPipe Hands JS SDK** detects 21 hand landmarks per hand at 30+ FPS from the webcam.

**Gesture Classifier** built on top of landmarks recognizes four gestures:

| Gesture | Action |
|---|---|
| Index finger pointing up | Draw mode — track index fingertip, render strokes on HTML5 canvas |
| Open palm | Erase mode — clear area near palm center |
| Closed fist | Idle/pause — stop drawing |
| Thumbs up (held 2 seconds) | Submit drawing to VLM |

**Canvas UX features:** color picker, stroke thickness slider, undo button, clear button, gesture indicator overlay, small webcam preview in corner.

**Canvas exports** the drawing as PNG via `canvas.toDataURL('image/png')`, base64-encoded, sent to backend.

### Layer 2 — Real-Time CNN Classifier (Frontend — Optional, recommended)

**TensorFlow.js + DoodleNet** provides instant "guessing while you draw" — like Google Quick Draw. Every 500ms (debounced), current canvas state is fed to the CNN, top-3 predictions with confidence shown in a sidebar.

This is optional for MVP. Skipping it saves complexity; keeping it significantly improves the user experience.

### Layer 3 — VLM Recognition & Conversation (Backend — Person B)

**FastAPI backend** receives the canvas PNG. Sends it to Ollama's REST API with a crafted prompt. Ollama runs a multimodal model locally.

**Model options (all viable on your RTX 5080 16GB):**

| Model | Parameters | VRAM | Best For |
|---|---|---|---|
| Llama 3.2 Vision 11B | 11B | 12GB | Best reasoning, primary choice |
| Moondream 2 | 1.8B | 4GB | Fast, lightweight fallback |
| MiniCPM-V 2.6 | ~2B | 6GB | Good balance |
| LLaVA 1.6 7B | 7B | 8GB | Battle-tested |

**Decision:** PRIMARY = `llama3.2-vision:11b`, FALLBACK = `moondream:latest`

**Streaming:** Response streams back to frontend via **Server-Sent Events (SSE)**, not WebSocket. Conversation is stateful — user can ask follow-up questions.

## Sketch Types the VLM Must Handle

1. **Objects/Animals** — "That's a cat. Cats are domesticated carnivores..."
2. **Geographic shapes** — "That resembles India's map..."
3. **Text/Letters** — OCR and interpret ("You wrote HELLO")
4. **Math expressions** — Recognize and solve ("That's 5 × 3 = 15")
5. **Diagrams/Flowcharts** — Describe structure
6. **Abstract/Unrecognizable** — Gracefully say "I'm not sure..."

Implemented via **mode selector**: OBJECT, GEOGRAPHY, MATH, TEXT, FREE.

## Canvas Preprocessing Pipeline

Before sending to VLM, preprocess in-browser (Canvas API) or on backend (Pillow):

1. **Background normalization** — white background, black strokes (VLMs prefer clean contrast)
2. **Stroke smoothing** — moving average or Bezier curve fitting to reduce jitter
3. **Centering and padding** — crop to stroke bounding box, add 15% padding, resize to 512×512
4. **Stroke thickening** — thicken all strokes to at least 3-4px (thin air-drawn lines confuse VLMs)
5. **Optional inversion** — test white-on-black vs black-on-white per model

## Backend Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app, lifespan, CORS, middleware
│   ├── config.py            # Pydantic Settings from .env
│   ├── logging_config.py    # JSON structured logging, request ID correlation
│   ├── routers/
│   │   ├── health.py        # GET /health
│   │   └── sessions.py      # POST /api/recognize, SSE endpoints, DELETE /api/session
│   ├── services/
│   │   ├── vlm_service.py   # OllamaAdapter, retry, timeout, dual-model fallback
│   │   ├── preprocess.py    # Image validation, normalization, crop, resize, thicken
│   │   ├── prompt_engine.py # System prompts, mode routing, history management
│   │   └── session_manager.py # In-memory session store, TTL cleanup
│   ├── models/
│   │   ├── requests.py      # DrawingSubmission, FollowUpMessage
│   │   ├── responses.py     # RecognitionResponse, HealthResponse, etc.
│   │   └── modes.py         # ModeEnum
│   └── exceptions/
│       ├── __init__.py      # Custom exceptions
│       └── handlers.py     # FastAPI exception handlers
├── tests/                   # Unit + integration tests
├── docs/                    # API_CONTRACT.md, PROMPT_EVALUATION.md, DESIGN.md
├── .env.example
├── requirements.txt
└── README.md
```

## Why SSE and Not WebSocket

SSE is unidirectional server-to-client streaming — perfect for VLM response streaming. For the submit-drawing flow, the frontend makes a POST to send the image (regular HTTP), then connects to an SSE endpoint to stream the response. This avoids WebSocket complexity (connection management, reconnection logic, backpressure). WebSocket is only needed if you later add bidirectional features like collaborative drawing.

## Why Ollama and Not Cloud API

1. **Privacy** — no sketch data leaves the machine
2. **Cost** — zero API fees vs OpenAI/Anthropic cloud costs
3. **Interview story** — "I set up a local inference pipeline" demonstrates ML infra understanding
4. **Offline capability** — works without internet

## Prompt Engineering Strategy

The model output should always be structured. We ask it to prefix responses with:

```
[CONFIDENCE:high]
[CONFIDENCE:medium]
[CONFIDENCE:low]
```

Frontend parses this to show a confidence indicator. One API call, not two.

Mode-specific prompts route the model into the right interpretation mode:
- OBJECT: "Focus on the shape, category, and visual features"
- GEOGRAPHY: "Look for country borders, landmarks, geographic features"
- MATH: "Parse this as a mathematical expression and solve it"
- TEXT: "This is handwriting — read and transcribe the text"
- FREE: no special routing, full open-ended interpretation

## Key Backend Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Streaming | SSE | Simpler than WebSocket, sufficient for server→client streaming |
| Ollama vs cloud | Ollama | Privacy, zero cost, offline, interview differentiation |
| Primary model | Llama 3.2 Vision 11B | Best reasoning among options, 16GB VRAM available |
| Fallback model | Moondream 2 | Ultra-light, works when primary is busy |
| Image size | 512×512 | Balance between detail and VRAM usage |
| Confidence | Single-pass via prompt | Double-pass (verify confidence) doubles latency |
| Session storage | In-memory | Simple, stateless design — sessions are ephemeral |
| Request concurrency | Semaphore(1) + queue | Ollama processes one request at a time by default |

## What Makes This "Production Level"

1. **Typed everywhere** — Pydantic models for every request/response, no raw dicts
2. **Async throughout** — FastAPI async endpoints, aiohttp for Ollama calls
3. **Structured logging** — JSON format, request ID correlation, not print statements
4. **Error handling** — custom exceptions with clean JSON error responses and HTTP status codes
5. **Retry logic** — exponential backoff for transient Ollama failures
6. **Timeout handling** — 30s timeout prevents hanging requests
7. **Image validation** — reject corrupt/blank/oversized images with friendly errors
8. **Session cleanup** — TTL-based cleanup prevents memory leaks
9. **Unit tests** — every service independently testable with mocks
10. **API contract documented** — `API_CONTRACT.md` is handed to frontend partner day one
11. **Design decisions documented** — `DESIGN.md` explains every architectural choice
