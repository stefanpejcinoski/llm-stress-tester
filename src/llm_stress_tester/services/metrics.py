"""Metrics aggregation for load test results."""

from __future__ import annotations

from llm_stress_tester.enums import RequestStatus
from llm_stress_tester.schemas import RequestMetric, StageMetric


def compute_stage_metrics(
    stage_index: int,
    elapsed_seconds: float,
    metrics: list[RequestMetric],
    target_rps: float,
    active_users: int,
) -> StageMetric:
    """Compute aggregated stage metrics from raw request metrics."""
    if not metrics:
        return StageMetric(
            stage_index=stage_index,
            elapsed_seconds=elapsed_seconds,
            target_rps=target_rps,
            achieved_rps=0,
            active_users=active_users,
            total_requests=0,
            successful=0,
            failed=0,
            avg_latency_ms=0,
            p50_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            error_rate=0,
        )

    latencies = sorted([m.latency_ms for m in metrics])
    n = len(metrics)
    successful = sum(
        1 for m in metrics if m.status == RequestStatus.SUCCESS
    )
    failed = sum(
        1 for m in metrics
        if m.status != RequestStatus.SUCCESS
    )

    return StageMetric(
        stage_index=stage_index,
        elapsed_seconds=elapsed_seconds,
        target_rps=target_rps,
        achieved_rps=n / max(elapsed_seconds, 0.001),
        active_users=active_users,
        total_requests=n,
        successful=successful,
        failed=failed,
        avg_latency_ms=sum(latencies) / n,
        p50_latency_ms=latencies[int(n * 0.50)] if n > 0 else 0,
        p95_latency_ms=latencies[int(n * 0.95)] if n > 0 else 0,
        p99_latency_ms=latencies[min(int(n * 0.99), n - 1)] if n > 0 else 0,
        error_rate=failed / n,
    )
