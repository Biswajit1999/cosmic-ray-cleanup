from __future__ import annotations

import numpy as np
import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError
from hst_ccd_cosmic_ray_rejection_benchmark.fetch import load_background
from hst_ccd_cosmic_ray_rejection_benchmark.synthetic import (
    build_synthetic_background,
    build_synthetic_ccd_hdulist,
)


def test_build_synthetic_background_deterministic():
    b1 = build_synthetic_background(seed=5)
    b2 = build_synthetic_background(seed=5)
    assert np.array_equal(b1.science, b2.science)
    assert b1.sources == b2.sources


def test_build_synthetic_background_shape_and_sources():
    bg = build_synthetic_background(seed=1, naxis1=100, naxis2=120, n_sources=4)
    assert bg.science.shape == (120, 100)
    assert len(bg.sources) == 4


def test_build_synthetic_ccd_hdulist_has_required_extensions():
    hdul = build_synthetic_ccd_hdulist(seed=1, naxis1=64, naxis2=64, n_sources=2)
    names = {hdu.name for hdu in hdul}
    assert {"SCI", "ERR", "DQ"}.issubset(names)


def test_load_background_reads_synthetic_hdulist(tmp_path):
    hdul = build_synthetic_ccd_hdulist(seed=1, naxis1=64, naxis2=64, n_sources=2)
    path = tmp_path / "synthetic.fits"
    hdul.writeto(path)

    bg = load_background(path)
    assert bg.science.shape == (64, 64)
    assert bg.instrument == "ACS"
    assert bg.detector == "WFC"
    assert bg.bunit.upper().startswith("ELECTRON")
    assert bg.detection_gain == 1.0  # already in electrons, so detection_gain must not double-convert
    assert not bg.readnoise_is_fallback


def test_load_background_missing_file_raises(tmp_path):
    with pytest.raises(DataSchemaError):
        load_background(tmp_path / "does_not_exist.fits")
