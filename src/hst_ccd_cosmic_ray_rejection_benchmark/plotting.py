from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import scienceplots  # noqa: F401

plt.style.use(["science", "no-latex"])


def plot_demo(values: np.ndarray, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(np.arange(values.size), values)
    ax.set_xlabel("Synthetic index")
    ax.set_ylabel("Synthetic value")
    ax.set_title("Smoke-test output - not a scientific result")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def imshow_with_mask_overlay(
    ax,
    image: np.ndarray,
    mask: np.ndarray,
    *,
    vmin: float | None = None,
    vmax: float | None = None,
    mask_color: tuple[float, float, float, float] = (1.0, 0.15, 0.15, 0.85),
) -> None:
    """Draw `image` in grayscale with `mask` (bool) overlaid as a translucent color.

    Shared helper for the "injected image and mask" and "cleaning comparison"
    figures required by docs/FIGURE_AND_UI_SPEC.md, so both scripts render the
    overlay identically.
    """
    ax.imshow(image, origin="lower", cmap="gray", vmin=vmin, vmax=vmax)
    overlay = np.zeros((*mask.shape, 4))
    overlay[mask] = mask_color
    ax.imshow(overlay, origin="lower")
