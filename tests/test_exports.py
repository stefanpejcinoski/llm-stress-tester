"""Tests for XLSX and PDF export services."""

import pytest

from llm_stress_tester.data.prompts import SUITES_DESCRIPTIONS
from llm_stress_tester.enums import BenchmarkSuite, RequestStatus
from llm_stress_tester.schemas import (
    RequestMetric,
    RunSummary,
    StageMetric,
    TestConfig,
    TokenEntry,
)
from llm_stress_tester.services.export_service import export_pdf, export_xlsx


@pytest.fixture
def sample_summary():
    """Create a minimal RunSummary with some metrics."""
    config = TestConfig(
        base_url="http://test.local",
        api_path="v1/chat/completions",
        tokens=[TokenEntry(token="sk-1", label="user-1")],
        models=[],
        rate_unit=BenchmarkSuite.CODING,
        initial_rate=1.0,
        max_rate=2.0,
        min_users=1,
        max_users=1,
        users_increment=0,
        scaling_factor=1.0,
        time_increment=1.0,
        benchmark_suite=BenchmarkSuite.CODING,
        timeout=10.0,
    )
    return RunSummary(config=config, status="completed")


def test_export_xlsx_empty(sample_summary):
    """XLSX export should succeed even with no metrics."""
    xlsx_bytes = export_xlsx(sample_summary)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 100


def test_export_xlsx_with_metrics(sample_summary):
    """XLSX export should include metrics data."""
    sample_summary.metrics = [
        RequestMetric(
            stage_index=0,
            model="gpt-4",
            model_percentage=100.0,
            token_index=0,
            token_label="user-1",
            active_users=1,
            target_rps=1.0,
            aggregate_rps=2.0,
            status=RequestStatus.SUCCESS,
            status_code=200,
            latency_ms=150.0,
            error_type=None,
            suite_id="coding",
            prompt_id="1",
        ),
    ]
    sample_summary.stage_metrics = [
        StageMetric(
            stage_index=0,
            elapsed_seconds=1.0,
            target_rps=1.0,
            achieved_rps=1.0,
            active_users=1,
            total_requests=1,
            successful=1,
            failed=0,
            avg_latency_ms=150.0,
            p50_latency_ms=150.0,
            p95_latency_ms=150.0,
            p99_latency_ms=150.0,
            error_rate=0.0,
        ),
    ]
    xlsx_bytes = export_xlsx(sample_summary)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 500


def test_export_pdf_empty(sample_summary):
    """PDF export should succeed even with no metrics."""
    pdf_bytes = export_pdf(sample_summary)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100


def test_export_pdf_with_metrics(sample_summary):
    """PDF export should succeed with metrics."""
    sample_summary.stage_metrics = [
        StageMetric(
            stage_index=i,
            elapsed_seconds=float(i),
            target_rps=1.0 * (i + 1),
            achieved_rps=1.0 * (i + 1),
            active_users=1,
            total_requests=1,
            successful=1,
            failed=0,
            avg_latency_ms=150.0,
            p50_latency_ms=150.0,
            p95_latency_ms=150.0,
            p99_latency_ms=150.0,
            error_rate=0.0,
        )
        for i in range(5)
    ]
    sample_summary.metrics = [
        RequestMetric(
            stage_index=0,
            model="gpt-4",
            model_percentage=100.0,
            token_index=0,
            token_label="user-1",
            active_users=1,
            target_rps=1.0,
            aggregate_rps=2.0,
            status=RequestStatus.SUCCESS,
            status_code=200,
            latency_ms=150.0,
            error_type=None,
            suite_id="coding",
            prompt_id="1",
        ),
    ]
    pdf_bytes = export_pdf(sample_summary)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
