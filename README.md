# AeroScript AI — Project Specification

## 1. Concept & Vision

AeroScript AI transforms air drawing into an intelligent, gesture-controlled experience. Users draw in 3D space with their finger while MediaPipe tracks their hand, rendering strokes on a canvas. A real-time CNN (DoodleNet) provides instant guesses while drawing, and a local VLM (via Ollama) delivers the final verdict with conversational follow-up. The vibe: sci-fi gesture computing meets playful AI sketch recognition.

**Tagline**: "Draw in the air. Let AI understand."

---

## 2. Design Language

### Aesthetic Direction
**Cyberpunk-neon on dark glass** — dark backgrounds with glowing accent strokes, like a holographic display floating in space. Clean geometric UI with subtle transparency effects.

### Color Palette
- `--bg-primary`: `#0a0e17` (deep space black)
- `--bg-secondary`: `#121829` (glass panel)
- `--bg-tertiary`: `#1a2235` (elevated surface)
- `--accent-primary`: `#00e5ff` (cyan glow — active/draw mode)
- `--accent-secondary`: `#7c3aed` (violet — AI/recognition)
- `--accent-warning`: `#f59e0b` (amber — erase mode)
- `--accent-idle`: `#64748b` (slate — idle/fist)
- `--accent-submit`: `#10b981` (emerald — thumbs up/submit)
- `--text-primary`: `#f1f5f9`
- `--text-secondary`: `#94a3b8`
- `--canvas-bg`: `#ffffff`

### Typography
- **Primary**: `Space Grotesk` (700 for headings, 500 for UI labels)
- **Monospace**: `JetBrains Mono` (for confidence scores, data)
- Fallback: `system-ui, sans-serif`

### Spatial System
- Base unit: 4px
- Component spacing: 12px, 16px, 24px
- Canvas padding: 0 (edge-to-edge drawing surface)
- UI panels: 16px padding, 12px border-radius, `backdrop-filter: blur(12px)`

### Motion Philosophy
- Gesture transitions: 150ms ease-out color/shadow shifts
- Canvas strokes: immediate (no lag — hand tracking must feel 1:1)
- CNN predictions: 200ms fade-in for new predictions
- VLM streaming: typewriter effect at 30ms/char
- Mode switch: 300ms spring animation on icon scale

### Visual Assets
- **Icons**: Lucide React (consistent stroke-width: 1.5)
- **Decorative**: Subtle grid pattern on bg, glowing borders on active elements
- **No emoji** — use inline SVG icons throughout

---

## 3. Layout & Structure

### Main Layout (Full Viewport)
```
┌─────────────────────────────────────────────────────────────────┐
│  [Header Bar - 48px]                                            │
│  AeroScript AI logo    [Mode: Free ▾]    [●] Webcam Status    │
├───────────────────────────────────────┬─────────────────────────┤
│                                       │  CNN Predictions Panel  │
│                                       │  ─────────────────────  │
│                                       │  Cat         ████░ 72%  │
│         CANVAS (Drawing Surface)      │  Dog         ██░░░ 15%  │
│         (transparent overlay on       │  Horse       █░░░░  8%  │
│          webcam feed)                  │                         │
│                                       │  ─────────────────────  │
│                                       │  VLM Response Area      │
│                                       │  (streaming text)       │
│                                       │                         │
├───────────────────────────────────────┴─────────────────────────┤
│  [Gesture Indicator Bar - 40px]                                 │
│  ✋ Idle   ✍️ Draw   🗑️ Erase   👍 Submit                    │
├─────────────────────────────────────────────────────────────────┤
│  [Toolbar - 56px]                                               │
│  [Color] [Thickness ━━●━━] [Undo] [Clear] [Submit ✈]            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  [Webcam Preview - floating, bottom-left, 180x135px]            │
│  Shows: hand skeleton overlay + gesture label                   │
└─────────────────────────────────────────────────────────────────┘
```

### Responsive Strategy
- **Desktop (>1024px)**: Full layout as above
- **Tablet (768-1024px)**: Sidebar collapses to bottom sheet
- **Mobile (<768px)**: Not supported — show "Desktop required" message

