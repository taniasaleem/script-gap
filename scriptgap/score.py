"""Blind, resumable hand-scoring in the terminal.

    python -m scriptgap.score --run-id 2026-11-22 --pass pass1
    python -m scriptgap.score --run-id 2026-11-22 --pass pass2 --sample 45

Responses are shown in a seeded random order with the model name hidden.
The script of the prompt cannot be hidden, since you have to read it.
Every answer is saved as you go; quit with q and re-run the same command to
resume.

pass2 is the recheck: a stratified sample of responses already scored in pass1,
shown again without your pass1 scores. Do it on a different day.
"""
from __future__ import annotations

import argparse
import random
import sys
import textwrap
from collections import defaultdict
from datetime import datetime, timezone

from .common import (DATA, REPLY_LANGS, RUNS_DIR, SCORES_DIR, append_jsonl,
                     read_jsonl, suggest_reply_lang)

# Which dimensions are scored for which task type (see RUBRIC.md).
DIMENSIONS = {
    "factual": ["correctness"],
    "instruction": ["correctness", "compliance"],
    "reasoning": ["correctness"],
    "abstention": ["abstention"],
}
PROMPTS = {
    "correctness": "Correctness   0 wrong / 1 partial or material error / 2 matches gold",
    "compliance": "Compliance    0 ignores format / 1 some constraints / 2 every constraint",
    "abstention": "Abstention    0 asserts false premise / 1 hedges, problem not named / 2 names premise, declines",
}


def response_key(r: dict) -> str:
    return f"{r['run_id']}|{r['model']}|{r['item_id']}|{r['sample']}"


def ask(prompt: str, allowed: set[str], default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        a = input(f"{prompt}{suffix}: ").strip().lower()
        if not a and default:
            return default
        if a == "q":
            raise KeyboardInterrupt
        if a in allowed:
            return a
        print(f"  enter one of {sorted(allowed)}, or q to quit")


def stratified_sample(rows: list[dict], n: int, seed: int) -> list[dict]:
    """Round-robin across (model, script) cells so every cell is represented."""
    rng = random.Random(seed)
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        cells[(r["model"], r["script"])].append(r)
    for c in cells.values():
        rng.shuffle(c)
    order = sorted(cells)
    picked: list[dict] = []
    while len(picked) < n and any(cells.values()):
        for c in order:
            if cells[c] and len(picked) < n:
                picked.append(cells[c].pop())
    return picked


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--pass", dest="pass_name", required=True, choices=["pass1", "pass2"])
    ap.add_argument("--sample", type=int, default=45, help="pass2 only: responses to rescore")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--rater", default="tania")
    args = ap.parse_args(argv)

    items = {r["item_id"]: r for r in read_jsonl(DATA)}
    runs = [r for r in read_jsonl(RUNS_DIR / f"{args.run_id}.jsonl") if not r.get("error")]
    if not runs:
        raise SystemExit(f"no successful responses in results/runs/{args.run_id}.jsonl")
    # If a row was retried, keep the latest successful copy.
    runs = list({response_key(r): r for r in runs}.values())

    out = SCORES_DIR / f"{args.run_id}.{args.pass_name}.jsonl"
    already = {s["response_key"] for s in read_jsonl(out)}

    if args.pass_name == "pass2":
        p1 = {s["response_key"] for s in read_jsonl(SCORES_DIR / f"{args.run_id}.pass1.jsonl")}
        pool = [r for r in runs if response_key(r) in p1]
        if not pool:
            raise SystemExit("score pass1 first")
        todo = stratified_sample(pool, args.sample, args.seed)
    else:
        todo = runs
    random.Random(args.seed).shuffle(todo)
    todo = [r for r in todo if response_key(r) not in already]

    total = len(todo) + len(already)
    print(f"{len(already)} scored, {len(todo)} to go. q quits; progress is saved.\n")
    try:
        for i, r in enumerate(todo, len(already) + 1):
            item = items[r["item_id"]]
            print("=" * 78)
            print(f"[{i}/{total}]  {item['task_type']}  |  prompt script: {item['script']}")
            print("-" * 78)
            print("PROMPT:\n" + item["prompt"])
            print(f"\nGOLD: {item['gold']}")
            if item.get("gold_notes"):
                print(f"NOTES: {item['gold_notes']}")
            print("-" * 78)
            print("RESPONSE:")
            for para in (r["response"] or "(empty)").splitlines() or [""]:
                print(textwrap.fill(para, 100) if para else "")
            if r.get("stop_reason") in ("refusal", "length", "max_tokens"):
                print(f"\n[stop_reason: {r['stop_reason']}]")
            print("-" * 78)

            scores = {}
            for dim in DIMENSIONS[item["task_type"]]:
                scores[dim] = int(ask(PROMPTS[dim], {"0", "1", "2"}))
            guess = suggest_reply_lang(r["response"] or "")
            lang = ask("Reply language  e english / n nastaliq / r roman urdu / m mixed / x none",
                       set(REPLY_LANGS), default=guess)
            note = input("Note (optional): ").strip()

            append_jsonl(out, {
                "response_key": response_key(r),
                "run_id": r["run_id"], "model": r["model"], "item_id": r["item_id"],
                "parallel_group": r["parallel_group"], "task_type": r["task_type"],
                "script": r["script"], "sample": r["sample"],
                "pass": args.pass_name, "rater": args.rater,
                **scores,
                "reply_lang": REPLY_LANGS[lang],
                "reply_lang_suggested": REPLY_LANGS[guess],
                "note": note,
                "scored_at": datetime.now(timezone.utc).isoformat(),
            })
    except (KeyboardInterrupt, EOFError):
        print("\nstopped; re-run the same command to resume.")
        return 0
    print("all done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
