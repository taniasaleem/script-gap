# script-gap

**Does LLM quality drop when Urdu is written in Roman script?**

Benchmarks test Urdu in Nastaliq. Most people in Pakistan type Roman Urdu: *"kya haal hai"*, not کیا حال ہے. This repo measures whether models answer the same question differently depending on which of the two scripts it is written in, with English as the reference.

## Finding

> *Not yet run. This section is written last and states a number, for example: "On this dataset, model X scores N points lower on Roman Urdu than on Nastaliq [95% CI a, b], and the drop is concentrated in reasoning items." A null result is reported with the same care.*

## Design, in one screen

| | |
|---|---|
| **Items** | 40 tasks × 3 scripts = 120 prompts: 10 each of factual recall, instruction following, reasoning and false-premise abstention. Written by hand in Roman Urdu first, then rendered in Nastaliq and English by the same author. No machine translation. |
| **Models** | 3 (see `config.toml`): one frontier model, one model from a different lab, and one open-weight model run locally. The model version that served each call is recorded. |
| **Prompting** | No system prompt, a single turn, and each provider's default sampling. |
| **Scoring** | By hand, blind to model, against a rubric frozen before the first call ([RUBRIC.md](RUBRIC.md)). 45 responses are rescored on a different day to measure agreement. |
| **Analysis** | Pre-registered in [ANALYSIS_PLAN.md](ANALYSIS_PLAN.md). Gaps are paired within each task's three versions, with bootstrap CIs and sign tests. Answering in the wrong language is counted separately from answering wrongly. |

## Running it

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

*To be written in the author's own voice after the run.* At minimum: 120 items by one author, in one person's Roman Urdu spelling; one scoring pass plus a rescored sample; three models on specific dates; per-task-type cells of about 10 pairs. These are findings about this dataset, not a general claim about Urdu capability.

## How this was built

The study design, the dataset, the rubric and every score are mine. The runner and analysis code were written with Claude Code.
