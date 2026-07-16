"""Generate the required figures (docs/FIGURE_AND_UI_SPEC.md) as SVG + 300 dpi PNG,
each with a sidecar JSON recording git commit, config hash, sample size and units.

Figures (per docs/RESEARCH_BLUEPRINT.md):
1. injected image and mask
2. cleaning comparison
3. precision-recall panel
4. flux bias
5. runtime

--demo builds figures from the synthetic, clearly-labelled data model in
`hst_ccd_cosmic_ray_rejection_benchmark.synthetic` (never presented as a
scientific result). The real-data path reads the actual downloaded FLT
background and must only be run after `scripts/run_analysis.py` (real mode)
has produced validated results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astroscrappy import detect_cosmics

from hst_ccd_cosmic_ray_rejection_benchmark import __version__
from hst_ccd_cosmic_ray_rejection_benchmark.core import (
    DEFAULT_OBJLIM,
    DEFAULT_SIGCLIP_VALUES,
    DEFAULT_SIGFRAC,
    detect_sources_real,
    run_pipeline,
    sources_from_synthetic,
)
from hst_ccd_cosmic_ray_rejection_benchmark.config import load_config
from hst_ccd_cosmic_ray_rejection_benchmark.fetch import cutout, load_background
from hst_ccd_cosmic_ray_rejection_benchmark.inject import inject_cosmic_rays, source_exclusion_mask, SyntheticPointSource
from hst_ccd_cosmic_ray_rejection_benchmark.plotting import imshow_with_mask_overlay
from hst_ccd_cosmic_ray_rejection_benchmark.provenance import get_git_commit, read_manifest, sha256_config
from hst_ccd_cosmic_ray_rejection_benchmark.synthetic import build_synthetic_background


def _sidecar(path: Path, *, data_kind: str, sample_size: int, units: str, config_path: Path, extra: dict | None = None) -> None:
    payload = {
        "figure": path.stem,
        "data_kind": data_kind,
        "sample_size": sample_size,
        "units": units,
        "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
        "config_sha256": sha256_config(config_path) if config_path.is_file() else None,
        "package_version": __version__,
    }
    if extra:
        payload.update(extra)
    path.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _save(fig, out_dir: Path, name: str) -> Path:
    svg_path = out_dir / f"{name}.svg"
    png_path = out_dir / f"{name}.png"
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)
    return png_path


def _sweep_figures(
    out_dir: Path,
    config_path: Path,
    background: np.ndarray,
    gain: float,
    readnoise: float,
    sources,
    data_kind: str,
    title_suffix: str,
    satlevel: float = 84000.0,
) -> None:
    config = load_config(config_path)
    result = run_pipeline(
        background=background, gain=gain, readnoise=readnoise, sources=sources, config=config,
        sigclip_values=DEFAULT_SIGCLIP_VALUES, n_trials_per_setting=5, n_cr_events=40, satlevel=satlevel,
    )

    # Fig 1: injected image and mask (one representative trial at the middle sigclip)
    mid_sigclip = DEFAULT_SIGCLIP_VALUES[len(DEFAULT_SIGCLIP_VALUES) // 2]
    exclusion = source_exclusion_mask(background.shape, tuple(
        SyntheticPointSource(x=s.x, y=s.y, flux=0.0) for s in sources), radius=5.0)
    injection = inject_cosmic_rays(background, n_events=40, seed=config.execution.seed, exclusion_mask=exclusion)
    crmask, cleaned = detect_cosmics(
        injection.image, sigclip=mid_sigclip, sigfrac=DEFAULT_SIGFRAC, objlim=DEFAULT_OBJLIM,
        gain=gain, readnoise=readnoise, satlevel=satlevel, cleantype="medmask", niter=4, verbose=False,
    )
    crmask = np.asarray(crmask, dtype=bool)

    vmin, vmax = np.percentile(injection.image, [1, 99])
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    imshow_with_mask_overlay(axes[0], injection.image, injection.truth_mask, vmin=vmin, vmax=vmax)
    axes[0].set_title(f"Injected image\n({injection.truth_mask.sum()} truth CR pixels)")
    imshow_with_mask_overlay(axes[1], injection.image, crmask, vmin=vmin, vmax=vmax)
    axes[1].set_title(f"astroscrappy detection (sigclip={mid_sigclip:g})\n({int(crmask.sum())} flagged pixels)")
    for ax in axes:
        ax.set_xlabel("Column (pixels)")
    axes[0].set_ylabel("Row (pixels)")
    fig.suptitle(f"Injected image and detection mask{title_suffix}")
    fig.tight_layout()
    path = _save(fig, out_dir, "fig01_injected_image_and_mask")
    _sidecar(path, data_kind=data_kind, sample_size=len(injection.events), units="electrons vs pixels",
             config_path=config_path, extra={"sigclip": mid_sigclip})

    # Fig 2: cleaning comparison (raw injected vs cleaned array)
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].imshow(injection.image, origin="lower", cmap="gray", vmin=vmin, vmax=vmax)
    axes[0].set_title("Before cleaning (injected)")
    axes[1].imshow(cleaned, origin="lower", cmap="gray", vmin=vmin, vmax=vmax)
    axes[1].set_title(f"After cleaning (sigclip={mid_sigclip:g})")
    for ax in axes:
        ax.set_xlabel("Column (pixels)")
    axes[0].set_ylabel("Row (pixels)")
    fig.suptitle(f"Cleaning comparison{title_suffix}")
    fig.tight_layout()
    path = _save(fig, out_dir, "fig02_cleaning_comparison")
    _sidecar(path, data_kind=data_kind, sample_size=1, units="electrons", config_path=config_path)

    # Fig 3: precision-recall panel across the sigclip sweep
    sigclips = [p.sigclip for p in result.sweep]
    recalls = [p.recall_mean for p in result.sweep]
    recall_err = [
        [p.recall_mean - p.recall_ci_low if np.isfinite(p.recall_ci_low) else 0 for p in result.sweep],
        [p.recall_ci_high - p.recall_mean if np.isfinite(p.recall_ci_high) else 0 for p in result.sweep],
    ]
    precisions = [p.precision_mean for p in result.sweep]
    precision_err = [
        [p.precision_mean - p.precision_ci_low if np.isfinite(p.precision_ci_low) else 0 for p in result.sweep],
        [p.precision_ci_high - p.precision_mean if np.isfinite(p.precision_ci_high) else 0 for p in result.sweep],
    ]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.errorbar(sigclips, recalls, yerr=recall_err, marker="o", label="Recall (injected CR pixels)", capsize=3)
    ax.errorbar(sigclips, precisions, yerr=precision_err, marker="s", label="Precision", capsize=3)
    ax.plot(sigclips, [p.psf_false_masking_mean for p in result.sweep], marker="^",
            label="PSF-core false-masking rate", color="tab:red")
    ax.set_xlabel("astroscrappy sigclip (detection significance threshold)")
    ax.set_ylabel("Rate (dimensionless)")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title(f"Precision/recall/false-masking vs sigclip{title_suffix}\n(n={sum(p.n_trials for p in result.sweep)} trials)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = _save(fig, out_dir, "fig03_precision_recall_panel")
    _sidecar(path, data_kind=data_kind, sample_size=sum(p.n_trials for p in result.sweep),
             units="dimensionless", config_path=config_path)

    # Fig 4: flux bias vs sigclip
    bias_mean = [p.flux_bias_mean for p in result.sweep]
    bias_err = [
        [p.flux_bias_mean - p.flux_bias_ci_low if np.isfinite(p.flux_bias_ci_low) else 0 for p in result.sweep],
        [p.flux_bias_ci_high - p.flux_bias_mean if np.isfinite(p.flux_bias_ci_high) else 0 for p in result.sweep],
    ]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
    ax.errorbar(sigclips, bias_mean, yerr=bias_err, marker="o", color="tab:purple", capsize=3)
    ax.set_xlabel("astroscrappy sigclip (detection significance threshold)")
    ax.set_ylabel("Aperture-flux fractional bias (cleaned - truth) / truth")
    ax.set_title(f"Photometric bias from CR cleaning vs sigclip{title_suffix}")
    fig.tight_layout()
    path = _save(fig, out_dir, "fig04_flux_bias")
    _sidecar(path, data_kind=data_kind, sample_size=len(sources), units="dimensionless", config_path=config_path)

    # Fig 5: runtime per megapixel vs sigclip
    runtimes = [p.mean_runtime_per_megapixel for p in result.sweep]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(sigclips, runtimes, marker="o", color="tab:green")
    ax.set_xlabel("astroscrappy sigclip (detection significance threshold)")
    ax.set_ylabel("Mean runtime per megapixel (seconds)")
    ax.set_title(f"Detection runtime vs sigclip{title_suffix}")
    fig.tight_layout()
    path = _save(fig, out_dir, "fig05_runtime")
    _sidecar(path, data_kind=data_kind, sample_size=sum(p.n_trials for p in result.sweep),
             units="seconds/megapixel", config_path=config_path)

    print(f"Wrote 5 figures (SVG+PNG+JSON) to {out_dir} ({title_suffix.strip()})")


def make_demo_figures(out_dir: Path, config_path: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(config_path)
    bg = build_synthetic_background(seed=config.execution.seed, naxis1=200, naxis2=200, n_sources=8)
    sources = sources_from_synthetic(bg.sources)
    _sweep_figures(
        out_dir, config_path, bg.science, bg.gain, bg.readnoise, sources,
        data_kind="synthetic_demo", title_suffix=" — SYNTHETIC DEMO",
    )


def make_real_figures(out_dir: Path, config_path: Path, manifest_path: Path, raw_dir: Path) -> None:
    manifest_rows = read_manifest(manifest_path)
    if not manifest_rows:
        raise SystemExit(
            "data/manifest.csv has no rows. Run scripts/fetch_data.py (with explicit "
            "operator authorization) and scripts/run_analysis.py before generating real figures."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(config_path)

    fits_paths = sorted(raw_dir.glob("*.fits"))
    if not fits_paths:
        raise SystemExit(f"No FITS files found under {raw_dir}. Run scripts/fetch_data.py first.")

    bg = load_background(fits_paths[0])
    ny, nx = bg.science.shape
    cy0, cy1 = ny // 2 - 300, ny // 2 + 300
    cx0, cx1 = nx // 2 - 300, nx // 2 + 300
    region = cutout(bg, max(0, cy0), min(ny, cy1), max(0, cx0), min(nx, cx1))
    sources = detect_sources_real(region.science)

    _sweep_figures(
        out_dir, config_path, region.science, region.detection_gain, region.readnoise, sources,
        data_kind=config.input.data_mode, title_suffix=f": {bg.product_id}", satlevel=region.saturate,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("figures"))
    parser.add_argument("--config", type=Path, default=Path("config/analysis.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    if args.demo:
        from hst_ccd_cosmic_ray_rejection_benchmark.plotting import plot_demo

        plot_demo(np.random.default_rng(20260713).normal(0, 1, 128), args.out_dir / "fig00_smoke_test.png")
        make_demo_figures(args.out_dir, args.config)
        return

    make_real_figures(args.out_dir, args.config, args.manifest, args.raw_dir)


if __name__ == "__main__":
    main()
