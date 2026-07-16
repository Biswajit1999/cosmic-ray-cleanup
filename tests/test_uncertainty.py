from __future__ import annotations

import numpy as np
import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import ConvergenceError, InsufficientDataError
from hst_ccd_cosmic_ray_rejection_benchmark.uncertainty import bootstrap_statistic, check_fit_convergence


def test_bootstrap_statistic_is_deterministic_given_seed():
    data = np.random.default_rng(0).normal(0, 1, 200)
    r1 = bootstrap_statistic(data, np.mean, n_resamples=200, seed=7)
    r2 = bootstrap_statistic(data, np.mean, n_resamples=200, seed=7)
    assert r1 == r2


def test_bootstrap_statistic_ci_contains_estimate():
    data = np.random.default_rng(0).normal(0, 1, 200)
    result = bootstrap_statistic(data, np.mean, n_resamples=500, seed=1)
    assert result.ci_low <= result.estimate <= result.ci_high


def test_bootstrap_statistic_too_few_samples_raises():
    with pytest.raises(InsufficientDataError):
        bootstrap_statistic(np.array([1.0]), np.mean, n_resamples=100, seed=1)


def test_bootstrap_statistic_bad_confidence_level_raises():
    with pytest.raises(ValueError):
        bootstrap_statistic(np.array([1.0, 2.0]), np.mean, n_resamples=10, seed=1, confidence_level=1.5)


def test_check_fit_convergence_well_conditioned():
    pcov = np.eye(2) * 0.01
    result = check_fit_convergence(pcov, residuals=np.array([0.1, -0.1, 0.05]), dof=1)
    assert result.converged
    assert result.reduced_chi_square is not None


def test_check_fit_convergence_ill_conditioned_raises():
    pcov = np.array([[1e20, 0], [0, 1e-20]])
    with pytest.raises(ConvergenceError):
        check_fit_convergence(pcov)


def test_check_fit_convergence_nonfinite_raises():
    pcov = np.array([[np.nan, 0], [0, 1.0]])
    with pytest.raises(ConvergenceError):
        check_fit_convergence(pcov)
