from __future__ import annotations

import numpy as np
import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError
from hst_ccd_cosmic_ray_rejection_benchmark.metrics import (
    background_masking_rate,
    precision_recall_f1,
    psf_core_false_masking_rate,
)


def test_precision_recall_f1_perfect_detection():
    truth = np.zeros((10, 10), dtype=bool)
    truth[2, 2] = truth[5, 5] = True
    detected = truth.copy()
    metrics = precision_recall_f1(truth, detected)
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0


def test_precision_recall_f1_partial_detection():
    truth = np.zeros((10, 10), dtype=bool)
    truth[2, 2] = truth[5, 5] = True
    detected = np.zeros((10, 10), dtype=bool)
    detected[2, 2] = True
    detected[7, 7] = True  # false positive
    metrics = precision_recall_f1(truth, detected)
    assert metrics.true_positive == 1
    assert metrics.false_negative == 1
    assert metrics.false_positive == 1
    assert metrics.recall == pytest.approx(0.5)
    assert metrics.precision == pytest.approx(0.5)


def test_precision_recall_f1_empty_truth_raises():
    truth = np.zeros((5, 5), dtype=bool)
    detected = np.zeros((5, 5), dtype=bool)
    with pytest.raises(DataSchemaError):
        precision_recall_f1(truth, detected)


def test_precision_recall_f1_shape_mismatch_raises():
    with pytest.raises(DataSchemaError):
        precision_recall_f1(np.zeros((5, 5), dtype=bool), np.zeros((4, 4), dtype=bool))


def test_psf_core_false_masking_rate():
    detected = np.zeros((10, 10), dtype=bool)
    core = np.zeros((10, 10), dtype=bool)
    core[3:6, 3:6] = True  # 9 pixels
    detected[3, 3] = True
    detected[4, 4] = True
    rate = psf_core_false_masking_rate(detected, core)
    assert rate == pytest.approx(2 / 9)


def test_psf_core_false_masking_rate_zero_core_raises():
    detected = np.zeros((5, 5), dtype=bool)
    core = np.zeros((5, 5), dtype=bool)
    with pytest.raises(DataSchemaError):
        psf_core_false_masking_rate(detected, core)


def test_background_masking_rate_excludes_truth_and_source():
    detected = np.zeros((10, 10), dtype=bool)
    truth = np.zeros((10, 10), dtype=bool)
    source = np.zeros((10, 10), dtype=bool)
    truth[0, 0] = True
    source[1, 1] = True
    detected[0, 0] = True  # a true-positive CR flag, not a background flag
    detected[9, 9] = True  # background false positive
    rate = background_masking_rate(detected, truth, source)
    n_background = 100 - 1 - 1
    assert rate == pytest.approx(1 / n_background)
