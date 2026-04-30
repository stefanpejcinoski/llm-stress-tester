"""Tests for metrics aggregation service."""

import pytest

from llm_stress_tester.enums import RequestStatus
from llm_stress_tester.schemas import (
    RequestMetric,
    StageMetric,
)
from llm_stress_tester.services.metrics import compute_stage_metrics


def test_compute_stage_metrics_empty():
    result = compute_stage_metrics(
        stage_index=0,
        elapsed_seconds=1.0,
        metrics=[],
        target_rps=10.0,
        active_users=2,
    )
    assert result.stage_index == 0
    assert result.total_requests == 0
    assert result.successful == 0
    assert result.failed == 0
    assert result.avg_latency_ms == 0
    assert result.error_rate == 0


def test_compute_stage_metrics_success():
    metrics = [
        RequestMetric(
            stage_index=0,
            model="gpt-4",
            model_percentage=100.0,
            token_index=0,
            token_label="user-a",
            active_users=1,
            target_rps=5.0,
            status=RequestStatus.SUCCESS,
            status_code=200,
            latency_ms=150.0,
            error_type=None,
            suite_id="coding",
            prompt_id="1",
        ),
        RequestMetric(
            stage_index=0,
            model="gpt-4",
            model_percentage=100.0,
            token_index=1,
            token_label="user-b",
            active_users=1,
            target_rps=5.0,
            status=RequestStatus.SUCCESS,
            status_code=200,
            latency_ms=250.0,
            error_type=None,
            suite_id="coding",
            prompt_id="2",
        ),
    ]
    result = compute_stage_metrics(
        stage_index=0,
        elapsed_seconds=5.0,
        metrics=metrics,
        target_rps=5.0,
        active_users=1,
    )
    assert result.total_requests == 2
    assert result.successful == 2
    assert result.failed == 0
    assert result.avg_latency_ms == 200.0
    assert result.p50_latency_ms == 250.0
    assert result.p95_latency_ms == 250.0
    assert result.p99_latency_ms == 250.0
    assert result.error_rate == 0


def test_compute_stage_metrics_with_failures():
    metrics = [
        RequestMetric(
            stage_index=0,
            model="gpt-4",
            model_percentage=100.0,
            token_index=0,
            token_label="user-a",
            active_users=1,
            target_rps=5.0,
            status=RequestStatus.SUCCESS,
            status_code=200,
            latency_ms=100.0,
            error_type=None,
            suite_id="coding",
            prompt_id="1",
        ),
        RequestMetric(
            stage_index=0,
            model="gpt-4",
            model_percentage=100.0,
            token_index=1,
            token_label="user-b",
            active_users=1,
            target_rps=5.0,
            status=RequestStatus.FAILURE,
            status_code=500,
            latency_ms=50.0,
            error_type="api_error",
            suite_id="coding",
            prompt_id="2",
        ),
    ]
    result = compute_stage_metrics(
        stage_index=0,
        elapsed_seconds=1.0,
        metrics=metrics,
        target_rps=5.0,
        active_users=1,
    )
    assert result.total_requests == 2
    assert result.successful == 1
    assert result.failed == 1
    assert result.error_rate == 0.5
