"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have the same length")
    valid = {"PASS", "FAIL"}
    h = [str(x).strip().upper() for x in human]
    j = [str(x).strip().upper() for x in judge]
    if any(x not in valid for x in (*h, *j)):
        raise ValueError("labels must be PASS or FAIL")
    return {
        "tp": sum(a == POS and b == POS for a, b in zip(h, j)),
        "fp": sum(a != POS and b == POS for a, b in zip(h, j)),
        "fn": sum(a == POS and b != POS for a, b in zip(h, j)),
        "tn": sum(a != POS and b != POS for a, b in zip(h, j)),
    }


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    predicted_positive = cm["tp"] + cm["fp"]
    actual_positive = cm["tp"] + cm["fn"]
    precision = cm["tp"] / predicted_positive if predicted_positive else 0.0
    recall = cm["tp"] / actual_positive if actual_positive else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    n = sum(cm.values())
    if n == 0:
        raise ValueError("kappa is undefined for an empty sample")
    p_observed = (cm["tp"] + cm["tn"]) / n
    human_fail = cm["tp"] + cm["fn"]
    human_pass = cm["tn"] + cm["fp"]
    judge_fail = cm["tp"] + cm["fp"]
    judge_pass = cm["tn"] + cm["fn"]
    p_expected = (human_fail * judge_fail + human_pass * judge_pass) / (n * n)
    if p_expected == 1.0:
        raise ValueError("kappa is undefined when expected agreement is 1")
    return (p_observed - p_expected) / (1.0 - p_expected)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    for name, value in (("observed_rate", observed_rate), ("sensitivity", sensitivity),
                        ("specificity", specificity)):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]")
    denominator = sensitivity + specificity - 1.0
    if denominator == 0.0:
        raise ValueError("Rogan-Gladen is undefined when sensitivity + specificity == 1")
    corrected = (observed_rate + specificity - 1.0) / denominator
    return min(1.0, max(0.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    if len(a) != len(b):
        raise ValueError("paired samples must have the same length")
    if len(a) == 0:
        raise ValueError("paired samples must not be empty")
    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    aa = np.asarray(a, dtype=float)
    bb = np.asarray(b, dtype=float)
    if not np.all(np.isfinite(aa)) or not np.all(np.isfinite(bb)):
        raise ValueError("paired samples must contain only finite values")
    differences = aa - bb
    mean_difference = float(np.mean(differences))
    if np.all(differences == 0):
        return 0.0, 0.0, 0.0

    result = bootstrap(
        (aa, bb),
        lambda x, y, axis: np.mean(x - y, axis=axis),
        paired=True,
        vectorized=True,
        n_resamples=n_resamples,
        confidence_level=confidence,
        method="percentile",
        rng=np.random.default_rng(rng),
    )
    return mean_difference, float(result.confidence_interval.low), float(result.confidence_interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_pass_k(n, c, k)
    return 1.0 - (comb(n - c, k) / comb(n, k) if n - c >= k else 0.0)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_pass_k(n, c, k)
    return comb(c, k) / comb(n, k) if c >= k else 0.0


def _validate_pass_k(n: int, c: int, k: int) -> None:
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if n <= 0 or c < 0 or c > n or k <= 0 or k > n:
        raise ValueError("require n > 0, 0 <= c <= n and 1 <= k <= n")
