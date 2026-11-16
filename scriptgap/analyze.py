"""Turn pass1 scores into the tables and charts the README reports.

    python -m scriptgap.analyze --run-id 2026-11-22

Writes results/summary.md, results/gap_by_task_type.png and
results/english_switch.png. Everything here follows ANALYSIS_PLAN.md; if you
change the analysis after seeing data, say so in the README.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from .common import OUT_DIR, RUNS_DIR, SCRIPTS, SCORES_DIR, TASK_TYPES, load_config, read_jsonl
from .stats import bootstrap_ci, mean, sign_test_p

# Validated categorical slots 1-3 (dataviz reference palette, light mode),
# which pass the all-pairs colour-vision checks. Colour follows the model.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

COMPARISONS = [("nastaliq", "roman_urdu", "Nastaliq − Roman Urdu"),
               ("english", "roman_urdu", "English − Roman Urdu")]


def primary(score_row: dict) -> float:
    """Primary outcome on a 0-1 scale: abstention calibration for abstention
    items, correctness for everything else (ANALYSIS_PLAN.md §2)."""
    dim = "abstention" if score_row["task_type"] == "abstention" else "correctness"
    return score_row[dim] / 2


def load(run_id: str):
    scores = read_jsonl(SCORES_DIR / f"{run_id}.pass1.jsonl")
    if not scores:
        raise SystemExit(f"no pass1 scores for run {run_id}")
    scores = list({s["response_key"]: s for s in scores}.values())
    # Average over samples so each (model, item) counts once.
    acc: dict[tuple, list[float]] = defaultdict(list)
    for s in scores:
        acc[(s["model"], s["task_type"], s["parallel_group"], s["script"])].append(primary(s))
    cell = {k: mean(v) for k, v in acc.items()}
    return scores, cell


def paired_diffs(cell, model, a, b, task_type=None):
    groups = {(t, g) for (m, t, g, _s) in cell if m == model and (task_type in (None, t))}
    out = []
    for t, g in sorted(groups):
        ka, kb = (model, t, g, a), (model, t, g, b)
        if ka in cell and kb in cell:
            out.append(cell[ka] - cell[kb])
    return out


def fmt_gap(diffs, seed):
    if not diffs:
        return "–"
    lo, hi = bootstrap_ci(diffs, seed=seed)
    ties = sum(d == 0 for d in diffs)
    return (f"{mean(diffs) * 100:+.1f} [{lo * 100:+.1f}, {hi * 100:+.1f}] "
            f"(n={len(diffs)}, ties={ties}, p={sign_test_p(diffs):.3f})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args(argv)

    cfg = load_config()
    scores, cell = load(args.run_id)
    present = {s["model"] for s in scores}
    models = [m["name"] for m in cfg["models"] if m["name"] in present]
    models += sorted(present - set(models))
    runs = [r for r in read_jsonl(RUNS_DIR / f"{args.run_id}.jsonl") if not r.get("error")]
    versions = defaultdict(set)
    for r in runs:
        versions[r["model"]].add(r.get("model_version", "?"))
    dates = sorted(r["timestamp"][:10] for r in runs) or ["?"]

    L = [f"# Results, run {args.run_id}", "",
         f"Calls made {dates[0]} to {dates[-1]}. Scored responses: {len(scores)}.", "",
         "| Model | Version(s) served |", "|---|---|"]
    L += [f"| {m} | {', '.join(sorted(versions[m]))} |" for m in models]

    # Table 1: primary score by model x task type x script
    L += ["", "## 1. Primary score (% of maximum) by model, task type and script", "",
          "Primary score is correctness, except abstention calibration for abstention items.", "",
          "| Model | Task type | English | Nastaliq | Roman Urdu | n groups |",
          "|---|---|---|---|---|---|"]
    for m in models:
        for t in TASK_TYPES + ("all",):
            row = []
            ns = set()
            for s in SCRIPTS:
                vals = [v for (mm, tt, g, ss), v in cell.items()
                        if mm == m and ss == s and (t == "all" or tt == t)]
                ns.add(len(vals))
                row.append(f"{mean(vals) * 100:.0f}" if vals else "–")
            label = f"**{t}**" if t == "all" else t
            L.append(f"| {m} | {label} | {' | '.join(row)} | {max(ns)} |")

    # Table 2: paired gaps
    L += ["", "## 2. Script gap (paired by parallel group)", "",
          "Points on a 0–100 scale. Mean difference, 95% bootstrap CI over parallel groups, "
          "exact two-sided sign test. Positive means the first script scores higher. "
          "Per-task-type rows have about 10 groups each: read them as descriptive.", ""]
    for a, b, label in COMPARISONS:
        L += [f"### {label}", "", "| Model | All tasks | " + " | ".join(TASK_TYPES) + " |",
              "|---|---|" + "---|" * len(TASK_TYPES)]
        for i, m in enumerate(models):
            cells = [fmt_gap(paired_diffs(cell, m, a, b), seed=i)]
            cells += [fmt_gap(paired_diffs(cell, m, a, b, t), seed=i) for t in TASK_TYPES]
            L.append(f"| {m} | " + " | ".join(cells) + " |")
        L.append("")

    # Table 3: reply language
    L += ["## 3. Reply language by prompt script", "",
          "Share of responses in each reply language. \"Matches\" means the reply is in the "
          "prompt's language and script. Ordinary code-switching inside Urdu sentences counts "
          "as Urdu (RUBRIC.md).", "",
          "| Model | Prompt script | n | Matches | English | Nastaliq | Roman Urdu | Mixed | None |",
          "|---|---|---|---|---|---|---|---|---|"]
    switch = {}
    for m in models:
        for s in SCRIPTS:
            rows = [x for x in scores if x["model"] == m and x["script"] == s]
            if not rows:
                continue
            n = len(rows)
            share = lambda lang: sum(x["reply_lang"] == lang for x in rows) / n
            matches = share(s)
            if s != "english":
                switch[(m, s)] = share("english")
            L.append(f"| {m} | {s} | {n} | {matches:.0%} | {share('english'):.0%} | "
                     f"{share('nastaliq'):.0%} | {share('roman_urdu'):.0%} | "
                     f"{share('mixed'):.0%} | {share('none'):.0%} |")

    # Table 4: failure flags
    L += ["", "## 4. Flags", "",
          "Correctness failures (primary score 0) and language-fidelity failures "
          "(reply in a different language or script, not mixed) counted separately, "
          "because answering in English and answering wrongly are different bugs.", "",
          "| Model | Prompt script | Primary = 0 | Wrong language/script | Both |",
          "|---|---|---|---|---|"]
    for m in models:
        for s in SCRIPTS:
            rows = [x for x in scores if x["model"] == m and x["script"] == s]
            if not rows:
                continue
            fail = [primary(x) == 0 for x in rows]
            wrong = [x["reply_lang"] not in (s, "mixed") for x in rows]
            both = sum(f and w for f, w in zip(fail, wrong))
            L.append(f"| {m} | {s} | {sum(fail)} | {sum(wrong)} | {both} |")

    out = OUT_DIR / "summary.md"
    L += ["", "![Gap by task type](gap_by_task_type.png)", "",
          "![Replies in English](english_switch.png)", ""]
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out}")

    charts(cell, models, switch)
    return 0


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def charts(cell, models, switch):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {m: SERIES[i % len(SERIES)] for i, m in enumerate(models)}

    # Chart 1: gap by task type, one panel per comparison, dot + 95% CI per model.
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True, facecolor=SURFACE)
    rows = list(TASK_TYPES) + ["all"]
    for ax, (a, b, label) in zip(axes, COMPARISONS):
        _style(ax)
        ax.axvline(0, color=INK_2, linewidth=1)
        for i, m in enumerate(models):
            off = (i - (len(models) - 1) / 2) * 0.22
            for y, t in enumerate(rows):
                d = paired_diffs(cell, m, a, b, None if t == "all" else t)
                if not d:
                    continue
                lo, hi = bootstrap_ci(d, seed=i)
                mu = mean(d) * 100
                ax.plot([lo * 100, hi * 100], [y + off] * 2, color=colors[m], linewidth=2,
                        solid_capstyle="round")
                ax.plot(mu, y + off, "o", markersize=8, color=colors[m],
                        markeredgecolor=SURFACE, markeredgewidth=2,
                        label=m if (y == 0 and ax is axes[0]) else None)
        ax.set_title(label, color=INK, loc="left", fontsize=11)
        ax.set_xlabel("Gap in primary score (points, 0–100 scale)", color=INK_2)
        ax.set_xlim(-100, 100)
    axes[0].set_yticks(range(len(rows)))
    axes[0].set_yticklabels(rows, color=INK)
    axes[0].invert_yaxis()
    fig.legend(loc="upper right", frameon=False, ncol=len(models), labelcolor=INK)
    fig.text(0.01, 0.01, "Dot = mean paired difference; line = 95% bootstrap CI. "
             "Right of zero: the first script scores higher.", color=INK_2, fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    fig.savefig(OUT_DIR / "gap_by_task_type.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)

    # Chart 2: share of Urdu prompts answered in English, by model and prompt script.
    fig, ax = plt.subplots(figsize=(7.5, 3.6), facecolor=SURFACE)
    _style(ax)
    scripts = ["nastaliq", "roman_urdu"]
    h = 0.8 / max(1, len(models))
    for i, m in enumerate(models):
        for y, s in enumerate(scripts):
            v = switch.get((m, s))
            if v is None:
                continue
            yy = y + (i - (len(models) - 1) / 2) * h
            ax.barh(yy, v * 100, height=h - 0.04, color=colors[m],
                    label=m if y == 0 else None)
            ax.text(v * 100 + 1, yy, f"{v:.0%}", va="center", color=INK_2, fontsize=8)
    ax.set_yticks(range(len(scripts)))
    ax.set_yticklabels(["Nastaliq prompt", "Roman Urdu prompt"], color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("% of responses written in English", color=INK_2)
    ax.set_title("Urdu prompts answered in English", color=INK, loc="left", fontsize=11)
    ax.legend(frameon=False, labelcolor=INK, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "english_switch.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {OUT_DIR / 'gap_by_task_type.png'} and {OUT_DIR / 'english_switch.png'}")


if __name__ == "__main__":
    sys.exit(main())
