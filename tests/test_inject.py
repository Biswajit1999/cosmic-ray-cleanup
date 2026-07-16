from __future__ import annotations

import numpy as np
import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError
from hst_ccd_cosmic_ray_rejection_benchmark.inject import (
    SyntheticPointSource,
    gaussian_psf_kernel,
    inject_cosmic_rays,
    inject_point_sources,
    source_exclusion_mask,
)


def test_inject_cosmic_rays_ground_truth_matches_placed_events():
    image = np.zeros((100, 100))
    result = inject_cosmic_rays(image, n_events=20, seed=1)
    assert len(result.events) == 20
    n_truth_pixels = sum(len(e.pixels) for e in result.events)
    assert result.truth_mask.sum() == n_truth_pixels
    # every truth pixel differs from the (zero) background
    assert np.all(result.image[result.truth_mask] > 0)


def test_inject_cosmic_rays_is_deterministic():
    image = np.zeros((80, 80))
    r1 = inject_cosmic_rays(image, n_events=10, seed=42)
    r2 = inject_cosmic_rays(image, n_events=10, seed=42)
    assert np.array_equal(r1.truth_mask, r2.truth_mask)
    assert np.array_equal(r1.image, r2.image)


def test_inject_cosmic_rays_respects_exclusion_mask():
    image = np.zeros((100, 100))
    exclusion = np.zeros((100, 100), dtype=bool)
    exclusion[:, :] = True
    exclusion[40:60, 40:60] = False  # only a small open region
    result = inject_cosmic_rays(image, n_events=5, seed=3, exclusion_mask=exclusion, margin=5)
    assert not np.any(result.truth_mask & exclusion)


def test_inject_cosmic_rays_raises_when_too_crowded():
    image = np.zeros((20, 20))
    exclusion = np.ones((20, 20), dtype=bool)
    exclusion[10, 10] = False  # a single open pixel: cannot fit many events
    with pytest.raises(DataSchemaError):
        inject_cosmic_rays(image, n_events=5, seed=1, exclusion_mask=exclusion, margin=1)


def test_inject_cosmic_rays_rejects_non_2d():
    with pytest.raises(DataSchemaError):
        inject_cosmic_rays(np.zeros((5, 5, 5)), n_events=1, seed=1)


def test_inject_point_sources_adds_flux():
    image = np.zeros((60, 60))
    sources = (SyntheticPointSource(x=30, y=30, flux=10000.0),)
    out = inject_point_sources(image, sources)
    assert out.sum() == pytest.approx(10000.0, rel=1e-2)
    assert out[30, 30] > 0


def test_gaussian_psf_kernel_normalized():
    kernel = gaussian_psf_kernel(2.5)
    assert kernel.sum() == pytest.approx(1.0)


def test_gaussian_psf_kernel_rejects_nonpositive_fwhm():
    with pytest.raises(ValueError):
        gaussian_psf_kernel(0.0)


def test_source_exclusion_mask_covers_expected_radius():
    sources = (SyntheticPointSource(x=25, y=25, flux=1.0),)
    mask = source_exclusion_mask((50, 50), sources, radius=3.0)
    assert mask[25, 25]
    assert mask[25, 27]
    assert not mask[25, 40]
