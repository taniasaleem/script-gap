"""Small, dependency-free statistics used by the analysis. Kept separate so
they can be unit-tested."""
from __future__ import annotations

import math
import random
from collections import Counter


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def bootstrap_ci(diffs, n_boot=10_000, seed=0, alpha=0.05):
    """Percentile bootstrap CI for the mean of paired differences.
    Resamples parallel groups, which are the independent unit."""
    diffs = list(diffs)
    if len(diffs) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(diffs)
    boots = sorted(mean(rng.choices(diffs, k=n)) for _ in range(n_boot))
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot) - 1]
    return lo, hi


def sign_test_p(diffs):
    """Exact two-sided sign test. Ties (zero differences) are dropped, which
    is the standard treatment; report how many there were alongside."""
    pos = sum(d > 0 for d in diffs)
    neg = sum(d < 0 for d in diffs)
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def cohen_kappa(a, b, weights=None, categories=None):
    """Cohen's kappa for two lists of labels. weights='quadratic' for ordinal
    integer scales (0/1/2), None for nominal labels."""
    assert len(a) == len(b) and a, "need two equal, non-empty lists"
    cats = sorted(set(categories or []) | set(a) | set(b))
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    if k == 1:
        return 1.0
    n = len(a)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1 / n
    pa, pb = Counter(a), Counter(b)
    exp = [[pa[ci] / n * pb[cj] / n for cj in cats] for ci in cats]
    if weights == "quadratic":
        w = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    else:
        w = [[0.0 if i == j else 1.0 for j in range(k)] for i in range(k)]
    num = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * exp[i][j] for i in range(k) for j in range(k))
    return 1.0 if den == 0 else 1 - num / den
