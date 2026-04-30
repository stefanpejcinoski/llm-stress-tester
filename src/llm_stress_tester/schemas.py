"""Pydantic schemas for configuration and metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from llm_stress_tester.enums import BenchmarkSuite, RateUnit, RequestStatus


@dataclass
class ProgressInfo:
    """Live progress info passed to the UI via callback."""

    stage_index: int
    total_metrics: int
    total_requests: int
    target_rps: float
    achieved_rps: float
    active_users: int
    elapsed_ms: float
    successful: int
    failed: int
    stage_elapsed_s: float = 0.0
    stage_duration_s: float = 0.0


class TokenEntry(BaseModel):
    """Single API token with optional label."""

    token: str
    label: str = ""


class ModelEntry(BaseModel):
    """LLM model to test with traffic percentage."""

    model: str
    percentage: float = Field(
        ..., ge=0, le=100, description="Traffic percentage (0-100)",
    )


# ---------------------------------------------------------------------------
# Test configuration
# ---------------------------------------------------------------------------


@dataclass
class TestConfig:
    """Complete test configuration."""

    base_url: str
    api_path: str
    tokens: list[TokenEntry]
    models: list[ModelEntry]
    rate_unit: RateUnit
    initial_rate: float
    max_rate: float
    min_users: int
    max_users: int
    users_increment: int
    scaling_factor: float
    time_increment: float
    benchmark_suite: BenchmarkSuite
    prompt_ids: list[str] = field(default_factory=list)
    timeout: float = 60.0
    is_public: bool = False


# ---------------------------------------------------------------------------
# Runtime metrics
# ---------------------------------------------------------------------------


@dataclass
class RequestMetric:
    """Metrics recorded for a single request."""

    stage_index: int
    model: str
    model_percentage: float
    token_index: int
    token_label: str
    active_users: int
    target_rps: float
    aggregate_rps: float
    status: RequestStatus
    status_code: int | None
    latency_ms: float
    error_type: str | None
    suite_id: str
    prompt_id: str


@dataclass
class StageMetric:
    """Aggregated metrics for one stage."""

    stage_index: int
    elapsed_seconds: float
    target_rps: float
    achieved_rps: float
    active_users: int
    total_requests: int
    successful: int
    failed: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float


@dataclass
class RunSummary:
    """Complete run summary including all metrics."""

    config: TestConfig
    metrics: list[RequestMetric] = field(default_factory=list)
    stage_metrics: list[StageMetric] = field(default_factory=list)
    status: Literal["running", "completed", "error"] = "running"
    error_message: str = ""
