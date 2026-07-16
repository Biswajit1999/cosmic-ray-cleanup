"""Aperture photometry and CR-rejection flux-bias measurement.

`aperture_flux` wraps `photutils.aperture.CircularAperture` /
`aperture_photometry` for a single deterministic circular-aperture
measurement with local annulus background subtraction. `flux_bias` compares
the aperture flux measured on a cosmic-ray-cleaned image against the flux
measured on the pre-injection (ground-truth) image at the same source
position, giving the photometric bias introduced by a given rejection
parameter setting — required by docs/RESEARCH_BLUEPRINT.md's
"aperture-flux bias" validation item.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from photutils.aperture import CircularAnnulus, CircularAperture, aperture_photometry

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError


@dataclass(frozen=True)
class ApertureFluxResult:
    x: float
    y: float
    raw_sum: float
    background_per_pixel: float
    net_flux: float
    aperture_area: float


def aperture_flux(
    image: np.ndarray,
    x: float,
    y: float,
    radius: float = 4.0,
    annulus_r_in: float = 8.0,
    annulus_r_out: float = 12.0,
) -> ApertureFluxResult:
    """Background-subtracted circular-aperture flux at (x, y) in `image`.

    Background is estimated as the median of an annulus around the source,
    matching the standard local-background aperture-photometry convention.
    Raises `DataSchemaError` if the aperture centre lies outside the image or
    the annulus contains no finite pixels.
    """
    if image.ndim != 2:
        raise DataSchemaError("image must be a 2D array")
    ny, nx = image.shape
    if not (0 <= x < nx and 0 <= y < ny):
        raise DataSchemaError(f"aperture centre ({x},{y}) lies outside image shape {(ny, nx)}")

    aperture = CircularAperture((x, y), r=radius)
    annulus = CircularAnnulus((x, y), r_in=annulus_r_in, r_out=annulus_r_out)

    ap_table = aperture_photometry(image, aperture)
    raw_sum = float(ap_table["aperture_sum"][0])

    annulus_mask = annulus.to_mask(method="center")
    annulus_data = annulus_mask.multiply(image)
    if annulus_data is None:
        raise DataSchemaError(f"annulus around ({x},{y}) does not overlap the image")
    annulus_values = annulus_data[annulus_mask.data > 0]
    finite_values = annulus_values[np.isfinite(annulus_values)]
    if finite_values.size == 0:
        raise DataSchemaError(f"annulus around ({x},{y}) contains no finite pixels")

    background_per_pixel = float(np.median(finite_values))
    net_flux = raw_sum - background_per_pixel * aperture.area

    return ApertureFluxResult(
        x=float(x),
        y=float(y),
        raw_sum=raw_sum,
        background_per_pixel=background_per_pixel,
        net_flux=net_flux,
        aperture_area=float(aperture.area),
    )


@dataclass(frozen=True)
class FluxBiasResult:
    x: float
    y: float
    truth_flux: float
    cleaned_flux: float
    absolute_bias: float
    fractional_bias: float


def flux_bias(
    truth_image: np.ndarray,
    cleaned_image: np.ndarray,
    x: float,
    y: float,
    radius: float = 4.0,
    annulus_r_in: float = 8.0,
    annulus_r_out: float = 12.0,
) -> FluxBiasResult:
    """Fractional aperture-flux bias introduced by CR cleaning at one source.

    `truth_image` is the pre-injection background (the uncontaminated
    ground-truth flux); `cleaned_image` is the same field after cosmic-ray
    injection and rejection/interpolation. Raises `DataSchemaError` if the
    truth-image flux at this source is not positive (fractional bias would be
    undefined or misleadingly large).
    """
    truth = aperture_flux(truth_image, x, y, radius, annulus_r_in, annulus_r_out)
    cleaned = aperture_flux(cleaned_image, x, y, radius, annulus_r_in, annulus_r_out)
    if not (truth.net_flux > 0):
        raise DataSchemaError(f"non-positive truth aperture flux at ({x},{y}): {truth.net_flux}")

    absolute_bias = cleaned.net_flux - truth.net_flux
    fractional_bias = absolute_bias / truth.net_flux
    return FluxBiasResult(
        x=float(x),
        y=float(y),
        truth_flux=truth.net_flux,
        cleaned_flux=cleaned.net_flux,
        absolute_bias=absolute_bias,
        fractional_bias=fractional_bias,
    )


__all__ = ["ApertureFluxResult", "aperture_flux", "FluxBiasResult", "flux_bias"]
