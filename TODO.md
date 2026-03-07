# TODO

## Blocking — fix before the next scored run

These issues mean current scores mostly reflect infrastructure problems, not writing quality.

- **Re-run all models at `max_output_tokens: 10000`.** The salvage run's leaderboard is misleading because the Gemini outputs were regenerated *after* the token cap was raised, while other models (Claude, GPT, etc.) were generated earlier with the old low cap still in place. This isn't a bug to investigate — it's a known sequencing issue. The fix is a clean run from scratch with a generous cap. Use 10,000 tokens: prioritizing completion is more important than token efficiency, and no model should be truncated for infrastructure reasons.
- **Add a post-generation truncation check.** After generation, compare each output's `completion_tokens` against the manifest's `max_output_tokens`. Flag any output where tokens used equals the cap exactly (strong truncation signal). Log a warning during the run and include it in the analysis report. Consider auto-quarantining or regenerating with a higher budget.
- **Strip thinking traces and non-prose output.** Qwen 3.5 leaked `<think>` blocks into roughly half its outputs despite `exclude_reasoning: true`. Add a post-generation sanitizer that strips known reasoning-trace patterns (`<think>...</think>`, `<reasoning>...</reasoning>`, etc.) before the output goes to judges. If stripping removes more than ~10% of the output, flag it for review.
- **Detect and handle truncated outputs before judging.** Add a truncation detector that catches outputs ending mid-sentence, mid-word, or with obvious cut-off patterns. Options: (a) quarantine and regenerate with a higher token budget, (b) flag for judges with explicit context that the piece is incomplete, or (c) score but annotate in analysis. Currently judges penalize truncation inconsistently — some dock heavily, others ignore it.
- **Remove same-company judging bias.** Do not let a judge score outputs from the same OpenRouter company prefix (for example `google/...` should not judge `google/...`, and `openai/...` should not judge `openai/...`). Current bias: Claude judge +0.65 for own company, Gemini judge +0.33.

## Next

- Add progress feedback to the terminal so we can monitor run progress easily there
- Tomorrow, start a brand-new clean scored run with the updated pipeline and `max_output_tokens: 10000`; once that run is complete, remove the preliminary-results disclaimer from `README.md`.

## Future

- Expand the judge panel from 3 to 5 once pipeline reliability is stable.
- Add a more standard judge inter-rater metric alongside the current custom agreement score.
- Run a controlled reasoning-effort comparison after the salvage path is stable.
- Increase number of prompts to give results more rigor
- Add more explicit retry coverage for malformed judge JSON if JSON mode alone proves insufficient in live runs
