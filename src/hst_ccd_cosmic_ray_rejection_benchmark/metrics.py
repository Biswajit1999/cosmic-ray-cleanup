"""Detection-quality metrics for the cosmic-ray rejection benchmark.

All metrics operate on boolean pixel masks with a known ground truth (the
injected cosmic-ray footprint from `inject.inject_cosmic_rays`) and a
detector-reported mask (astroscrappy's `crmask`). Three distinct quantities
are reported per docs/VALIDATION_CONTRACT.md and docs/RESEARCH_BLUEPRINT.md:

- precision/recall/F1 against the *exactly known* injected-pixel population;
- a PSF-core false-masking rate against real/synthetic point-source cores
  (unambiguous: any detector flag inside a source core is a false positive,
  no cosmic-ray truth needed);
- a background masking rate over pixels that are neither injected CR pixels
  nor source-core pixels — reported as an *upper bound* on the true false
  positive rate, since a real background frame may already contain
  unlabelled real cosmic rays (see docs/ASSUMPTIONS_AND_LIMITATIONS.md).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError


@dataclass(frozen=True)
class DetectionMetrics:
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    precision: float
    recall: float
    f1: float
    n_truth_pixels: int
    n_detected_pixels: int


def _check_masks(truth_mask: np.ndarray, detected_mask: np.ndarray) -> None:
    if truth_mask.shape != detected_mask.shape:
        raise DataSchemaError(
            f"truth_mask shape {truth_mask.shape} != detected_mask shape {detected_mask.shape}"
        )
    if truth_mask.dtype != bool or detected_mask.dtype != bool:
        raise DataSchemaError("truth_mask and detected_mask must be boolean arrays")


def precision_recall_f1(truth_mask: np.ndarray, detected_mask: np.ndarray) -> DetectionMetrics:
    """Pixel-level precision/recall/F1 of `detected_mask` against `truth_mask`.

    Raises `DataSchemaError` if there are zero injected truth pixels — recall
    is undefined against an empty ground-truth population and must not be
    silently reported as 0 or NaN.
    """
    _check_masks(truth_mask, detected_mask)
    n_truth = int(truth_mask.sum())
    if n_truth == 0:
        raise DataSchemaError("truth_mask has zero positive pixels; recall is undefined")

    tp = int(np.logical_and(truth_mask, detected_mask).sum())
    fp = int(np.logical_and(~truth_mask, detected_mask).sum())
    fn = int(np.logical_and(truth_mask, ~detected_mask).sum())
    tn = int(np.logical_and(~truth_mask, ~detected_mask).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if np.isfinite(precision) and np.isfinite(recall) and (precision + recall) > 0
        else float("nan")
    )
    return DetectionMetrics(
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        true_negative=tn,
        precision=precision,
        recall=recall,
        f1=f1,
        n_truth_pixels=n_truth,
        n_detected_pixels=int(detected_mask.sum()),
    )


def psf_core_false_masking_rate(detected_mask: np.ndarray, source_core_mask: np.ndarray) -> float:
    """Fraction of real/synthetic point-source-core pixels incorrectly flagged as CR.

    Requires no cosmic-ray ground truth: any detector-flagged pixel inside a
    known stellar PSF core is unambiguously a false positive against real
    astrophysical signal.
    """
    if detected_mask.shape != source_core_mask.shape:
        raise DataSchemaError("detected_mask and source_core_mask shapes disagree")
    n_core = int(source_core_mask.sum())
    if n_core == 0:
        raise DataSchemaError("source_core_mask has zero pixels; false-masking rate is undefined")
    flagged_core = int(np.logical_and(detected_mask, source_core_mask).sum())
    return flagged_core / n_core


def background_masking_rate(
    detected_mask: np.ndarray, truth_mask: np.ndarray, source_core_mask: np.ndarray
) -> float:
    """Fraction of non-injected, non-source-core pixels flagged as CR.

    This is an UPPER BOUND on the true background false-positive rate: a real
    HST background frame may already contain unlabelled real cosmic-ray hits
    that astroscrappy correctly flags but which this metric cannot
    distinguish from a genuine false positive. Documented explicitly in
    docs/ASSUMPTIONS_AND_LIMITATIONS.md and the report's Limitations section.
    """
    if not (detected_mask.shape == truth_mask.shape == source_core_mask.shape):
        raise DataSchemaError("detected_mask, truth_mask, source_core_mask shapes disagree")
    background_region = np.logical_and(~truth_mask, ~source_core_mask)
    n_background = int(background_region.sum())
    if n_background == 0:
        raise DataSchemaError("no background pixels remain outside truth/source masks")
    flagged_background = int(np.logical_and(detected_mask, background_region).sum())
    return flagged_background / n_background


__all__ = [
    "DetectionMetrics",
    "precision_recall_f1",
    "psf_core_false_masking_rate",
    "background_masking_rate",
]
