---
layout: default
title: "ZinsserBench Qualitative Analysis: 2026-03-07-openrouter-v0-1-salvage-1"
---

# The salvage run: what fixed Gemini, what broke everyone else, and what we actually learned about writing

**Run:** `2026-03-07-openrouter-v0-1-salvage-1` · **Benchmark version:** `v0.1` · **Models:** 12 candidates, 3 judges · **Prompts:** 20 across 6 categories

This is the follow-up run. The first run had a catastrophic Gemini truncation bug: both Gemini models spent their token budget on internal reasoning and returned nearly nothing, landing at the bottom with overall scores of 1.05 and 1.07. The salvage run fixed that. It also changed the landscape completely.

---

## The new leaderboard

| Rank | Model | Overall | Clarity | Simplicity | Structure |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Gemini 3.1 Pro | 4.92 | 5.00 | 4.28 | 5.00 |
| 2 | Gemini 3.1 Flash Lite | 4.65 | 4.98 | 4.18 | 5.00 |
| 3 | GPT-5.3 Chat | 4.30 | 4.80 | 4.82 | 4.25 |
| 4 | Kimi K2.5 | 4.26 | 4.79 | 4.28 | 4.32 |
| 5 | GLM-5 | 4.19 | 4.79 | 4.42 | 4.30 |
| 6 | Claude Opus 4.6 | 3.95 | 4.67 | 4.48 | 3.85 |
| 7 | Claude Sonnet 4.6 | 3.88 | 4.68 | 4.58 | 3.87 |
| 8 | Grok 4.1 Fast | 3.87 | 4.72 | 4.02 | 3.90 |
| 9 | DeepSeek V3.2 | 3.80 | 4.65 | 4.32 | 3.95 |
| 10 | GPT-5.4 | 3.80 | 4.63 | 4.68 | 3.72 |
| 11 | MiniMax M2.5 | 3.72 | 4.61 | 4.54 | 3.86 |
| 12 | Qwen 3.5 35B | 2.53 | 3.25 | 3.22 | 2.62 |

The story that jumps off the page: Gemini 3.1 Pro went from dead last (1.05) to a near-perfect first place (4.92). Gemini Flash Lite went from 11th (1.07) to 2nd (4.65). Meanwhile, the middle of the pack barely moved. Claude Opus went from 4.03 to 3.95. GPT-5.4 went from 3.52 to 3.80. The salvage run didn't change the benchmark's conclusions about most models. It revealed that the first run's conclusions about Gemini were completely wrong.

---

## 1. The dominant story: this is a truncation benchmark

The single most important finding in this run is that **truncation is the primary determinant of scores for most models, and writing quality is secondary.**

Here are the completion token counts and truncation rates:

| Model | Avg Tokens | % Truncated | Overall Score |
| --- | ---: | ---: | ---: |
| Gemini 3.1 Pro | 1,604 | 5% | 4.92 |
| Gemini Flash Lite | 1,308 | 10% | 4.65 |
| Kimi K2.5 | 1,005 | 55% | 4.26 |
| GLM-5 | 1,292 | 60% | 4.19 |
| Grok 4.1 Fast | 800 | 80% | 3.87 |
| DeepSeek V3.2 | 652 | 70% | 3.80 |
| MiniMax M2.5 | 564 | 85% | 3.72 |
| GPT-5.3 Chat | 464 | 60% | 4.30 |
| Claude Opus 4.6 | 500 | 80% | 3.95 |
| Claude Sonnet 4.6 | 500 | 95% | 3.88 |
| GPT-5.4 | 678 | 90% | 3.80 |
| Qwen 3.5 35B | 1,089 | 85% | 2.53 |

The manifest says `max_output_tokens: 2500`, but something is capping many models far below that. Claude Opus and Sonnet both hit exactly 500 tokens on every single output—all 20 prompts, no variation. That's not a coincidence; that's a hard cap somewhere in the pipeline, likely an OpenRouter default or a model-specific override that's not respecting the 2500-token setting. GPT-5.4 similarly hits 500 tokens on 18 of 20 prompts.

Gemini Pro, by contrast, averages 1,604 tokens and never hits a wall. It has room to finish its thoughts. It uses 1,978 tokens at most, well under the 2500-token budget. It simply writes complete pieces.

