from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .types import (
    BenchmarkVersion,
    ModelSpec,
    PROMPT_CATEGORIES,
    Prompt,
    RUBRIC_AXES,
    Rubric,
    RubricAxis,
)


def benchmark_versions_dir(root: Path) -> Path:
    return root / "benchmark_versions"


def load_benchmark_version(root: Path, version: str) -> BenchmarkVersion:
    version_dir = benchmark_versions_dir(root) / version
    if not version_dir.exists():
        raise FileNotFoundError(f"Benchmark version not found: {version_dir}")

    prompts = _load_json(version_dir / "prompts.json")
    rubric_data = _load_json(version_dir / "rubric.json")
    models = _load_json(version_dir / "models.json")

    prompt_objs = [_parse_prompt(item) for item in prompts]
    rubric = _parse_rubric(version, rubric_data)
    model_objs = [_parse_model(item) for item in models if item.get("enabled", True)]

    return BenchmarkVersion(version=version, prompts=prompt_objs, rubric=rubric, models=model_objs)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_prompt(data: Dict[str, Any]) -> Prompt:
    required = ["prompt_id", "category", "title", "task"]
    for field in required:
        if not data.get(field):
            raise ValueError(f"Prompt missing required field {field!r}: {data}")
    if data["category"] not in PROMPT_CATEGORIES:
        raise ValueError(f"Invalid prompt category {data['category']!r}")
    return Prompt(
        prompt_id=data["prompt_id"],
        category=data["category"],
        title=data["title"],
        task=data["task"],
        topic_tags=list(data.get("topic_tags", [])),
        target_length=data.get("target_length", ""),
    )


def _parse_rubric(version: str, data: Dict[str, Any]) -> Rubric:
    axes = [RubricAxis(axis_id=item["axis_id"], name=item["name"], description=item["description"]) for item in data["axes"]]
    axis_ids = [axis.axis_id for axis in axes]
    if axis_ids != RUBRIC_AXES:
        raise ValueError(f"Rubric axes must exactly match {RUBRIC_AXES}, got {axis_ids}")
    return Rubric(
        version=version,
        score_min=int(data["score_min"]),
        score_max=int(data["score_max"]),
        axes=axes,
        judging_instructions=data["judging_instructions"],
    )


def _parse_model(data: Dict[str, Any]) -> ModelSpec:
    if not data.get("model_id") or not data.get("label"):
        raise ValueError(f"Model entry missing required fields: {data}")
    return ModelSpec(
        model_id=data["model_id"],
        label=data["label"],
        provider=data.get("provider", "openrouter"),
        enabled=bool(data.get("enabled", True)),
    )
