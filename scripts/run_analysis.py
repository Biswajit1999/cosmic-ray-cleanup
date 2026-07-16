"""Run the cosmic-ray rejection sigclip sweep: either the synthetic --demo
smoke path, or the real-data pipeline over data/manifest.csv + data/raw/.

Peak memory is measured with the stdlib `tracemalloc` (Python-level
allocations) rather than a full process-RSS profiler such as psutil, which is
not part of this project's pinned dependency set; noted as a scope limitation
in docs/BENCHMARK_PLAN.md reporting.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import tracemalloc
from pathlib import Path

from hst_ccd_cosmic_ray_rejection_benchmark import __version__
from hst_ccd_cosmic_ray_rejection_benchmark.config import load_config
from hst_ccd_cosmic_ray_rejection_benchmark.core import (
    DEFAULT_OBJLIM,
    DEFAULT_SIGCLIP_VALUES,
    DEFAULT_SIGFRAC,
    PipelineResult,
    detect_sources_real,
    run_pipeline,
    sources_from_synthetic,
)
from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import ProjectError
from hst_ccd_cosmic_ray_rejection_benchmark.fetch import cutout, load_background
from hst_ccd_cosmic_ray_rejection_benchmark.logging_utils import get_logger
from hst_ccd_cosmic_ray_rejection_benchmark.provenance import get_git_commit, read_manifest, sha256_config
from hst_ccd_cosmic_ray_rejection_benchmark.results_io import Metric, write_summary
from hst_ccd_cosmic_ray_rejection_benchmark.synthetic import build_synthetic_background

LOGGER = get_logger(__name__)


def _write_benchmark(path: Path, label: str, wall_time_s: float, peak_memory_mib: float, dataset_size: int) -> None:
    payload = {
        "label": label,
        "wall_time_seconds": wall_time_s,
        "peak_memory_mib": peak_memory_mib,
        "peak_memory_method": "tracemalloc (Python-level allocations, not full process RSS)",
        "dataset_size": dataset_size,
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "package_version": __version__,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    existing.append(payload)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def _sweep_metrics(result: PipelineResult) -> list[Metric]:
    metrics: list[Metric] = []
    for point in result.sweep:
        prefix = f"sigclip_{point.sigclip:g}"
        metrics.append(Metric(
            name=f"{prefix}_recall", estimate=point.recall_mean,
            uncertainty_low=point.recall_ci_low, uncertainty_high=point.recall_ci_high,
            units="dimensionless", sample_size=point.n_trials,
        ))
        metrics.append(Metric(
            name=f"{prefix}_precision", estimate=point.precision_mean,
            uncertainty_low=point.precision_ci_low, uncertainty_high=point.precision_ci_high,
            units="dimensionless", sample_size=point.n_trials,
        ))
        metrics.append(Metric(
            name=f"{prefix}_f1", estimate=point.f1_mean,
            units="dimensionless", sample_size=point.n_trials,
        ))
        metrics.append(Metric(
            name=f"{prefix}_psf_core_false_masking_rate", estimate=point.psf_false_masking_mean,
            units="dimensionless", sample_size=point.n_trials,
        ))
        metrics.append(Metric(
            name=f"{prefix}_background_masking_rate_upper_bound", estimate=point.background_masking_mean,
            units="dimensionless", sample_size=point.n_trials,
        ))
        metrics.append(Metric(
            name=f"{prefix}_aperture_flux_fractional_bias", estimate=point.flux_bias_mean,
            uncertainty_low=point.flux_bias_ci_low, uncertainty_high=point.flux_bias_ci_high,
            units="dimensionless", sample_size=point.n_trials,
        ))
        metrics.append(Metric(
            name=f"{prefix}_mean_runtime_per_megapixel", estimate=point.mean_runtime_per_megapixel,
            units="seconds/megapixel", sample_size=point.n_trials,
        ))
    return metrics


def run_demo() -> None:
    tracemalloc.start()
    start = time.perf_counter()

    config = load_config(Path("config/analysis.yml"))
    bg = build_synthetic_background(seed=config.execution.seed, naxis1=200, naxis2=200, n_sources=8)
    sources = sources_from_synthetic(bg.sources)

    result = run_pipeline(
        background=bg.science,
        gain=bg.gain,
        readnoise=bg.readnoise,
        sources=sources,
        config=config,
        sigclip_values=DEFAULT_SIGCLIP_VALUES,
        n_trials_per_setting=3,
        n_cr_events=25,
    )

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    metrics = _sweep_metrics(result)
    out = Path("results")
    payload = write_summary(
        out / "summary.json",
        project="HST CCD Cosmic-Ray Rejection Benchmark (demo smoke test)",
        data_kind="synthetic_demo",
        metrics=metrics,
        provenance={
            "config_sha256": sha256_config("config/analysis.yml"),
            "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
            "package_version": __version__,
            "sigclip_values": list(DEFAULT_SIGCLIP_VALUES),
            "sigfrac": DEFAULT_SIGFRAC,
            "objlim": DEFAULT_OBJLIM,
        },
        warnings=list(result.warnings),
    )
    (out / "warnings.json").write_text(json.dumps(list(result.warnings), indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2)[:2000])

    _write_benchmark(out / "benchmarks.json", "demo", elapsed, peak / (1024 * 1024), bg.science.size)


def run_real_data(config_path: Path, manifest_path: Path, raw_dir: Path, results_dir: Path) -> None:
    config = load_config(config_path)
    try:
        manifest_rows = read_manifest(manifest_path)
    except ProjectError as exc:
        raise SystemExit(
            f"Cannot run the real-data pipeline: {exc}. Run scripts/fetch_data.py "
            "(with explicit operator authorization) first."
        ) from exc

    if not manifest_rows:
        raise SystemExit(
            "data/manifest.csv has no rows. Run scripts/fetch_data.py "
            "(with explicit operator authorization) before running the real-data pipeline."
        )

    fits_paths = sorted(raw_dir.glob("*.fits"))
    if not fits_paths:
        raise SystemExit(f"No FITS files found under {raw_dir}. Run scripts/fetch_data.py first.")

    tracemalloc.start()
    start = time.perf_counter()

    all_warnings: list[str] = []
    all_sweeps = []
    n_pixels_total = 0
    for fits_path in fits_paths:
        bg = load_background(fits_path)
        if bg.readnoise_is_fallback:
            all_warnings.append(
                f"{bg.product_id}: no READNSE* header keyword found; used documented ACS/WFC "
                "typical read noise fallback"
            )
        # A modest cutout keeps the sweep computationally tractable while
        # retaining real background statistics and real point sources.
        ny, nx = bg.science.shape
        cy0, cy1 = ny // 2 - 300, ny // 2 + 300
        cx0, cx1 = nx // 2 - 300, nx // 2 + 300
        region = cutout(bg, max(0, cy0), min(ny, cy1), max(0, cx0), min(nx, cx1))

        try:
            sources = detect_sources_real(region.science)
        except ProjectError as exc:
            all_warnings.append(f"{bg.product_id}: source detection failed, skipped ({exc})")
            continue

        result = run_pipeline(
            background=region.science,
            gain=region.detection_gain,
            readnoise=region.readnoise,
            sources=sources,
            config=config,
            sigclip_values=DEFAULT_SIGCLIP_VALUES,
            n_trials_per_setting=5,
            n_cr_events=40,
            satlevel=region.saturate,
        )
        all_warnings.extend(result.warnings)
        all_sweeps.append((bg.product_id, result))
        n_pixels_total += region.science.size

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if not all_sweeps:
        raise SystemExit("No real background produced usable sweep results; see warnings above.")

    # Combine sweep points across products by simple concatenation of metrics,
    # each metric name prefixed with the product id so results remain
    # traceable to a specific real exposure.
    metrics: list[Metric] = []
    for product_id, result in all_sweeps:
        for m in _sweep_metrics(result):
            metrics.append(Metric(
                name=f"{product_id}_{m.name}", estimate=m.estimate, units=m.units,
                sample_size=m.sample_size, uncertainty_low=m.uncertainty_low,
                uncertainty_high=m.uncertainty_high,
            ))

    provenance = {
        "config_sha256": sha256_config(config_path),
        "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
        "package_version": __version__,
        "sigclip_values": list(DEFAULT_SIGCLIP_VALUES),
        "sigfrac": DEFAULT_SIGFRAC,
        "objlim": DEFAULT_OBJLIM,
        "n_real_products": len(all_sweeps),
        "product_ids": [pid for pid, _ in all_sweeps],
    }

    results_dir.mkdir(exist_ok=True)
    write_summary(
        results_dir / "summary.json",
        project=config.project.title,
        data_kind=config.input.data_mode,
        metrics=metrics,
        provenance=provenance,
        warnings=all_warnings,
    )
    (results_dir / "warnings.json").write_text(json.dumps(all_warnings, indent=2), encoding="utf-8")

    _write_benchmark(results_dir / "benchmarks.json", "real_data", elapsed, peak / (1024 * 1024), n_pixels_total)
    print(f"Wrote {results_dir / 'summary.json'} ({len(metrics)} metrics, {len(all_warnings)} warnings)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Run synthetic smoke data only")
    parser.add_argument("--config", type=Path, default=Path("config/analysis.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    run_real_data(args.config, args.manifest, args.raw_dir, args.results_dir)


if __name__ == "__main__":
    main()