---

## 4. Features & Interactions

### Layer 1 — Hand Tracking & Canvas

#### Hand Detection
- MediaPipe Hands runs at 30+ FPS from webcam
- 21 hand landmarks tracked per hand
- Webcam feed shown as dimmed background (opacity 0.4)
- Canvas overlay on top for stroke rendering

#### Gesture Classifier
Four gestures recognized in real-time:

| Gesture | Landmarks Pattern | Action | Visual Feedback |
|---------|------------------|--------|------------------|
| **Index Point** | Index extended, other fingers curled | Draw mode — track index fingertip | Cyan glow on canvas border |
| **Open Palm** | All fingers extended, spread | Erase mode — clear near palm center | Amber glow |
| **Closed Fist** | All fingers curled, no extended | Idle/pause — stop rendering | Slate gray |
| **Thumbs Up** | Thumb extended up, 2+ seconds | Submit — export & send to backend | Emerald pulse animation |

#### Drawing Mechanics
- Index finger position mapped to canvas coordinates
- Minimum movement threshold: 5px (prevents jitter)
- Stroke smoothing: Bezier curve fitting with 3-point buffer
- Stroke color: user-selected (default: `#00e5ff`)
- Stroke width: user-selected (default: 3px, range: 1-20)

#### Canvas Preprocessing (on submit)
1. **Invert**: black strokes on white bg
2. **Crop**: bounding box of all strokes + 15% padding
3. **Resize**: 512×512 (letterboxed if needed)
4. **Thicken**: all strokes to minimum 4px width
5. **Export**: `canvas.toDataURL('image/png')` → base64

#### UI Controls
- **Color Picker**: 8 preset colors + custom hex input
  - Presets: cyan, magenta, yellow, green, orange, pink, white, black
- **Thickness Slider**: range 1-20, step 1, shows preview
- **Undo Button**: removes last stroke (max 50 in history)
- **Clear Button**: clears entire canvas with confirmation pulse
- **Submit Button**: triggers thumbs-up confirm modal (3s countdown or immediate)

### Layer 2 — Real-Time CNN (Optional but Recommended)

#### DoodleNet Integration
- TensorFlow.js with DoodleNet (345 categories)
- Inference every 500ms (debounced to canvas changes)
- Canvas must have ≥10 strokes to trigger inference

#### Display
- **Top 3 predictions**: category name + confidence bar + percentage
- **Loading state**: skeleton pulse while model loads
- **"Keep drawing..." message** when confidence < 20%
- Predictions fade out 2s after drawing stops

### Layer 3 Stub (for friend to implement)
- WebSocket connection to `ws://localhost:8000/ws`
- Send: `{ type: "submit", image: "base64...", mode: "free" }`
- Receive: `{ type: "stream", content: "..." }` chunks
- Placeholder UI shown until backend connected

---

## 5. Component Inventory

### `<Header />`
- Logo (inline SVG, "AeroScript AI")
- Mode selector dropdown (Free, Object, Geography, Math)
- WebSocket connection status indicator (green dot / red dot)

### `<Canvas />`
- Full-area drawing surface
- Layers: background (webcam) → canvas (strokes) → gesture overlay
- States: drawing, idle, submitting (pulsing border)

### `<GestureIndicator />`
- 4-segment horizontal bar
- Active segment glows with accent color
- Icon + label for each gesture

### `<Toolbar />`
- Horizontal bar with grouped controls
- Color swatches (circular, 32px, ring on active)
- Range slider for thickness
- Icon buttons: Undo (arrow-left), Clear (trash-2), Submit (send)

### `<PredictionPanel />`
- CNN predictions with confidence bars
- "Thinking..." skeleton during inference
- Smooth fade transitions

### `<ResponsePanel />`
- VLM streaming text display
- Scrollable, auto-scroll to bottom
- Placeholder: "Draw something and submit to see the magic!"

### `<WebcamPreview />`
- Floating card, bottom-left corner
- Live feed with MediaPipe skeleton overlay
- Gesture label badge

