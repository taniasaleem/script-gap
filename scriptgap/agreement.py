"""Compare pass1 and pass2 scores on the rechecked sample.

    python -m scriptgap.agreement --run-id 2026-11-22

Writes results/agreement.md. This is *intra*-rater agreement (you against
yourself on a different day), and the README should call it that. If a second
Urdu speaker scores the same sample as pass2 with --rater <name>, the same
numbers become inter-rater agreement.
"""
from __future__ import annotations

import argparse
import sys

from .common import OUT_DIR, SCORES_DIR, read_jsonl
from .stats import cohen_kappa

DIMS = ["correctness", "compliance", "abstention", "reply_lang"]
DISAGREEMENT_LIMIT = 0.20  # pre-registered in ANALYSIS_PLAN.md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args(argv)

    p1 = {s["response_key"]: s for s in read_jsonl(SCORES_DIR / f"{args.run_id}.pass1.jsonl")}
    p2 = {s["response_key"]: s for s in read_jsonl(SCORES_DIR / f"{args.run_id}.pass2.jsonl")}
    keys = sorted(set(p1) & set(p2))
    if not keys:
        raise SystemExit("no responses scored in both passes yet")

    raters = sorted({p2[k]["rater"] for k in keys} | {p1[k]["rater"] for k in keys})
    kind = "Intra-rater" if len(raters) == 1 else "Inter-rater"
    lines = [f"# {kind} agreement, run {args.run_id}", "",
             f"{len(keys)} responses scored in both passes. Raters: {', '.join(raters)}.", "",
             "| Dimension | n | Exact agreement | Cohen's kappa | Status |",
             "|---|---|---|---|---|"]
    any_fail = False
    for d in DIMS:
        pairs = [(p1[k][d], p2[k][d]) for k in keys if d in p1[k] and d in p2[k]]
        if not pairs:
            continue
        a, b = zip(*pairs)
        exact = sum(x == y for x, y in pairs) / len(pairs)
        if d == "reply_lang":
            kappa = cohen_kappa(a, b)
            klabel = f"{kappa:.2f} (nominal)"
        else:
            kappa = cohen_kappa(a, b, weights="quadratic", categories=[0, 1, 2])
            klabel = f"{kappa:.2f} (quadratic weighted)"
        fail = (1 - exact) > DISAGREEMENT_LIMIT
        any_fail |= fail
        status = "**over limit: tighten anchors and rescore**" if fail else "ok"
        lines.append(f"| {d} | {len(pairs)} | {exact:.0%} | {klabel} | {status} |")

    disagreements = [(k, d) for k in keys for d in DIMS
                     if d in p1[k] and d in p2[k] and p1[k][d] != p2[k][d]]
    if disagreements:
        lines += ["", "## Disagreements", "",
                  "Read each one. They tell you which anchor is vague.", "",
                  "| Response | Dimension | pass1 | pass2 |", "|---|---|---|---|"]
        for k, d in disagreements:
            lines.append(f"| `{k}` | {d} | {p1[k][d]} | {p2[k][d]} |")

    out = OUT_DIR / "agreement.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4 + len(DIMS) + 2]))
    print(f"\nwrote {out}")
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
