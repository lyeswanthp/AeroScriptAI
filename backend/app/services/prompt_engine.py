"""Prompt engineering and mode routing."""

import re
from app.models.modes import Mode
from app.config import settings

# ── System Prompt ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT_BASE = """You identify hand-drawn sketches made in the air. The drawings are imperfect, sparse strokes.

Rules:
1. Name the subject FIRST — the first word(s) must be what you identified. Do not start with "The image presents" or "This is a drawing of".
2. Keep your response to 1-2 short sentences maximum.
3. If you cannot identify what it is, say "Unclear sketch" — do not guess wildly or use filler phrases.
4. Do not use the phrase "simple yet" or "striking contrast" or "intriguing" — just describe what is actually drawn."""

MODE_TEMPLATES = {
    "OBJECT": "Look for objects, animals, plants, or manufactured items. Identify the overall silhouette and key features. Be specific about what it is.",
    "GEOGRAPHY": "Look for country borders, continent shapes, maps, or geographic features. Identify any recognizable landmass, body of water, or location.",
    "MATH": "This is a math sketch. Parse the expression or diagram and solve it. Show your answer clearly.",
    "TEXT": "This is handwriting. Read and transcribe the text exactly as written.",
    "FREE": "Identify whatever the user drew. Be as specific as possible.",
}

HISTORY_INJECTION_TEMPLATE = """
Previous conversation:
{history}
Now respond to the user's new question."""


def _build_system_prompt(mode: Mode, history: list[dict]) -> str:
    """Assemble the full system prompt with mode context and history."""
    mode_instruction = MODE_TEMPLATES.get(mode, MODE_TEMPLATES["FREE"])

    system = f"{SYSTEM_PROMPT_BASE}\n\n{mode_instruction}"

    if history:
        history_text = "\n".join(
            f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
            for h in history[-settings.max_history_length:]
        )
        system += HISTORY_INJECTION_TEMPLATE.format(history=history_text)

    return system


def assemble_prompt(mode: Mode, user_message: str, history: list[dict]) -> list[dict]:
    """
    Build the full message list for the VLM API.

    Returns a list of message dicts compatible with the OpenAI chat format.
    """
    messages = [
        {"role": "system", "content": _build_system_prompt(mode, history)},
        {"role": "user", "content": user_message},
    ]
    return messages


def parse_confidence(text: str) -> str:
    """
    Extract or infer confidence level from the response text.

    Tries [CONFIDENCE:...] tag first (for backwards compat and future models).
    Falls back to heuristic language analysis for LLaVA which ignores the tag.
    """
    # Try explicit tag first
    match = re.search(r"\[CONFIDENCE:(\w+)\]", text, re.IGNORECASE)
    if match:
        level = match.group(1).lower()
        if level in ("high", "medium", "low"):
            return level
        return "unknown"

    lower = text.lower()
    words = set(lower.replace(",", " ").replace(".", " ").split())

    # Explicit uncertainty — overrides everything
    uncertain_signals = [
        "unclear", "can't tell", "cannot tell", "hard to tell",
        "not sure", "unsure", "unrecognizable", "i don't know",
        "i'm not sure", "not certain", "too vague", "too abstract",
        "difficult to identify", "hard to identify", "could be several",
        "might be several", "appears to be several",
    ]
    if any(sig in lower for sig in uncertain_signals):
        return "low"

    # Hedging language — medium confidence
    hedge_signals = [
        "could be", "might be", "perhaps", "possibly",
        "looks like", "looks a bit like", "resembles",
        "might be a", "could be an", "possibly a",
        "somewhat like", "vaguely", "partially",
        "this could be", "it looks like a",
    ]
    hedge_count = sum(1 for sig in hedge_signals if sig in lower)

    # Multiple alternatives — medium/low
    alt_signals = ["or perhaps", "or maybe", "or it could", "or a", "alternatively"]
    alt_count = sum(1 for sig in alt_signals if sig in lower)

    if hedge_count >= 2 or alt_count >= 1:
        return "medium"
    if hedge_count >= 1:
        return "medium"

    # Strong certainty signals — high confidence
    certain_signals = [
        "this is a", "that is a", "it is a", "this looks like a",
        "you drew a", "you drew an", "it appears to be",
        "definitely", "clearly", "obviously",
    ]
    if any(sig in lower for sig in certain_signals):
        return "high"

    # Starts with identification (capitalized phrase followed by noun) — high
    if re.search(r"^[A-Z][a-z]+ (is|looks?|appears?|seems?) ", text):
        return "high"

    # Short, direct responses are usually confident
    if len(text) < 100:
        return "high"

    # Default to medium — most responses fall here
    return "medium"


def strip_confidence_tag(text: str) -> str:
    """Remove the [CONFIDENCE:*] tag from the response text (backwards-compatible)."""
    return re.sub(r"\[CONFIDENCE:\w+\]\s*", "", text, flags=re.IGNORECASE).strip()


def truncate_history(history: list[dict], max_length: int) -> list[dict]:
    """
    Truncate conversation history to max_length.
    Always keeps the first message (original drawing context) and
    the most recent messages, dropping middle ones.
    """
    if len(history) <= max_length:
        return history

    # Keep first message and last max_length-1 messages
    return [history[0]] + history[-(max_length - 1):]


# Singleton instance
class PromptEngine:
    """Facade for prompt-related operations."""

    def assemble_prompt(self, mode: Mode, user_message: str, history: list[dict]) -> list[dict]:
        return assemble_prompt(mode, user_message, history)

    def parse_confidence(self, text: str) -> str:
        return parse_confidence(text)

    def strip_confidence_tag(self, text: str) -> str:
        return strip_confidence_tag(text)


prompt_engine = PromptEngine()
