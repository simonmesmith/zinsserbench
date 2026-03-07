from __future__ import annotations

from dataclasses import dataclass, field

from .types import Prompt
import re
from typing import Dict, List

_TARGET_WORD_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s+words", re.IGNORECASE)
_THINK_BLOCK_PATTERNS = [
    ("think_block", re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)),
    ("reasoning_block", re.compile(r"<reasoning\b[^>]*>.*?</reasoning>", re.IGNORECASE | re.DOTALL)),
]
_THINKING_PREFIX_RE = re.compile(
    r"^\s*(?:thinking process|reasoning|analysis|chain of thought)\s*:.*?(?=\n\s*\n|\n[#A-Z*`]|$)",
    re.IGNORECASE | re.DOTALL,
)
_WORD_END_RE = re.compile(r"[A-Za-z]{3,}$")
_SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]?\s*$")
_BULLET_LINE_RE = re.compile(r"(?m)^\s*(?:[-*]|\d+\.)\s+\S.*$")
_DANGLING_END_RE = re.compile(r"(?s)(?:[:;,]\s*$|(?:^|\n)\s*(?:[-*]|\d+\.)\s*$|```[^`]*$|[#*`_]+$)")


@dataclass(frozen=True)
class OutputGuardResult:
    is_valid: bool
    reason: str
    word_count: int
    minimum_words: int


@dataclass(frozen=True)
class SanitizationResult:
    text: str
    removed_chars: int
    removed_ratio: float
    patterns: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.removed_chars > 0


@dataclass(frozen=True)
class TruncationCheckResult:
    is_truncated: bool
    reasons: List[str] = field(default_factory=list)


def evaluate_output(prompt: Prompt, response_text: str) -> OutputGuardResult:
    text = response_text.strip()
    word_count = len(text.split())
    minimum_words = minimum_required_words(prompt)

    if word_count < minimum_words:
        return OutputGuardResult(False, "too_short", word_count, minimum_words)
    return OutputGuardResult(True, "", word_count, minimum_words)


def sanitize_output(response_text: str) -> SanitizationResult:
    original = response_text or ""
    text = original
    patterns: List[str] = []

    for pattern_name, pattern in _THINK_BLOCK_PATTERNS:
        updated = pattern.sub("", text)
        if updated != text:
            patterns.append(pattern_name)
            text = updated

    updated = _THINKING_PREFIX_RE.sub("", text)
    if updated != text:
        patterns.append("thinking_prefix")
        text = updated

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    removed_chars = max(0, len(original) - len(text))
    removed_ratio = (removed_chars / len(original)) if original else 0.0
    return SanitizationResult(text=text, removed_chars=removed_chars, removed_ratio=removed_ratio, patterns=patterns)


def detect_truncation(response_text: str, metadata: Dict[str, object], max_output_tokens: int) -> TruncationCheckResult:
    text = (response_text or "").rstrip()
    reasons: List[str] = []
    usage = metadata.get("usage", {})
    if not isinstance(usage, dict):
        usage = {}

    finish_reason = metadata.get("finish_reason")
    if finish_reason == "length":
        reasons.append("finish_reason_length")

    completion_tokens = usage.get("completion_tokens")
    if isinstance(completion_tokens, int) and completion_tokens >= max_output_tokens:
        reasons.append("completion_tokens_at_cap")

    if text:
        if _DANGLING_END_RE.search(text):
            reasons.append("dangling_ending")
        elif not _SENTENCE_END_RE.search(text):
            last_line = text.splitlines()[-1].strip()
            if _BULLET_LINE_RE.match(last_line):
                reasons.append("dangling_bullet")
            elif _WORD_END_RE.search(last_line):
                reasons.append("missing_terminal_punctuation")
            else:
                reasons.append("incomplete_ending")

    return TruncationCheckResult(is_truncated=bool(reasons), reasons=reasons)


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