### `<SubmitModal />`
- Confirmation before submission
- Preview of processed image
- "Sending..." loading state

---

## 6. Technical Approach

### Frontend Stack
- **Framework**: React 18 + Vite + TypeScript
- **Styling**: Tailwind CSS v3 with custom config
- **State**: React hooks (useState, useRef, useCallback) — no external state lib needed
- **Hand Tracking**: `@mediapipe/hands` + `@mediapipe/camera_utils`
- **ML**: TensorFlow.js + DoodleNet (Keras model, .h5 format)
- **Canvas**: Native HTML5 Canvas API
- **WebSocket**: Native WebSocket API

### File Structure
```
src/
├── App.tsx                 # Main layout
├── components/
│   ├── Header.tsx
│   ├── Canvas.tsx          # Drawing surface + MediaPipe integration
│   ├── Toolbar.tsx
│   ├── GestureIndicator.tsx
│   ├── PredictionPanel.tsx
│   ├── ResponsePanel.tsx
│   └── WebcamPreview.tsx
├── hooks/
│   ├── useHandTracking.ts  # MediaPipe logic
│   ├── useGestureClassifier.ts
│   ├── useCanvasDrawing.ts
│   └── useCNNInference.ts  # DoodleNet
├── utils/
│   ├── canvasPreprocessing.ts
│   └── gestureDetection.ts
├── types/
│   └── index.ts
└── styles/
    └── index.css           # Tailwind + custom properties
```

### Key Implementation Details

#### MediaPipe Setup
```typescript
// Initialize Hands with optimized config
const hands = new Hands({
  locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
});
hands.setOptions({
  maxNumHands: 1,
  modelComplexity: 1,
  minDetectionConfidence: 0.7,
  minTrackingConfidence: 0.5
});
```

#### Gesture Detection Logic
```typescript
// Index point: index MCP to tip distance > 0.09, other fingers curled
// Open palm: all finger lengths extended (> 0.07 from palm center)
// Fist: no fingers extended
// Thumbs up: thumb extended, index curled, held > 2s
```

#### Canvas Coordinate Mapping
```typescript
// Map webcam coords (640x480) to canvas coords (viewport-adaptive)
// Account for canvas resize on window resize
```

### Backend Contract (for friend)

#### WebSocket Endpoint
- `ws://localhost:8000/ws?session_id=<uuid>`
- Client sends: `{ type: "submit", image: "base64", mode: "free" }`
- Server streams: `{ type: "stream", content: "chunk" }` + `{ type: "done" }`
- Follow-up: `{ type: "chat", message: "..." }` — maintains conversation history

#### REST Endpoint (fallback)
- `POST /api/submit` — accepts base64 image, returns async response ID
- `GET /api/response/{id}` — poll for response

---

## 7. MVP Scope

### Must Have (MVP)
- [x] MediaPipe hand tracking integration
- [x] 4-gesture classifier (draw, erase, idle, submit)
- [x] Canvas drawing with index finger
- [x] Color picker, thickness slider
- [x] Undo, clear buttons
- [x] Gesture indicator bar
- [x] Canvas preprocessing + export to PNG
- [x] WebSocket client stub (connects to backend)
- [x] Basic response display (placeholder)

### Nice to Have (Post-MVP)
- [ ] DoodleNet real-time CNN predictions
- [ ] Mode selector (Free, Object, Geography, Math)
- [ ] Smooth stroke rendering (Bezier curves)
- [ ] Submit confirmation modal

### Out of Scope (Friend's Layer 3)
- Ollama integration
- VLM prompt engineering
- Conversation state management
- Streaming response logic

---

## 8. Testing Checklist

- [ ] Webcam permissions granted and working
- [ ] Hand detected within 2 seconds of page load
- [ ] All 4 gestures recognized correctly
- [ ] Drawing feels 1:1 with finger movement (no perceptible lag)
- [ ] Undo removes last stroke
- [ ] Clear removes all strokes
- [ ] Canvas export produces clean 512x512 PNG
- [ ] WebSocket connects to backend (when available)
- [ ] No console errors in normal operation