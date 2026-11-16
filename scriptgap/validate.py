"""Check data/items.jsonl before anything is sent to a model.

    python -m scriptgap.validate [path]

Exits non-zero on any error. Warnings (for example, fewer than 10 groups per
task type) do not fail, so you can validate while the dataset is half-built.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

from .common import DATA, SCRIPTS, TASK_TYPES, arabic_ratio, read_jsonl

REQUIRED = ("item_id", "task_type", "script", "prompt", "gold",
            "parallel_group", "author", "built_on")
TARGET_GROUPS_PER_TYPE = 10


def validate(rows: list[dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    ids = Counter(r.get("item_id") for r in rows)
    for item_id, n in ids.items():
        if n > 1:
            errors.append(f"item_id {item_id!r} appears {n} times; it must be unique per row")

    groups: dict[str, list[dict]] = defaultdict(list)
    for i, r in enumerate(rows, 1):
        where = f"row {i} ({r.get('item_id', '?')})"
        missing = [k for k in REQUIRED if not str(r.get(k, "")).strip()]
        if missing:
            errors.append(f"{where}: missing {', '.join(missing)}")
            continue
        if r["task_type"] not in TASK_TYPES:
            errors.append(f"{where}: task_type {r['task_type']!r} not in {TASK_TYPES}")
        if r["script"] not in SCRIPTS:
            errors.append(f"{where}: script {r['script']!r} not in {SCRIPTS}")
        expected_id = f"{r['parallel_group']}.{r['script']}"
        if r["item_id"] != expected_id:
            errors.append(f"{where}: item_id should be {expected_id!r}")

        ar = arabic_ratio(r["prompt"])
        if r["script"] == "nastaliq" and ar < 0.9:
            errors.append(f"{where}: nastaliq prompt is only {ar:.0%} Arabic-script letters")
        if r["script"] in ("english", "roman_urdu") and ar > 0:
            errors.append(f"{where}: {r['script']} prompt contains Arabic-script letters")

        groups[r["parallel_group"]].append(r)

    for g, members in groups.items():
        scripts = sorted(m["script"] for m in members)
        if scripts != sorted(SCRIPTS):
            errors.append(f"group {g}: has scripts {scripts}, needs exactly one of each of {list(SCRIPTS)}")
        types = {m["task_type"] for m in members}
        if len(types) > 1:
            errors.append(f"group {g}: rows disagree on task_type {sorted(types)}")

    per_type = Counter(next(iter({m['task_type'] for m in ms})) for ms in groups.values() if ms)
    for t in TASK_TYPES:
        if per_type[t] != TARGET_GROUPS_PER_TYPE:
            warnings.append(f"{t}: {per_type[t]} parallel groups (target {TARGET_GROUPS_PER_TYPE})")

    return errors, warnings


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else DATA
    rows = read_jsonl(path)
    if not rows:
        print(f"{path}: no items yet")
        return 1
    errors, warnings = validate(rows)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    n_groups = len({r.get('parallel_group') for r in rows})
    print(f"{len(rows)} rows, {n_groups} parallel groups, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