The score penalty for truncation is substantial: across all models and prompts, clean (non-truncated) outputs average **4.54**, while truncated outputs average **4.11**. That's a 0.43-point gap. For some models the penalty is even worse: GPT-5.4's clean outputs average 4.83, but its truncated outputs average 4.18—a 0.65-point penalty. Kimi K2.5 shows a 0.61-point penalty.

This means the leaderboard is not primarily measuring writing quality. It's measuring which models happened to get enough tokens to finish their pieces.

---

## 2. Why Gemini scored near-perfect (and why it's partly real and partly artifact)

Gemini 3.1 Pro scored 4.92 overall, with perfect 5.0 on both clarity and structure. That sounds absurdly high. Let me break down why.

### The real part: Gemini writes well

When Gemini Pro has room to write, it produces genuinely strong nonfiction. Its union job essay opens with "I spent my twenties in a state of perpetual hustle, which is just a polite, modern word for desperation"—a line that's vivid, personal, and immediately establishes voice. Its food recall explainer uses a concrete scene (a phone alert about spinach in your crisper) to hook the reader before delivering information. Its op-eds maintain a consistent argumentative throughline from opening to close.

Gemini's structural advantage shows clearly in the data. Every other top model loses points when pieces get cut off mid-argument or mid-paragraph. Gemini almost never does, because it gets enough tokens to land its endings. Structure scores depend heavily on whether a piece has a proper conclusion, and Gemini almost always does.

### The artifact part: three compounding advantages

Gemini Pro benefits from three things that aren't about writing quality:

**First, it finishes its pieces.** Only 1 of its 20 outputs shows any sign of truncation. Compare that to Claude Opus (16 of 20 truncated) or GPT-5.4 (18 of 20 truncated). When judges see an incomplete piece, they dock structure, flow, and overall scores regardless of how good the existing writing is. This alone accounts for much of Gemini's lead.

**Second, it judges itself.** Gemini 3.1 Pro is simultaneously a candidate and a judge. When judging its own family's outputs, it gives perfect 5.0 scores across the board—every single prompt, for both Gemini Pro and Gemini Flash Lite. The Gemini judge gave its own family a mean of 5.00; the other two judges gave Gemini's family a mean of 4.67. That's a +0.33 self-family bias, and since each judge is one-third of the panel, it inflates the final score by about 0.11 points.

For comparison, Claude Opus has a larger self-family bias (+0.65), but since it's judging truncated outputs from Claude models, the bias doesn't help as much—it just slightly reduces the truncation penalty.

**Third, the complete-output advantage compounds with judge scoring tendencies.** Judges are more unanimous on Gemini's outputs than on anyone else's. The average standard deviation of judge scores for Gemini Pro is just 0.14 (on a 1-5 scale). For Claude Opus it's 0.61. For GPT-5.4 it's 0.47. When a piece is clearly complete and clearly competent, judges converge. When a piece is truncated, judges disagree about how much to penalize it. Gemini benefits from both the direct score boost and the reduced scoring variance.

### What Gemini's true score probably is

If you took only the non-truncated outputs from all models, Gemini Pro's advantage would shrink substantially. Its clean outputs average 4.71. For comparison, GPT-5.4's clean outputs average 4.83, Kimi K2.5's average 4.80, and MiniMax M2.5's average 4.67. In a fair race where every model gets enough tokens to finish, Gemini Pro would likely still be excellent—but it wouldn't be running away with the benchmark by a full point.

---

## 3. What actually differentiates high-quality from low-quality output

Setting aside truncation artifacts, the qualitative differences between strong and weak writing are visible in the actual text.

### Top-tier writing opens with a scene or a hook

Gemini Pro's food recall explainer doesn't start with "A food recall is a process by which..." It starts with "You are about to make dinner when a news alert pops up on your phone." GPT-5.3 Chat's union job essay opens with sensory detail: "I remember the smell first: coffee that had been sitting on a burner too long, machine oil, and the faint dust of old concrete." These openings pull the reader into a situation before delivering information.

By contrast, Claude Opus's food recall explainer begins: "A food recall is a voluntary or mandated action in which a product is pulled from store shelves." That's accurate and clear, but it reads like a Wikipedia lead. The information is the same; the craft is different.

### Structure means more than headers

