"""Unit tests for the prompt engine."""

import pytest

from app.services.prompt_engine import (
    assemble_prompt,
    parse_confidence,
    strip_confidence_tag,
    truncate_history,
)


class TestAssemblePrompt:
    def test_system_message_included(self):
        messages = assemble_prompt("FREE", "What did I draw?", [])
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 0

    def test_user_message_included(self):
        messages = assemble_prompt("FREE", "Is this a cat?", [])
        assert any(m["role"] == "user" and "Is this a cat?" in m["content"] for m in messages)

    def test_mode_in_system_prompt(self):
        messages = assemble_prompt("GEOGRAPHY", "What is this?", [])
        assert "GEOGRAPHY" in messages[0]["content"].upper() or "landmass" in messages[0]["content"].lower()

    def test_history_injected(self):
        history = [
            {"role": "user", "content": "I drew a cat"},
            {"role": "assistant", "content": "That's a cat!"},
        ]
        messages = assemble_prompt("OBJECT", "What color is it?", history)
        assert "cat" in messages[0]["content"].lower()

    def test_empty_history_works(self):
        messages = assemble_prompt("FREE", "What is this?", [])
        assert len(messages) == 2  # system + user


class TestParseConfidence:
    def test_high_confidence(self):
        assert parse_confidence("[CONFIDENCE:high] It's a cat.") == "high"

    def test_medium_confidence(self):
        assert parse_confidence("[CONFIDENCE:medium] Might be a dog.") == "medium"

    def test_low_confidence(self):
        assert parse_confidence("[CONFIDENCE:low] Could be anything.") == "low"

    def test_case_insensitive(self):
        assert parse_confidence("[Confidence:HIGH] text") == "high"
        assert parse_confidence("[confidence:Low] text") == "low"

    def test_no_tag_returns_unknown(self):
        assert parse_confidence("Just some text without a tag.") == "unknown"


class TestStripConfidenceTag:
    def test_strips_high(self):
        result = strip_confidence_tag("[CONFIDENCE:high] It's a cat.")
        assert result == "It's a cat."

    def test_strips_low(self):
        result = strip_confidence_tag("[CONFIDENCE:low] Not sure.")
        assert result == "Not sure."

    def test_strips_and_trims(self):
        result = strip_confidence_tag("[CONFIDENCE:medium]   Hello world  ")
        assert result == "Hello world"

    def test_no_tag_unchanged(self):
        text = "Just normal text."
        assert strip_confidence_tag(text) == text


class TestTruncateHistory:
    def test_under_limit_unchanged(self):
        history = [{"role": "user", "content": "hello"} for _ in range(5)]
        result = truncate_history(history, 10)
        assert len(result) == 5
        assert result == history

    def test_over_limit_truncates(self):
        history = [{"role": "user", "content": f"msg{i}"} for i in range(30)]
        result = truncate_history(history, 10)
        assert len(result) == 10
        assert result[0]["content"] == "msg0"  # First message preserved
        assert result[-1]["content"] == "msg29"  # Last message preserved

    def test_exact_limit_unchanged(self):
        history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        result = truncate_history(history, 10)
        assert len(result) == 10

    def test_empty_history(self):
        result = truncate_history([], 10)
        assert result == []
