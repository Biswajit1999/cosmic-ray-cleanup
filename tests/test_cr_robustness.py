import numpy as np
import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.cr_robustness import (
    confusion_curve, image_cluster_bootstrap, flux_cost_threshold,
)


def test_perfect_separation():
    curve = confusion_curve([.9, .8, .2, .1], np.array([1, 1, 0, 0], bool), [.5])
    assert np.allclose(curve[0, :3], 1)


def test_zero_predictions_not_nan():
    curve = confusion_curve([.9, .1], np.array([1, 0], bool), [1.])
    assert np.all(np.isfinite(curve)) and curve[0, 2] == 0


def test_bootstrap_constant():
    result = image_cluster_bootstrap(np.ones(10)*.2, seed=3)
    assert np.allclose(result["ci95"], .2)


def test_bootstrap_reproducible():
    x = np.array([1., 2., 3., 4.])
    assert np.array_equal(image_cluster_bootstrap(x, seed=4)["ci95"],
                          image_cluster_bootstrap(x, seed=4)["ci95"])


def test_cost_prefers_stellar_preservation():
    truth = np.array([1, 1, 0, 0], bool)
    core = np.array([0, 0, 1, 0], bool)
    result = flux_cost_threshold([.9, .7, .8, .1], truth, core, [.6, .85], 10)
    assert result["threshold"] == .85


def test_invalid_truth():
    with pytest.raises(ValueError):
        confusion_curve([1, 2], np.array([0, 0], bool), [.5])