GPT-5.3 Chat's memo about a shift schedule change demonstrates something subtle. It's short (184 words), direct, and reads like an actual memo a real operations manager would send. It has a clear "here's what's changing" section and a brief "here's what to do" close. No markdown headers, no bullet-point hierarchies—just clean prose organized by function.

GPT-5.4's version of the same memo is longer and more visually organized with markdown headers ("Effective Dates," "Updated Shift Schedule," "What This Means," "Why We Are Making This Change"). It looks more structured on the page, but it reads like a template: it has `[Insert Date]` placeholders and generic language. The judges scored GPT-5.3's version at 4.86 and GPT-5.4's at 4.05. The smaller model wrote a more *real* document; the larger model wrote a more *corporate* one.

### Voice is what separates good from great

Among the non-truncated outputs, the models that score highest on humanity and voice tend to do two things: they vary sentence length, and they include specific, observed detail rather than generic description. Gemini Pro's union job essay has a character named Marcus with "grease permanently tattooed into the creases of his knuckles." GPT-5.3's version has a character named Raul with "a gray beard tucked into his collar and a union patch sewn onto his jacket sleeve." Both are specific enough to feel authored rather than generated.

The models that score lower on voice tend to rely on abstract claims ("The library is an essential community resource") rather than concrete scenes ("A teenager in the reference section, headphones on, working through a geometry problem at 7:30 on a Tuesday night"). The abstraction habit is the clearest marker of AI-generated prose.

---

## 4. The placeholder question: are models unfairly penalized?

Several models produced outputs with placeholder text like `[Insert Date]`, `[Company Name]`, or `[Your Name]`. This happened most often in memos, which makes sense—memos have fields that a model might reasonably leave as fill-in-the-blank.

The numbers: Grok (4 outputs with placeholders), Gemini Flash Lite (4), GPT-5.4 (3), MiniMax (3), Claude Sonnet (2), Kimi (2). The models that avoided placeholders entirely: Claude Opus, GPT-5.3 Chat (both invented specific details instead).

Are the judges penalizing this fairly? Looking at the rationales, judges do mention placeholders but don't generally destroy a score over them. MiniMax's incident response memo, which was essentially a template with bracketed placeholders throughout, got a 3.19—a noticeable penalty, but not a 1. Gemini Flash Lite's budget freeze memo, which had a few `[Date]` fields but was otherwise complete, got a 4.29.

The judges seem to treat placeholders as a specificity problem rather than a dealbreaker, which seems reasonable. A memo that says "effective November 15" is more convincing than one that says "effective [Insert Date]," and the benchmark is specifically measuring whether models can produce realistic nonfiction, not fill-in-the-blank templates. Models that invented plausible details (GPT-5.3 Chat picking "November 27 through December 29" for a holiday shift change) earned their higher specificity scores honestly.

---

## 5. Why smaller models outperformed larger ones

The most surprising pattern in the leaderboard: GPT-5.3 Chat (3rd place, 4.30) beats GPT-5.4 (10th place, 3.80). Gemini Flash Lite (2nd place, 4.65) beats Claude Opus 4.6 (6th place, 3.95).

This is almost entirely explained by truncation rates.

GPT-5.3 Chat hits 500 tokens on 13 of its 20 outputs, but 7 of them finish under that cap. Its shorter, punchier style means it can complete a memo in 184 words or an explainer in 232 words and still land a satisfying ending. GPT-5.4 hits the same 500-token cap but writes in a more expansive style that needs more room—so it gets cut off 90% of the time.

Gemini Flash Lite uses 1,308 tokens on average (apparently not subject to the same 500-token cap that hits Claude and GPT). It simply has room to write complete pieces. Claude Opus, capped at exactly 500 tokens on every output, writes 300-380 words of strong prose and then gets guillotined mid-sentence.

There's a secondary effect too. Smaller models may be trained to be more concise. GPT-5.3 Chat consistently produces tighter prose than GPT-5.4: shorter sentences, fewer qualifiers, less throat-clearing. This isn't necessarily because it's a better writer—it may just have a tighter default output distribution that happens to fit under the token cap more often. But the practical result is the same: it finishes more pieces, so it scores higher.

