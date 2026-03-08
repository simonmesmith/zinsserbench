from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Dict, Iterable, List

from .types import ModelSpec, Prompt, RUBRIC_AXES, Rubric


class ModelBackend(ABC):
    name = "base"

    @abstractmethod
    def generate(self, model: ModelSpec, prompt: Prompt, settings: Dict[str, object]) -> Dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def judge(
        self,
        judge_model: ModelSpec,
        candidate_model: ModelSpec,
        prompt: Prompt,
        candidate_text: str,
        rubric: Rubric,
        settings: Dict[str, object],
    ) -> Dict[str, object]:
        raise NotImplementedError


class MockBackend(ModelBackend):
    name = "mock"

    def generate(self, model: ModelSpec, prompt: Prompt, settings: Dict[str, object]) -> Dict[str, object]:
        topic = ", ".join(prompt.topic_tags[:2]) or "the topic"
        sentence = (
            f"This {prompt.category.replace('_', ' ')} draft answers the task directly, stays specific, "
            f"and adds concrete detail about {topic} while keeping the prose readable. "
        )
        text = f"{model.label} response to {prompt.title}.\n\n" + (sentence * 24)
        return {"response_text": text, "metadata": {"mode": "mock", "finish_reason": "stop", "usage": {"completion_tokens": 200}}}

    def judge(
        self,
        judge_model: ModelSpec,
        candidate_model: ModelSpec,
        prompt: Prompt,
        candidate_text: str,
        rubric: Rubric,
        settings: Dict[str, object],
    ) -> Dict[str, object]:
        base = _stable_int(f"{judge_model.model_id}|{candidate_model.model_id}|{prompt.prompt_id}", 5)
        scores = {}
        for index, axis in enumerate(RUBRIC_AXES):
            score = rubric.score_min + ((base + index) % (rubric.score_max - rubric.score_min + 1))
            scores[axis] = score
        rationale = (
            f"{judge_model.label} mock judgment for {candidate_model.label} on {prompt.prompt_id}: "
            f"clear enough, moderately structured, with room for sharper detail."
        )
        return {"scores": scores, "rationale": rationale, "metadata": {"mode": "mock"}}


class OpenRouterBackend(ModelBackend):
    name = "openrouter"
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for the OpenRouter backend")

    def generate(self, model: ModelSpec, prompt: Prompt, settings: Dict[str, object]) -> Dict[str, object]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are writing a nonfiction piece in response to a direct task. "
                    "Answer the task directly. Do not mention any benchmark or judging setup."
                ),
            },
            {"role": "user", "content": prompt.task},
        ]
        data = self._chat_completion_with_reasoning_fallback(model.model_id, messages, settings)
        return {
            "response_text": _extract_text(data),
            "metadata": {"id": data.get("id"), "usage": data.get("usage", {}), "finish_reason": _extract_finish_reason(data)},
        }

    def judge(
        self,
        judge_model: ModelSpec,
        candidate_model: ModelSpec,
        prompt: Prompt,
        candidate_text: str,
        rubric: Rubric,
        settings: Dict[str, object],
    ) -> Dict[str, object]:
        axes_blob = "\n".join(
            f"- {axis.name} ({axis.axis_id}): {axis.description}" for axis in rubric.axes
        )
        schema_hint = {
            "scores": {axis: rubric.score_min for axis in RUBRIC_AXES},
            "rationale": "Short explanation",
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "You are grading a nonfiction writing sample. "
                    "Return strict JSON with keys 'scores' and 'rationale'. "
                    f"Each score must be an integer from {rubric.score_min} to {rubric.score_max}."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Prompt:\n{prompt.task}\n\n"
                    f"Candidate response:\n{candidate_text}\n\n"
                    f"Rubric axes:\n{axes_blob}\n\n"
                    f"Judging instructions:\n{rubric.judging_instructions}\n\n"
                    f"Return JSON like:\n{json.dumps(schema_hint)}"
                ),
            },
        ]
        judge_settings = dict(settings)
        judge_settings["json_mode"] = True
        data, text, payload = self._judge_completion_with_parse_fallback(judge_model.model_id, messages, judge_settings)
        return {
            "scores": payload["scores"],
            "rationale": payload.get("rationale", ""),
            "metadata": {"id": data.get("id"), "usage": data.get("usage", {}), "raw_text": text},
        }

    def _chat_completion_with_reasoning_fallback(
        self, model_id: str, messages: List[Dict[str, str]], settings: Dict[str, object]
    ) -> Dict[str, object]:
        data = self._chat_completion(model_id, messages, settings)
        if _response_needs_visibility_retry(data) and settings.get("reasoning_effort") != "none":
            retry_settings = dict(settings)
            retry_settings["reasoning_effort"] = "none"
            data = self._chat_completion(model_id, messages, retry_settings)
        if _response_needs_visibility_retry(data):
            retry_settings = dict(settings)
            retry_settings["reasoning_effort"] = "none"
            retry_settings["max_output_tokens"] = max(int(settings.get("max_output_tokens", 500)) * 3, 1200)
            data = self._chat_completion(model_id, messages, retry_settings)
        return data

    def _judge_completion_with_parse_fallback(
        self, model_id: str, messages: List[Dict[str, str]], settings: Dict[str, object]
    ) -> tuple[Dict[str, object], str, Dict[str, object]]:
        data = self._chat_completion_with_reasoning_fallback(model_id, messages, settings)
        text = _extract_text(data, prefer_reasoning=settings.get("json_mode", False))
        try:
            payload = _extract_json_object(text)
            return data, text, payload
        except (json.JSONDecodeError, RuntimeError):
            retry_settings = dict(settings)
            retry_settings["reasoning_effort"] = "none"
            retry_settings["temperature"] = 0
            retry_settings["max_output_tokens"] = max(int(settings.get("max_output_tokens", 500)) * 2, 1000)
            data = self._chat_completion_with_reasoning_fallback(model_id, messages, retry_settings)
            text = _extract_text(data, prefer_reasoning=retry_settings.get("json_mode", False))
            payload = _extract_json_object(text)
            return data, text, payload

    def _chat_completion(self, model_id: str, messages: List[Dict[str, str]], settings: Dict[str, object]) -> Dict[str, object]:
        reasoning = None
        reasoning_effort = settings.get("reasoning_effort")
        if reasoning_effort and reasoning_effort != "none":
            reasoning = {
                "effort": reasoning_effort,
                "exclude": bool(settings.get("exclude_reasoning", True)),
            }
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": settings.get("temperature", 0.2),
            "max_tokens": settings.get("max_output_tokens", 500),
            "response_format": {"type": "json_object"} if settings.get("json_mode") else None,
            "reasoning": reasoning,
            "provider": {"require_parameters": bool(settings.get("require_parameters", True))},
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.get("referer", "https://github.com"),
                "X-Title": settings.get("title", "ZinsserBench"),
            },
            method="POST",
        )
        max_attempts = int(settings.get("request_retries", 3))
        for attempt in range(max_attempts):
            try:
                with urllib.request.urlopen(request, timeout=int(settings.get("timeout_seconds", 120))) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if (
                    exc.code == 404
                    and settings.get("require_parameters", True)
                    and _is_missing_parameter_compatible_endpoint(body)
                ):
                    retry_settings = dict(settings)
                    retry_settings["require_parameters"] = False
                    return self._chat_completion(model_id, messages, retry_settings)
                if exc.code == 429 and attempt + 1 < max_attempts:
                    time.sleep(_extract_retry_after_seconds(body) or (attempt + 1) * 5)
                    continue
                raise RuntimeError(f"OpenRouter request failed ({exc.code}): {body}") from exc
        raise RuntimeError("OpenRouter request failed after retries")


