from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .backends import ModelBackend
from .specs import load_benchmark_version
from .storage import RunStorage
from .types import GenerationRecord, JudgmentRecord, RunManifest, validate_axis_scores, utc_now_iso


def initialize_run(
    root: Path,
    run_name: str,
    benchmark_version: str,
    backend_name: str,
    settings: Dict[str, object],
    model_ids: List[str],
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
            settings=settings,
        )
    else:
        manifest.updated_at = now
        manifest.model_ids = sorted(set(manifest.model_ids) | set(model_ids))
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
        root, run_name, benchmark_version, backend.name, settings, [model.model_id for model in benchmark.models]
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
        root, run_name, benchmark_version, backend.name, settings, [model.model_id for model in benchmark.models]
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
            for judge in benchmark.models:
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
    payload = backend.generate(model, prompt, settings)
    record = GenerationRecord(
        benchmark_version=benchmark_version,
        run_name=storage.run_name,
        prompt_id=prompt.prompt_id,
        prompt_category=prompt.category,
        candidate_model_id=model.model_id,
        candidate_label=model.label,
        response_text=payload["response_text"],
        created_at=utc_now_iso(),
        backend=backend.name,
        metadata=dict(payload.get("metadata", {})),
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
    payload = backend.judge(judge, candidate, prompt, candidate_text, benchmark.rubric, settings)
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
