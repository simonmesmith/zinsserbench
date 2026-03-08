from __future__ import annotations

import argparse
from pathlib import Path

from zinsserbench.backends import build_backend
from zinsserbench.env import load_dotenv
from zinsserbench.specs import load_benchmark_version
from zinsserbench.storage import RunStorage
from zinsserbench.types import JudgmentRecord, model_company, utc_now_iso, validate_axis_scores


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing judgments one by one with per-item logging.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--benchmark-version", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--backend", default="openrouter", choices=["openrouter", "mock"])
    parser.add_argument("--judge-model-id", required=True)
    parser.add_argument("--judge-max-output-tokens", type=int, default=700)
    parser.add_argument("--reasoning-effort", default="medium")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--passes", type=int, default=3)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    load_dotenv(root / ".env")
    load_dotenv(root / ".env.local")

    benchmark = load_benchmark_version(root, args.benchmark_version)
    storage = RunStorage(root, args.run_name)
    backend = build_backend(args.backend)

    judge = next((item for item in benchmark.judges if item.model_id == args.judge_model_id), None)
    if judge is None:
        raise ValueError(f"Judge model not found in benchmark judges: {args.judge_model_id}")

    outputs = {
        (record.prompt_id, record.candidate_model_id): record
        for record in storage.load_outputs()
        if record.benchmark_version == args.benchmark_version
    }
    prompt_by_id = {prompt.prompt_id: prompt for prompt in benchmark.prompts}

    settings = {
        "temperature": args.temperature,
        "max_output_tokens": args.judge_max_output_tokens,
        "judge_max_output_tokens": args.judge_max_output_tokens,
        "timeout_seconds": args.timeout_seconds,
        "reasoning_effort": args.reasoning_effort,
        "exclude_reasoning": True,
    }

    for attempt in range(1, args.passes + 1):
        pending = _collect_missing_tasks(storage, benchmark, outputs, judge.model_id)
        print(f"pass {attempt}: pending={len(pending)}")
        if not pending:
            return 0

        progress = 0
        for index, (prompt_id, candidate_model_id) in enumerate(pending, start=1):
            prompt = prompt_by_id[prompt_id]
            candidate = next(model for model in benchmark.models if model.model_id == candidate_model_id)
            output = outputs[(prompt_id, candidate_model_id)]
            label = f"{index}/{len(pending)} {prompt_id} :: {candidate_model_id} -> {judge.model_id}"
            try:
                payload = backend.judge(judge, candidate, prompt, output.response_text, benchmark.rubric, settings)
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
                progress += 1
                print(f"ok   {label}")
            except Exception as exc:  # noqa: BLE001
                print(f"fail {label}: {exc}")

        if progress == 0:
            print("no progress this pass")
            return 1

    remaining = _collect_missing_tasks(storage, benchmark, outputs, judge.model_id)
    print(f"remaining={len(remaining)}")
    return 0 if not remaining else 1


def _collect_missing_tasks(storage: RunStorage, benchmark, outputs, judge_model_id: str) -> list[tuple[str, str]]:
    tasks: list[tuple[str, str]] = []
    for prompt in benchmark.prompts:
        for candidate in benchmark.models:
            if model_company(candidate.model_id) == model_company(judge_model_id):
                continue
            output = outputs.get((prompt.prompt_id, candidate.model_id))
            if output is None:
                continue
            if storage.has_judgment(benchmark.version, prompt.prompt_id, candidate.model_id, judge_model_id):
                continue
            tasks.append((prompt.prompt_id, candidate.model_id))
    return tasks


if __name__ == "__main__":
    raise SystemExit(main())
