from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from .aggregate import aggregate_run
from .backends import build_backend
from .env import load_dotenv
from .pipeline import generate_missing, judge_missing
from .report import generate_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="zinsserbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _common_run_parser(subparsers.add_parser("run", help="Generate, judge, aggregate, and report"))
    _common_run_parser(subparsers.add_parser("generate", help="Generate missing outputs"))
    _common_run_parser(subparsers.add_parser("judge", help="Generate missing judgments"))

    analyze_parser = subparsers.add_parser("analyze", help="Aggregate and report from stored outputs and judgments")
    analyze_parser.add_argument("--run-name", required=True)
    analyze_parser.add_argument("--root", default=".", help="Repository root")

    args = parser.parse_args()
    root = Path(args.root).resolve()
    load_dotenv(root / ".env")
    load_dotenv(root / ".env.local")

    if args.command == "run":
        settings = _settings_from_args(args)
        backend = build_backend(args.backend)
        generate_missing(root, args.run_name, args.benchmark_version, backend, settings)
        judge_missing(root, args.run_name, args.benchmark_version, backend, settings)
        summary = generate_report(root, args.run_name)
        print(json.dumps({"status": "ok", "run_name": args.run_name, "summary_keys": sorted(summary.keys())}, indent=2))
        return

    if args.command == "generate":
        settings = _settings_from_args(args)
        backend = build_backend(args.backend)
        result = generate_missing(root, args.run_name, args.benchmark_version, backend, settings)
        print(json.dumps(result, indent=2))
        return

    if args.command == "judge":
        settings = _settings_from_args(args)
        backend = build_backend(args.backend)
        result = judge_missing(root, args.run_name, args.benchmark_version, backend, settings)
        print(json.dumps(result, indent=2))
        return

    if args.command == "analyze":
        summary = generate_report(root, args.run_name)
        print(json.dumps({"status": "ok", "run_name": args.run_name, "summary_keys": sorted(summary.keys())}, indent=2))
        return


def _common_run_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--benchmark-version", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--backend", default="openrouter", choices=["openrouter", "mock"])
    parser.add_argument("--generation-concurrency", type=int, default=4)
    parser.add_argument("--judge-concurrency", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-output-tokens", type=int, default=2500)
    parser.add_argument(
        "--judge-max-output-tokens",
        type=int,
        default=700,
        help="Separate output cap for judge JSON responses.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument(
        "--reasoning-effort",
        default="medium",
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
    )
    parser.add_argument(
        "--include-reasoning",
        action="store_true",
        help="Return reasoning blocks in the API response when the model supports them.",
    )
    return parser


def _settings_from_args(args: argparse.Namespace) -> Dict[str, object]:
    return {
        "generation_concurrency": args.generation_concurrency,
        "judge_concurrency": args.judge_concurrency,
        "temperature": args.temperature,
        "max_output_tokens": args.max_output_tokens,
        "judge_max_output_tokens": args.judge_max_output_tokens,
        "timeout_seconds": args.timeout_seconds,
        "reasoning_effort": args.reasoning_effort,
        "exclude_reasoning": not args.include_reasoning,
    }
