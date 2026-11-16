# Analysis plan

Written and committed before any model is called. `git log` on this file is the evidence of that.

## 1. Question

For the same underlying task, does model performance differ between English, Nastaliq Urdu and Roman Urdu? If it does, by how much, on which task types, and in which direction?

## 2. Outcomes

- **Primary score:** correctness for factual, instruction and reasoning items, and abstention calibration for abstention items. Each is scored 0/1/2 and rescaled to 0–100.
- **Secondary:** reply language, from which language fidelity is derived, and instruction compliance.

## 3. Unit of analysis

The **parallel group**: one task written three ways. Every comparison is *paired* within a group, so a hard question counts as hard in all three scripts and drops out of the difference. With `samples > 1`, a model's score on an item is the mean over its samples.

## 4. Headline comparison

**Script gap = Nastaliq − Roman Urdu**, the mean paired difference in primary score, for each model, pooled over all 40 groups.

Reported alongside it: **English − Roman Urdu**, since English is the ceiling most benchmarks implicitly assume.

For each gap:
- the mean paired difference, in points;
- a 95% percentile bootstrap CI that resamples parallel groups (10,000 resamples, fixed seed);
- an exact two-sided sign test, with the number of ties stated.

Per-task-type gaps (about 10 groups each) are **descriptive**. With ten pairs, only a large gap is detectable. The README will not claim that a gap is concentrated in one task type unless that type's CI excludes zero and the others' do not, and even then it will describe this as suggestive.

With 3 models × 2 comparisons there are six headline tests. A p-value is reported as evidence, not as a pass/fail gate. If one is used as a gate, apply a Bonferroni threshold of 0.05/6 ≈ 0.008 and say so.

## 5. Language fidelity

A table of model × prompt script showing the share of replies in each language, and the share of Urdu prompts answered in English. Fidelity failures are counted separately from correctness failures, as is the overlap between the two.

## 6. Agreement

Intra-rater: pass1 against pass2 on 45 responses. The report gives exact agreement and Cohen's kappa (quadratic-weighted for 0/1/2 scores, nominal for reply language). If disagreement on any dimension is above 20%, that dimension's anchors are rewritten and rescored (RUBRIC.md).

## 7. What would count as "no gap"

A pooled Nastaliq − Roman Urdu CI that lies within ±10 points and includes zero, for every model. That result is a finding and is reported with the same care.

## 8. Fixed in advance

- **Models and versions:** in `config.toml`. The served version is recorded per call.
- **Prompting:** no system prompt, a single user turn, and each provider's default sampling.
- **Claude:** effort pinned in config. Server-side refusal fallbacks are off, so every answer comes from the model named. A refusal is scored as it stands.
- **Run date:** recorded. These results expire as models change.

## 9. Deviations

Any change to this plan after data is seen goes here, with the date and the reason.

- *(none yet)*
