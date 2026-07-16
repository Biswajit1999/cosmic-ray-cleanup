from __future__ import annotations

import json

import pytest

from hst_ccd_cosmic_ray_rejection_benchmark.exceptions import DataSchemaError
from hst_ccd_cosmic_ray_rejection_benchmark.results_io import Metric, validate_summary, write_summary


def test_write_summary_roundtrip(tmp_path):
    path = tmp_path / "summary.json"
    metrics = [Metric(name="recall", estimate=0.9, units="dimensionless", sample_size=10)]
    payload = write_summary(
        path, project="p", data_kind="synthetic_demo", metrics=metrics,
        provenance={"git_commit": "abc"}, warnings=["w1"],
    )
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == payload
    validate_summary(on_disk)


def test_validate_summary_rejects_missing_keys():
    with pytest.raises(DataSchemaError):
        validate_summary({"project": "p"})


def test_validate_summary_rejects_bad_metric():
    payload = {
        "project": "p", "data_kind": "d", "provenance": {}, "warnings": [],
        "metrics": [{"name": "x"}],
    }
    with pytest.raises(DataSchemaError):
        validate_summary(payload)
