"""Send every item to every model in config.toml and store raw responses.

    python -m scriptgap.run --run-id 2026-11-22 [--only claude] [--workers 4]

Output: results/runs/<run_id>.jsonl, one row per (item, model, sample).
Re-running the same command resumes: rows already stored without an error are
skipped, and failed rows are retried.
"""
from __future__ import annotations

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from .common import DATA, RUNS_DIR, append_jsonl, load_config, read_jsonl
from .providers import PROVIDERS
from .validate import validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True, help="e.g. the run date, 2026-11-22")
    ap.add_argument("--only", help="run a single model by its config name")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, help="first N items only (smoke test)")
    args = ap.parse_args(argv)

    cfg = load_config()
    items = read_jsonl(DATA)
    if not items:
        print(f"{DATA} has no items; nothing to run.")
        return 1
    errors, _ = validate(items)
    if errors:
        print("Dataset has errors; run `python -m scriptgap.validate` first.")
        return 1
    if args.limit:
        items = items[: args.limit]

    models = cfg["models"]
    if args.only:
        models = [m for m in models if m["name"] == args.only]
        if not models:
            raise SystemExit(f"no model named {args.only!r} in config.toml")
    for m in models:
        if "FILL_ME" in m["model"]:
            raise SystemExit(f"Set the model ID for {m['name']!r} in config.toml first")
        if m["provider"] not in PROVIDERS:
            raise SystemExit(f"unknown provider {m['provider']!r}")

    samples = int(cfg.get("samples", 1))
    out = RUNS_DIR / f"{args.run_id}.jsonl"
    done = {(r["item_id"], r["model"], r["sample"])
            for r in read_jsonl(out) if not r.get("error")}

    jobs = [(it, m, s) for m in models for it in items for s in range(samples)
            if (it["item_id"], m["name"], s) not in done]
    print(f"{len(jobs)} calls to make ({len(done)} already stored) -> {out}")

    lock = threading.Lock()

    def work(item: dict, model: dict, sample: int) -> str:
        row = {
            "run_id": args.run_id,
            "model": model["name"],
            "provider": model["provider"],
            "model_requested": model["model"],
            "item_id": item["item_id"],
            "parallel_group": item["parallel_group"],
            "task_type": item["task_type"],
            "script": item["script"],
            "sample": sample,
        }
        try:
            row.update(PROVIDERS[model["provider"]](model, item["prompt"]))
        except Exception as e:  # stored, then retried on the next invocation
            row["error"] = f"{type(e).__name__}: {e}"
        row["timestamp"] = datetime.now(timezone.utc).isoformat()
        with lock:
            append_jsonl(out, row)
        return row.get("error") or "ok"

    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, *j) for j in jobs]
        for n, f in enumerate(as_completed(futures), 1):
            status = f.result()
            if status != "ok":
                failures += 1
                print(f"  [{n}/{len(jobs)}] {status}")
            elif n % 20 == 0 or n == len(jobs):
                print(f"  [{n}/{len(jobs)}]")
    print(f"done; {failures} failures" + (" (re-run the same command to retry)" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
