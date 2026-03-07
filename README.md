# ZinsserBench

**Which AI models write the best nonfiction?**

ZinsserBench is a benchmark that tests how well language models write the kinds of nonfiction real people actually read: memos, explainers, profiles, how-to guides, opinion pieces, and personal essays. A panel of frontier AI judges scores every response on clarity, simplicity, brevity, structure, specificity, voice, and overall effectiveness.

## Scores

The most recent completed run (`2026-03-07-openrouter-v0-1-salvage-1`, benchmark version `v0.1`) tested 12 candidate models across 20 prompts. Scores are on a 1-to-5 scale. Higher is better.

![Overall scores](runs/2026-03-07-openrouter-v0-1-salvage-1/analysis/overall_scores.svg)

**Top three by overall writing quality:**

| Rank | Model | Overall |
| ---: | --- | ---: |
| 1 | google/gemini-3.1-pro-preview | 4.92 |
| 2 | google/gemini-3.1-flash-lite-preview | 4.65 |
| 3 | openai/gpt-5.3-chat | 4.30 |

Full results are in the [detailed report](runs/2026-03-07-openrouter-v0-1-salvage-1/analysis/REPORT.md).

### Judge agreement

ZinsserBench also measures how closely each judge matches the rest of the panel. In this run, `google/gemini-3.1-pro-preview` had the highest agreement, ahead of `openai/gpt-5.4` and `anthropic/claude-opus-4.6`.

![Judge quality](runs/2026-03-07-openrouter-v0-1-salvage-1/analysis/judge_quality.svg)

### Caveats for this run

This is an early `v0.1` run using OpenRouter with `--reasoning-effort medium`. Treat the results as directional, not definitive.

- **Salvaged from the original run.** This leaderboard comes from `2026-03-07-openrouter-v0-1-salvage-1`, a repaired copy of the original OpenRouter run. The salvage run kept valid outputs, regenerated contaminated ones, removed judge identity leakage, and re-judged the full run under one consistent method.
- **A few outputs are still excluded.** Three candidate outputs were quarantined because they were visibly cut off and too short to score fairly. A [response-length audit](runs/2026-03-07-openrouter-v0-1-salvage-1/analysis/response_lengths_by_model.csv) and [quarantine table](runs/2026-03-07-openrouter-v0-1-salvage-1/analysis/quarantined_outputs.csv) are available.
- **Judge panel.** The panel is `openai/gpt-5.4`, `anthropic/claude-opus-4.6`, and `google/gemini-3.1-pro-preview`. Three judges is a starting point; future runs may expand the panel.
- **Prompt count.** 20 prompts across 6 categories. Enough to see patterns, not enough to claim statistical precision.

## Good nonfiction writing and William Zinsser

The benchmark is named for William Zinsser (1922-2015), journalist, editor, teacher at Yale, and author of *On Writing Well*, one of the most widely read books on the craft of nonfiction. Zinsser argued that good nonfiction should be lucid, economical, concrete, and alive on the page. Strip the clutter. Use plain words. Be specific. Sound human.

ZinsserBench does not ask models to imitate Zinsser's voice. It uses his recurring principles as a practical standard for judging modern AI writing. The rubric scores seven dimensions:

| Dimension | What it means |
| --- | --- |
| Clarity | Easy to understand on a first read |
| Simplicity | Plain, direct language without puffed-up wording |
| Brevity and economy | No wasted space, repetition, or throat-clearing |
| Structure and flow | Ideas arrive in a logical, readable order |
| Specificity and precision | Concrete details instead of vague abstraction |
| Humanity and voice | Sounds written for people, not by committee |
| Overall effectiveness | Overall nonfiction quality for the task |

The goal is not literary imitation. The goal is strong public-facing prose.

### Why nonfiction?

A great deal of real-world AI writing is nonfiction: memos, consumer explainers, civic guides, service writing, profiles, and opinion pieces. These are everyday forms that people read to understand work, institutions, money, health, policy, and one another.

Nonfiction is also where weak writing habits become obvious. Models can hide behind flourish in fiction; they have less room to hide when they need to explain, persuade, or inform plainly.

