"""Tests for load runner stage metrics behavior."""

import threading

import pytest

from llm_stress_tester.enums import BenchmarkSuite, RateUnit, RequestStatus
from llm_stress_tester.schemas import ModelEntry, RequestMetric, TestConfig
from llm_stress_tester.services.schedule import ScheduleStage


@pytest.mark.asyncio
async def test_run_test_stage0_achieved_rate_is_reasonable(monkeypatch):
    """Achieved RPS should be based on stage duration, not cumulative time."""
    from llm_stress_tester.services import load_runner

    async def fake_execute_request(*_args, **kwargs):
        return RequestMetric(
            stage_index=0,
            model="gpt-4",
            model_percentage=100.0,
            token_index=0,
            token_label="public",
            active_users=1,
            target_rps=10.0,
            status=RequestStatus.SUCCESS,
            status_code=200,
            latency_ms=5.0,
            error_type=None,
            suite_id="coding",
            prompt_id="0",
        )

    monkeypatch.setattr(
        load_runner,
        "build_schedule",
        lambda *_args, **_kwargs: [
            ScheduleStage(stage_index=0, target_rps=10.0, active_users=1, duration=0.2),
        ],
    )
    monkeypatch.setattr(load_runner, "_execute_request", fake_execute_request)

    config = TestConfig(
        base_url="http://localhost:8000",
        api_path="v1/chat/completions",
        tokens=[],
        models=[ModelEntry(model="gpt-4", percentage=100.0)],
        rate_unit=RateUnit.RPS,
        initial_rate=10.0,
        max_rate=10.0,
        min_users=1,
        max_users=1,
        users_increment=1,
        scaling_factor=1.0,
        time_increment=0.2,
        benchmark_suite=BenchmarkSuite.CODING,
        timeout=1.0,
        is_public=True,
    )

    summary = await load_runner.run_test(config, cancel_event=threading.Event())

    assert summary.stage_metrics
    achieved = summary.stage_metrics[0].achieved_rps
    assert achieved > 0
    assert achieved < 50
