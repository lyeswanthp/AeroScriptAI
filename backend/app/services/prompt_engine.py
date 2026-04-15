"""Prompt engineering and mode routing."""

import re
from app.models.modes import Mode
from app.config import settings


SYSTEM_PROMPT_BASE = """You are a sketch recognition assistant. The user draws things in the air with their hand — the drawings are hand-drawn, sparse, and imperfect. Focus on the overall shape and structure.

Identify what was drawn and provide a brief, informative response. If it could be multiple things, mention the most likely interpretation.

IMPORTANT: Rate your confidence in your identification by starting your response with a confidence tag:
- [CONFIDENCE:high] — if you are certain what it is
- [CONFIDENCE:medium] — if you have a reasonable guess but aren't certain
- [CONFIDENCE:low] — if the drawing is unclear and you're guessing

Be concise. 2-3 sentences maximum."""

MODE_TEMPLATES = {
    "OBJECT": "Focus on identifying objects, animals, plants, or manufactured items. Consider the overall silhouette, distinguishing features, and typical shapes.",
    "GEOGRAPHY": "Look for country borders, continent shapes, landmarks, maps, or geographic features. Identify any recognizable landmass, body of water, or location.",
    "MATH": "Parse this as a mathematical expression, equation, or diagram. Solve it if possible and show your reasoning.",
    "TEXT": "This is handwriting — read and transcribe the text exactly as written. Pay attention to individual letters and their arrangement.",
    "FREE": "Interpret freely — the user may have drawn anything. Go with your best guess based on the overall shape.",
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
    Extract the confidence level from a response.
    Returns 'high', 'medium', 'low', or 'unknown'.
    """
    match = re.search(r"\[CONFIDENCE:(\w+)\]", text, re.IGNORECASE)
    if match:
        level = match.group(1).lower()
        if level in ("high", "medium", "low"):
            return level
    return "unknown"


def strip_confidence_tag(text: str) -> str:
    """Remove the [CONFIDENCE:*] tag from the response text."""
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
