---
layout: default
title: "ZinsserBench Qualitative Analysis: 2026-03-08-openrouter-v0-2-clean-3"
---

# The first clean v0.2 run: much more believable, still too compressed at the top

**Run:** `2026-03-08-openrouter-v0-2-clean-3` · **Benchmark version:** `v0.2` · **Models:** 12 candidates, 4 judges · **Prompts:** 20 across 6 categories

This is the first run in this repo that looks clean enough to take seriously as a writing benchmark rather than as a provider-debugging exercise. There were `0` quarantined outputs, `0` truncation warnings, only `6` light sanitization events, and same-company judgments were excluded before scoring. That is a major improvement over the salvage-era runs.

The harder truth is that the benchmark is now running into a different problem: **ceiling effects**. The field is tightly packed, the judges are often generous on the `overall` axis, and the top of the table is more crowded than the raw ranks suggest.

## The official leaderboard

| Rank | Model | Official overall |
| ---: | --- | ---: |
| 1 | anthropic/claude-sonnet-4.6 | 5.0000 |
| 2 | moonshotai/kimi-k2.5 | 4.9750 |
| 3 | anthropic/claude-opus-4.6 | 4.9667 |
| 4 | google/gemini-3.1-pro-preview | 4.9333 |
| 5 | openai/gpt-5.4 | 4.8500 |
| 6 | z-ai/glm-5 | 4.8500 |
| 7 | openai/gpt-5.3-chat | 4.8333 |
| 8 | deepseek/deepseek-v3.2 | 4.8125 |
| 9 | google/gemini-3.1-flash-lite-preview | 4.7167 |
| 10 | minimax/minimax-m2.5 | 4.7125 |
| 11 | x-ai/grok-4.1-fast | 4.6500 |
| 12 | qwen/qwen3.5-35b-a3b | 4.2375 |

One important technical note: the leaderboard's `overall` column is the mean of the judges' **overall effectiveness** score, not the arithmetic mean of all seven rubric axes. That matters a lot in this run.

## 1. How to interpret the results

### This run is directionally reliable

Compared with the earlier runs, the basic setup is much better:

- same-company judgments were skipped, removing the most obvious self-family bias channel
- judges no longer see the candidate model label in the prompt
- there were no truncated or quarantined outputs in the final analysis
- the only sanitization was Qwen leaking a small thinking prefix on `6` prompts, with very small removed ratios

So the run is telling us something real about the models' writing. It is not just measuring truncation anymore.

### But the exact top ranking is not reliable

The top of the table is too compressed to read literally.

Using prompt-level `overall effectiveness` scores, the top seven models are packed into a band from `4.6833` to `4.8381`. Adjacent gaps are tiny:

- Sonnet vs Opus: `0.0262`
- Opus vs Kimi: `0.0101`
- Kimi vs GPT-5.3 Chat: `0.0089`
- GPT-5.4 vs Gemini Pro: `0.0024`

Those gaps are smaller than the prompt-level noise. In paired prompt comparisons, every adjacent top-model gap has an approximate 95% interval that crosses zero. In plain English: **the run does not justify strong claims that the top few models are meaningfully different from one another**.

The one separation that does look real is at the bottom. `qwen/qwen3.5-35b-a3b` is clearly below the pack because it had multiple genuinely bad outputs, not just slightly weaker ones.

### The benchmark is hitting a ceiling

The strongest evidence:

- `81.6%` of all raw `overall` judgments were `5`
- `97.6%` of all raw `clarity` judgments were `5`
- `96.6%` of all raw `structure_flow` judgments were `5`

That means the benchmark currently has much more room to discriminate on **brevity**, **simplicity**, **specificity**, and **voice** than on clarity or structure. In this run, clarity is basically solved, and structure is close to solved for most top models.

### Were models penalized for artifacts rather than writing?

Mostly, no, with two exceptions.

First, **placeholder/template behavior** did hurt models somewhat. Outputs containing obvious placeholders averaged `4.64` overall versus `4.82` for outputs without placeholders. That looks like a real penalty, but it is also a fair one. A memo with `[Insert Date]` or `[Hospital Name]` is less finished and less believable than one with concrete details.

Second, **Qwen's reasoning leakage** definitely hurt it. Six outputs needed light sanitization before judging, and several low-scoring Qwen pieces still read like planning notes or partially converted outlines. That is not a mere formatting nit. It is a real failure mode for this benchmark.

Other formatting choices seem much less important:

- markdown headings were common and not penalized overall
- bullet lists were essentially neutral on average

