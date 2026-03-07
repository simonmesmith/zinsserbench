from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


RUBRIC_AXES = [
    "clarity",
    "simplicity",
    "brevity_economy",
    "structure_flow",
    "specificity_precision",
    "humanity_voice",
    "overall",
]

PROMPT_CATEGORIES = [
    "memo",
    "explain",
    "profile",
    "service_howto",
    "persuasion_oped",
    "personal_nonfiction",
]


@dataclass(frozen=True)
class Prompt:
    prompt_id: str
    category: str
    title: str
    task: str
    topic_tags: List[str] = field(default_factory=list)
    target_length: str = ""


@dataclass(frozen=True)
class RubricAxis:
    axis_id: str
    name: str
    description: str


@dataclass(frozen=True)
class Rubric:
    version: str
    score_min: int
    score_max: int
    axes: List[RubricAxis]
    judging_instructions: str


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    label: str
    provider: str = "openrouter"
    enabled: bool = True


@dataclass(frozen=True)
class BenchmarkVersion:
    version: str
    prompts: List[Prompt]
    rubric: Rubric
    models: List[ModelSpec]
    judges: List[ModelSpec]


@dataclass
class GenerationRecord:
    benchmark_version: str
    run_name: str
    prompt_id: str
    prompt_category: str
    candidate_model_id: str
    candidate_label: str
    response_text: str
    created_at: str
    backend: str
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class JudgmentRecord:
    benchmark_version: str
    run_name: str
    prompt_id: str
    prompt_category: str
    candidate_model_id: str
    judge_model_id: str
    scores: Dict[str, float]
    rationale: str
    created_at: str
    backend: str
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class RunManifest:
    run_name: str
    benchmark_version: str
    backend: str
    created_at: str
    updated_at: str
    model_ids: List[str]
    settings: Dict[str, object]
    judge_model_ids: List[str] = field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def validate_axis_scores(scores: Dict[str, float], score_min: int, score_max: int) -> None:
    missing = [axis for axis in RUBRIC_AXES if axis not in scores]
    if missing:
        raise ValueError(f"Missing rubric scores: {missing}")
    for axis, value in scores.items():
        if axis not in RUBRIC_AXES:
            raise ValueError(f"Unknown rubric axis {axis!r}")
        if not (score_min <= value <= score_max):
            raise ValueError(
                f"Score for axis {axis!r} must be between {score_min} and {score_max}, got {value}"
            )