The exception that proves the rule is Qwen 3.5 35B. It has 1,089 average tokens—more than Claude or GPT-5.4—but still scores last at 2.53. That's because roughly half its outputs are consumed by leaked thinking text ("Thinking Process: 1. Analyze the Request...") that never transitions to actual writing. Qwen's problem isn't token budget; it's that its reasoning traces aren't being stripped from the output, so judges receive an outline instead of an essay.

---

## 6. Judgment validity: are the judges getting it right?

### The truncation penalty is legitimate but disproportionate

Judges consistently identify truncation and penalize it. When Gemini's judge sees Claude Opus's food recall explainer cut off mid-sentence, the rationale says: "the response cuts off mid-sentence and completely fails to address the second half of the prompt." That's a fair observation. But the resulting score of 2 (out of 5) for a piece whose existing text was described as having "excellent use of specific examples" feels harsh. The judges are treating incompleteness as a fundamental structural failure rather than an unfortunate technical limitation.

This is a rubric design issue more than a judge quality issue. The rubric apparently doesn't distinguish between "the model chose to write something short and unfinished" and "the model was cut off by an external token limit." A human editor would recognize the difference. The judge models can't, because they don't know about the token cap.

### Judge agreement varies dramatically by model

| Model | Avg StdDev of Judge Scores |
| --- | ---: |
| Gemini 3.1 Pro | 0.14 |
| Qwen 3.5 35B | 0.20 |
| Kimi K2.5 | 0.21 |
| DeepSeek V3.2 | 0.37 |
| GPT-5.3 Chat | 0.38 |
| Gemini Flash Lite | 0.43 |
| Grok 4.1 Fast | 0.46 |
| GPT-5.4 | 0.47 |
| MiniMax M2.5 | 0.48 |
| GLM-5 | 0.48 |
| Claude Sonnet 4.6 | 0.53 |
| Claude Opus 4.6 | 0.61 |

Judges agree most on Gemini Pro (stddev 0.14) and Qwen (0.20)—the best and worst models. They agree least on Claude Opus (0.61) and Claude Sonnet (0.53). This makes sense: the extremes are easy to judge. A complete, well-written piece is obviously good. An output that's mostly thinking traces is obviously bad. The hard cases are the middle-tier models where a piece is well-written but truncated, and judges must decide how much to penalize the cutoff.

### Judge agreement varies by prompt type too

| Prompt | Avg StdDev |
| --- | ---: |
| explain_food_recall | 0.24 |
| profile_school_custodian | 0.28 |
| memo_incident_response | 0.48 |
| howto_school_board_comment | 0.48 |

Judges agree more on explainers and profiles than on memos and how-to guides. Explainers and profiles have relatively clear quality signals: did the explainer explain the thing? Does the profile bring the person to life? Memos and how-tos have more ambiguous success criteria. Is a memo with placeholder fields acceptable? How much structural scaffolding should a how-to guide have? These are judgment calls where reasonable judges diverge.

### Self-family bias is real but smaller than the truncation effect

The Gemini judge gives its own family perfect 5s across all prompts. That's a +0.33 bias over what other judges give Gemini. Claude Opus shows an even larger self-family bias of +0.65 (it rates Claude outputs 4.35 while the other judges rate them 3.70). GPT-5.4's judge is actually slightly *negative* on its own family (-0.11), rating GPT outputs lower than the other judges do.

These biases are real but ultimately secondary. The truncation effect (0.43 points average) dwarfs the self-judging bias (0.11-0.22 points on the final averaged score). Removing self-judging would change rankings by a position or two, but it wouldn't change the fundamental pattern.

---

## 7. What could improve model output

### The obvious fix: more tokens

This is the overwhelming finding. The `max_output_tokens` setting of 2500 is apparently not being respected for most models. Claude Opus and Sonnet are hard-capped at 500 tokens—a limit so low that they cannot complete a 400-word essay. If the pipeline ensured all models actually received 2500 tokens (or better, enough to finish their pieces), the leaderboard would look radically different.

### Prompt-level improvements that might help

Based on the patterns in this run:

**Tell models to be concise.** GPT-5.3 Chat scores well partly because it writes tighter prose that fits under the token cap. A prompt that says "Write 250-400 words" could be supplemented with "Aim for the lower end of that range. Every sentence should earn its place."

