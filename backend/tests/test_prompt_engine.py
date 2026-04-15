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
    def test_definitive_statement_high(self):
        # Direct identification = high confidence
        assert parse_confidence("It is a cat.") == "high"

    def test_starts_with_capitalized_identification(self):
        # Starts with capitalized phrase = high
        assert parse_confidence("This is a dog.") == "high"

    def test_short_text_high(self):
        # Short response = confident
        assert parse_confidence("Circle.") == "high"

    def test_hedge_language_medium(self):
        # "looks like", "could be" = hedging = medium
        assert parse_confidence("It looks like a dog.") == "medium"
        assert parse_confidence("This could be a cat.") == "medium"
        assert parse_confidence("That might be a bird.") == "medium"

    def test_multiple_hedges_medium(self):
        # Multiple hedges = definitely medium
        assert parse_confidence("It could be a dog or maybe a fox.") == "medium"

    def test_uncertain_language_low(self):
        # Explicit uncertainty = low
        assert parse_confidence("I cannot tell what this is.") == "low"
        assert parse_confidence("Too vague and abstract to identify.") == "low"
        assert parse_confidence("This is too unclear to say.") == "low"

    def test_contains_both_hedge_and_certain(self):
        # Hedge overrides certainty when explicitly uncertain words present
        result = parse_confidence("I am not sure what this is, but it could be a tree.")
        assert result == "low"

    def test_long_verbose_text_medium(self):
        # Long verbose text without certainty signals = medium
        text = "The image presents a scene. There are shapes that could be interpreted in different ways."
        assert parse_confidence(text) == "medium"

    def test_no_tag_no_longer_returns_unknown(self):
        # We no longer rely on [CONFIDENCE:...] tags
        # Short text without tags is high confidence
        assert parse_confidence("Circle.") == "high"


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
