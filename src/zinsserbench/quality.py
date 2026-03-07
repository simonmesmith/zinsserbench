from __future__ import annotations

from dataclasses import dataclass

from .types import Prompt

import re

_TARGET_WORD_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s+words", re.IGNORECASE)


@dataclass(frozen=True)
class OutputGuardResult:
    is_valid: bool
    reason: str
    word_count: int
    minimum_words: int


def evaluate_output(prompt: Prompt, response_text: str) -> OutputGuardResult:
    text = response_text.strip()
    word_count = len(text.split())
    minimum_words = minimum_required_words(prompt)

    if word_count < minimum_words:
        return OutputGuardResult(False, "too_short", word_count, minimum_words)
    return OutputGuardResult(True, "", word_count, minimum_words)


def minimum_required_words(prompt: Prompt) -> int:
    target_min = _target_length_lower_bound(prompt.target_length)
    if target_min is None:
        return 80
    return max(80, int(round(target_min * 0.4)))


def _target_length_lower_bound(target_length: str) -> int | None:
    match = _TARGET_WORD_RE.search(target_length)
    if not match:
        return None
    return int(match.group(1))