## How the benchmark works

1. ZinsserBench gives every candidate model the same set of nonfiction writing prompts.
2. The prompts cover several common forms: explainers, internal memos, profiles, practical how-to guidance, opinion writing, and personal nonfiction.
3. A separate judge panel scores every response on the rubric above.
4. The repo aggregates those scores into two headline views:
   - **Writing score** -- how well a model writes across the full benchmark.
   - **Judge quality** -- how closely a judge agrees with the rest of the panel.

This makes the benchmark useful for two questions: *Which models write the strongest nonfiction?* and *Which models are the most reliable judges of nonfiction quality?*

### Prompt design

Version `v0.1` uses 20 prompts across six categories:

| Category | Count |
| --- | ---: |
| Memo | 4 |
| Explainer | 4 |
| Profile | 3 |
| Service / how-to | 3 |
| Opinion / op-ed | 3 |
| Personal nonfiction | 3 |

Prompts are intentionally short and direct. They do not ask for Zinsser pastiche or elaborate stylistic role-play. The benchmark measures writing quality, not prompt-following on a baroque instruction set.

---

## Installation and usage

Everything below is for people who want to run ZinsserBench themselves.

### Repository layout

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

Benchmark versions are intended to be immutable. If you materially change prompts, rubric, or scoring policy, create a new version directory and rerun.

### Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or run directly from source:

```bash
PYTHONPATH=src python3 -m zinsserbench --help
```

### Configuration

Model selection is versioned:

- `benchmark_versions/<version>/models.json` -- candidate models
- `benchmark_versions/<version>/judges.json` -- judge panel

### Running a full benchmark

OpenRouter is the default backend.

```bash
cp .env.example .env
# edit .env and set OPENROUTER_API_KEY=...

zinsserbench run \
  --root . \
  --benchmark-version v0.1 \
  --run-name my-run \
  --backend openrouter \
  --generation-concurrency 4 \
  --judge-concurrency 4 \
  --reasoning-effort medium \
  --max-output-tokens 2500
```

The CLI loads `.env` and `.env.local` from `--root` on startup. Shell environment variables take precedence.

Runs are resumable. If work is partially complete, reuse the same `--run-name`.

### Salvaging a run

If a run is partly valid but contaminated by provider failures, copy it to a new run name before repairing it.

```bash
cp -R runs/old-run runs/new-run
```

Then remove the bad outputs and stale judgments from `runs/new-run/`, keeping unaffected outputs in place. Resume with the same benchmark version and a fresh `--run-name` pointed at the copied directory. ZinsserBench will regenerate only the missing artifacts.

### Running stages separately

Each stage skips artifacts that already exist.

```bash
zinsserbench generate --root . --benchmark-version v0.1 --run-name my-run --backend openrouter
zinsserbench judge    --root . --benchmark-version v0.1 --run-name my-run --backend openrouter
zinsserbench analyze  --root . --run-name my-run
```

### OpenRouter handling

The repo includes defensive handling for provider quirks observed in live runs:

- Some providers return `content: null` after spending tokens on reasoning.
- Some providers need a retry with reasoning disabled and a larger token budget.
- `429` responses with `retry_after_seconds` are honored, not treated as fatal.
- OpenRouter requests require provider parameter support so routing does not silently ignore requested controls.
- Judge calls stay in JSON mode.

When OpenRouter supports reasoning controls for a model, ZinsserBench sends reasoning effort while excluding returned reasoning blocks by default.

### Analysis outputs

After a run, `runs/<run_name>/analysis/` contains:

- `REPORT.md` -- human-readable summary
- `summary.json`
- `quarantined_outputs.csv`
- `response_lengths_by_model.csv`
- `writing_by_model.csv` -- the leaderboard
- `writing_by_model_axis.csv`, `writing_by_model_category.csv`, `writing_by_model_prompt.csv`
- `writing_by_prompt_axis.csv`
- `judge_quality.csv`
- `model_prompt_details.csv` -- the main drill-down table for a specific model + prompt
- Headline SVG charts with adaptive left margins for long model names and source attribution

### Testing

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
