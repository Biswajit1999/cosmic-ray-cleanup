from __future__ import annotations

import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import ProvenanceError
from hst_ccd_cosmic_ray_rejection_benchmark.provenance import (
    ManifestRow,
    append_manifest_row,
    get_git_commit,
    read_manifest,
    sha256_bytes,
    sha256_file,
)


def _row(product_id: str = "abc") -> ManifestRow:
    return ManifestRow(
        product_id=product_id,
        source="MAST/HST",
        source_url="https://mast.stsci.edu",
        retrieved_utc="2026-07-14T00:00:00+00:00",
        sha256="deadbeef",
        file_size_bytes=123,
        selection_reason="test",
        licence_or_terms="PUBLIC",
    )


def test_append_and_read_manifest_roundtrip(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    append_manifest_row(manifest_path, _row("a"))
    append_manifest_row(manifest_path, _row("b"))
    rows = read_manifest(manifest_path)
    assert [r["product_id"] for r in rows] == ["a", "b"]


def test_read_manifest_missing_file_raises(tmp_path):
    with pytest.raises(ProvenanceError):
        read_manifest(tmp_path / "missing.csv")


def test_sha256_file_matches_sha256_bytes(tmp_path):
    path = tmp_path / "data.bin"
    data = b"the quick brown fox"
    path.write_bytes(data)
    assert sha256_file(path) == sha256_bytes(data)


def test_get_git_commit_never_raises(tmp_path):
    # tmp_path is not a git repo; must return the documented sentinel, not raise.
    result = get_git_commit(tmp_path)
    assert isinstance(result, str)
    assert result != ""
