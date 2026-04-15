"""Response cleaning for LLaVA's verbose image descriptions.

LLaVA 8B models tend to prefix all responses with generic phrases like
"The image presents...". This module extracts the actual identification
and provides a concise response.
"""
from __future__ import annotations

import re


# Subject nouns to search for, in priority order
_SUBJECT_PATTERNS = [
    r"\b(circle|circles)\b",
    r"\b(square|squares)\b",
    r"\b(triangle|triangles)\b",
    r"\b(rectangle|rectangles)\b",
    r"\b(oval|ovals)\b",
    r"\b(spiral|spirals)\b",
    r"\b(line|lines|stroke|strokes)\b",
    r"\b(house|houses|building|buildings)\b",
    r"\b(tree|trees|plant|plants|flower|flowers)\b",
    r"\b(car|cars|vehicle|vehicles)\b",
    r"\b(person|people|man|men|woman|women|human)\b",
    r"\b(cat|cats|dog|dogs|bird|birds|fish|horse|horses|cow)\b",
    r"\b(map|maps|continent|continents|country|countries|landmass|landmasses)\b",
    r"\b(india|america|europe|africa|asia|australia|sri lanka)\b",
    r"\b(text|words|letter|letters|word|number|numbers|symbols|symbol)\b",
    r"\b(math|equation|equations|expression|algebra|formula)\b",
    r"\b(hello|how are you|thank you|yes|no|okay)\b",
    r"\b(drawing|sketch|art|pattern)\b",
]


def _strip_verbose_prefixes(text: str) -> str:
    """Remove LLaVA's formulaic prefix phrases."""
    t = text.strip()

    # Strip "The image presents..." style openings
    patterns = [
        # "The image presents a simple yet striking..."
        r"^the image presents? (to you )?(a |an |one )?[^,.]*[,.\s]+",
        # "The image you've sent..."
        r"^the image you'?ve sent [^,.]*[,.\s]+",
        # "The image / drawing / sketch / scene / photo..."
        r"^the (image|drawing|sketch|scene|photo|picture)[^,.]*[,.\s]+",
        # "This is a simple yet charming..."
        r"^this (is |looks? |appears? )?(a |an |)?(simple yet |striking |beautiful |elegant |charming )?(black and white )?(hand-drawn )?(line )?(drawing |sketch |composition |image |scene )?",
        # "A simple yet striking..."
        r"^a (simple yet |striking |beautiful )?(black and white )?(hand-drawn )?(line )?(drawing |sketch |composition )?",
        # "Dominating the center/frame..."
        r"^dominating (the |its )?(center|frame|foreground|scene)[^,.]*[,.\s]+",
        # "At the center/midpoint..."
        r"^at the (center|midpoint|foreground)[^,.]*[,.\s]+",
        # "The main/primary subject..."
        r"^the (main |primary )?(subject|focus|figure|object)[^,.]*[,.\s]+",
    ]

    for pattern in patterns:
        t = re.sub(pattern, "", t, flags=re.IGNORECASE)

    t = t.strip()

    # Capitalize if we have content
    if t:
        t = t[0].upper() + t[1:]

    return t if t else text


def extract_subject(text: str) -> str | None:
    """
    Find the most likely subject noun/phrase in the response.
    Returns the full phrase containing the first recognized subject, or None.
    """
    text_lower = text.lower()

    for pattern in _SUBJECT_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(0)

    return None


def clean_response(text: str) -> str:
    """
    Clean LLaVA's verbose description into a concise, readable response.

    Removes formulaic prefixes and keeps the meaningful identification content.
    Falls back to the original text if cleaning would produce an empty result.
    """
    original = text
    cleaned = _strip_verbose_prefixes(text)

    # If the result is empty or too short, return original
    if len(cleaned) < 10:
        return original

    # Cap at ~200 chars to prevent verbose tail
    cleaned = cleaned[:200]

    return cleaned


def build_final_response(text: str) -> str:
    """
    Build the final user-facing response.
    Uses the cleaned version for concise, readable output.
    """
    cleaned = clean_response(text)
    return cleaned if cleaned else text
