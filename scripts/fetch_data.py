"""Deterministic, provenance-recording fetch of real public HST ACS/WFC FLT data.

Queries MAST directly (no fabricated metadata) via
`hst_ccd_cosmic_ray_rejection_benchmark.fetch.select_observations` /
`download_flt`, downloads a small deterministic sample of exposure-level FLT
products (uncombined single exposures — required since this project injects
synthetic cosmic rays into an *uncombined* background) to data/raw/
(git-ignored), verifies checksums, and appends rows to data/manifest.csv.

Only FLT products are needed (not FLC), unlike the sibling CTE-audit project.
This performs real network downloads (~170 MB per FITS file) and must only be
invoked with explicit user authorization for the current session, per
docs/DATASET_PLAN.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import ArchiveAccessError
from hst_ccd_cosmic_ray_rejection_benchmark.fetch import (
    FILTER_NAME,
    LICENCE_TERMS,
    PROPOSAL_ID,
    SOURCE_URL,
    download_flt,
    select_observations,
)
from hst_ccd_cosmic_ray_rejection_benchmark.logging_utils import get_logger
from hst_ccd_cosmic_ray_rejection_benchmark.provenance import ManifestRow, append_manifest_row, sha256_file

LOGGER = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n-exposures",
        type=int,
        default=2,
        help="Number of FLT exposures to fetch deterministically (a modest real background sample).",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument(
        "--i-have-authorization",
        action="store_true",
        help=(
            "Required flag confirming the operator has explicitly authorized this "
            "real network download in the current session."
        ),
    )
    args = parser.parse_args()

    if not args.i_have_authorization:
        raise SystemExit(
            "Refusing to download real archive data without --i-have-authorization. "
            "This flag exists so the download only runs after the operator has "
            "explicitly confirmed it in the current session (see docs/DATASET_PLAN.md)."
        )

    selected = select_observations(args.n_exposures)
    LOGGER.info("Selected %d observations from proposal %s", len(selected), PROPOSAL_ID)

    downloaded = download_flt(selected, args.out_dir)
    retrieved_utc = datetime.now(timezone.utc).isoformat()

    for local_path in downloaded:
        if not local_path.is_file():
            raise ArchiveAccessError(f"expected downloaded file missing: {local_path}")
        digest = sha256_file(local_path)
        size = local_path.stat().st_size
        row = ManifestRow(
            product_id=local_path.stem,
            source="MAST/HST",
            source_url=SOURCE_URL,
            retrieved_utc=retrieved_utc,
            sha256=digest,
            file_size_bytes=size,
            selection_reason=(
                f"deterministic first-{args.n_exposures} public ACS/WFC {FILTER_NAME} FLT "
                f"exposure sample from proposal {PROPOSAL_ID}, sorted by obs_id, used as a "
                "real background for controlled synthetic cosmic-ray injection"
            ),
            licence_or_terms=LICENCE_TERMS,
        )
        append_manifest_row(args.manifest, row)
        LOGGER.info("Recorded manifest row for %s (%d bytes)", local_path.name, size)

    print(f"Downloaded and recorded {len(downloaded)} files under {args.out_dir}")


if __name__ == "__main__":
    main()
