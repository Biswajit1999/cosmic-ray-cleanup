from __future__ import annotations

import numpy as np
import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError
from hst_ccd_cosmic_ray_rejection_benchmark.inject import SyntheticPointSource, inject_point_sources
from hst_ccd_cosmic_ray_rejection_benchmark.photometry import aperture_flux, flux_bias


def test_aperture_flux_recovers_known_source_flux():
    image = np.full((60, 60), 10.0)  # flat background
    sources = (SyntheticPointSource(x=30, y=30, flux=20000.0),)
    image = inject_point_sources(image, sources, psf_fwhm=2.5, half_box=8)
    result = aperture_flux(image, 30, 30, radius=8.0, annulus_r_in=12.0, annulus_r_out=18.0)
    assert result.net_flux == pytest.approx(20000.0, rel=0.05)


def test_aperture_flux_rejects_centre_outside_image():
    image = np.zeros((20, 20))
    with pytest.raises(DataSchemaError):
        aperture_flux(image, 100, 100)


def test_flux_bias_zero_for_unmodified_image():
    image = np.full((60, 60), 10.0)
    sources = (SyntheticPointSource(x=30, y=30, flux=15000.0),)
    truth_image = inject_point_sources(image, sources, half_box=8)
    result = flux_bias(truth_image, truth_image, 30, 30, radius=8.0, annulus_r_in=12.0, annulus_r_out=18.0)
    assert result.fractional_bias == pytest.approx(0.0, abs=1e-9)


def test_flux_bias_detects_flux_loss():
    image = np.full((60, 60), 10.0)
    sources = (SyntheticPointSource(x=30, y=30, flux=15000.0),)
    truth_image = inject_point_sources(image, sources, half_box=8)
    damaged = truth_image.copy()
    damaged[28:33, 28:33] = 10.0  # zero out the source core (simulates over-aggressive masking)
    result = flux_bias(truth_image, damaged, 30, 30, radius=8.0, annulus_r_in=12.0, annulus_r_out=18.0)
    assert result.fractional_bias < -0.1
