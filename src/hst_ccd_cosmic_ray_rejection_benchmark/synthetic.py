"""Synthetic HST-CCD-like background generation, clearly labelled and never real data.

Shared by both the test suite (injection-recovery validation gate) and
`scripts/make_figures.py --demo` / `scripts/run_analysis.py --demo`, so the
synthetic-data model is implemented once rather than duplicated between tests
and demo scripts, matching the pattern used by the sibling HST instrumentation
projects in this pack.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from astropy.io import fits

from hst_ccd_cosmic_ray_rejection_benchmark.inject import SyntheticPointSource, inject_point_sources

DEFAULT_GAIN = 2.0
DEFAULT_READNOISE = 4.0
DEFAULT_BACKGROUND = 20.0


@dataclass(frozen=True)
class SyntheticBackground:
    science: np.ndarray
    gain: float
    readnoise: float
    exptime: float
    sources: tuple[SyntheticPointSource, ...]


def build_synthetic_background(
    *,
    seed: int = 20260713,
    naxis1: int = 200,
    naxis2: int = 200,
    n_sources: int = 6,
    background: float = DEFAULT_BACKGROUND,
    read_noise: float = DEFAULT_READNOISE,
    gain: float = DEFAULT_GAIN,
    exptime: float = 460.0,
    psf_fwhm: float = 2.5,
) -> SyntheticBackground:
    """Build a minimal, labelled-synthetic CCD-style background with point sources.

    Read noise and Poisson-like background scatter are simulated with a normal
    approximation (electrons), matching the sibling ACS project's simplified
    detector-noise model. This is a smoke-test / validation-gate background,
    never presented as an observation.
    """
    rng = np.random.default_rng(seed)
    science = rng.normal(loc=background, scale=read_noise, size=(naxis2, naxis1)).astype(np.float64)

    src_rng = np.random.default_rng(seed + 1)
    margin = 20
    fluxes = src_rng.uniform(4000.0, 30000.0, size=n_sources)
    xs = src_rng.uniform(margin, naxis1 - margin, size=n_sources)
    ys = src_rng.uniform(margin, naxis2 - margin, size=n_sources)
    sources = tuple(
        SyntheticPointSource(x=float(x), y=float(y), flux=float(f))
        for x, y, f in zip(xs, ys, fluxes)
    )
    science = inject_point_sources(science, sources, psf_fwhm=psf_fwhm)

    return SyntheticBackground(
        science=science, gain=gain, readnoise=read_noise, exptime=exptime, sources=sources
    )


def build_synthetic_ccd_hdulist(**kwargs) -> fits.HDUList:
    """Wrap `build_synthetic_background` as a minimal FITS HDUList for I/O tests."""
    bg = build_synthetic_background(**kwargs)

    primary_header = fits.Header()
    primary_header["INSTRUME"] = "ACS"
    primary_header["DETECTOR"] = "WFC"
    primary_header["EXPTIME"] = bg.exptime
    primary_header["CCDGAIN"] = bg.gain
    primary_header["FILTER1"] = "CLEAR1L"
    primary_header["FILTER2"] = "F606W"
    primary_header["ROOTNAME"] = "synthetic0"

    sci_header = fits.Header()
    sci_header["EXTNAME"] = "SCI"
    sci_header["EXTVER"] = 1
    sci_header["BUNIT"] = "ELECTRONS"
    sci_header["READNSEA"] = bg.readnoise

    err = np.sqrt(np.clip(bg.science, 1.0, None) / bg.gain + bg.readnoise**2).astype(np.float64)
    dq = np.zeros(bg.science.shape, dtype=np.int16)

    return fits.HDUList(
        [
            fits.PrimaryHDU(header=primary_header),
            fits.ImageHDU(data=bg.science.astype(np.float32), header=sci_header, name="SCI"),
            fits.ImageHDU(data=err.astype(np.float32), header=sci_header.copy(), name="ERR"),
            fits.ImageHDU(data=dq, header=sci_header.copy(), name="DQ"),
        ]
    )
