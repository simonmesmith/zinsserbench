# TODO

## Current

- Add better terminal progress feedback during long generation and judging runs so live monitoring does not depend on manual file counting.
- For `v0.3`, switch judge calls to `reasoning_effort: none` and raise the judge token budget substantially, likely from `700` to at least `1200-1400`. Reason: in the current `v0.2` run, successful judge calls are spending a large share of completion budget on reasoning tokens, especially `z-ai/glm-5` at about `554 / 644` on average, with `google/gemini-3.1-pro-preview` around `304 / 440` and `openai/gpt-5.4` around `150 / 267`. This should improve reliability and cost with little to no meaningful effect on judgment quality. If this change is made, version it as `v0.3` and explain that rationale in the docs/report.

## Later

- Add a more standard judge inter-rater metric alongside the current custom agreement score.
- Increase the number of prompts to give results more rigor.
- Add more explicit retry coverage for malformed judge JSON if JSON mode alone proves insufficient in live runs.
