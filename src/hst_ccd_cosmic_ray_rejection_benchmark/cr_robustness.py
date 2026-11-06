"""Synthetic cosmic-ray rejection threshold and clustered uncertainty audit.

Pixels within an exposure are correlated; resample independent images.
"""
import numpy as np


def confusion_curve(scores, truth, thresholds):
    """Precision, recall, F1 and false-positive count across thresholds."""
    scores = np.asarray(scores, dtype=float)
    truth = np.asarray(truth)
    thresholds = np.asarray(thresholds, dtype=float)
    if (scores.shape != truth.shape or truth.dtype != bool or scores.size == 0
            or not np.all(np.isfinite(scores)) or not np.any(truth)):
        raise ValueError("invalid score/truth arrays")
    if thresholds.ndim != 1 or not np.all(np.isfinite(thresholds)):
        raise ValueError("invalid thresholds")
    result = []
    for cut in thresholds:
        predicted = scores >= cut
        tp = np.count_nonzero(predicted & truth)
        fp = np.count_nonzero(predicted & ~truth)
        fn = np.count_nonzero(~predicted & truth)
        precision = tp / (tp + fp) if tp + fp else 0.
        recall = tp / (tp + fn)
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.
        result.append((precision, recall, f1, fp))
    return np.array(result)


def image_cluster_bootstrap(per_image, repetitions=2000, seed=17):
    """Resample independent images, not individual pixels, for mean-bias CI."""
    values = np.asarray(per_image, dtype=float)
    if (values.ndim != 1 or len(values) < 2 or not np.all(np.isfinite(values))
            or repetitions < 100):
        raise ValueError("at least two finite images and 100 resamples required")
    rng = np.random.default_rng(seed)
    means = np.empty(repetitions)
    for i in range(repetitions):
        means[i] = np.mean(values[rng.integers(len(values), size=len(values))])
    return {"mean": float(np.mean(values)),
            "ci95": np.quantile(means, [.025, .975]),
            "bootstrap_se": float(np.std(means, ddof=1))}


def flux_cost_threshold(scores, truth, stellar_core, thresholds, false_positive_cost=10.):
    """Minimize missed CR pixels plus weighted false masking of stellar cores.

    The relative cost is illustrative and is not an empirically calibrated
    astrophysical utility function.
    """
    scores = np.asarray(scores, float)
    truth = np.asarray(truth)
    core = np.asarray(stellar_core)
    if (scores.shape != truth.shape or core.shape != truth.shape
            or truth.dtype != bool or core.dtype != bool or np.any(core & truth)
            or false_positive_cost < 0):
        raise ValueError("invalid disjoint truth and source masks")
    thresholds = np.asarray(thresholds, float)
    if thresholds.ndim != 1 or not len(thresholds) or not np.all(np.isfinite(thresholds)):
        raise ValueError("invalid thresholds")
    costs = []
    for threshold in thresholds:
        predicted = scores >= threshold
        costs.append(np.count_nonzero(truth & ~predicted)
                     + false_positive_cost * np.count_nonzero(core & predicted))
    costs = np.asarray(costs, float)
    return {"threshold": float(thresholds[np.argmin(costs)]), "costs": costs}
