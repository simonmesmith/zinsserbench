from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from .quality import evaluate_output
from .specs import load_benchmark_version
from .storage import RunStorage
from .types import JudgmentRecord, RUBRIC_AXES, model_company


def aggregate_run(root: Path, run_name: str) -> Dict[str, object]:
    storage = RunStorage(root, run_name)
    manifest = storage.load_manifest()
    if manifest is None:
        raise FileNotFoundError(f"Run manifest not found for {run_name}")
    judgments = storage.load_judgments()
    if not judgments:
        raise RuntimeError(f"No judgments found for run {run_name}")

    benchmark = load_benchmark_version(root, manifest.benchmark_version)
    prompt_by_id = {prompt.prompt_id: prompt for prompt in benchmark.prompts}
    outputs = storage.load_outputs()
    output_lookup = {(record.prompt_id, record.candidate_model_id): record for record in outputs}
    quarantined_outputs = []
    truncation_warnings = []
    sanitization_warnings = []
    exact_cap_hits = []
    valid_output_keys = set()
    for record in outputs:
        prompt = prompt_by_id.get(record.prompt_id)
        if prompt is None:
            continue
        guard = evaluate_output(prompt, record.response_text)
        quality_guard = record.metadata.get("quality_guard", {})
        if not isinstance(quality_guard, dict):
            quality_guard = {}
        truncation = record.metadata.get("truncation", {})
        if not isinstance(truncation, dict):
            truncation = {}
        sanitization = record.metadata.get("sanitization", {})
        if not isinstance(sanitization, dict):
            sanitization = {}
        usage = record.metadata.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        generation_settings = record.metadata.get("generation_settings", {})
        if not isinstance(generation_settings, dict):
            generation_settings = {}

        if sanitization.get("changed"):
            sanitization_warnings.append(
                {
                    "candidate_model_id": record.candidate_model_id,
                    "prompt_id": record.prompt_id,
                    "removed_ratio": sanitization.get("removed_ratio", 0),
                    "patterns": ",".join(sanitization.get("patterns", [])),
                    "generation_attempt": record.metadata.get("generation_attempt", 1),
                }
            )
        completion_tokens = usage.get("completion_tokens")
        output_cap = generation_settings.get("max_output_tokens")
        if isinstance(completion_tokens, int) and isinstance(output_cap, int) and completion_tokens >= output_cap:
            exact_cap_hits.append(
                {
                    "candidate_model_id": record.candidate_model_id,
                    "prompt_id": record.prompt_id,
                    "completion_tokens": completion_tokens,
                    "max_output_tokens": output_cap,
                }
            )
        if truncation.get("is_truncated"):
            truncation_warnings.append(
                {
                    "candidate_model_id": record.candidate_model_id,
                    "prompt_id": record.prompt_id,
                    "reasons": ",".join(truncation.get("reasons", [])),
                    "generation_attempt": record.metadata.get("generation_attempt", 1),
                }
            )

        if guard.is_valid and quality_guard.get("status") == "ok":
            valid_output_keys.add((record.prompt_id, record.candidate_model_id))
            continue
        quarantined_outputs.append(
            {
                "prompt_id": record.prompt_id,
                "candidate_model_id": record.candidate_model_id,
                "reason": quality_guard.get("reason", guard.reason),
                "word_count": guard.word_count,
                "minimum_words": guard.minimum_words,
            }
        )
    judgments = [
        judgment
        for judgment in judgments
        if (judgment.prompt_id, judgment.candidate_model_id) in valid_output_keys
    ]
    if not judgments:
        raise RuntimeError(f"No valid judgments found for run {run_name}")

    per_item, per_axis, skipped_same_company, excluded_for_insufficient_judges = _build_per_item_records(
        judgments,
        output_lookup,
        benchmark.judges,
    )
    writing_by_model = _average_group(per_item, ("candidate_model_id",), RUBRIC_AXES)
    writing_by_model_axis = _average_group(per_axis, ("candidate_model_id", "axis"), ["score"])
    writing_by_model_category = _average_group(per_axis, ("candidate_model_id", "prompt_category"), ["score"])
    writing_by_model_prompt = _average_group(per_axis, ("candidate_model_id", "prompt_id"), ["score"])
    writing_by_prompt_axis = _average_group(per_axis, ("prompt_id", "axis"), ["score"])
    judge_quality = _judge_quality(judgments)

    summary = {
        "run_name": run_name,
        "benchmark_version": manifest.benchmark_version,
        "writing_by_model": writing_by_model,
        "writing_by_model_axis": writing_by_model_axis,
        "writing_by_model_category": writing_by_model_category,
        "writing_by_model_prompt": writing_by_model_prompt,
        "writing_by_prompt_axis": writing_by_prompt_axis,
        "judge_quality": judge_quality,
        "exact_cap_hits": sorted(exact_cap_hits, key=lambda item: (item["candidate_model_id"], item["prompt_id"])),
        "truncation_warnings": sorted(
            truncation_warnings,
            key=lambda item: (item["candidate_model_id"], item["prompt_id"]),
        ),
        "sanitization_warnings": sorted(
            sanitization_warnings,
            key=lambda item: (item["candidate_model_id"], item["prompt_id"]),
        ),
        "skipped_same_company_judgments": skipped_same_company,
        "excluded_for_insufficient_judges": excluded_for_insufficient_judges,
        "quarantined_outputs": sorted(
            quarantined_outputs,
            key=lambda item: (item["candidate_model_id"], item["prompt_id"]),
        ),
        "response_lengths_by_model": _response_lengths_by_model(outputs, prompt_by_id),
        "model_prompt_details": [
            {
                "candidate_model_id": item["candidate_model_id"],
                "prompt_id": item["prompt_id"],
                "prompt_category": item["prompt_category"],
                "candidate_response_text": output_lookup[(item["prompt_id"], item["candidate_model_id"])].response_text,
                "scores": item["scores"],
            }
            for item in sorted(per_item, key=lambda row: (row["candidate_model_id"], row["prompt_id"]))
        ],
    }

    storage.write_analysis_json("summary.json", summary)
    _write_csv(storage.analysis_dir / "writing_by_model.csv", writing_by_model)
    _write_csv(storage.analysis_dir / "writing_by_model_axis.csv", writing_by_model_axis)
    _write_csv(storage.analysis_dir / "writing_by_model_category.csv", writing_by_model_category)
    _write_csv(storage.analysis_dir / "writing_by_model_prompt.csv", writing_by_model_prompt)
    _write_csv(storage.analysis_dir / "writing_by_prompt_axis.csv", writing_by_prompt_axis)
    _write_csv(storage.analysis_dir / "judge_quality.csv", judge_quality)
    _write_csv(storage.analysis_dir / "quarantined_outputs.csv", summary["quarantined_outputs"])
    _write_csv(storage.analysis_dir / "exact_cap_hits.csv", summary["exact_cap_hits"])
    _write_csv(storage.analysis_dir / "truncation_warnings.csv", summary["truncation_warnings"])
    _write_csv(storage.analysis_dir / "sanitization_warnings.csv", summary["sanitization_warnings"])
    _write_csv(storage.analysis_dir / "skipped_same_company_judgments.csv", summary["skipped_same_company_judgments"])
    _write_csv(storage.analysis_dir / "excluded_for_insufficient_judges.csv", summary["excluded_for_insufficient_judges"])
    _write_csv(storage.analysis_dir / "response_lengths_by_model.csv", summary["response_lengths_by_model"])
    _write_csv(storage.analysis_dir / "model_prompt_details.csv", summary["model_prompt_details"])
    return summary


