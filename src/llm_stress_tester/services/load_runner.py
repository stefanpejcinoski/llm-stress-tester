"""Load test runner that executes concurrent requests."""

from __future__ import annotations

import asyncio
import threading

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
    compute_total_outgoing_rps,
    pick_model,
)


async def run_test(
    config: TestConfig,
    on_progress: callable | None = None,
    cancel_event: threading.Event | None = None,
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
        cumulative_prev_s = 0.0
        has_tokens = bool(config.tokens)

        # Emit an initial placeholder so the UI cards appear immediately
        if on_progress and stages:
            first_stage = stages[0]
            first_users = (
                first_stage.active_users
                if config.is_public
                else min(first_stage.active_users, len(config.tokens)) if config.tokens else first_stage.active_users
            )
            on_progress(ProgressInfo(
                stage_index=0,
                total_metrics=0,
                total_requests=0,
                target_rps=first_stage.target_rps,
                achieved_rps=0.0,
                active_users=first_users,
                elapsed_ms=0.0,
                successful=0,
                failed=0,
                stage_elapsed_s=0.0,
                stage_duration_s=first_stage.duration,
            ))

        for stage in stages:
            target_rps = stage.target_rps
            n_users = stage.active_users
            if config.is_public:
                current_users = n_users
            else:
                current_users = min(n_users, len(config.tokens)) if config.tokens else n_users
            total_out = compute_total_outgoing_rps(target_rps, config.models)

            loop = asyncio.get_running_loop()
            stage_start = loop.time()
            end_time = stage_start + stage.duration

            stage_successful = 0
            stage_failed = 0
            stage_count = 0

            # Interval between requests (seconds). Enforces target_rps exactly
            # regardless of endpoint latency. At 200 RPM (3.33 RPS) this is
            # 0.3 s; at 6 RPM (0.1 RPS) this is 10 s.
            interval_s = 1.0 / max(target_rps, 1e-6)

            # Semaphore caps in-flight concurrent requests to active_users.
            # Requests that can't acquire a slot wait until one is released.
            semaphore = asyncio.Semaphore(max(current_users, 1))

            while loop.time() < end_time:
                tick_start = loop.time()

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

                # Acquire a concurrency slot, fire the request, release slot
                async with semaphore:
                    result = await _execute_request(
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
                    )

                summary.metrics.append(result)
                stage_count += 1
                if result.status == RequestStatus.SUCCESS:
                    stage_successful += 1
                else:
                    stage_failed += 1

                # Check for cancellation
                if cancel_event is not None and cancel_event.is_set():
                    break

                # Emit live progress after every request
                if on_progress:
                    stage_elapsed_s = loop.time() - stage_start
                    achieved_rps = stage_count / max(stage_elapsed_s, 0.001)
                    on_progress(ProgressInfo(
                        stage_index=stage.stage_index,
                        total_metrics=len(summary.metrics),
                        total_requests=round_total,
                        target_rps=target_rps,
                        achieved_rps=achieved_rps,
                        active_users=current_users,
                        elapsed_ms=(cumulative_prev_s + stage_elapsed_s) * 1000,
                        successful=stage_successful,
                        failed=stage_failed,
                        stage_elapsed_s=stage_elapsed_s,
                        stage_duration_s=stage.duration,
                    ))

                # Sleep for the remainder of the interval so we hit target_rps.
                # If the request took longer than interval_s, sleep_for <= 0
                # and we skip the sleep — achieved RPS is naturally capped by
                # endpoint latency in that case.
                sleep_for = interval_s - (loop.time() - tick_start)
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)

            # If cancelled mid-stage, still record what was collected then stop
            cancelled = cancel_event is not None and cancel_event.is_set()

            # End-of-stage: compute and store stage metrics
            stage_metrics_this = [
                m for m in summary.metrics if m.stage_index == stage.stage_index
            ]
            stage_summary = compute_stage_metrics(
                stage.stage_index,
                cumulative_prev_s,
                stage_metrics_this,
                target_rps,
                total_out,
                current_users,
            )
            summary.stage_metrics.append(stage_summary)
            cumulative_prev_s += stage.duration

            if cancelled:
                break

        summary.status = "completed" if not (cancel_event is not None and cancel_event.is_set()) else "running"
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
