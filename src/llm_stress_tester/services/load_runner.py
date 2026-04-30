"""Load test runner that executes concurrent requests."""

from __future__ import annotations

import asyncio

from httpx import AsyncClient, Limits

from llm_stress_tester.constants import DEFAULT_TIMEOUT
from llm_stress_tester.data.prompts import BENCHMARK_PROMPTS
from llm_stress_tester.enums import RequestStatus
from llm_stress_tester.schemas import (
    ProgressInfo,
    RequestMetric,
    RunSummary,
    TestConfig,
    TokenEntry,
)
from llm_stress_tester.services.http_client import send_request
from llm_stress_tester.services.metrics import compute_stage_metrics
from llm_stress_tester.services.schedule import build_schedule
from llm_stress_tester.services.traffic_allocator import (
    compute_allocated_rps,
    compute_total_outgoing_rps,
    pick_model,
)


async def run_test(
    config: TestConfig,
    on_progress: callable | None = None,
) -> RunSummary:
    """Run the full load test according to config and schedule."""
    summary = RunSummary(config=config, status="running")
    summary.metrics = []
    summary.stage_metrics = []

    if not config.tokens and not config.is_public:
        summary.status = "error"
        return summary

    base_url = config.base_url.rstrip("/")
    api_path = config.api_path.strip("/")
    req_url = f"{base_url}/{api_path}"

    prompts = BENCHMARK_PROMPTS.get(config.benchmark_suite.value, [])

    http = AsyncClient(
        limits=Limits(max_connections=100),
        timeout=config.timeout or DEFAULT_TIMEOUT,
    )
    try:
        stages = build_schedule(
            initial_rps=config.initial_rate,
            max_rps=config.max_rate,
            min_users=config.min_users,
            max_users=config.max_users,
            users_increment=config.users_increment,
            scaling_factor=config.scaling_factor,
            time_increment=config.time_increment,
        )

        round_total = 0
        elapsed = 0.0
        has_tokens = bool(config.tokens)

        for stage in stages:
            stage_results: list[tuple[RequestMetric]] = []
            target_rps = stage.target_rps
            n_users = stage.active_users
            if config.is_public:
                current_users = n_users
            else:
                current_users = min(n_users, len(config.tokens)) if config.tokens else n_users
            total_out = compute_total_outgoing_rps(
                target_rps, config.models,
            )
            loop = asyncio.get_running_loop()
            end_time = loop.time() + stage.duration

            while loop.time() < end_time:
                for model in config.models:
                    per_model_rps = compute_allocated_rps(
                        target_rps, model.percentage,
                    )
                    n_reqs_for_model = max(
                        1, int(per_model_rps * 1.0),
                    )
                    if n_reqs_for_model == 0:
                        n_reqs_for_model = 1

                    tasks = []
                    for _ in range(n_reqs_for_model):
                        round_total += 1
                        model_pick = pick_model(round_total, config.models)
                        m_name = model_pick["model"]
                        m_pct = model_pick["percentage"]
                        if has_tokens:
                            token_idx = round_total % len(config.tokens)
                            token = config.tokens[token_idx]
                        else:
                            token_idx = 0
                            token = _PUBLIC_SENTINEL
                        prompt_idx = round_total % len(prompts) if prompts else 0
                        prompt_text = prompts[prompt_idx] if prompts else ""

                        tasks.append(
                            _execute_request(
                                http,
                                config,
                                req_url,
                                m_name,
                                m_pct,
                                token,
                                token_idx,
                                current_users,
                                target_rps,
                                total_out,
                                stage.stage_index,
                                prompt_text,
                            ),
                        )

                    results = await asyncio.gather(*tasks)
                    for m in results:
                        summary.metrics.append(m)
                        stage_results.append((m,))

            stage_metrics_this = [
                m for m in summary.metrics if m.stage_index == stage.stage_index
            ]
            stage_summary = compute_stage_metrics(
                stage.stage_index,
                elapsed,
                stage_metrics_this,
                target_rps,
                total_out,
                current_users,
            )
            summary.stage_metrics.append(stage_summary)
            elapsed += stage.duration

            if on_progress:
                successful = sum(
                    1 for m in stage_metrics_this
                    if m.status == RequestStatus.SUCCESS
                )
                failed = len(stage_metrics_this) - successful
                achieved_rps = (
                    len(stage_metrics_this) / elapsed
                    if elapsed > 0 else 0
                )
                elapsed_ms = elapsed * 1000
                on_progress(
                    ProgressInfo(
                        stage_index=stage.stage_index + 1,
                        total_metrics=len(summary.metrics),
                        total_requests=round_total,
                        target_rps=target_rps,
                        achieved_rps=achieved_rps,
                        active_users=current_users,
                        elapsed_ms=elapsed_ms,
                        successful=successful,
                        failed=failed,
                    ),
                )

        summary.status = "completed"
    except asyncio.CancelledError:
        summary.status = "error"
        summary.error_message = "Test cancelled"
    except Exception as exc:
        summary.status = "error"
        summary.error_message = f"{type(exc).__name__}: {exc}"
    finally:
        await http.aclose()

    return summary


_PUBLIC_SENTINEL = TokenEntry(token="", label="public")


async def _execute_request(
    client: AsyncClient,
    client_config: TestConfig,
    url: str,
    model: str,
    model_pct: float,
    token: TokenEntry,
    token_idx: int,
    active_users: int,
    target_rps: float,
    aggregate_rps: float,
    stage_index: int,
    prompt_text: str,
) -> RequestMetric:
    """Execute a single request and return metrics."""
    try:
        messages = [{"role": "user", "content": prompt_text}]
        resp, latency_ms = await send_request(
            client, url, model, messages, client_config.timeout,
        )
        code = resp.status_code
        if 200 <= code < 400:
            status = RequestStatus.SUCCESS
        else:
            status = RequestStatus.FAILURE
        return RequestMetric(
            stage_index=stage_index,
            model=model,
            model_percentage=model_pct,
            token_index=token_idx,
            token_label=token.label or f"user-{token_idx}",
            active_users=active_users,
            target_rps=target_rps,
            aggregate_rps=aggregate_rps,
            status=status,
            status_code=code,
            latency_ms=latency_ms,
            error_type=None,
            suite_id=client_config.benchmark_suite.value,
            prompt_id=str(stage_index),
        )
    except TimeoutError:
        return RequestMetric(
            stage_index=stage_index,
            model=model,
            model_percentage=model_pct,
            token_index=token_idx,
            token_label=token.label or f"user-{token_idx}",
            active_users=active_users,
            target_rps=target_rps,
            aggregate_rps=aggregate_rps,
            status=RequestStatus.TIMEOUT,
            status_code=None,
            latency_ms=0.0,
            error_type="timeout",
            suite_id=client_config.benchmark_suite.value,
            prompt_id=str(stage_index),
        )
    except Exception as exc:
        return RequestMetric(
            stage_index=stage_index,
            model=model,
            model_percentage=model_pct,
            token_index=token_idx,
            token_label=token.label or f"user-{token_idx}",
            active_users=active_users,
            target_rps=target_rps,
            aggregate_rps=aggregate_rps,
            status=RequestStatus.ERROR,
            status_code=None,
            latency_ms=0.0,
            error_type=str(type(exc).__name__),
            suite_id=client_config.benchmark_suite.value,
            prompt_id=str(stage_index),
        )
