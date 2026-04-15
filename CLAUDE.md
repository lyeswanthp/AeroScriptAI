# AeroScriptAI — Project Context

## What This Project Is

AeroScriptAI is a 3-layer air-drawing + AI recognition system. The user draws in the air using hand gestures, and a local VLM recognizes what was drawn and explains it conversationally.

## System Architecture

```
Layer 1 (Frontend - Person A):
  Browser → MediaPipe Hands (JS) → Gesture Classifier → HTML5 Canvas
          → TensorFlow.js + DoodleNet (optional, real-time CNN guesses)

Layer 2 (Backend - Person B, that's you):
  FastAPI → LM Studio (local VLM) → Streaming response via SSE
  ├── Image preprocessing pipeline (Pillow)
  ├── Prompt engineering with mode routing
  ├── Session management (conversation state)
  └── VLM adapter with retry + dual-model fallback
```

## Tech Stack

- **Frontend:** React (Vite + TypeScript), MediaPipe Hands JS, HTML5 Canvas, TensorFlow.js + DoodleNet, Tailwind CSS
- **Backend:** FastAPI (Python), httpx (async HTTP), Pillow, Pydantic
- **AI:** LM Studio on `localhost:1234` — OpenAI-compatible — CURRENT_MODEL: `llava-llama-3-8b-v1_1`
- **Streaming:** Server-Sent Events (SSE), NOT WebSocket

## User Info

- **Name:** Harsit Kumar Upadhya
- **Role:** Backend (Person B) — you own everything in `backend/`
- **Goal:** Production-level code suitable for AI startup and big company interviews
- **Hardware:** Harsit-Gaming — Intel Core Ultra 9 275HX, 32GB RAM, RTX 5080 Mobile 16GB VRAM

## Critical Notes

- This is a 2-person project. Frontend is Person A. Do NOT touch frontend code.
- Production-level means: typed Pydantic models everywhere, async throughout, structured logging, unit tests, clean error handling, API contract documented.
- The single most important backend task is **prompt engineering** — test with real hand-drawn sketches, not clean digital images.
- LM Studio server must be running (started from GUI) before starting FastAPI backend.
- LM Studio must have a vision model loaded before API calls work.

## Key Files

- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) — Full project overview, layer descriptions, prompt strategy
- [.claude/memory/MEMORY.md](.claude/memory/MEMORY.md) — Memory index for cross-session context
- [.claude/memory/backend_tasks.md](.claude/memory/backend_tasks.md) — Complete ordered task list
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md) — Exact API request/response shapes
- [docs/PROMPT_EVALUATION.md](docs/PROMPT_EVALUATION.md) — Prompt testing log and results
- [docs/DESIGN.md](docs/DESIGN.md) — Design decisions and rationale

## Getting Started for Backend

1. Start LM Studio GUI
2. Load a vision model (e.g., `llava-llama-3-8b-v1_1`) via the GUI
3. Make sure the local server is running on port 1234
4. Then start building Phase 1 of the backend

## Current Status

Phase 0 ✅ — LM Studio verified. LLaVA accepts images, streaming works, model correctly identifies handwritten text.
