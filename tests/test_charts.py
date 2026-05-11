"""Tests for chart data preparation."""

from llm_stress_tester.enums import BenchmarkSuite, RateUnit
from llm_stress_tester.schemas import RunSummary, StageMetric, TestConfig
from llm_stress_tester.ui.charts import _build_rate_chart_df, _compute_scale_info


def test_build_rate_chart_df_outputs_target_and_achieved_rpm():
    config = TestConfig(
        base_url="http://localhost:8000",
        api_path="v1/chat/completions",
        tokens=[],
        models=[],
        rate_unit=RateUnit.RPS,
        initial_rate=1.0,
        max_rate=2.0,
        min_users=1,
        max_users=1,
        users_increment=1,
        scaling_factor=2.0,
        time_increment=10.0,
        benchmark_suite=BenchmarkSuite.CODING,
        is_public=True,
    )
    summary = RunSummary(
        config=config,
        status="completed",
        stage_metrics=[
            StageMetric(
                stage_index=0,
                elapsed_seconds=10.0,
                target_rps=2.0,
                achieved_rps=1.5,
                active_users=2,
                total_requests=15,
                successful=15,
                failed=0,
                avg_latency_ms=100.0,
                p50_latency_ms=100.0,
                p95_latency_ms=120.0,
                p99_latency_ms=140.0,
                error_rate=0.0,
            ),
        ],
    )

    df = _build_rate_chart_df(summary)
    assert len(df) == 2
    assert set(df["series"]) == {"Target RPM", "Achieved RPM"}

    target = df[df["series"] == "Target RPM"]["rpm"].iloc[0]
    achieved = df[df["series"] == "Achieved RPM"]["rpm"].iloc[0]
    assert target == 120.0
    assert achieved == 90.0


def test_compute_scale_info_uses_achieved_scale_above_10x():
    df = _build_rate_chart_df(
        RunSummary(
            config=TestConfig(
                base_url="http://localhost:8000",
                api_path="v1/chat/completions",
                tokens=[],
                models=[],
                rate_unit=RateUnit.RPS,
                initial_rate=1.0,
                max_rate=2.0,
                min_users=1,
                max_users=1,
                users_increment=1,
                scaling_factor=2.0,
                time_increment=10.0,
                benchmark_suite=BenchmarkSuite.CODING,
                is_public=True,
            ),
            status="completed",
            stage_metrics=[
                StageMetric(
                    stage_index=0,
                    elapsed_seconds=10.0,
                    target_rps=10.0,
                    achieved_rps=0.5,
                    active_users=2,
                    total_requests=5,
                    successful=5,
                    failed=0,
                    avg_latency_ms=100.0,
                    p50_latency_ms=100.0,
                    p95_latency_ms=120.0,
                    p99_latency_ms=140.0,
                    error_rate=0.0,
                ),
            ],
        ),
    )
    info = _compute_scale_info(df)
    assert info["use_achieved_scale"] is True
    assert info["target_max"] == 600.0
    assert info["achieved_max"] == 30.0


def test_compute_scale_info_uses_normal_scale_below_threshold():
    df = _build_rate_chart_df(
        RunSummary(
            config=TestConfig(
                base_url="http://localhost:8000",
                api_path="v1/chat/completions",
                tokens=[],
                models=[],
                rate_unit=RateUnit.RPS,
                initial_rate=1.0,
                max_rate=2.0,
                min_users=1,
                max_users=1,
                users_increment=1,
                scaling_factor=2.0,
                time_increment=10.0,
                benchmark_suite=BenchmarkSuite.CODING,
                is_public=True,
            ),
            status="completed",
            stage_metrics=[
                StageMetric(
                    stage_index=0,
                    elapsed_seconds=10.0,
                    target_rps=2.0,
                    achieved_rps=1.0,
                    active_users=2,
                    total_requests=10,
                    successful=10,
                    failed=0,
                    avg_latency_ms=100.0,
                    p50_latency_ms=100.0,
                    p95_latency_ms=120.0,
                    p99_latency_ms=140.0,
                    error_rate=0.0,
                ),
            ],
        ),
    )
    info = _compute_scale_info(df)
    assert info["use_achieved_scale"] is False
    assert info["y_max"] == 120.0