def _build_per_item_records(
    judgments: List[JudgmentRecord],
    output_lookup: Dict[Tuple[str, str], object],
    judges: List[object],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]]]:
    grouped: Dict[Tuple[str, str], Dict[str, object]] = {}
    by_axis_rows: List[Dict[str, object]] = []
    for judgment in judgments:
        key = (judgment.prompt_id, judgment.candidate_model_id)
        bucket = grouped.setdefault(
            key,
            {
                "prompt_id": judgment.prompt_id,
                "prompt_category": judgment.prompt_category,
                "candidate_model_id": judgment.candidate_model_id,
                "scores": {axis: [] for axis in RUBRIC_AXES},
            },
        )
        for axis, score in judgment.scores.items():
            bucket["scores"][axis].append(score)
            by_axis_rows.append(
                {
                    "prompt_id": judgment.prompt_id,
                    "prompt_category": judgment.prompt_category,
                    "candidate_model_id": judgment.candidate_model_id,
                    "axis": axis,
                    "score": score,
                }
            )

    rows = []
    skipped_same_company = []
    excluded_for_insufficient_judges = []
    judge_ids = [judge.model_id for judge in judges]
    for bucket in grouped.values():
        output_record = output_lookup.get((bucket["prompt_id"], bucket["candidate_model_id"]))
        company = model_company(bucket["candidate_model_id"])
        same_company_judges = [
            judge_id for judge_id in judge_ids if model_company(judge_id) == company
        ]
        for judge_id in same_company_judges:
            skipped_same_company.append(
                {
                    "candidate_model_id": bucket["candidate_model_id"],
                    "prompt_id": bucket["prompt_id"],
                    "judge_model_id": judge_id,
                    "company": company,
                }
            )

        required_judges = max(1, len(judge_ids) - len(same_company_judges))
        judge_count = len(next(iter(bucket["scores"].values())))
        if judge_count < required_judges:
            excluded_for_insufficient_judges.append(
                {
                    "candidate_model_id": bucket["candidate_model_id"],
                    "prompt_id": bucket["prompt_id"],
                    "judge_count": judge_count,
                    "required_judges": required_judges,
                    "candidate_response_text": output_record.response_text if output_record else "",
                }
            )
            continue
        averaged_scores = {
            axis: round(sum(values) / len(values), 4) for axis, values in bucket["scores"].items() if values
        }
        rows.append(
            {
                "prompt_id": bucket["prompt_id"],
                "prompt_category": bucket["prompt_category"],
                "candidate_model_id": bucket["candidate_model_id"],
                "scores": averaged_scores,
                **averaged_scores,
            }
        )
    return rows, by_axis_rows, sorted(
        skipped_same_company,
        key=lambda item: (item["candidate_model_id"], item["prompt_id"], item["judge_model_id"]),
    ), sorted(
        excluded_for_insufficient_judges,
        key=lambda item: (item["candidate_model_id"], item["prompt_id"]),
    )


