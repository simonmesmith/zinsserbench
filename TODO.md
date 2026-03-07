# TODO

- Fix the Gemini/OpenRouter truncation failure from `2026-03-07-openrouter-v0-1`.
  - What happened: both Gemini candidate models often spent nearly the full completion budget on reasoning at `--reasoning-effort medium`, then returned only a visible fragment while still looking like a non-empty response.
  - What to do: verify the new visibility-based retry path against live OpenRouter behavior, add a short-output guard before judging, and backfill or rerun the affected Gemini generations and judgments for `v0.1`.
- After kicking off a long-running generate/judge/run command, post a short terminal progress update instead of going silent.
- Consider adding more explicit retry coverage for malformed judge JSON if JSON mode alone proves insufficient in live runs.
