from __future__ import annotations

import csv
import json
import os
import tempfile
import urllib.error
import unittest
from pathlib import Path
from unittest import mock

from zinsserbench.aggregate import aggregate_run
from zinsserbench.backends import MockBackend, OpenRouterBackend, _extract_retry_after_seconds
from zinsserbench.env import load_dotenv
from zinsserbench.pipeline import generate_missing, judge_missing
from zinsserbench.quality import evaluate_output, sanitize_output
from zinsserbench.report import generate_report
from zinsserbench.specs import load_benchmark_version
from zinsserbench.types import model_company


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
            "max_output_tokens": 10000,
            "judge_max_output_tokens": 120,
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

    def test_v0_2_uses_four_judges(self) -> None:
        benchmark = load_benchmark_version(self.temp_dir, "v0.2")
        self.assertEqual(4, len(benchmark.judges))
        self.assertEqual(
            ["openai/gpt-5.4", "anthropic/claude-opus-4.6", "google/gemini-3.1-pro-preview", "z-ai/glm-5"],
            [judge.model_id for judge in benchmark.judges],
        )

    def test_incremental_generation_and_judging(self) -> None:
        first_generate = generate_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        second_generate = generate_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        self.assertEqual(240, first_generate["scheduled"])
        self.assertEqual(0, second_generate["scheduled"])

        first_judge = judge_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        second_judge = judge_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        self.assertEqual(600, first_judge["scheduled"])
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
        self.assertTrue((analysis_dir / "exact_cap_hits.csv").exists())
        self.assertTrue((analysis_dir / "truncation_warnings.csv").exists())
        self.assertTrue((analysis_dir / "sanitization_warnings.csv").exists())
        self.assertTrue((analysis_dir / "skipped_same_company_judgments.csv").exists())

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

    def test_judging_uses_separate_output_budget(self) -> None:
        calls = []

        class CaptureBackend(MockBackend):
            def judge(self, judge_model, candidate_model, prompt, candidate_text, rubric, settings):
                calls.append(dict(settings))
                return super().judge(judge_model, candidate_model, prompt, candidate_text, rubric, settings)

        backend = CaptureBackend()
        generate_missing(self.temp_dir, "fixture-run", "v0.1", backend, self.settings)
        judge_missing(self.temp_dir, "fixture-run", "v0.1", backend, self.settings)

        self.assertTrue(calls)
        self.assertEqual(120, calls[0]["max_output_tokens"])

    def test_judge_prompt_is_blind_to_candidate_identity(self) -> None:
        benchmark = load_benchmark_version(self.temp_dir, "v0.1")
        backend = OpenRouterBackend(api_key="test-key")
        captured = {}

        def fake_judge_completion(model_id, messages, settings):
            captured["messages"] = messages
            return (
                {"id": "ok", "usage": {}, "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]},
                '{"scores":{"clarity":5,"simplicity":5,"brevity_economy":5,"structure_flow":5,"specificity_precision":5,"humanity_voice":5,"overall":5},"rationale":"ok"}',
                {
                    "scores": {
                        "clarity": 5,
                        "simplicity": 5,
                        "brevity_economy": 5,
                        "structure_flow": 5,
                        "specificity_precision": 5,
                        "humanity_voice": 5,
                        "overall": 5,
                    },
                    "rationale": "ok",
                },
            )

        backend._judge_completion_with_parse_fallback = fake_judge_completion  # type: ignore[method-assign]
        backend.judge(
            benchmark.judges[0],
            benchmark.models[0],
            benchmark.prompts[0],
            "Candidate response text",
            benchmark.rubric,
            self.settings,
        )

        self.assertNotIn("Candidate model:", captured["messages"][1]["content"])

    def test_judge_missing_skips_quarantined_outputs(self) -> None:
        class ShortOutputBackend(MockBackend):
            def generate(self, model, prompt, settings):
                payload = super().generate(model, prompt, settings)
                if model.model_id == "openai/gpt-5.4" and prompt.prompt_id == "memo_remote_work_policy":
                    payload["response_text"] = "Too short to score."
                return payload

        backend = ShortOutputBackend()
        generate_missing(self.temp_dir, "fixture-run", "v0.1", backend, self.settings)
        judge_result = judge_missing(self.temp_dir, "fixture-run", "v0.1", backend, self.settings)

        self.assertEqual(598, judge_result["scheduled"])

    def test_aggregate_reports_quarantined_outputs(self) -> None:
        class ShortOutputBackend(MockBackend):
            def generate(self, model, prompt, settings):
                payload = super().generate(model, prompt, settings)
                if model.model_id == "openai/gpt-5.4" and prompt.prompt_id == "memo_remote_work_policy":
                    payload["response_text"] = "Too short to score."
                return payload

        backend = ShortOutputBackend()
        generate_missing(self.temp_dir, "fixture-run", "v0.1", backend, self.settings)
        judge_missing(self.temp_dir, "fixture-run", "v0.1", backend, self.settings)
        summary = generate_report(self.temp_dir, "fixture-run")

        self.assertEqual(1, len(summary["quarantined_outputs"]))
        self.assertEqual("openai/gpt-5.4", summary["quarantined_outputs"][0]["candidate_model_id"])
        self.assertTrue((self.temp_dir / "runs" / "fixture-run" / "analysis" / "quarantined_outputs.csv").exists())

    def test_same_company_judging_is_excluded(self) -> None:
        generate_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        judge_missing(self.temp_dir, "fixture-run", "v0.1", self.backend, self.settings)
        summary = aggregate_run(self.temp_dir, "fixture-run")

        self.assertEqual(120, len(summary["skipped_same_company_judgments"]))
        self.assertEqual(
            {"openai", "anthropic", "google"},
            {row["company"] for row in summary["skipped_same_company_judgments"]},
        )

    def test_aggregate_excludes_items_missing_expected_non_conflicted_judges(self) -> None:
        generate_missing(self.temp_dir, "fixture-run", "v0.2", self.backend, self.settings)
        judge_missing(self.temp_dir, "fixture-run", "v0.2", self.backend, self.settings)

        missing_judgment = (
            self.temp_dir
            / "runs"
            / "fixture-run"
            / "judgments"
            / "v0.2"
            / "memo_budget_freeze"
            / "openai__gpt-5.3-chat"
            / "anthropic__claude-opus-4.6.json"
        )
        missing_judgment.unlink()

        summary = aggregate_run(self.temp_dir, "fixture-run")
        self.assertEqual(1, len(summary["excluded_for_insufficient_judges"]))
        self.assertEqual(2, summary["excluded_for_insufficient_judges"][0]["judge_count"])
        self.assertEqual(3, summary["excluded_for_insufficient_judges"][0]["required_judges"])

    def test_sanitize_output_strips_reasoning_traces(self) -> None:
        result = sanitize_output("<think>plan</think>\n\nThinking Process: draft it\n\nActual prose.")
        self.assertEqual("Actual prose.", result.text)
        self.assertTrue(result.changed)
        self.assertIn("think_block", result.patterns)

    def test_generation_retries_after_heavy_sanitization(self) -> None:
        calls = []
        retry_settings = dict(self.settings)
        retry_settings["generation_concurrency"] = 1

        class RetryBackend(MockBackend):
            def generate(self, model, prompt, settings):
                calls.append(dict(settings))
                if len(calls) == 1:
                    return {
                        "response_text": "<think>secret plan</think>\nVisible draft.",
                        "metadata": {"finish_reason": "stop", "usage": {"completion_tokens": 100}},
                    }
                return {
                    "response_text": "Visible draft that is safe to judge.",
                    "metadata": {"finish_reason": "stop", "usage": {"completion_tokens": 100}},
                }

        generate_missing(self.temp_dir, "fixture-run", "v0.1", RetryBackend(), retry_settings)
        output_path = (
            self.temp_dir
            / "runs"
            / "fixture-run"
            / "outputs"
            / "v0.1"
            / "memo_remote_work_policy"
            / "openai__gpt-5.4.json"
        )
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(2, payload["metadata"]["generation_attempt"])
        self.assertEqual("none", calls[1]["reasoning_effort"])

    def test_generation_does_not_quarantine_outputs_based_on_truncation_heuristics(self) -> None:
        class CapHitBackend(MockBackend):
            def generate(self, model, prompt, settings):
                payload = super().generate(model, prompt, settings)
                if model.model_id != "openai/gpt-5.4" or prompt.prompt_id != "memo_remote_work_policy":
                    return payload
                return {
                    "response_text": (
                        "This memo explains the policy shift, what teams should expect next, "
                        "and how managers should handle scheduling questions while the company "
                        "moves to the new remote-work setup "
                    )
                    * 12,
                    "metadata": {
                        "finish_reason": "length",
                        "usage": {"completion_tokens": settings["max_output_tokens"]},
                    },
                }

        generate_missing(self.temp_dir, "fixture-run", "v0.1", CapHitBackend(), self.settings)
        judge_result = judge_missing(self.temp_dir, "fixture-run", "v0.1", CapHitBackend(), self.settings)
        self.assertEqual(600, judge_result["scheduled"])

        summary = aggregate_run(self.temp_dir, "fixture-run")
        self.assertEqual(0, len(summary["quarantined_outputs"]))
        self.assertEqual(1, len(summary["exact_cap_hits"]))

    def test_model_company_uses_prefix_before_slash(self) -> None:
        self.assertEqual("openai", model_company("openai/gpt-5.4"))
        self.assertEqual("custom", model_company("custom"))

    def test_placeholders_do_not_trigger_quarantine_by_themselves(self) -> None:
        benchmark = load_benchmark_version(self.temp_dir, "v0.1")
        prompt = next(item for item in benchmark.prompts if item.prompt_id == "memo_budget_freeze")
        body = (
            "This memo explains the temporary freeze, what is affected, what is not, "
            "and which operational risks managers should raise immediately. "
        ) * 20

        output = evaluate_output(
            prompt,
            f"To: Department Heads\nDate: [Insert Date]\nStart: [Insert Start Date]\n\n{body}",
        )
        self.assertTrue(output.is_valid)

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

    def test_openrouter_retries_when_reasoning_exhausts_budget_and_visible_text_is_tiny(self) -> None:
        backend = OpenRouterBackend(api_key="test-key")
        calls = []
        responses = [
            {
                "choices": [
                    {
                        "message": {"content": "A promising title that cuts off"},
                        "finish_reason": "length",
                    }
                ],
                "usage": {
                    "completion_tokens": 496,
                    "completion_tokens_details": {"reasoning_tokens": 478},
                },
            },
            {
                "choices": [
                    {
                        "message": {"content": "A complete response with enough visible text to score." * 10},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"completion_tokens": 220, "completion_tokens_details": {"reasoning_tokens": 0}},
            },
        ]

        def fake_chat_completion(model_id, messages, settings):
            calls.append(dict(settings))
            return responses[len(calls) - 1]

        backend._chat_completion = fake_chat_completion  # type: ignore[method-assign]
        data = backend._chat_completion_with_reasoning_fallback(
            "google/gemini-3.1-pro-preview",
            [{"role": "user", "content": "test"}],
            {"reasoning_effort": "medium", "max_output_tokens": 500},
        )

        self.assertEqual(2, len(calls))
        self.assertEqual("medium", calls[0]["reasoning_effort"])
        self.assertEqual("none", calls[1]["reasoning_effort"])
        self.assertGreater(len(data["choices"][0]["message"]["content"]), 200)

    def test_extract_retry_after_seconds_from_openrouter_error(self) -> None:
        body = (
            '{"error":{"message":"Provider returned error","code":429,'
            '"metadata":{"retry_after_seconds":60}}}'
        )
        self.assertEqual(60, _extract_retry_after_seconds(body))
        self.assertIsNone(_extract_retry_after_seconds("not json"))

    def test_judge_retries_when_first_json_parse_fails(self) -> None:
        backend = OpenRouterBackend(api_key="test-key")
        calls = []
        responses = [
            {
                "choices": [
                    {
                        "message": {"content": '{"scores":{"clarity":5}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {},
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"scores":{"clarity":5,"simplicity":5,"brevity_economy":5,"structure_flow":5,"specificity_precision":5,"humanity_voice":5,"overall":5},"rationale":"ok"}'
                        },
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
        data, text, payload = backend._judge_completion_with_parse_fallback(
            "openai/gpt-5.4",
            [{"role": "user", "content": "test"}],
            {"reasoning_effort": "medium", "json_mode": True, "max_output_tokens": 500, "temperature": 0.2},
        )

        self.assertEqual(2, len(calls))
        self.assertEqual("medium", calls[0]["reasoning_effort"])
        self.assertEqual("none", calls[1]["reasoning_effort"])
        self.assertEqual(0, calls[1]["temperature"])
        self.assertEqual(1000, calls[1]["max_output_tokens"])
        self.assertEqual("ok", payload["rationale"])

    def test_judge_can_parse_json_from_reasoning_when_content_is_null(self) -> None:
        backend = OpenRouterBackend(api_key="test-key")
        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "reasoning": (
                                '{"scores":{"clarity":5,"simplicity":4,"brevity_economy":4,'
                                '"structure_flow":5,"specificity_precision":5,"humanity_voice":4,"overall":5},'
                                '"rationale":"ok from reasoning"}'
                            ),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {},
            }
        ]

        def fake_chat_completion(model_id, messages, settings):
            return responses[0]

        backend._chat_completion = fake_chat_completion  # type: ignore[method-assign]
        _, text, payload = backend._judge_completion_with_parse_fallback(
            "z-ai/glm-5",
            [{"role": "user", "content": "test"}],
            {"reasoning_effort": "medium", "json_mode": True, "max_output_tokens": 700, "temperature": 0.2},
        )

        self.assertIn('"scores"', text)
        self.assertEqual("ok from reasoning", payload["rationale"])

    def test_openrouter_request_requires_provider_parameters(self) -> None:
        backend = OpenRouterBackend(api_key="test-key")
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}],"usage":{}}'

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with mock.patch("zinsserbench.backends.urllib.request.urlopen", side_effect=fake_urlopen):
            backend._chat_completion(
                "openai/gpt-5.4",
                [{"role": "user", "content": "test"}],
                {"reasoning_effort": "medium", "max_output_tokens": 500},
            )

        self.assertEqual({"require_parameters": True}, captured["payload"]["provider"])

    def test_openrouter_retries_without_require_parameters_when_no_compatible_endpoint_exists(self) -> None:
        backend = OpenRouterBackend(api_key="test-key")
        calls = []

        def fake_urlopen(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            calls.append(payload)
            if len(calls) == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    404,
                    "Not Found",
                    hdrs=None,
                    fp=FakeHttpBody(
                        b'{"error":{"message":"No endpoints found that can handle the requested parameters.","code":404}}'
                    ),
                )
            return FakeResponseBody(b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}],"usage":{}}')

        with mock.patch("zinsserbench.backends.urllib.request.urlopen", side_effect=fake_urlopen):
            data = backend._chat_completion(
                "openai/gpt-5.4",
                [{"role": "user", "content": "test"}],
                {"reasoning_effort": "medium", "max_output_tokens": 500},
            )

        self.assertEqual(2, len(calls))
        self.assertEqual({"require_parameters": True}, calls[0]["provider"])
        self.assertEqual({"require_parameters": False}, calls[1]["provider"])
        self.assertEqual("ok", data["choices"][0]["message"]["content"])

    def _copy_tree(self, source: Path, destination: Path) -> None:
        for path in source.rglob("*"):
            relative = path.relative_to(source)
            target = destination / relative
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())

class FakeResponseBody:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


class FakeHttpBody:
    def __init__(self, body: bytes):
        self.body = body

    def read(self):
        return self.body

    def close(self):
        return None


if __name__ == "__main__":
    unittest.main()
