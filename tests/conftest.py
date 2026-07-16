"""Shared synthetic-data fixtures for tests.

The synthetic-data model itself lives in
`hst_ccd_cosmic_ray_rejection_benchmark.synthetic` (shared with
`scripts/run_analysis.py --demo` / `scripts/make_figures.py --demo`); this
module only adds the pytest fixture layer on top.
"""
from __future__ import annotations

import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.config import load_config
from hst_ccd_cosmic_ray_rejection_benchmark.core import sources_from_synthetic
from hst_ccd_cosmic_ray_rejection_benchmark.synthetic import build_synthetic_background


@pytest.fixture
def config():
    return load_config("config/analysis.yml")


@pytest.fixture
def synthetic_background():
    return build_synthetic_background(seed=20260713, naxis1=150, naxis2=150, n_sources=6)


@pytest.fixture
def synthetic_sources(synthetic_background):
    return sources_from_synthetic(synthetic_background.sources)