So the judges do not appear to be punishing "markdown-looking output" in general. They are mostly reacting to whether the piece feels finished, specific, and reader-facing.

### How did Claude Sonnet 4.6 get a perfect score?

Not by getting perfect scores on every axis. It got a perfect score because the **three non-Anthropic judges gave it `overall = 5` on all 20 prompts**, for `60/60` raw `overall` judgments.

At the same time, those same judges still knocked Sonnet down on sub-axes:

- `brevity_economy` fell to `4` or `3` many times
- `simplicity` fell to `4` or `3` several times
- `humanity_voice` was occasionally a `4`

So Sonnet did not produce literally flawless prose. What happened is that the judges treated "excellent but a bit wordy" as still deserving a `5` on holistic overall effectiveness. That is the ceiling problem in one example.

## 2. What actually separated the top models from the weaker ones

The main differentiators in this run were not grammar or basic coherence. Almost everyone has those.

They were:

1. **Economy.** The widest average prompt-level spread across models was on `brevity_economy` (`1.63` points), by far the most discriminating axis.
2. **Simplicity.** The next biggest separator was plainness versus puffed-up wording.
3. **Specificity and voice.** The better models used concrete examples, plausible situational detail, and a tone that felt written for an actual reader.
4. **Finished-document behavior.** Models lost ground when they wrote templates instead of completed documents, leaked reasoning, or padded pieces far beyond the requested length.

The category pattern is also revealing:

- **Profiles** were the least differentiating category. Almost everyone was good there.
- **Service/how-to** was also tightly clustered at the top.
- **Memos** and **personal nonfiction** produced the largest spreads and were the most useful discriminators.

That makes sense. Profiles and explainers are familiar, high-prior genres. Memos and personal essays expose whether a model can sound specific, credible, and human without falling into template-speak.

## 3. Strengths, weaknesses, and prompting advice by model

| Model | Strengths | Weaknesses | Prompt strategy |
| --- | --- | --- | --- |
| anthropic/claude-sonnet-4.6 | Extremely consistent; strong across every category; very high clarity, structure, and specificity; finished documents with few visible artifacts. | Mild tendency toward over-explaining and smoothing everything into polished prose; some loss on brevity and simplicity. | Ask for a hard length cap and a plainspoken register: "keep it tight, cut throat-clearing, prefer short sentences, no generic intro." |
| anthropic/claude-opus-4.6 | Richest voice in the field; excellent explainers, profiles, and op-eds; concrete openings and strong narrative control. | Most overlong model in the run; service/how-to pieces can become elaborate and heavier than needed. | Constrain scope aggressively: "450 words max, practical over comprehensive, no long preamble, prioritize the 3-5 most useful points." |
| moonshotai/kimi-k2.5 | Near-top performance across almost everything; especially strong on explainers, memos, and op-eds; usually sounds finished and confident. | Can run long; service/how-to pieces become procedural and bulky; some simplicity drift. | Ask for "plain English, fewer steps, shorter paragraphs, one concrete example rather than exhaustive coverage." |
| google/gemini-3.1-pro-preview | Highly reliable; excellent on memos and service writing; clear, well-organized, and usually complete. | Slightly generic compared with the top Anthropic models; op-eds can feel competent rather than vivid; brevity is a real issue. | Push for specificity and voice: "open with one concrete scene or example, avoid generic framing, don't restate the prompt." |
| openai/gpt-5.4 | Strong personal nonfiction and profiles; polished explainers; broad competence. | Wordiest OpenAI model here; memo writing often slips into HR-template language and placeholders; Opus judged it notably harsher than the rest of the panel did. | For workplace writing, say "write a completed memo, not a template; invent realistic specifics; no placeholders; under 350 words." |
| z-ai/glm-5 | Very reliable judge and strong writer; good service/how-to and profiles; usually concrete and easy to follow. | Can read procedural or managerial; memos are its weakest area; brevity and voice lag the leaders. | Add audience framing and tone: "write to a real employee/homeowner/parent, not as a formal report; use one vivid concrete detail." |
| openai/gpt-5.3-chat | Best concision balance among the top group; strong personal nonfiction and profiles; usually avoids overbuilding the document. | Less distinctive voice than the Anthropic leaders; some memo outputs still look templated; can undershoot emotional vividness. | Lean into its strengths: "be direct, specific, and slightly conversational; avoid placeholders; favor concrete nouns over abstractions." |
| deepseek/deepseek-v3.2 | Strong service/how-to and personal nonfiction; often clear, useful, and surprisingly warm. | Weaker op-eds and some profiles; simplicity drifts into puffier wording; specificity is less reliable than the top tier. | Ask it to argue through examples: "use 2-3 concrete observations, avoid grand claims, keep language plain, cut moralizing." |
| google/gemini-3.1-flash-lite-preview | Good service/how-to and explainers; clear structure; generally competent. | More generic and template-prone than Gemini Pro; weakest category is op-ed; more placeholder behavior and thinner voice. | Keep tasks narrow and utilitarian: "write a completed final document with specific details, no placeholders, no corporate phrasing." |
| minimax/minimax-m2.5 | Solid explainers and some service writing; can produce clear, organized prose when constrained. | Memos are a clear weakness; often template-shaped with brackets and formal memo scaffolding; middling specificity and voice. | Give it anti-template instructions: "do not use brackets, do not write a form, fill in plausible details, make this sound like an actual memo sent today." |
| x-ai/grok-4.1-fast | Good memos and some strong explainers; high structural competence; can write energetic prose. | Personal nonfiction is its weak spot; voice can become showy or overeager; some placeholder/template behavior. | Ask for restraint: "write in a calm, observant tone; avoid punchlines and verbal flourish; keep metaphors minimal and precise." |
| qwen/qwen3.5-35b-a3b | When it actually writes the piece, it can be perfectly respectable, especially on explainers and some profiles. | Clear lowest performer because of reasoning leakage, outline-like starts, and very weak brevity on failed prompts; personal nonfiction was especially poor. | First priority is defensive prompting: "respond only with the final piece, no analysis, no outline, no planning notes." Also keep genre demands simple and concrete. |

