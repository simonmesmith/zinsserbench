from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

from zinsserbench.aggregate import aggregate_run
from zinsserbench.backends import MockBackend, OpenRouterBackend, _extract_retry_after_seconds
from zinsserbench.env import load_dotenv
from zinsserbench.pipeline import generate_missing, judge_missing
from zinsserbench.report import generate_report
from zinsserbench.specs import load_benchmark_version


class ZinsserBenchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parent.parent
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zinsserbench-test-"))
        self._copy_tree(self.repo_root / "benchmark_versions", self.temp_dir / "benchmark_versions")
        self.backend = MockBackend()
        self.settings = {
            "generation_concurrency": 2,
            "judge_concurrency": 2,
            "temperature": 0.2,
            "max_output_tokens": 300,
            "timeout_seconds": 30,
        }

    def test_spec_validation(self) -> None:
        benchmark = load_benchmark_version(self.temp_dir, "v0.1")
        self.assertEqual(20, len(benchmark.prompts))
        self.assertEqual(12, len(benchmark.models))
        self.assertEqual(3, len(benchmark.judges))
        self.assertEqual(
            ["openai/gpt-5.4", "anthropic/claude-opus-4.6", "google/gemini-3.1-pro-preview"],
            [judge.model_id for judge in benchmark.judges],
        )
        self.assertEqual("memo", benchmark.prompts[0].category)

    def test_incremental_generation_and_judging(self) -> None:
        first_generate = generate_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        second_generate = generate_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        self.assertEqual(240, first_generate["scheduled"])
        self.assertEqual(0, second_generate["scheduled"])

        first_judge = judge_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        second_judge = judge_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        self.assertEqual(720, first_judge["scheduled"])
        self.assertEqual(0, second_judge["scheduled"])

    def test_aggregation_outputs_and_reports(self) -> None:
        generate_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        judge_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        summary = generate_report(self.temp_dir, "fixture-run")

        self.assertIn("writing_by_model", summary)
        self.assertIn("writing_by_model_category", summary)
        self.assertIn("writing_by_model_prompt", summary)
        self.assertIn("judge_quality", summary)

        analysis_dir = self.temp_dir / "runs" / "fixture-run" / "analysis"
        self.assertTrue((analysis_dir / "summary.json").exists())
        self.assertTrue((analysis_dir / "REPORT.md").exists())
        self.assertTrue((analysis_dir / "overall_scores.svg").exists())
        self.assertTrue((analysis_dir / "judge_quality.svg").exists())

        with (analysis_dir / "writing_by_model.csv").open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(12, len(rows))

        with (analysis_dir / "model_prompt_details.csv").open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(240, len(rows))

    def test_add_model_only_backfills_missing_work(self) -> None:
        generate_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        judge_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)

        models_path = self.temp_dir / "benchmark_versions" / "v0.1" / "models.json"
        original = models_path.read_text(encoding="utf-8")
        models_path.write_text(
            original.rstrip()[:-1] + ',\n  { "model_id": "test/new-model", "label": "New Model" }\n]\n',
            encoding="utf-8",
        )

        generate_result = generate_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        judge_result = judge_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        self.assertEqual(20, generate_result["scheduled"])
        self.assertEqual(60, judge_result["scheduled"])

    def test_load_dotenv_reads_local_env_file_without_overriding_existing_env(self) -> None:
        env_path = self.temp_dir / ".env"
        env_path.write_text(
            "# comment\n"
            "OPENROUTER_API_KEY=from-dotenv\n"
            "export OTHER_KEY='quoted-value'\n",
            encoding="utf-8",
        )

        old_openrouter = os.environ.get("OPENROUTER_API_KEY")
        old_other = os.environ.get("OTHER_KEY")
        try:
            os.environ["OPENROUTER_API_KEY"] = "already-set"
            os.environ.pop("OTHER_KEY", None)

            self.assertTrue(load_dotenv(env_path))
            self.assertEqual("already-set", os.environ["OPENROUTER_API_KEY"])
            self.assertEqual("quoted-value", os.environ["OTHER_KEY"])
        finally:
            if old_openrouter is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = old_openrouter
            if old_other is None:
                os.environ.pop("OTHER_KEY", None)
            else:
                os.environ["OTHER_KEY"] = old_other

    def test_openrouter_retries_without_reasoning_when_content_is_empty(self) -> None:
        backend = OpenRouterBackend(api_key="test-key")
        calls = []
        responses = [
            {
                "choices": [
                    {
                        "message": {"content": None},
                        "finish_reason": "length",
                    }
                ],
                "usage": {"completion_tokens_details": {"reasoning_tokens": 400}},
            },
            {
                "choices": [
                    {
                        "message": {"content": "final text"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {},
            },
        ]

        def fake_chat_completion(model_id, messages, settings):
            calls.append(dict(settings))
            return responses[len(calls) - 1]

        backend._chat_completion = fake_chat_completion  # type: ignore[method-assign]
        data = backend._chat_completion_with_reasoning_fallback(
            "qwen/qwen3.5-35b-a3b",
            [{"role": "user", "content": "test"}],
            {"reasoning_effort": "medium"},
        )

        self.assertEqual("medium", calls[0]["reasoning_effort"])
        self.assertEqual("none", calls[1]["reasoning_effort"])
        self.assertEqual("final text", data["choices"][0]["message"]["content"])

    def test_openrouter_retries_with_larger_budget_when_empty_content_persists(self) -> None:
        backend = OpenRouterBackend(api_key="test-key")
        calls = []
        responses = [
            {
                "choices": [
                    {
                        "message": {"content": None},
                        "finish_reason": "length",
                    }
                ],
                "usage": {},
            },
            {
                "choices": [
                    {
                        "message": {"content": None},
                        "finish_reason": "length",
                    }
                ],
                "usage": {},
            },
            {
                "choices": [
                    {
                        "message": {"content": "expanded text"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {},
            },
        ]

        def fake_chat_completion(model_id, messages, settings):
            calls.append(dict(settings))
            return responses[len(calls) - 1]

        backend._chat_completion = fake_chat_completion  # type: ignore[method-assign]
        data = backend._chat_completion_with_reasoning_fallback(
            "z-ai/glm-5",
            [{"role": "user", "content": "test"}],
            {"reasoning_effort": "medium", "max_output_tokens": 500},
        )

        self.assertEqual("medium", calls[0]["reasoning_effort"])
        self.assertEqual("none", calls[1]["reasoning_effort"])
        self.assertEqual("none", calls[2]["reasoning_effort"])
        self.assertEqual(1500, calls[2]["max_output_tokens"])
        self.assertEqual("expanded text", data["choices"][0]["message"]["content"])

    def test_extract_retry_after_seconds_from_openrouter_error(self) -> None:
        body = (
            '{"error":{"message":"Provider returned error","code":429,'
            '"metadata":{"retry_after_seconds":60}}}'
        )
        self.assertEqual(60, _extract_retry_after_seconds(body))
        self.assertIsNone(_extract_retry_after_seconds("not json"))

    def _copy_tree(self, source: Path, destination: Path) -> None:
        for path in source.rglob("*"):
            relative = path.relative_to(source)
            target = destination / relative
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())


if __name__ == "__main__":
    unittest.main()
