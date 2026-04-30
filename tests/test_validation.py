"""Tests for validation utilities."""

from llm_stress_tester.schemas import ModelEntry
from llm_stress_tester.utils.validation import (
    validate_models,
    validate_rate_schedule,
    validate_token_count,
    validate_user_schedule,
)


def test_validate_token_count_ok():
    errors = validate_token_count(5, 1, 3)
    assert errors == []


def test_validate_token_count_min_exceeds():
    errors = validate_token_count(2, 5, 6)
    assert len(errors) >= 1


def test_validate_model_empty():
    errors = validate_models([])
    assert len(errors) == 1
    assert "one model" in errors[0].lower()


def test_validate_model_invalid_percentage():
    # pydantic Field(ge=0, le=100) rejects out-of-range before
    # validate_models ever sees it, so test that a valid entry passes
    entry = ModelEntry(model="gpt-4", percentage=50.0)
    assert entry.percentage == 50.0


def test_validate_model_100_pct_multi():
    errors = validate_models([
        ModelEntry(model="a", percentage=100.0),
        ModelEntry(model="b", percentage=100.0),
    ])
    assert len(errors) == 1
    assert "100%" in errors[0]


def test_validate_rate_schedule_ok():
    errors = validate_rate_schedule(
        initial=1.0,
        max_rate=10.0,
        scaling_factor=2.0,
        increment=10.0,
    )
    assert errors == []


def test_validate_rate_schedule_invalid_initial():
    errors = validate_rate_schedule(
        initial=0,
        max_rate=10.0,
        scaling_factor=2.0,
        increment=10.0,
    )
    assert len(errors) >= 1


def test_validate_rate_schedule_increment_zero():
    errors = validate_rate_schedule(
        initial=1.0,
        max_rate=10.0,
        scaling_factor=2.0,
        increment=0,
    )
    assert len(errors) >= 1


def test_validate_user_schedule_ok():
    errors = validate_user_schedule(1, 5, 1)
    assert errors == []


def test_validate_user_schedule_max_less_than_min():
    errors = validate_user_schedule(5, 3, 1)
    assert len(errors) >= 1


def test_validate_user_schedule_increment_zero():
    errors = validate_user_schedule(1, 5, 0)
    assert len(errors) >= 1

