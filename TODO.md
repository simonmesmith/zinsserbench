# TODO

## Immediate

- Create the salvage copy `2026-03-07-openrouter-v0-1-salvage-1` from `2026-03-07-openrouter-v0-1` and keep the original run untouched.
- Remove bad outputs from the salvage run:
  - all Gemini candidate outputs
  - clearly truncated or placeholder outputs for Kimi K2.5 and GPT-5.4
  - all existing judgments in the salvage run so blind judging can be applied consistently
- Verify the higher generation token budget (`2500`) against live OpenRouter behavior while keeping `--reasoning-effort medium` for all candidate models.
- Resume the salvage run and regenerate missing outputs, judgments, and analysis artifacts.
- After kicking off a long-running generate/judge/run command, post a short terminal progress update instead of going silent.

## Future

- Add explicit quarantine reporting for outputs that still fail quality guards after retries.
- Expand the judge panel from 3 to 5 once pipeline reliability is stable.
- Add a more standard inter-rater metric alongside the current custom agreement score.
- Run a controlled reasoning-effort comparison after the salvage path is stable.
- Increase prompt count once benchmark validity issues are fixed.
- Add more explicit retry coverage for malformed judge JSON if JSON mode alone proves insufficient in live runs.