## 4. What I think the benchmark learned about these models

The top group is not separated by raw capability so much as by **default writing habits**.

- Anthropic's models sound the most like polished magazine or feature prose.
- OpenAI's models are strong but split: `gpt-5.3-chat` is tighter; `gpt-5.4` is grander and more template-prone in workplace writing.
- Gemini Pro is dependable and structurally disciplined, but less distinctive.
- GLM-5 and DeepSeek are competitive in practical nonfiction, especially when the task rewards clarity over flair.
- Kimi belongs in the top conversation.
- Qwen is the only model whose benchmark result is still dominated by a non-writing failure mode.

That is useful. It means the benchmark is now mostly measuring writing style and document behavior, not infrastructure bugs, except for Qwen.

## 5. A few extra things worth noticing

### The judge panel is still compressing the field

Agreement scores are decent, but the judges are not equally severe.

- `google/gemini-3.1-pro-preview` had mean raw `overall` score `4.93`
- `z-ai/glm-5` had mean raw `overall` score `4.95`
- `openai/gpt-5.4` had mean raw `overall` score `4.65`
- `anthropic/claude-opus-4.6` had mean raw `overall` score `4.58`

So Gemini Pro and GLM-5 are not just "high-agreement" judges. They are also very generous judges. Opus is both the harshest and the least agreeable judge. That does not make any of them wrong, but it does help explain why the top end is so full of 5s.

### The target lengths are not being enforced strongly enough

Several top models blew well past the requested ranges and still kept near-perfect `overall` scores.

- Claude Opus averaged about `2.79x` the target upper bound
- Claude Sonnet averaged about `2.02x`
- GPT-5.4 averaged about `2.29x`

The judges *did* penalize brevity, but not enough for those penalties to move the headline ranking much. If the benchmark really cares about Zinsser-style economy, it probably needs either stricter prompt compliance scoring or explicit length normalization in analysis.

### The most useful prompts are not the ones I expected

Profiles turned out to be easy for almost everyone. The best discriminators were:

- `memo_incident_response`
- `memo_remote_work_policy`
- `personal_night_shift_bus`
- `personal_public_pool`

Those prompts expose whether a model can sound like a person or a real institution instead of a generic writing engine.

## Bottom line

This run is the first one that looks trustworthy enough to learn from. It tells us that the current frontier models are all very good at baseline nonfiction, that `qwen/qwen3.5-35b-a3b` still has a serious output-format failure mode, and that the rest of the field is separated mostly by concision, specificity, and voice.

It does **not** tell us that Claude Sonnet 4.6 is definitively better than Claude Opus 4.6, Kimi K2.5, Gemini Pro, GPT-5.4, GLM-5, or GPT-5.3 Chat in a statistically strong sense. The top of the leaderboard is too compressed for that.

So my read is:

- trust the **tiers**
- trust the **qualitative strengths and weaknesses**
- trust the conclusion that this benchmark is now mostly measuring writing rather than truncation
- do **not** over-trust the exact ordering of the top models
