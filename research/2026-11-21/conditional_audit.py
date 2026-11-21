"""Conditional cosmic-ray threshold and clustered uncertainty diagnostics.

Synthetic examples only; masks are not HST reference truth.
Run: python -m unittest research/2026-11-21/test_conditional_audit.py
"""
import numpy as np


def threshold_curve(scores, truth, thresholds, source_core=None):
    """Return precision, recall and source-core masking fraction per threshold."""
    s = np.asarray(scores, dtype=float)
    t = np.asarray(truth, dtype=bool)
    h = np.asarray(thresholds, dtype=float)
    if s.shape != t.shape or s.size == 0 or not np.isfinite(s).all():
        raise ValueError("scores/truth must be finite and shape-matched")
    if h.ndim != 1 or not len(h) or not np.isfinite(h).all():
        raise ValueError("finite threshold vector required")
    core = np.zeros_like(t) if source_core is None else np.asarray(source_core, dtype=bool)
    if core.shape != t.shape:
        raise ValueError("source_core shape mismatch")
    out = []
    for cut in h:
        p = s >= cut
        tp = np.count_nonzero(p & t)
        fp = np.count_nonzero(p & ~t)
        fn = np.count_nonzero(~p & t)
        precision = tp / (tp + fp) if tp + fp else np.nan
        recall = tp / (tp + fn) if tp + fn else np.nan
        false_core = np.count_nonzero(p & core & ~t) / max(1, np.count_nonzero(core & ~t))
        out.append((precision, recall, false_core))
    return np.asarray(out)


def image_cluster_bootstrap(values, image_ids, n_boot=1000, seed=0):
    """Resample whole images, retaining within-image pixel dependence.

    Returns bootstrap mean quantiles; does not estimate independent pixel uncertainty.
    """
    v = np.asarray(values, dtype=float)
    ids = np.asarray(image_ids)
    if v.ndim != 1 or ids.shape != v.shape or len(v) == 0 or not np.isfinite(v).all():
        raise ValueError("finite paired one-dimensional inputs required")
    if n_boot < 2:
        raise ValueError("n_boot must be at least two")
    labels, inverse = np.unique(ids, return_inverse=True)
    if len(labels) < 2:
        raise ValueError("at least two independent images required")
    sums = np.bincount(inverse, weights=v)
    counts = np.bincount(inverse)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(labels), size=(n_boot, len(labels)))
    means = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return np.quantile(means, [0.025, 0.5, 0.975])


def threshold_sensitivity(scores, truth, thresholds, source_core=None):
    """Compute an explicit threshold-dependent precision/recall/core-cost audit."""
    return threshold_curve(scores, truth, thresholds, source_core)
