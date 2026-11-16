# script-gap

**Does LLM quality drop when Urdu is written in Roman script?**

Benchmarks test Urdu in Nastaliq. Most people in Pakistan type Roman Urdu: *"kya haal hai"*, not کیا حال ہے. This repo measures whether models answer the same question differently depending on which of the two scripts it is written in, with English as the reference.

## Status

**In progress. The study is pre-registered; the data has not been collected yet.**

| Stage | State |
|---|---|
| Rubric and analysis plan | Frozen and tagged [`prereg`](../../tree/prereg) before any model call |
| Tooling (validate, run, score, agreement, analyze) | Done, tested end to end on synthetic data |
| Dataset: 40 tasks × 3 scripts, hand-written | Being written |
| Model run, scoring, agreement check | Not started |
| Finding | Written last, once the numbers exist |

## Finding

> *Not yet run. This section will state a number, for example: "On this dataset, model X scores N points lower on Roman Urdu than on Nastaliq [95% CI a, b], and the drop is concentrated in reasoning items." A null result is reported with the same care.*

## Design, in one screen

| | |
|---|---|
| **Items** | 40 tasks × 3 scripts = 120 prompts: 10 each of factual recall, instruction following, reasoning and false-premise abstention. Written by hand in Roman Urdu first, then rendered in Nastaliq and English by the same author. No machine translation. |
| **Models** | 3 (see `config.toml`): one frontier model, one model from a different lab, and one open-weight model run locally. The model version that served each call is recorded. |
| **Prompting** | No system prompt, a single turn, and each provider's default sampling. |
| **Scoring** | By hand, blind to model, against a rubric frozen before the first call ([RUBRIC.md](RUBRIC.md)). 45 responses are rescored on a different day to measure agreement. |
| **Analysis** | Pre-registered in [ANALYSIS_PLAN.md](ANALYSIS_PLAN.md). Gaps are paired within each task's three versions, with bootstrap CIs and sign tests. Answering in the wrong language is counted separately from answering wrongly. |

## Models, and why these three

| Role | Model | Why |
|---|---|---|
| Frontier | Claude Opus 5.5 (`claude-opus-5-5`) | A current frontier model. If the gap exists even here, it is a property of the field rather than of weak models. |
| Different lab, mid-tier or older | *to be chosen before the run* | Shows whether a gap is specific to one lab's training data. |
| Open-weight, stated multilingual support | *to be chosen before the run* | The kind of model a Pakistani company could self-host. It is run locally through Ollama, and the weights' digest is recorded. |

Three is enough to tell whether a gap belongs to one model or to all of them. The exact model IDs go into `config.toml`, and the version that served each call is recorded with every response. These results describe those versions on the run date, and they will expire as models change.

## Related work

Script effects in Urdu have been measured before, in narrower settings. This study differs in using one hand-written set of general tasks (factual, instruction following, reasoning and false-premise abstention) in three parallel versions, scored by a native speaker against a pre-registered rubric.

- **[U-MIRAGE](https://aclanthology.org/2026.abjadnlp-1.55)** (medical question answering in Urdu and Roman Urdu) reports lower scores in both Urdu variants than in English, with **Roman Urdu scoring higher than Nastaliq**. This runs against the intuition behind this repo, so it is a direct prediction to test outside the medical domain.
- **[RUAB](https://aclanthology.org/2026.abjadnlp-1.37)** tests 400 safety intents in English, mixed Roman Urdu and pure Roman Urdu: the same parallel-variant design, applied to safety rather than task quality.
- **[Urdu idiom translation](https://arxiv.org/abs/2510.17460)**, and a [later study with 4,000 aligned pairs](https://aclanthology.org/2026.findings-emnlp.1181/), compare Nastaliq and Roman Urdu inputs for translation into English.
- **[UrduBench](https://arxiv.org/abs/2601.21000)** translates reasoning benchmarks into Nastaliq Urdu only.

## Running it

Requires **Python 3.11 or later** (the config is read with `tomllib`).

```bash
pip install -r requirements.txt
python -m pytest -q                         # sanity-check the tooling

python -m scriptgap.validate                # check data/items.jsonl
python -m scriptgap.run --run-id 2026-11-22 --limit 3   # smoke test: 3 items x 3 models
python -m scriptgap.run --run-id 2026-11-22             # full run; re-run to resume or retry failures

python -m scriptgap.score --run-id 2026-11-22 --pass pass1
python -m scriptgap.score --run-id 2026-11-22 --pass pass2     # another day; 45 responses
python -m scriptgap.agreement --run-id 2026-11-22
python -m scriptgap.analyze --run-id 2026-11-22                # results/summary.md + charts
```

The runner needs `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`, and Ollama running locally with the open-weight model pulled.

## Dataset format

One JSON object per line in `data/items.jsonl`. `data/EXAMPLE.jsonl` shows one complete parallel group.

| Field | |
|---|---|
| `item_id` | `<parallel_group>.<script>`, e.g. `reason-07.roman_urdu`. Unique per row. |
| `parallel_group` | Ties a task's three versions together. Every comparison is made within a group. |
| `task_type` | `factual` / `instruction` / `reasoning` / `abstention` |
| `script` | `english` / `nastaliq` / `roman_urdu` |
| `prompt`, `gold`, `gold_notes` | `gold_notes` lists accepted variants and, for instruction items, every constraint. |
| `author`, `built_on` | Who wrote this version, and when. |
| `derived_from` | Optional: `roman_urdu` on the Nastaliq and English rows. |

## Repository

```
data/            items.jsonl (the dataset), EXAMPLE.jsonl
scriptgap/       validate, run, score, agreement, analyze, providers, stats
results/runs/    raw responses, one file per run
results/scores/  hand scores, <run>.pass1.jsonl and <run>.pass2.jsonl
results/         summary.md, agreement.md, charts
```

## Limits

*To be written in the author's own voice after the run.* Known from the design, before any data:

- **Small and single-authored.** 120 items by one author, in one person's Roman Urdu spelling. Roman Urdu has no standard spelling, so another writer's version of the same task could score differently.
- **One rater.** The agreement figure is intra-rater: the same person on two different days. It is not agreement between independent raters.
- **Partial blinding.** The scorer hides the model's name, but a response can still give its model away, for example by naming itself. The prompt's script cannot be hidden, because the rater has to read it.
- **Small cells.** Each task type has about 10 parallel groups, so per-type gaps are descriptive. Only the pooled gap per model is tested.
- **Versions expire.** Three models on specific dates. The results describe those versions, not the models' later releases.

These are findings about this dataset, not a general claim about Urdu capability.

## How this was built

The study design, the dataset, the rubric and every score are mine. The runner and analysis code were written with Claude Code.
