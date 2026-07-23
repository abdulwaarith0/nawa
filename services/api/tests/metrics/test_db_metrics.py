import pytest

from nawa_api.metrics.db import database_request_duration_seconds, observe_db


def _get_sample_count(labels: dict) -> float:
    for metric in database_request_duration_seconds.collect():
        for sample in metric.samples:
            if sample.name.endswith("_count") and all(
                sample.labels.get(k) == v for k, v in labels.items()
            ):
                return sample.value
    return 0.0


def test_observe_db_records_a_success_sample():
    labels = {"operation": "read", "table": "founder_profiles", "method": "test_success_method"}
    before = _get_sample_count({**labels, "success": "true"})
    with observe_db(**labels) as obs:
        obs.success = True
    after = _get_sample_count({**labels, "success": "true"})
    assert after == before + 1


def test_observe_db_records_a_failure_sample_and_defaults_to_false():
    labels = {"operation": "read", "table": "founder_profiles", "method": "test_default_method"}
    before = _get_sample_count({**labels, "success": "false"})
    with observe_db(**labels):
        pass  # obs.success left at its default (False)
    after = _get_sample_count({**labels, "success": "false"})
    assert after == before + 1


def test_observe_db_still_records_when_the_body_raises():
    labels = {"operation": "write", "table": "founder_profiles", "method": "test_raise_method"}
    before = _get_sample_count({**labels, "success": "false"})
    with pytest.raises(ValueError):
        with observe_db(**labels) as obs:
            obs.success = False
            raise ValueError("boom")
    after = _get_sample_count({**labels, "success": "false"})
    assert after == before + 1


def test_double_import_does_not_raise():
    """The histogram registration must be double-import safe."""
    import importlib

    from nawa_api.metrics import db as db_metrics_module

    importlib.reload(db_metrics_module)
