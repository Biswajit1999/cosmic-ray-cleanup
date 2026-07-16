"""Fetch module: real-archive access (MAST) and real-background loading.

Implements the "real HST cutouts" half of docs/DATASET_PLAN.md's "real HST
cutouts + controlled injection" data mode. Network/download logic here is
called from scripts/fetch_data.py (gated behind --i-have-authorization);
`load_background` is called by both scripts/run_analysis.py (real mode) and
scripts/make_figures.py (real mode) to read the downloaded FITS files.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from astropy.io import fits

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import ArchiveAccessError, DataSchemaError

REQUIRED_EXTENSIONS = ("SCI", "ERR", "DQ")

# ACS/WFC typical per-amplifier read noise (electrons), used only as a
# documented last-resort fallback if no READNSE* header keyword is present at
# all (see docs/ASSUMPTIONS_AND_LIMITATIONS.md); never silently substituted
# without being recorded — callers append a warning when this path is taken.
ACS_WFC_TYPICAL_READNOISE_E = 5.0


@dataclass(frozen=True)
class BackgroundImage:
    product_id: str
    science: np.ndarray
    dq_mask: np.ndarray
    gain: float
    readnoise: float
    readnoise_is_fallback: bool
    exptime: float
    saturate: float
    instrument: str
    detector: str
    filter_name: str
    bunit: str

    @property
    def detection_gain(self) -> float:
        """Gain to pass to astroscrappy.detect_cosmics's noise model.

        Calibrated ACS/WFC FLT science arrays are stored in ELECTRONS
        (BUNIT=ELECTRONS), i.e. CCDGAIN has already been applied on-detector;
        passing the header CCDGAIN again would double-convert the noise model.
        If BUNIT indicates the array is still in raw counts, the header gain is
        used as astroscrappy expects. See docs/ASSUMPTIONS_AND_LIMITATIONS.md.
        """
        return 1.0 if self.bunit.strip().upper().startswith("ELECTRON") else self.gain


def load_background(path: str | Path, extver: int = 1) -> BackgroundImage:
    """Load one chip's SCI/DQ pair plus exposure metadata from a real HST FLT file.

    Raises DataSchemaError for a missing file, missing required extensions, or
    a missing gain header keyword, per docs/ERROR_HANDLING.md. Read noise falls
    back to a documented ACS/WFC typical value (flagged via
    `readnoise_is_fallback`) only if no per-amp or chip-level READNSE* keyword
    is present.
    """
    fits_path = Path(path)
    if not fits_path.is_file():
        raise DataSchemaError(f"FITS product not found: {fits_path}")

    with fits.open(fits_path) as hdul:
        extnames = {hdu.name for hdu in hdul}
        missing_ext = [ext for ext in REQUIRED_EXTENSIONS if ext not in extnames]
        if missing_ext:
            raise DataSchemaError(f"{fits_path.name} missing required extensions: {missing_ext}")
        try:
            sci_hdu = hdul["SCI", extver]
            dq_hdu = hdul["DQ", extver]
        except KeyError as exc:
            raise DataSchemaError(f"{fits_path.name} missing SCI/DQ pair for EXTVER={extver}") from exc

        primary_header = hdul[0].header
        sci_header = sci_hdu.header

        science = np.asarray(sci_hdu.data, dtype=float)
        dq = np.asarray(dq_hdu.data, dtype=int)
        if science.shape != dq.shape:
            raise DataSchemaError(
                f"{fits_path.name}: SCI/DQ array shapes disagree: {science.shape} vs {dq.shape}"
            )
        if not np.any(np.isfinite(science)):
            raise DataSchemaError(f"{fits_path.name}: science array has no finite pixels")

        if "EXPTIME" not in primary_header:
            raise DataSchemaError(f"{fits_path.name} missing required EXPTIME header keyword")

        gain = float(primary_header.get("CCDGAIN") or primary_header.get("ATODGAIN") or np.nan)
        if not np.isfinite(gain) or gain <= 0:
            raise DataSchemaError(f"{fits_path.name}: missing/invalid CCDGAIN header keyword")

        # ACS/WFC per-amp read noise (READNSEA/B/C/D) varies by a few tenths of
        # an electron across amplifiers; the mean of whichever amp keywords are
        # present is used as a single representative scalar, since
        # astroscrappy.detect_cosmics takes one scalar readnoise per call.
        merged = {**dict(primary_header), **dict(sci_header)}
        amp_keys = [k for k in ("READNSEA", "READNSEB", "READNSEC", "READNSED") if k in merged]
        readnoise_is_fallback = False
        if amp_keys:
            readnoise = float(np.mean([float(merged[k]) for k in amp_keys]))
        elif "READNSE" in primary_header:
            readnoise = float(primary_header["READNSE"])
        else:
            readnoise = ACS_WFC_TYPICAL_READNOISE_E
            readnoise_is_fallback = True

        product_id = str(primary_header.get("ROOTNAME", fits_path.stem))
        instrument = str(primary_header.get("INSTRUME", ""))
        detector = str(primary_header.get("DETECTOR", ""))
        filter_name = str(primary_header.get("FILTER1", "")) or str(primary_header.get("FILTER2", ""))
        exptime = float(primary_header["EXPTIME"])
        saturate = float(primary_header.get("SATURATE", 65535.0 * gain))
        bunit = str(sci_header.get("BUNIT", "") or primary_header.get("BUNIT", ""))

    return BackgroundImage(
        product_id=product_id,
        science=science,
        dq_mask=dq,
        gain=gain,
        readnoise=readnoise,
        readnoise_is_fallback=readnoise_is_fallback,
        exptime=exptime,
        saturate=saturate,
        instrument=instrument,
        detector=detector,
        filter_name=filter_name,
        bunit=bunit,
    )


def cutout(background: BackgroundImage, y0: int, y1: int, x0: int, x1: int) -> BackgroundImage:
    """Return a rectangular cutout, for a computationally tractable injection experiment."""
    ny, nx = background.science.shape
    if not (0 <= y0 < y1 <= ny and 0 <= x0 < x1 <= nx):
        raise DataSchemaError(f"cutout bounds ({y0},{y1},{x0},{x1}) invalid for shape {(ny, nx)}")
    return BackgroundImage(
        product_id=f"{background.product_id}_cutout_{y0}_{y1}_{x0}_{x1}",
        science=background.science[y0:y1, x0:x1].copy(),
        dq_mask=background.dq_mask[y0:y1, x0:x1].copy(),
        gain=background.gain,
        readnoise=background.readnoise,
        readnoise_is_fallback=background.readnoise_is_fallback,
        exptime=background.exptime,
        saturate=background.saturate,
        instrument=background.instrument,
        detector=background.detector,
        filter_name=background.filter_name,
        bunit=background.bunit,
    )


# --- Real-archive access (used by scripts/fetch_data.py) -------------------

PROPOSAL_ID = "18004"
INSTRUMENT = "ACS/WFC"
FILTER_NAME = "F606W"
LICENCE_TERMS = (
    "STScI/MAST public HST archive data (dataRights=PUBLIC), no proprietary period; "
    "standard STScI archive usage terms apply, https://archive.stsci.edu/copyright.html"
)
SOURCE_URL = "https://mast.stsci.edu"


def select_observations(n_exposures: int):
    """Query MAST for a deterministic sample of public ACS/WFC FLT products.

    Raises ArchiveAccessError if astroquery is unavailable, the query fails,
    returns no rows, or any selected observation is not confirmed PUBLIC.
    """
    try:
        from astroquery.mast import Observations
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ArchiveAccessError("astroquery is not installed in this environment") from exc

    try:
        obs = Observations.query_criteria(
            obs_collection="HST",
            instrument_name=INSTRUMENT,
            proposal_id=[PROPOSAL_ID],
            dataproduct_type="image",
            calib_level=[2],
            filters=FILTER_NAME,
        )
    except Exception as exc:  # noqa: BLE001 - any archive/network failure is fatal here
        raise ArchiveAccessError(f"MAST query failed: {exc}") from exc

    if len(obs) == 0:
        raise ArchiveAccessError(f"MAST query for proposal {PROPOSAL_ID} returned zero observations")

    obs.sort("obs_id")
    selected = obs[:n_exposures]

    for row in selected:
        if str(row["dataRights"]) != "PUBLIC":
            raise ArchiveAccessError(
                f"observation {row['obs_id']} is not PUBLIC (dataRights={row['dataRights']!r}); "
                "refusing to download"
            )
    return selected


def download_flt(observations, out_dir: Path) -> list[Path]:
    """Download exposure-level FLT products and flatten mastDownload/ nesting.

    Only FLT (not CR-combined) products are used since this project's method
    injects synthetic cosmic rays into an *uncombined* single-exposure
    background; FLC/DRZ products would already reflect CR rejection performed
    by the standard mission pipeline.
    """
    from astroquery.mast import Observations

    out_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    for row in observations:
        try:
            products = Observations.get_product_list(observations[observations["obs_id"] == row["obs_id"]])
        except Exception as exc:  # noqa: BLE001
            raise ArchiveAccessError(f"failed to list products for {row['obs_id']}: {exc}") from exc

        subset = products[
            (products["productSubGroupDescription"] == "FLT")
            & np.array([not str(name).startswith("hst_") for name in products["productFilename"]])
        ]
        if len(subset) == 0:
            raise ArchiveAccessError(f"no exposure-level FLT products found for {row['obs_id']}")

        download_manifest = Observations.download_products(subset, download_dir=str(out_dir))
        for local_path_str in download_manifest["Local Path"]:
            nested_path = Path(local_path_str)
            flat_path = out_dir / nested_path.name
            if nested_path != flat_path:
                shutil.move(str(nested_path), str(flat_path))
            downloaded.append(flat_path)

    mast_download_dir = out_dir / "mastDownload"
    if mast_download_dir.is_dir():
        shutil.rmtree(mast_download_dir, ignore_errors=True)

    return downloaded
