# Scoring rubric

**Freeze this file before the first model call.** Commit it, tag the commit `prereg`, and change it afterwards only if the agreement check forces a change. If it does, say so in the README.

Every score has three levels, and each level is defined by something you can see in the response. On a five-point scale the 2 and 4 would have no anchors, and those are the scores two raters, or one rater on two different days, disagree on.

## Which dimensions apply to which task type

| Task type | Correctness | Compliance | Abstention | Reply language |
|---|---|---|---|---|
| factual | ✓ | | | ✓ |
| instruction | ✓ | ✓ | | ✓ |
| reasoning | ✓ | | | ✓ |
| abstention | | | ✓ | ✓ |

A dimension that does not apply to a task type is not scored, rather than defaulted to a middle value.

## Correctness (factual, instruction, reasoning)

| Score | Anchor |
|---|---|
| **0** | The answer is wrong, missing, or a refusal. |
| **1** | Partly right: the final answer is right but reached through a stated error, or one part of a multi-part answer is wrong, or the right answer sits alongside a contradicting one. |
| **2** | Matches the gold answer, accepting the variants listed in `gold_notes`. Extra correct detail does not cost points. |

Score the content, not the language. A correct answer in English to a Roman Urdu question gets a 2 here and is caught under **Reply language**.

## Instruction compliance (instruction only)

| Score | Anchor |
|---|---|
| **0** | Ignores the stated format: wrong count, wrong structure, or the constraint is not visible at all. |
| **1** | Meets some stated constraints but not all, for example three bullets with a preamble that was forbidden. |
| **2** | Meets every stated constraint. |

Before scoring, list the item's constraints in its `gold_notes` so that "every constraint" means a fixed list.

## Abstention calibration (abstention only)

| Score | Anchor |
|---|---|
| **0** | Accepts the false premise and answers as if it were true. |
| **1** | Hedges or adds a disclaimer but does not say which part of the question is false, or names the problem and then answers as if it were true anyway. |
| **2** | Says which premise is false and does not invent an answer. Correcting the premise ("Iqbal wrote it, not Faiz") counts. |

## Reply language (all items)

Record what the reply actually is. Fidelity is derived from it afterwards.

| Code | Meaning |
|---|---|
| `e` | English |
| `n` | Urdu in Nastaliq / Perso-Arabic script |
| `r` | Roman Urdu |
| `m` | Mixed: switches language or script at sentence level or between sections, unprompted |
| `x` | Nothing usable: empty, refusal boilerplate, or an error |

**Code-switching rule. This needs deciding before you score, because it is the judgement only a native speaker can make.** Roman Urdu as people actually type it is full of English words: "yeh formula use karo", "mera exam cancel ho gaya". English loanwords and phrases inside an Urdu sentence are **Urdu** (`r` or `n`). A reply is `m` only when whole sentences or sections change language, or when Nastaliq and Roman script are both used for Urdu text. Mark `e` only when the reply is written as English sentences.

Derived fidelity: 2 if the reply language matches the prompt's script, 1 if `m`, and 0 otherwise. A reply language of `e`, or the other Urdu script, on an Urdu prompt is a **language-fidelity failure**. It is reported separately from correctness failures and never folded into them.

The scoring tool pre-fills a guess at the reply language from a simple script-and-stopword heuristic. That guess is a convenience only. Read the response and override it whenever it is wrong. The tool stores both values, so the README can report how often the heuristic was wrong.

## Procedure

1. Score pass1 blind to the model: `python -m scriptgap.score --run-id <id> --pass pass1`.
2. At least a day later, score pass2 on a stratified sample of 45 responses (12.5% of 360): `--pass pass2`. You will not see your pass1 scores.
3. Run `python -m scriptgap.agreement --run-id <id>`. If any dimension's exact disagreement is above **20%**, the anchors for that dimension are too vague. Rewrite them, rescore **all** of pass1 for that dimension, and say so in the README.
