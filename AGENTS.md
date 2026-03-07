# AGENTS.md

Repository notes for future coding agents:

- Read [TODO.md](/Users/simonsmith/Scratch/2026-03-07-zinsserbench/TODO.md) before starting substantive work.
- The benchmark uses two versioned config files:
  - `benchmark_versions/<version>/models.json` for candidate models.
  - `benchmark_versions/<version>/judges.json` for the judge panel.
- Current `v0.1` judge panel is intentionally lite: `openai/gpt-5.4`, `anthropic/claude-opus-4.6`, `google/gemini-3.1-pro-preview`.
- OpenRouter behavior in this repo has required defensive handling:
  - Some providers return `content: null` after spending tokens on reasoning.
  - Some providers need a retry with reasoning disabled and a larger token budget.
  - Some providers return `429` with `retry_after_seconds`; honor that instead of aborting.
- Judge calls should stay in JSON mode.
- Existing runs are resumable. Prefer resuming the same `run-name` over starting over when work is partially complete.
- Do not commit live run artifacts unless explicitly asked.
