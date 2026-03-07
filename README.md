# ZinsserBench

ZinsserBench is a public benchmark for evaluating AI models on nonfiction writing quality and model-based judging quality. It uses a Zinsser-inspired rubric grounded in recurring principles from *On Writing Well*: clarity, simplicity, brevity, structure, specificity, and humanity.

Version `v0.1` is intentionally small and cheap enough to run as a pilot while still supporting deeper analysis across models, prompts, prompt categories, rubric elements, and judges.

## What the benchmark measures

Every enabled model in a benchmark version does one job:

1. It writes one response for every prompt.

A configured judge panel scores every model response against the rubric.

This produces two headline metrics:

- `writing score`: average rubric performance across all prompts and all judges
- `judge quality`: leave-one-out agreement with panel consensus

The stored data also supports drill-down analysis for:

- model + prompt
- model + prompt category
- model + rubric element
- prompt + rubric element
- judge model

## Repository layout

```text
benchmark_versions/<version>/
  prompts.json
  rubric.json
  models.json
  judges.json

runs/<run_name>/
  manifest.json
  outputs/
  judgments/
  analysis/
```

Benchmark versions are immutable. If prompts, rubric, or scoring policy change in a material way, create a new version directory and rerun the full matrix for that version.

## Prompt taxonomy

Each prompt has a required category so results can be analyzed by nonfiction form:

- `memo`
- `explain`
- `profile`
- `service_howto`
- `persuasion_oped`
- `personal_nonfiction`

Prompts are short and direct by design. They do not ask models to imitate Zinsser or to follow elaborate stylistic instructions.

## Rubric

Each judgment contains scores from `1` to `5` for:

- `clarity`
- `simplicity`
- `brevity_economy`
- `structure_flow`
- `specificity_precision`
- `humanity_voice`
- `overall`

## Running the benchmark

OpenRouter is the default backend for real runs.

```bash
cp .env.example .env
# then edit .env and set OPENROUTER_API_KEY=...
python3 -m zinsserbench run \
  --root . \
  --benchmark-version v0.1 \
  --run-name 2026-03-07-v0-1 \
  --backend openrouter \
  --generation-concurrency 4 \
  --judge-concurrency 4 \
  --reasoning-effort medium \
  --max-output-tokens 500
```

On startup, the CLI loads `.env` and `.env.local` from `--root` if present. Existing shell environment variables still take precedence, so a one-off `export OPENROUTER_API_KEY=...` overrides the file for that session.

Judge selection is versioned in `benchmark_versions/<version>/judges.json`. For `v0.1`, the lite panel is:

- `openai/gpt-5.4`
- `anthropic/claude-opus-4.6`
- `google/gemini-3.1-pro-preview`

You can also run stages separately. Each stage is resumable and skips any artifact that already exists.

```bash
python3 -m zinsserbench generate --root . --benchmark-version v0.1 --run-name 2026-03-07-v0-1 --backend openrouter
python3 -m zinsserbench judge --root . --benchmark-version v0.1 --run-name 2026-03-07-v0-1 --backend openrouter
python3 -m zinsserbench analyze --root . --run-name 2026-03-07-v0-1
```

When OpenRouter supports reasoning controls for a model, ZinsserBench sends `reasoning: { "effort": "medium", "exclude": true }` by default. This keeps the requested reasoning level consistent across supported models while avoiding returned reasoning blocks in stored artifacts. Models that do not support the parameter simply ignore it.

## v0.1 models

- `openai/gpt-5.4`
- `openai/gpt-5.3-chat`
- `google/gemini-3.1-flash-lite-preview`
- `google/gemini-3.1-pro-preview`
- `anthropic/claude-sonnet-4.6`
- `anthropic/claude-opus-4.6`
- `x-ai/grok-4.1-fast`
- `z-ai/glm-5`
- `deepseek/deepseek-v3.2`
- `moonshotai/kimi-k2.5`
- `qwen/qwen3.5-35b-a3b`
- `minimax/minimax-m2.5`

## Example run in this repo

This repository includes a committed example run created with the built-in `mock` backend so the artifact layout, reports, and charts are inspectable without API access. Replace it with a live OpenRouter run when you are ready to publish benchmark results.

Latest example report: [runs/example-v0-1-12-models/analysis/REPORT.md](/Users/simonsmith/Scratch/2026-03-07-zinsserbench/runs/example-v0-1-12-models/analysis/REPORT.md)

Latest example charts:

![Overall scores](/Users/simonsmith/Scratch/2026-03-07-zinsserbench/runs/example-v0-1-12-models/analysis/overall_scores.svg)

![Judge quality](/Users/simonsmith/Scratch/2026-03-07-zinsserbench/runs/example-v0-1-12-models/analysis/judge_quality.svg)

## Outputs and analysis

For each run, `runs/<run_name>/analysis/` contains:

- `summary.json`
- `REPORT.md`
- `writing_by_model.csv`
- `writing_by_model_axis.csv`
- `writing_by_model_category.csv`
- `writing_by_model_prompt.csv`
- `writing_by_prompt_axis.csv`
- `judge_quality.csv`
- `model_prompt_details.csv`
- SVG charts for headline metrics

`model_prompt_details.csv` is the key drill-down table for inspecting an individual model/prompt pair alongside its aggregated rubric scores.

## Testing

The test suite uses the standard library only.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