def _average_group(rows: List[Dict[str, object]], group_keys: Tuple[str, ...], value_keys: List[str]) -> List[Dict[str, object]]:
    buckets: Dict[Tuple[object, ...], Dict[str, object]] = {}
    for row in rows:
        if any(value_key not in row for value_key in value_keys):
            continue
        key = tuple(row[key_name] for key_name in group_keys)
        bucket = buckets.setdefault(
            key,
            {key_name: row[key_name] for key_name in group_keys} | {value_key: [] for value_key in value_keys},
        )
        for value_key in value_keys:
            bucket[value_key].append(float(row[value_key]))

    results = []
    for bucket in buckets.values():
        item = {key: bucket[key] for key in group_keys}
        for value_key in value_keys:
            values = bucket[value_key]
            item[value_key] = round(sum(values) / len(values), 4)
        results.append(item)
    return sorted(results, key=lambda item: tuple(item[key] for key in group_keys))


def _judge_quality(judgments: List[JudgmentRecord]) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str], List[JudgmentRecord]] = defaultdict(list)
    for judgment in judgments:
        grouped[(judgment.prompt_id, judgment.candidate_model_id)].append(judgment)

    judge_axis_errors: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    judge_overall_errors: Dict[str, List[float]] = defaultdict(list)

    for item_judgments in grouped.values():
        for judgment in item_judgments:
            peers = [peer for peer in item_judgments if peer.judge_model_id != judgment.judge_model_id]
            if not peers:
                continue
            for axis in RUBRIC_AXES:
                peer_mean = sum(peer.scores[axis] for peer in peers) / len(peers)
                error = abs(judgment.scores[axis] - peer_mean)
                judge_axis_errors[(judgment.judge_model_id, axis)].append(error)
                judge_overall_errors[judgment.judge_model_id].append(error)

    results = []
    for judge_model_id, errors in sorted(judge_overall_errors.items()):
        row = {
            "judge_model_id": judge_model_id,
            "agreement_overall": round(1 / (1 + (sum(errors) / len(errors))), 4),
        }
        for axis in RUBRIC_AXES:
            axis_errors = judge_axis_errors.get((judge_model_id, axis), [])
            row[f"agreement_{axis}"] = round(1 / (1 + (sum(axis_errors) / len(axis_errors))), 4) if axis_errors else 0.0
        results.append(row)
    return results


def _write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _response_lengths_by_model(outputs: List[object], prompt_by_id: Dict[str, object]) -> List[Dict[str, object]]:
    rows = []
    for record in outputs:
        prompt = prompt_by_id.get(record.prompt_id)
        if prompt is None:
            continue
        guard = evaluate_output(prompt, record.response_text)
        quality_guard = record.metadata.get("quality_guard", {})
        if not isinstance(quality_guard, dict):
            quality_guard = {}
        rows.append(
            {
                "candidate_model_id": record.candidate_model_id,
                "prompt_id": record.prompt_id,
                "prompt_category": record.prompt_category,
                "word_count": guard.word_count,
                "minimum_words": guard.minimum_words,
                "status": quality_guard.get("status", "ok" if guard.is_valid else "quarantined"),
                "reason": quality_guard.get("reason", guard.reason),
            }
        )
    return sorted(rows, key=lambda item: (item["candidate_model_id"], item["prompt_id"]))
