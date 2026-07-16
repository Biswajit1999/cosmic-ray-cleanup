from __future__ import annotations

import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.config import load_config
from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError


def test_load_config_reads_real_file():
    config = load_config("config/analysis.yml")
    assert config.project.repository == "hst-ccd-cosmic-ray-rejection-benchmark"
    assert config.execution.seed == 20260713
    assert config.validation.bootstrap_resamples == 1000


def test_load_config_missing_file_raises():
    with pytest.raises(DataSchemaError):
        load_config("config/does_not_exist.yml")


def test_load_config_missing_section_raises(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("project:\n  title: x\n", encoding="utf-8")
    with pytest.raises(DataSchemaError):
        load_config(bad)


def test_load_config_bad_confidence_level_raises(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text(
        """
project: {title: x, repository: y, author: z, curation_status: c, priority: 1.0}
execution: {seed: 1, output_directory: results, overwrite: false, fail_on_warning: false}
input: {data_mode: m, manifest: data/manifest.csv, raw_directory: data/raw, example_directory: data/example}
validation: {minimum_sample_size: 1, bootstrap_resamples: 10, confidence_level: 1.5}
provenance: {record_environment: true, record_git_commit: true, verify_checksums: true}
""",
        encoding="utf-8",
    )
    with pytest.raises(DataSchemaError):
        load_config(bad)
