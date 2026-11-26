# Item-writing protocol

How the 120 rows in `data/items.jsonl` are written. This file was committed while `data/items.jsonl` was still empty, so the history shows the rules came before the items.

## What gets written

40 tasks, each written three ways (Roman Urdu, Nastaliq, English), so 120 rows. Ten tasks of each type:

| Groups | Task type | Scored on (RUBRIC.md) |
|---|---|---|
| `fact-01` … `fact-10` | factual | correctness |
| `instr-01` … `instr-10` | instruction | correctness and compliance |
| `reason-01` … `reason-10` | reasoning | correctness |
| `abstain-01` … `abstain-10` | abstention (false premise) | abstention |

`data/TEMPLATE.jsonl` already has every row's ID, task type and script. `data/EXAMPLE.jsonl` is one finished group.

## 1. Plan all 40 before writing any JSON

Write a one-line idea for every task first, ten per type, and check the set as a whole.

- **Aim for medium difficulty**, something a well-educated adult could answer. A task every model gets right in all three scripts, or wrong in all three, cannot show a gap even where one exists: it scores the same three times, and the sign test leaves ties out and only counts them (ANALYSIS_PLAN.md §4).
- **Don't use famous puzzles or riddles.** Models have likely memorised the English version, which would favour English for a reason that has nothing to do with script.
- **Don't use facts that change or are disputed:** populations, records, current office-holders, recent events.
- **Don't use tasks whose answer depends on the script**, such as counting letters, spelling, rhyme or alphabetical order. They are not the same task in three scripts.
- **Don't use topics that invite hedging or refusal:** health or legal advice, religious rulings, politics. Models often hedge or refuse on these, and may do so differently in each script. The rubric scores a refusal as 0 (RUBRIC.md, correctness), so safety behaviour would be mixed into the quality score.

## 2. Write one group at a time, in this order

1. **Roman Urdu first**, as you would naturally type it. English words inside an Urdu sentence are fine. That is how people write, and the rubric counts them as Urdu (RUBRIC.md, code-switching rule).
2. **Then Nastaliq**: the same task, written by you. Write English loanwords in Urdu script too. The validator requires at least 90% of a Nastaliq prompt's letters to be Arabic-script. Digits are not letters, so `۱۲` and `12` are both fine.
3. **Then English**: the same task again. English and Roman Urdu prompts may not contain any Arabic-script letter.

The three versions must ask for the same thing, at the same difficulty, at roughly the same length. Don't make one version more explicit or give it an extra hint.

**Never say which language to answer in.** The reply language is something the study measures, so the prompt must not set it.

## 3. Fill in every field

| Field | What goes in it |
|---|---|
| `prompt` | The whole message, exactly as a user would send it. |
| `gold` | The correct answer, written in that row's script (as in `EXAMPLE.jsonl`). |
| `gold_notes` | Other answers to accept: spellings, short forms, digits or number words. For instruction items, every constraint (the validator rejects an instruction row without them). |
| `author` | Who wrote the row. The same person writes all three versions. |
| `built_on` | The date the row was written, `YYYY-MM-DD`. |

Leave `item_id`, `task_type`, `script`, `parallel_group` and `derived_from` as the template has them.

## 4. What each task type needs

**Factual.** One question, one checkable answer that will not change. List accepted variants in `gold_notes`, for example `accept Iqbal / Muhammad Iqbal`.

**Instruction.** A task with constraints the rater can check by eye: "exactly 3 numbered points", "no introduction", "each point on one line", "end with a question". Don't use word or character limits, because word boundaries and lengths are not comparable across the three scripts. Use the same constraints in all three versions, and list them all in `gold_notes` so that the compliance score is checked against a fixed list:

```
Constraints: (1) exactly 3 numbered points; (2) no opening sentence; (3) each point one line. Content: <what a correct answer covers>
```

**Reasoning.** A problem that takes several steps and ends in one final answer: arithmetic, dates, ordering or simple logic. Write new problems rather than adapting known ones. If the answer is a number, accept both digit forms in `gold_notes` (`12` / `۱۲`), since replies may use either.

**Abstention (false premise).** A question built on a premise that is clearly and checkably false, not merely debatable or unknown. The rubric's example is a poem credited to the wrong poet. Put the false part and the true fact in `gold` (for example `Faiz did not write it; Iqbal did`). Put what counts as naming the false premise in `gold_notes`, because a score of 2 depends on it (RUBRIC.md, abstention). Keep the same false premise in all three versions.

## 5. Rules for the whole process

- **No machine translation**, not even to check a version.
- **Don't try any item on any model while writing.** Keeping or editing items according to how a model answers them would bias the study.
- **A model may suggest topic areas, never items.** Treat a model's topic ideas as categories only. The specific fact, numbers and false premise come from your own knowledge, and the README says which model was used. Some of this study's topic areas came from Claude, one of the models tested.
- **Keep your natural Roman Urdu spelling.** Single-author spelling is a stated limit of the study, not something to correct.
- **Commit after each sitting.** The dated commits are the public record that the items were written before any model run.

## 6. Putting rows in the file

1. Copy the group's three lines from `data/TEMPLATE.jsonl` into `data/items.jsonl` and replace the blanks with what you wrote.
2. Keep each row on one line. If a prompt genuinely needs a line break, type `\n`.
3. Use single quotes inside values, as `EXAMPLE.jsonl` does. An unescaped double quote ends the value early, and the validator reports the line as invalid JSON.
4. Nastaliq and English on the same line can look scrambled in an editor. That is only how right-to-left text is displayed; the file is stored correctly. Typing the Nastaliq in a notes app and pasting it in is easier.
5. Run `python -m scriptgap.validate`, fix every `ERROR`, and check the progress line.

## 7. Done means

- `python -m scriptgap.validate` reports **120 of 120 rows, 40 of 40 parallel groups complete, 0 errors, 0 warnings**.
- Every group has been read once more with its three versions side by side, checking for the same meaning, the same difficulty and a correct gold answer.

Only then is the commit tagged `prereg`, freezing the items together with RUBRIC.md and ANALYSIS_PLAN.md, before any model is called.
