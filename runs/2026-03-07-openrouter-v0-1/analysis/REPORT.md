# ZinsserBench Report: 2026-03-07-openrouter-v0-1

- Benchmark version: `v0.1`
- Models evaluated: `12`

## Overall writing leaderboard

| candidate_model_id | overall | clarity | simplicity | structure_flow |
| --- | --- | --- | --- | --- |
| openai/gpt-5.3-chat | 4.1833 | 4.8333 | 4.7667 | 4.3 |
| z-ai/glm-5 | 4.05 | 4.7333 | 4.3833 | 4.1833 |
| anthropic/claude-opus-4.6 | 4.025 | 4.7417 | 4.5667 | 3.9833 |
| anthropic/claude-sonnet-4.6 | 3.8333 | 4.6667 | 4.5667 | 3.85 |
| x-ai/grok-4.1-fast | 3.7917 | 4.625 | 4.0333 | 3.7167 |
| deepseek/deepseek-v3.2 | 3.7 | 4.6167 | 4.25 | 3.7667 |
| minimax/minimax-m2.5 | 3.5167 | 4.55 | 4.5167 | 3.7 |
| openai/gpt-5.4 | 3.5167 | 4.575 | 4.6333 | 3.5333 |
| moonshotai/kimi-k2.5 | 3.1 | 4.1833 | 4.1167 | 3.1333 |
| qwen/qwen3.5-35b-a3b | 2.5333 | 3.2667 | 3.1 | 2.6333 |
| google/gemini-3.1-flash-lite-preview | 1.0667 | 1.8833 | 2.6333 | 1.1333 |
| google/gemini-3.1-pro-preview | 1.05 | 1.3 | 1.9833 | 1.0167 |

## Judge quality leaderboard

| judge_model_id | agreement_overall | agreement_clarity | agreement_structure_flow |
| --- | --- | --- | --- |
| google/gemini-3.1-pro-preview | 0.6752 | 0.7237 | 0.7248 |
| openai/gpt-5.4 | 0.6732 | 0.6068 | 0.5667 |
| anthropic/claude-opus-4.6 | 0.5919 | 0.7018 | 0.5473 |

## Analysis files

- `writing_by_model.csv`
- `writing_by_model_axis.csv`
- `writing_by_model_category.csv`
- `writing_by_model_prompt.csv`
- `writing_by_prompt_axis.csv`
- `judge_quality.csv`
- `model_prompt_details.csv`

## Charts

![Overall scores](overall_scores.svg)

![Judge quality](judge_quality.svg)
