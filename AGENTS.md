# AGENTS.md

Repository notes for future coding agents:

- Read [TODO.md](/Users/simonsmith/Scratch/2026-03-07-zinsserbench/TODO.md) before starting substantive work.
- The benchmark uses two versioned config files:
  - `benchmark_versions/<version>/models.json` for candidate models.
  - `benchmark_versions/<version>/judges.json` for the judge panel.
- OpenRouter behavior in this repo has required defensive handling:
  - Some providers return `content: null` after spending tokens on reasoning.
  - Some providers need a retry with reasoning disabled and a larger token budget.
  - Some providers return `429` with `retry_after_seconds`; honor that instead of aborting.
- Judge calls should stay in JSON mode.
- Keep truncation detection lightweight. Do not reintroduce heuristic pre-judge truncation quarantine without strong evidence; earlier attempts created too many false positives on complete outputs with signatures, footers, or formatting artifacts. Prefer generous budgets plus post-run audits such as exact-cap-hit reporting and spot checks.
- Existing runs are resumable. Prefer resuming the same `run-name` over starting over when work is partially complete.
- Do not commit live run artifacts unless explicitly asked.
