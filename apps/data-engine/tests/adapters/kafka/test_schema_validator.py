import pathlib
import pytest

from filternarrange_engine.adapters.kafka.schema_validator import (
    SchemaValidator,
    SchemaValidationError,
)

CONTRACTS = (
    pathlib.Path(__file__).resolve().parents[5] / "contracts" / "kafka"
)


def test_valid_jobs_message_passes():
    v = SchemaValidator(CONTRACTS)
    msg = {
        "job_id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "kind": "batch-filter",
        "params": {},
        "priority": 0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id": "t",
    }
    v.validate("topic.v1.jobs", msg)


def test_missing_required_field_raises():
    v = SchemaValidator(CONTRACTS)
    bad = {"job_id": "11111111-1111-1111-1111-111111111111"}
    with pytest.raises(SchemaValidationError):
        v.validate("topic.v1.jobs", bad)


def test_unknown_topic_raises():
    v = SchemaValidator(CONTRACTS)
    with pytest.raises(SchemaValidationError):
        v.validate("topic.v1.nonexistent", {})