def build_backend(name: str) -> ModelBackend:
    if name == "mock":
        return MockBackend()
    if name == "openrouter":
        return OpenRouterBackend()
    raise ValueError(f"Unknown backend {name!r}")


def _stable_int(seed: str, modulo: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def _extract_text(payload: Dict[str, object], prefer_reasoning: bool = False) -> str:
    choices = payload.get("choices", [])
    if not choices:
        raise RuntimeError(f"No choices returned: {payload}")
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(part for part in parts if part).strip()
    if prefer_reasoning:
        reasoning_text = _extract_reasoning_text(message)
        if reasoning_text:
            return reasoning_text
    raise RuntimeError(f"Unsupported OpenRouter response format: {payload}")


def _response_has_empty_content(payload: Dict[str, object]) -> bool:
    choices = payload.get("choices", [])
    if not choices:
        return False
    message = choices[0].get("message", {})
    content = message.get("content")
    return content is None


def _extract_finish_reason(payload: Dict[str, object]) -> str | None:
    choices = payload.get("choices", [])
    if not choices:
        return None
    finish_reason = choices[0].get("finish_reason")
    return finish_reason if isinstance(finish_reason, str) else None


def _response_needs_visibility_retry(payload: Dict[str, object]) -> bool:
    if _response_has_empty_content(payload):
        return True

    choices = payload.get("choices", [])
    if not choices:
        return False
    choice = choices[0]
    if choice.get("finish_reason") != "length":
        return False

    text = _extract_text(payload)
    if len(text.strip()) >= 200:
        return False

    usage = payload.get("usage", {})
    completion_tokens = usage.get("completion_tokens")
    details = usage.get("completion_tokens_details", {})
    if not isinstance(details, dict):
        details = {}
    reasoning_tokens = details.get("reasoning_tokens", 0)
    if not isinstance(reasoning_tokens, int):
        return False
    if completion_tokens is None:
        completion_tokens = reasoning_tokens
    if not isinstance(completion_tokens, int) or completion_tokens <= 0:
        return False
    return reasoning_tokens >= int(completion_tokens * 0.5)


def _extract_retry_after_seconds(body: str) -> int | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    error = payload.get("error", {})
    metadata = error.get("metadata", {})
    value = metadata.get("retry_after_seconds")
    if isinstance(value, int):
        return value
    return None


def _is_missing_parameter_compatible_endpoint(body: str) -> bool:
    return "No endpoints found that can handle the requested parameters" in body


def _extract_json_object(text: str) -> Dict[str, object]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise RuntimeError(f"Could not find JSON object in response: {text}")
    return json.loads(text[start : end + 1])


def _extract_reasoning_text(message: Dict[str, object]) -> str:
    reasoning = message.get("reasoning")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning.strip()
    details = message.get("reasoning_details")
    if not isinstance(details, list):
        return ""
    parts = []
    for item in details:
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    return "\n".join(parts).strip()
