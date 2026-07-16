"""Pipeline orchestration composing the reusable scientific modules.

`run_pipeline` is the single non-notebook entry point for both the
`--demo` synthetic smoke path and the real-data path; scripts/run_analysis.py
calls into it rather than reimplementing logic. It sweeps astroscrappy's
`sigclip` parameter (holding `sigfrac`/`objlim` fixed at their documented
defaults per IMPLEMENTATION_PLAN.md section 6) over a fixed injected-CR
population, repeated over independent injection trials per setting, and
aggregates precision/recall/F1, PSF-core false-masking, background masking
rate and aperture-flux bias with bootstrap uncertainty.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from astroscrappy import detect_cosmics
from photutils.detection import DAOStarFinder

from hst_ccd_cosmic_ray_rejection_benchmark.config import AnalysisConfig
from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import (
    ConvergenceError,
    DataSchemaError,
    InsufficientDataError,
)
from hst_ccd_cosmic_ray_rejection_benchmark.inject import (
    SyntheticPointSource,
    inject_cosmic_rays,
    source_exclusion_mask,
)
from hst_ccd_cosmic_ray_rejection_benchmark.logging_utils import get_logger
from hst_ccd_cosmic_ray_rejection_benchmark.metrics import (
    DetectionMetrics,
    background_masking_rate,
    precision_recall_f1,
    psf_core_false_masking_rate,
)
from hst_ccd_cosmic_ray_rejection_benchmark.photometry import flux_bias
from hst_ccd_cosmic_ray_rejection_benchmark.uncertainty import bootstrap_statistic

LOGGER = get_logger(__name__)

DEFAULT_SIGCLIP_VALUES: tuple[float, ...] = (3.0, 4.5, 6.0, 8.0, 10.0)
DEFAULT_SIGFRAC = 0.3
DEFAULT_OBJLIM = 5.0
DEFAULT_SOURCE_CORE_RADIUS = 3.0


@dataclass(frozen=True)
class SourceSpec:
    """A point source used both to exclude CR injection and to measure flux bias."""

    x: float
    y: float


def sources_from_synthetic(sources: tuple[SyntheticPointSource, ...]) -> tuple[SourceSpec, ...]:
    return tuple(SourceSpec(x=s.x, y=s.y) for s in sources)


def detect_sources_real(
    image: np.ndarray, fwhm: float = 2.5, threshold_nsigma: float = 8.0
) -> tuple[SourceSpec, ...]:
    """Detect real point sources with DAOStarFinder for the PSF-core false-masking metric.

    Uses a robust sigma-clipped background estimate (median/1.4826*MAD) rather
    than a raw std, since real HST frames contain bright sources that would
    otherwise inflate a naive standard deviation. Raises `InsufficientDataError`
    if no sources are found (the PSF-core metric is then undefined).
    """
    if image.ndim != 2:
        raise DataSchemaError("image must be a 2D array")
    finite = image[np.isfinite(image)]
    if finite.size == 0:
        raise DataSchemaError("image has no finite pixels")
    median = float(np.median(finite))
    mad_std = float(np.median(np.abs(finite - median)) * 1.4826)
    if mad_std <= 0:
        raise InsufficientDataError("background MAD is zero; cannot set a detection threshold")

    finder = DAOStarFinder(fwhm=fwhm, threshold=threshold_nsigma * mad_std)
    table = finder(image - median)
    if table is None or len(table) == 0:
        raise InsufficientDataError("DAOStarFinder found no real point sources above threshold")
    return tuple(SourceSpec(x=float(row["xcentroid"]), y=float(row["ycentroid"])) for row in table)


@dataclass(frozen=True)
class TrialResult:
    sigclip: float
    trial_index: int
    detection: DetectionMetrics
    psf_false_masking_rate: float
    background_masking_rate: float
    flux_biases: tuple[float, ...]
    runtime_seconds: float
    n_pixels: int


def _run_single_trial(
    background: np.ndarray,
    gain: float,
    readnoise: float,
    sources: tuple[SourceSpec, ...],
    sigclip: float,
    sigfrac: float,
    objlim: float,
    seed: int,
    trial_index: int,
    n_cr_events: int,
    source_core_radius: float,
    satlevel: float,
) -> TrialResult:
    exclusion = source_exclusion_mask(background.shape, tuple(
        SyntheticPointSource(x=s.x, y=s.y, flux=0.0) for s in sources
    ), radius=source_core_radius + 2.0)

    injection = inject_cosmic_rays(
        background, n_events=n_cr_events, seed=seed, exclusion_mask=exclusion
    )

    t0 = time.perf_counter()
    crmask, cleaned = detect_cosmics(
        injection.image,
        sigclip=sigclip,
        sigfrac=sigfrac,
        objlim=objlim,
        gain=gain,
        readnoise=readnoise,
        satlevel=satlevel,
        cleantype="medmask",
        niter=4,
        verbose=False,
    )
    runtime = time.perf_counter() - t0
    crmask = np.asarray(crmask, dtype=bool)

    source_core = source_exclusion_mask(background.shape, tuple(
        SyntheticPointSource(x=s.x, y=s.y, flux=0.0) for s in sources
    ), radius=source_core_radius)

    detection = precision_recall_f1(injection.truth_mask, crmask)
    psf_rate = psf_core_false_masking_rate(crmask, source_core)
    bg_rate = background_masking_rate(crmask, injection.truth_mask, source_core)

    biases: list[float] = []
    for s in sources:
        try:
            result = flux_bias(background, cleaned, s.x, s.y)
            biases.append(result.fractional_bias)
        except DataSchemaError:
            continue  # source too close to the edge for this aperture; skip, do not fabricate

    return TrialResult(
        sigclip=sigclip,
        trial_index=trial_index,
        detection=detection,
        psf_false_masking_rate=psf_rate,
        background_masking_rate=bg_rate,
        flux_biases=tuple(biases),
        runtime_seconds=runtime,
        n_pixels=int(background.size),
    )


@dataclass(frozen=True)
class SweepPointSummary:
    sigclip: float
    n_trials: int
    recall_mean: float
    recall_ci_low: float
    recall_ci_high: float
    precision_mean: float
    precision_ci_low: float
    precision_ci_high: float
    f1_mean: float
    psf_false_masking_mean: float
    background_masking_mean: float
    flux_bias_mean: float
    flux_bias_ci_low: float
    flux_bias_ci_high: float
    mean_runtime_seconds: float
    mean_runtime_per_megapixel: float


@dataclass(frozen=True)
class PipelineResult:
    sweep: tuple[SweepPointSummary, ...]
    trials: tuple[TrialResult, ...]
    sources: tuple[SourceSpec, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)


def run_pipeline(
    background: np.ndarray,
    gain: float,
    readnoise: float,
    sources: tuple[SourceSpec, ...],
    config: AnalysisConfig,
    sigclip_values: tuple[float, ...] = DEFAULT_SIGCLIP_VALUES,
    sigfrac: float = DEFAULT_SIGFRAC,
    objlim: float = DEFAULT_OBJLIM,
    n_trials_per_setting: int = 5,
    n_cr_events: int = 40,
    source_core_radius: float = DEFAULT_SOURCE_CORE_RADIUS,
    satlevel: float = 84000.0,
) -> PipelineResult:
    """Sweep `sigclip` over independent injection trials and aggregate metrics.

    Raises `InsufficientDataError` immediately if the background is empty or
    no sources are supplied. Per-trial failures (a bad injection placement,
    a detect_cosmics/photometry failure) are caught individually, recorded as
    warnings, and skipped — never aborting the whole sweep for one bad trial,
    per docs/ERROR_HANDLING.md.
    """
    if background.size == 0:
        raise InsufficientDataError("background image is empty")
    if not sources:
        raise InsufficientDataError("no point sources supplied; cannot measure PSF-core metrics")
    if not sigclip_values:
        raise InsufficientDataError("sigclip_values sweep must be non-empty")

    LOGGER.info(
        "Running sigclip sweep over %d values x %d trials on a %s image",
        len(sigclip_values), n_trials_per_setting, background.shape,
    )

    all_warnings: list[str] = []
    all_trials: list[TrialResult] = []

    for sigclip in sigclip_values:
        for trial_index in range(n_trials_per_setting):
            seed = config.execution.seed + trial_index * 1000 + int(round(sigclip * 10))
            try:
                trial = _run_single_trial(
                    background=background,
                    gain=gain,
                    readnoise=readnoise,
                    sources=sources,
                    sigclip=sigclip,
                    sigfrac=sigfrac,
                    objlim=objlim,
                    seed=seed,
                    trial_index=trial_index,
                    n_cr_events=n_cr_events,
                    source_core_radius=source_core_radius,
                    satlevel=satlevel,
                )
            except (DataSchemaError, ConvergenceError, InsufficientDataError) as exc:
                all_warnings.append(
                    f"sigclip={sigclip}, trial={trial_index}: skipped ({exc})"
                )
                continue
            all_trials.append(trial)

    if not all_trials:
        raise InsufficientDataError("every sweep trial failed; no usable results")

    sweep_summaries: list[SweepPointSummary] = []
    for sigclip in sigclip_values:
        subset = [t for t in all_trials if t.sigclip == sigclip]
        if not subset:
            all_warnings.append(f"sigclip={sigclip}: no successful trials, omitted from sweep summary")
            continue

        recalls = np.array([t.detection.recall for t in subset])
        precisions = np.array([t.detection.precision for t in subset])
        f1s = np.array([t.detection.f1 for t in subset])
        psf_rates = np.array([t.psf_false_masking_rate for t in subset])
        bg_rates = np.array([t.background_masking_rate for t in subset])
        runtimes = np.array([t.runtime_seconds for t in subset])
        megapixels = subset[0].n_pixels / 1.0e6
        all_biases = np.concatenate([np.array(t.flux_biases) for t in subset if t.flux_biases]) \
            if any(t.flux_biases for t in subset) else np.array([])

        def _bootstrap_or_nan(values: np.ndarray) -> tuple[float, float, float]:
            if values.size >= 2:
                res = bootstrap_statistic(
                    values, np.mean, n_resamples=config.validation.bootstrap_resamples,
                    seed=config.execution.seed, confidence_level=config.validation.confidence_level,
                )
                return res.estimate, res.ci_low, res.ci_high
            if values.size == 1:
                return float(values[0]), float("nan"), float("nan")
            return float("nan"), float("nan"), float("nan")

        recall_mean, recall_lo, recall_hi = _bootstrap_or_nan(recalls)
        precision_mean, precision_lo, precision_hi = _bootstrap_or_nan(precisions)
        bias_mean, bias_lo, bias_hi = _bootstrap_or_nan(all_biases)
        if all_biases.size == 0:
            all_warnings.append(f"sigclip={sigclip}: no valid flux-bias measurements (all sources too near edge)")

        sweep_summaries.append(
            SweepPointSummary(
                sigclip=sigclip,
                n_trials=len(subset),
                recall_mean=recall_mean, recall_ci_low=recall_lo, recall_ci_high=recall_hi,
                precision_mean=precision_mean, precision_ci_low=precision_lo, precision_ci_high=precision_hi,
                f1_mean=float(np.nanmean(f1s)),
                psf_false_masking_mean=float(np.mean(psf_rates)),
                background_masking_mean=float(np.mean(bg_rates)),
                flux_bias_mean=bias_mean, flux_bias_ci_low=bias_lo, flux_bias_ci_high=bias_hi,
                mean_runtime_seconds=float(np.mean(runtimes)),
                mean_runtime_per_megapixel=float(np.mean(runtimes) / megapixels),
            )
        )

    return PipelineResult(
        sweep=tuple(sweep_summaries),
        trials=tuple(all_trials),
        sources=sources,
        warnings=tuple(all_warnings),
    )


__all__ = [
    "DEFAULT_SIGCLIP_VALUES",
    "DEFAULT_SIGFRAC",
    "DEFAULT_OBJLIM",
    "SourceSpec",
    "sources_from_synthetic",
    "detect_sources_real",
    "TrialResult",
    "SweepPointSummary",
    "PipelineResult",
    "run_pipeline",
]
