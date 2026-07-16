"""Controlled synthetic cosmic-ray and point-source injection.

These functions are applied on top of *either* a fully synthetic background
(`hst_ccd_cosmic_ray_rejection_benchmark.synthetic`) *or* a real downloaded HST
background array (`hst_ccd_cosmic_ray_rejection_benchmark.fetch.load_background`).
The injection ground truth (exact pixel footprint, amplitude, position) is always
known exactly regardless of which background is used — this is the "real HST
cutouts + controlled injection" data mode documented in docs/DATASET_PLAN.md.

A synthetic cosmic-ray track is modelled as a short, sharp, non-PSF-convolved
multi-pixel energy deposit (the real physical CR signature: a single detector
read with no optical broadening), which is exactly the property L.A.Cosmic's
Laplacian-edge-detection algorithm (van Dokkum 2001) exploits to distinguish CR
hits from PSF-convolved astrophysical point sources. This is a deliberately
simple geometric line-track model, not a Monte Carlo particle-transport
simulation, and is documented as such in docs/ASSUMPTIONS_AND_LIMITATIONS.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError


@dataclass(frozen=True)
class SyntheticPointSource:
    x: float
    y: float
    flux: float


@dataclass(frozen=True)
class InjectedCosmicRay:
    x: int
    y: int
    amplitude: float
    length: int
    angle_rad: float
    pixels: tuple[tuple[int, int], ...]  # (row, col) pairs touched by this track


@dataclass(frozen=True)
class InjectionResult:
    image: np.ndarray
    truth_mask: np.ndarray
    events: tuple[InjectedCosmicRay, ...]


def gaussian_psf_kernel(fwhm: float, half_box: int = 4) -> np.ndarray:
    if fwhm <= 0:
        raise ValueError("fwhm must be positive")
    sigma = fwhm / 2.3548
    yy, xx = np.mgrid[-half_box : half_box + 1, -half_box : half_box + 1]
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    kernel /= kernel.sum()
    return kernel


def inject_point_sources(
    image: np.ndarray,
    sources: tuple[SyntheticPointSource, ...],
    psf_fwhm: float = 2.5,
    half_box: int = 4,
) -> np.ndarray:
    """Add Gaussian-PSF point sources with known flux onto `image` (additive, copy)."""
    out = np.array(image, dtype=float, copy=True)
    if out.ndim != 2:
        raise DataSchemaError("image must be a 2D array")
    kernel = gaussian_psf_kernel(psf_fwhm, half_box)
    ny, nx = out.shape
    for src in sources:
        xi, yi = int(round(src.x)), int(round(src.y))
        y0, y1 = yi - half_box, yi + half_box + 1
        x0, x1 = xi - half_box, xi + half_box + 1
        cy0, cy1 = max(0, -y0), kernel.shape[0] - max(0, y1 - ny)
        cx0, cx1 = max(0, -x0), kernel.shape[1] - max(0, x1 - nx)
        out[max(0, y0) : min(ny, y1), max(0, x0) : min(nx, x1)] += (
            src.flux * kernel[cy0:cy1, cx0:cx1]
        )
    return out


def _track_pixels(
    x0: int, y0: int, length: int, angle_rad: float, shape: tuple[int, ...]
) -> list[tuple[int, int]]:
    ny, nx = shape
    dx, dy = np.cos(angle_rad), np.sin(angle_rad)
    pixels: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for t in range(length):
        xi = int(round(x0 + dx * t))
        yi = int(round(y0 + dy * t))
        if 0 <= yi < ny and 0 <= xi < nx and (yi, xi) not in seen:
            pixels.append((yi, xi))
            seen.add((yi, xi))
    return pixels


def inject_cosmic_rays(
    image: np.ndarray,
    n_events: int,
    seed: int,
    amplitude_range: tuple[float, float] = (300.0, 3000.0),
    length_range: tuple[int, int] = (1, 5),
    margin: int = 10,
    exclusion_mask: np.ndarray | None = None,
) -> InjectionResult:
    """Inject `n_events` synthetic cosmic-ray tracks with known ground truth.

    `exclusion_mask` (e.g. real-source PSF cores) prevents injected tracks from
    overlapping pixels that are already claimed by real astrophysical signal, so
    the injected-pixel ground truth is never confounded with real source flux.

    Raises DataSchemaError if the image is not 2D, too small for `margin`, or
    if fewer than `n_events` non-overlapping tracks could be placed after a
    bounded number of attempts (rather than silently returning a partial
    injection).
    """
    arr = np.array(image, dtype=float, copy=True)
    if arr.ndim != 2:
        raise DataSchemaError("image must be a 2D array")
    ny, nx = arr.shape
    if ny <= 2 * margin or nx <= 2 * margin:
        raise DataSchemaError(f"image too small ({ny}x{nx}) for margin={margin}")
    if n_events <= 0:
        raise ValueError("n_events must be positive")
    if exclusion_mask is not None and exclusion_mask.shape != arr.shape:
        raise DataSchemaError(
            f"exclusion_mask shape {exclusion_mask.shape} does not match image shape {arr.shape}"
        )

    rng = np.random.default_rng(seed)
    truth = np.zeros(arr.shape, dtype=bool)
    events: list[InjectedCosmicRay] = []
    attempts = 0
    max_attempts = n_events * 200
    placed = 0
    while placed < n_events and attempts < max_attempts:
        attempts += 1
        x0 = int(rng.integers(margin, nx - margin))
        y0 = int(rng.integers(margin, ny - margin))
        if exclusion_mask is not None and exclusion_mask[y0, x0]:
            continue
        length = int(rng.integers(length_range[0], length_range[1] + 1))
        angle = float(rng.uniform(0, 2 * np.pi))
        amplitude = float(rng.uniform(*amplitude_range))
        pixels = _track_pixels(x0, y0, length, angle, arr.shape)
        if not pixels:
            continue
        if truth[tuple(np.array(pixels).T)].any():
            continue  # avoid overlapping a previously-placed track
        if exclusion_mask is not None and any(exclusion_mask[r, c] for r, c in pixels):
            continue

        # Sharp per-pixel jitter (real CR tracks are not smooth or PSF-like);
        # deliberately no PSF convolution, unlike inject_point_sources above.
        jitter = rng.uniform(0.6, 1.0, size=len(pixels))
        for (r, c), j in zip(pixels, jitter):
            arr[r, c] += amplitude * j
            truth[r, c] = True
        events.append(
            InjectedCosmicRay(
                x=x0, y=y0, amplitude=amplitude, length=length, angle_rad=angle,
                pixels=tuple(pixels),
            )
        )
        placed += 1

    if placed < n_events:
        raise DataSchemaError(
            f"could only place {placed}/{n_events} non-overlapping synthetic CR events "
            f"after {attempts} attempts (image too crowded or too small)"
        )

    return InjectionResult(image=arr, truth_mask=truth, events=tuple(events))


def source_exclusion_mask(
    shape: tuple[int, ...], sources: tuple[SyntheticPointSource, ...], radius: float
) -> np.ndarray:
    """Boolean mask True within `radius` pixels of any source centre."""
    ny, nx = shape
    mask = np.zeros(shape, dtype=bool)
    yy, xx = np.mgrid[0:ny, 0:nx]
    for src in sources:
        mask |= (xx - src.x) ** 2 + (yy - src.y) ** 2 <= radius**2
    return mask
