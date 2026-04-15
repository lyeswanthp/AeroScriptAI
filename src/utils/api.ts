import type { ConfidenceLevel } from '../types';

const API_BASE = 'http://localhost:8000';

/** Map frontend Mode (lowercase) to backend Mode (uppercase). */
function toBackendMode(mode: string): string {
  return mode.toUpperCase();
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      signal: AbortSignal.timeout(5000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// ── SSE reader helper ──────────────────────────────────────────────────────────

/**
 * Consume a fetch() Response whose body is a text/event-stream.
 * Calls the appropriate callback for each parsed event line.
 */
async function readSSEStream(
  res: Response,
  handlers: {
    onSession?: (id: string) => void;
    onConfidence: (level: ConfidenceLevel) => void;
    onToken: (text: string) => void;
    onDone: () => void;
    onError: (msg: string) => void;
  },
): Promise<void> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        // Stream closed without [DONE] — still resolve the UI
        handlers.onDone();
        break;
      }

      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();

        if (payload === '[DONE]') {
          handlers.onDone();
          return;
        }

        try {
          const msg = JSON.parse(payload) as Record<string, string>;
          if (msg.type === 'session' && handlers.onSession) {
            handlers.onSession(msg.session_id);
          } else if (msg.type === 'confidence') {
            handlers.onConfidence(msg.level as ConfidenceLevel);
          } else if (msg.type === 'token') {
            handlers.onToken(msg.content);
          }
        } catch {
          // malformed JSON line — ignore
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ── Recognition ───────────────────────────────────────────────────────────────

/**
 * POST the canvas image and open an SSE stream for the AI recognition response.
 * Returns an abort function — call it to cancel the in-flight request.
 *
 * Event flow:
 *   onSession(id)     — fired first; store this as your sessionId
 *   onConfidence(lvl) — fired once before tokens start
 *   onToken(text)     — fired repeatedly as the model streams
 *   onDone()          — stream finished successfully
 *   onError(msg)      — HTTP error or network failure
 */
export function streamRecognition(
  base64Image: string,
  mode: string,
  sessionId: string | null,
  callbacks: {
    onSession: (id: string) => void;
    onConfidence: (level: ConfidenceLevel) => void;
    onToken: (text: string) => void;
    onDone: () => void;
    onError: (msg: string) => void;
  },
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/recognize/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base64_image: base64Image,
          mode: toBackendMode(mode),
          session_id: sessionId ?? null,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        callbacks.onError((body as { error?: string }).error ?? `HTTP ${res.status}`);
        return;
      }

      await readSSEStream(res, callbacks);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      callbacks.onError(err instanceof Error ? err.message : 'Network error');
    }
  })();

  return () => controller.abort();
}

// ── Follow-up ─────────────────────────────────────────────────────────────────

/**
 * Open an SSE stream for a follow-up question on an existing session.
 * Returns an abort function.
 */
export function streamFollowUp(
  sessionId: string,
  text: string,
  callbacks: {
    onConfidence: (level: ConfidenceLevel) => void;
    onToken: (text: string) => void;
    onDone: () => void;
    onError: (msg: string) => void;
  },
): () => void {
  const controller = new AbortController();

  const url =
    `${API_BASE}/api/followup/stream/${encodeURIComponent(sessionId)}` +
    `?text=${encodeURIComponent(text)}`;

  (async () => {
    try {
      const res = await fetch(url, { signal: controller.signal });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        callbacks.onError((body as { error?: string }).error ?? `HTTP ${res.status}`);
        return;
      }

      await readSSEStream(res, callbacks);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      callbacks.onError(err instanceof Error ? err.message : 'Network error');
    }
  })();

  return () => controller.abort();
}