**Ask for a specific opening.** The top-scoring outputs almost always open with a concrete scene or specific detail. Adding "Open with a specific scene or example, not a definition" to the prompt would probably improve output across the board.

**Discourage templates.** For memos and how-to guides, adding "Write this as a completed document with realistic details, not as a template with placeholder fields" would address the `[Insert Date]` problem.

**Explicitly request endings.** Given the truncation problem, a prompt that says "Make sure your piece has a clear conclusion" might cause models to budget their tokens differently, prioritizing completion over thoroughness.

### What prompting probably can't fix

Some limitations appear to be model-level, not prompt-level. Claude Opus and Sonnet produce extremely competent, well-organized prose that reads like polished Wikipedia—clear and authoritative but rarely surprising. This is a voice and style tendency that's baked into the model. You can prompt for voice ("Write as if you're telling a friend"), but models with a strong default register will tend to revert.

Qwen's thinking-trace leak is a model-level bug (or a configuration issue with `exclude_reasoning`). No prompt will fix that.

---

## 8. The curious case of Qwen 3.5

Qwen 3.5 35B is fascinating because it's bimodal. On the prompts where it actually produces finished writing (memo_schedule_change, memo_incident_response, explain_municipal_bonds), it scores 4.29-4.71—solidly mid-tier, competitive with models many times its size. On the prompts where it dumps its thinking process instead, it scores 1.19-1.29.

The thinking traces are clearly being included in the output despite the `exclude_reasoning: true` setting in the manifest. The traces follow a consistent pattern: "Thinking Process: 1. Analyze the Request... 2. Determine the Tone... 3. Brainstorm Arguments... 4. Structure the Piece..." followed by an outline that gets cut off before any actual prose is written.

This happens on roughly half the prompts, but not randomly—it seems to correlate with prompt complexity. Qwen successfully writes complete memos and explainers (structured, formulaic genres) but leaks thinking traces on op-eds, personal essays, and profiles (genres that require more creative planning). This suggests the model's reasoning system engages more heavily on open-ended creative tasks, and whatever mechanism is supposed to strip the reasoning traces before output is failing intermittently.

If the thinking-trace issue were fixed, Qwen's real score would probably be in the 3.8-4.2 range—competitive with the middle tier despite being a much smaller model. That's an impressive underlying capability hidden by a configuration bug.

---

## 9. What the judges agree and disagree about

### They agree: clarity is solved

Every model except Qwen scores 4.6+ on clarity. The judges rarely disagree about whether a piece is understandable. This axis has hit a ceiling and no longer discriminates between models. Future benchmark versions might consider dropping it in favor of axes that actually differentiate.

### They agree: Gemini writes well and Qwen has problems

The lowest standard deviation across judges is for Gemini Pro (0.14) and Qwen (0.20). For Gemini, all three judges consistently give 4s and 5s. For Qwen, all three consistently give 1s on the thinking-trace outputs and 4s on the actual writing. The judges are calibrated on the extremes.

### They disagree: how much to penalize truncation

The biggest source of judge disagreement is incomplete outputs from otherwise-good writers. When Claude Opus produces a food recall explainer that cuts off mid-sentence, one judge gives an overall 2 ("completely fails to address the second half"), another gives 3 ("conspicuously unfinished"), and the third gives 3 ("truncated before giving the key practical steps"). The rationales show the judges all *see* the same problem but weight it differently.

This is the clearest signal that the rubric needs guidance on how to handle truncation. Should judges evaluate the writing that exists, ignoring the cutoff? Should they penalize proportionally to how much is missing? Or should truncation be treated as a structural failure regardless of the writing quality? Right now each judge is making this call independently, which is the primary source of disagreement.

### They disagree: structure in the middle tier

Structure scores have the widest judge disagreement for models in the 3.7-4.3 range. For memos and how-to guides especially, judges differ on whether bullet-point formatting counts as good structure or whether prose-based organization is better. GPT-5.4's memo with markdown headers gets a different structural assessment from each judge. This suggests the rubric's definition of "structure and flow" is ambiguous enough to produce inconsistent evaluations on formats that are neither clearly narrative nor clearly broken.

---

## 10. Some additional observations

### The memo_budget_freeze prompt is the hardest

