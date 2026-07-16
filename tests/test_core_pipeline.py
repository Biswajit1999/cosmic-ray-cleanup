"""Core pipeline tests: injection-recovery validation gate, null control, failure modes.

Per docs/VALIDATION_CONTRACT.md rule 5 ("at least one null, negative-control
or failure-mode test") and docs/VALIDATION_CONTRACT.md's requirement that the
injection-recovery validation gate must pass before real data is touched.
"""
from __future__ import annotations

import numpy as np
import pytest
from astroscrappy import detect_cosmics

from hst_ccd_cosmic_ray_rejection_benchmark.core import (
    DEFAULT_OBJLIM,
    DEFAULT_SIGCLIP_VALUES,
    DEFAULT_SIGFRAC,
    SourceSpec,
    detect_sources_real,
    run_pipeline,
)
from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import InsufficientDataError


def test_run_pipeline_injection_recovery_validation_gate(config, synthetic_background, synthetic_sources):
    """Hard validation gate: recall against known-injected CR pixels must be
    high across the sigclip sweep, and precision must clearly increase as
    sigclip becomes more conservative -- the exact detection-vs-false-masking
    trade-off this project benchmarks. If this fails, the pipeline must not
    proceed to real data (per docs/VALIDATION_CONTRACT.md).
    """
    result = run_pipeline(
        background=synthetic_background.science,
        gain=synthetic_background.gain,
        readnoise=synthetic_background.readnoise,
        sources=synthetic_sources,
        config=config,
        sigclip_values=DEFAULT_SIGCLIP_VALUES,
        n_trials_per_setting=3,
        n_cr_events=25,
    )
    assert len(result.sweep) == len(DEFAULT_SIGCLIP_VALUES)
    for point in result.sweep:
        assert 0.0 <= point.recall_mean <= 1.0
        assert 0.0 <= point.precision_mean <= 1.0
        assert point.recall_mean > 0.85, f"recall too low at sigclip={point.sigclip}: {point.recall_mean}"

    by_sigclip = {p.sigclip: p for p in result.sweep}
    assert by_sigclip[3.0].precision_mean < by_sigclip[10.0].precision_mean, (
        "expected precision to increase with a more conservative sigclip threshold "
        "(known detection-vs-false-masking trade-off)"
    )
    assert not result.warnings


def test_run_pipeline_empty_background_raises(config, synthetic_sources):
    with pytest.raises(InsufficientDataError):
        run_pipeline(
            background=np.zeros((0, 0)),
            gain=2.0,
            readnoise=4.0,
            sources=synthetic_sources,
            config=config,
        )


def test_run_pipeline_no_sources_raises(config, synthetic_background):
    with pytest.raises(InsufficientDataError):
        run_pipeline(
            background=synthetic_background.science,
            gain=synthetic_background.gain,
            readnoise=synthetic_background.readnoise,
            sources=(),
            config=config,
        )


def test_run_pipeline_empty_sigclip_sweep_raises(config, synthetic_background, synthetic_sources):
    with pytest.raises(InsufficientDataError):
        run_pipeline(
            background=synthetic_background.science,
            gain=synthetic_background.gain,
            readnoise=synthetic_background.readnoise,
            sources=synthetic_sources,
            config=config,
            sigclip_values=(),
        )


def test_null_control_no_injected_cosmic_rays_low_false_positive_rate(synthetic_background):
    """Negative control: with NO cosmic rays injected, astroscrappy at the
    default sigclip must flag only a small fraction of a clean synthetic
    background+source field as cosmic rays.
    """
    crmask, _cleaned = detect_cosmics(
        synthetic_background.science,
        sigclip=4.5,
        sigfrac=DEFAULT_SIGFRAC,
        objlim=DEFAULT_OBJLIM,
        gain=synthetic_background.gain,
        readnoise=synthetic_background.readnoise,
        satlevel=84000.0,
        cleantype="medmask",
        niter=4,
        verbose=False,
    )
    flagged_fraction = np.asarray(crmask, dtype=bool).mean()
    assert flagged_fraction < 0.02, f"unexpectedly high false-positive rate on CR-free data: {flagged_fraction}"


def test_detect_sources_real_finds_injected_sources(synthetic_background):
    sources = detect_sources_real(synthetic_background.science)
    assert len(sources) >= 1
    assert all(isinstance(s, SourceSpec) for s in sources)


def test_detect_sources_real_raises_on_flat_image():
    flat = np.full((40, 40), 10.0)
    with pytest.raises(InsufficientDataError):
        detect_sources_real(flat)
