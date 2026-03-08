from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

from .backends import ModelBackend
from .quality import evaluate_output, sanitize_output
from .specs import load_benchmark_version
from .storage import RunStorage
from .types import GenerationRecord, JudgmentRecord, RunManifest, model_company, validate_axis_scores, utc_now_iso


def initialize_run(
    root: Path,
    run_name: str,
    benchmark_version: str,
    backend_name: str,
    settings: Dict[str, object],
    model_ids: List[str],
    judge_model_ids: List[str],
) -> RunStorage:
    storage = RunStorage(root, run_name)
    manifest = storage.load_manifest()
    now = utc_now_iso()
    if manifest is None:
        manifest = RunManifest(
            run_name=run_name,
            benchmark_version=benchmark_version,
            backend=backend_name,
            created_at=now,
            updated_at=now,
            model_ids=model_ids,
            judge_model_ids=judge_model_ids,
            settings=settings,
        )
    else:
        manifest.run_name = run_name
        manifest.updated_at = now
        manifest.model_ids = sorted(set(manifest.model_ids) | set(model_ids))
        manifest.judge_model_ids = judge_model_ids
        manifest.settings = settings
        manifest.backend = backend_name
        manifest.benchmark_version = benchmark_version
    storage.write_manifest(manifest)
    return storage


def generate_missing(
    root: Path,
    run_name: str,
    benchmark_version: str,
    backend: ModelBackend,
    settings: Dict[str, object],
) -> Dict[str, int]:
    benchmark = load_benchmark_version(root, benchmark_version)
    storage = initialize_run(
        root,
        run_name,
        benchmark_version,
        backend.name,
        settings,
        [model.model_id for model in benchmark.models],
        [model.model_id for model in benchmark.judges],
    )
    tasks: List[Tuple] = []
    for prompt in benchmark.prompts:
        for model in benchmark.models:
            if not storage.has_output(benchmark_version, prompt.prompt_id, model.model_id):
                tasks.append((prompt, model))
    _run_parallel(tasks, int(settings.get("generation_concurrency", 4)), lambda item: _generate_one(storage, benchmark_version, backend, settings, item[0], item[1]))
    return {"scheduled": len(tasks), "completed": len(tasks)}


def judge_missing(
    root: Path,
    run_name: str,
    benchmark_version: str,
    backend: ModelBackend,
    settings: Dict[str, object],
) -> Dict[str, int]:
    benchmark = load_benchmark_version(root, benchmark_version)
    storage = initialize_run(
        root,
        run_name,
        benchmark_version,
        backend.name,
        settings,
        [model.model_id for model in benchmark.models],
        [model.model_id for model in benchmark.judges],
    )
    outputs = {
        (record.prompt_id, record.candidate_model_id): record
        for record in storage.load_outputs()
        if record.benchmark_version == benchmark_version
    }
    tasks: List[Tuple] = []
    for prompt in benchmark.prompts:
        for candidate in benchmark.models:
            output = outputs.get((prompt.prompt_id, candidate.model_id))
            if output is None:
                continue
            guard = output.metadata.get("quality_guard", {})
            if isinstance(guard, dict) and guard.get("status") != "ok":
                continue
            if not evaluate_output(prompt, output.response_text).is_valid:
                continue
            for judge in benchmark.judges:
                if model_company(candidate.model_id) == model_company(judge.model_id):
                    continue
                if not storage.has_judgment(benchmark_version, prompt.prompt_id, candidate.model_id, judge.model_id):
                    tasks.append((prompt, candidate, judge, output.response_text))
    _run_parallel(
        tasks,
        int(settings.get("judge_concurrency", 4)),
        lambda item: _judge_one(storage, benchmark, backend, settings, item[0], item[1], item[2], item[3]),
    )
    return {"scheduled": len(tasks), "completed": len(tasks)}


def _generate_one(
    storage: RunStorage,
    benchmark_version: str,
    backend: ModelBackend,
    settings: Dict[str, object],
    prompt,
    model,
) -> None:
    payload, text, metadata = _generate_with_post_processing(backend, model, prompt, settings)
    guard = evaluate_output(prompt, text)
    status = "ok"
    reason = ""
    if not guard.is_valid:
        status = "quarantined"
        reason = guard.reason
    metadata["quality_guard"] = {
        "status": status,
        "reason": reason,
        "word_count": guard.word_count,
        "minimum_words": guard.minimum_words,
    }
    record = GenerationRecord(
        benchmark_version=benchmark_version,
        run_name=storage.run_name,
        prompt_id=prompt.prompt_id,
        prompt_category=prompt.category,
        candidate_model_id=model.model_id,
        candidate_label=model.label,
        response_text=text,
        created_at=utc_now_iso(),
        backend=backend.name,
        metadata=metadata,
    )
    storage.write_output(record)


def _judge_one(
    storage: RunStorage,
    benchmark,
    backend: ModelBackend,
    settings: Dict[str, object],
    prompt,
    candidate,
    judge,
    candidate_text: str,
) -> None:
    judge_settings = dict(settings)
    judge_settings["max_output_tokens"] = int(settings.get("judge_max_output_tokens", settings.get("max_output_tokens", 700)))
    payload = backend.judge(judge, candidate, prompt, candidate_text, benchmark.rubric, judge_settings)
    validate_axis_scores(payload["scores"], benchmark.rubric.score_min, benchmark.rubric.score_max)
    record = JudgmentRecord(
        benchmark_version=benchmark.version,
        run_name=storage.run_name,
        prompt_id=prompt.prompt_id,
        prompt_category=prompt.category,
        candidate_model_id=candidate.model_id,
        judge_model_id=judge.model_id,
        scores=dict(payload["scores"]),
        rationale=payload.get("rationale", ""),
        created_at=utc_now_iso(),
        backend=backend.name,
        metadata=dict(payload.get("metadata", {})),
    )
    storage.write_judgment(record)


def _run_parallel(tasks: Sequence[Tuple], max_workers: int, fn: Callable[[Tuple], None]) -> None:
    if not tasks:
        return
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fn, task) for task in tasks]
        for future in as_completed(futures):
            future.result()


def _generate_with_post_processing(backend, model, prompt, settings):
    base_max_tokens = int(settings.get("max_output_tokens", 10000))
    attempts = [
        dict(settings),
        dict(settings, reasoning_effort="none", max_output_tokens=max(base_max_tokens * 2, 20000)),
    ]
    last_payload = None
    last_text = ""
    last_metadata = {}

    for attempt_index, attempt_settings in enumerate(attempts, start=1):
        payload = backend.generate(model, prompt, attempt_settings)
        raw_text = payload["response_text"]
        metadata = dict(payload.get("metadata", {}))
        metadata["raw_response_text"] = raw_text
        metadata["generation_attempt"] = attempt_index
        metadata["generation_settings"] = {
            "max_output_tokens": int(attempt_settings.get("max_output_tokens", base_max_tokens)),
            "reasoning_effort": attempt_settings.get("reasoning_effort"),
        }

        sanitized = sanitize_output(raw_text)
        metadata["sanitization"] = {
            "changed": sanitized.changed,
            "removed_chars": sanitized.removed_chars,
            "removed_ratio": round(sanitized.removed_ratio, 4),
            "patterns": sanitized.patterns,
        }

        last_payload = payload
        last_text = sanitized.text
        last_metadata = metadata

        heavy_sanitization = sanitized.removed_ratio > 0.10
        if not heavy_sanitization:
            break

    return last_payload, last_text, last_metadata