Budget freeze memos produce the widest score range across models (3.33 to 4.71) and the most judge disagreement. The prompt asks for something tricky: a memo that communicates bad news clearly while maintaining morale. Models that default to corporate-speak ("well-positioned to meet our long-term operational goals") get dinged on voice. Models that try to be human about it ("we know this isn't easy") get rewarded. It's a good discriminating prompt.

### Personal nonfiction is where the best writing happens

The three personal nonfiction prompts (union job, night-shift bus, public pool) produced the highest individual scores and some of the most distinctive prose in the run. Models have to invent sensory details, maintain a consistent first-person voice, and create a narrative arc. The pieces that succeed—Gemini's union job essay, GPT-5.3's version of the same, GLM-5's night-shift bus essay—read like actual creative nonfiction. The pieces that fail read like Wikipedia articles written in first person.

### Token efficiency correlates with quality independently of truncation

Even among non-truncated outputs, the tightest writers tend to score highest. GPT-5.3 Chat's complete memo (184 words) scores higher than GPT-5.4's longer but truncated version. Gemini Pro's complete outputs average 647 words—longer than most, but every word is earning its place. The models that pad with transition phrases ("Furthermore, it is worth noting that...") score lower on brevity, and the brevity penalty correlates with lower overall scores even when pieces are complete. William Zinsser would approve: shorter and clearer beats longer and fuzzier.

---

## 11. Recommendations for the next run

### Fix the token cap (critical)

Whatever is limiting Claude and GPT to 500 completion tokens needs to be identified and fixed. This is the single highest-priority issue. The benchmark cannot produce valid writing quality comparisons when most models can't finish their pieces. Check whether OpenRouter has model-specific token limits that override the `max_output_tokens` parameter.

### Handle truncation in the rubric

Add explicit guidance to the judge prompt: "If a piece appears to be cut off before completion, evaluate the writing quality of what exists, then note the incompleteness as a separate factor. Do not give an overall score below 3 for a piece whose existing text is well-written but incomplete." This won't eliminate the truncation problem, but it will reduce the variance in how judges handle it.

### Remove self-judging

Don't use a model as a judge of its own outputs (or its family's outputs). The Gemini self-judging bias (+0.33) and the Claude self-judging bias (+0.65) are both large enough to affect rankings. Use three judges that are not in the candidate pool, or at minimum, exclude each judge's scores on its own family.

### Strip or quarantine thinking traces

Qwen's thinking-trace leak is costing it 1.5-2 points on affected prompts. If `exclude_reasoning: true` isn't working for this model, add post-processing that detects and removes thinking traces before sending outputs to judges. The regex pattern is straightforward: anything starting with "Thinking Process:" or similar markers.

### Consider a fairer score for this run

Given how deeply truncation affects the results, the analysis report might benefit from two leaderboards: one with raw scores (as currently reported) and one that only includes non-truncated outputs from each model. The second leaderboard would give a much more accurate picture of actual writing quality, though sample sizes would be small for the most-truncated models.

---

## 12. What we actually learned about writing quality

Strip away the token cap issues, the self-judging bias, and the thinking-trace bugs, and there's a real finding underneath: **frontier language models are converging on a narrow band of nonfiction writing quality, and the differences between them are smaller than the differences caused by technical artifacts.**

Among non-truncated outputs, the gap between the best model (GPT-5.4 at 4.83) and the weakest non-Qwen model (Grok at 4.48) is just 0.35 points. That's real but modest. The models are all producing clear, competent, publishable nonfiction prose. The differences are in voice (does it sound like a person or a textbook?), structure (does it have an arc or just a list of points?), and economy (does every sentence earn its place?).

Those are exactly the dimensions William Zinsser cared about, and they're exactly the dimensions where AI writing still has room to improve. The ceiling effect on clarity and simplicity means the frontier has moved: the next generation of writing benchmarks needs to focus on the subtler craft elements—voice, pacing, detail selection, knowing when to stop—that separate competent prose from good prose.

The salvage run fixed the Gemini bug and revealed that under fair conditions, Gemini is genuinely among the strongest nonfiction writers in the current model generation. But it also revealed that "fair conditions" don't exist yet in this benchmark: token caps, self-judging, and reasoning-trace bugs are all larger effects than the actual writing quality differences between models. The benchmark infrastructure needs to be as good as the rubric before we can trust the rankings.
