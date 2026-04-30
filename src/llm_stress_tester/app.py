"""Streamlit entry point for LLM Stress Tester."""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

import streamlit as st

from llm_stress_tester.data.prompts import SUITES_DESCRIPTIONS
from llm_stress_tester.enums import BenchmarkSuite
from llm_stress_tester.schemas import ProgressInfo, RunSummary, TestConfig
from llm_stress_tester.services.export_service import export_pdf, export_xlsx
from llm_stress_tester.services.load_runner import run_test
from llm_stress_tester.services.schedule import build_schedule
from llm_stress_tester.ui.charts import render_charts, render_raw_metrics
from llm_stress_tester.ui.forms import (
    render_advanced_form,
    render_benchmark_form,
    render_endpoint_form,
    render_models_form,
    render_rate_form,
    render_tokens_form,
    render_users_form,
)
from llm_stress_tester.utils.validation import (
    validate_models,
    validate_rate_schedule,
    validate_token_count,
    validate_user_schedule,
)

# Module-level executor lives across Streamlit reruns
_EXECUTOR = ThreadPoolExecutor(max_workers=4)


# Thread-safe progress holder. The background thread writes; the main thread reads.
# A simple dict + lock is enough for this one-writer, one-reader pattern.
class _ProgressHolder:
    """Thread-safe holder for live progress updates."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._info: ProgressInfo | None = None

    def set(self, info: ProgressInfo) -> None:
        with self._lock:
            self._info = info

    def get(self) -> ProgressInfo | None:
        with self._lock:
            return self._info


def _run_test_in_thread(
    config: TestConfig,
    holder: _ProgressHolder,
) -> RunSummary:
    """Run the async load test in this worker thread's event loop.

    Returns the RunSummary when complete. Exceptions inside run_test
    are captured in summary.error_message.
    """
    def _on_progress(info: ProgressInfo) -> None:
        holder.set(info)

    async def _runner() -> RunSummary:
        return await run_test(config, on_progress=_on_progress)

    return asyncio.run(_runner())


def main():
    """Main Streamlit entry point."""
    # ── Page config ──────────────────────────────────────────────
    st.set_page_config(
        page_title="LLM Stress Tester",
        page_icon="⚡",
        layout="wide",
    )

    st.title("⚡ LLM Stress Tester")
    st.caption(
        "Load test any OpenAI-compatible inference endpoint. "
        "No data leaves your machine.",
    )

    # ── Session state ────────────────────────────────────────────
    if "summary" not in st.session_state:
        st.session_state.summary = None
    if "running" not in st.session_state:
        st.session_state.running = False
    if "future" not in st.session_state:
        st.session_state.future = None
    if "progress_holder" not in st.session_state:
        st.session_state.progress_holder = None

    # ── Forms ────────────────────────────────────────────────────
    # Step 1: Endpoint
    st.header("1. Endpoint")
    base_url, api_path, is_public = render_endpoint_form()

    # Step 2: Tokens
    if is_public:
        st.header("2. Authentication")
        st.info("Public endpoint selected - no tokens required.")
        tokens: list = []
    else:
        st.header("2. API Tokens")
        tokens = render_tokens_form()

    # Step 3: Rate
    st.header("3. Rate & Schedule")
    rate_unit, initial_rate, max_rate, scaling_factor, time_increment = (
        render_rate_form()
    )

    # Step 4: Users
    st.header("4. Users")
    min_users, max_users, users_increment = render_users_form()

    # Step 5: Models
    st.header("5. Models & Traffic Split")
    models = render_models_form()

    # Step 6: Benchmark
    st.header("6. Benchmark Suite")
    benchmark_suite = render_benchmark_form()

    # Step 7: Advanced
    st.header("7. Advanced Settings")
    timeout, num_rows = render_advanced_form(timeout=60, num_rows=100)

    # ── Validate ─────────────────────────────────────────────────
    errors: list[str] = []

    if tokens:
        validation_errors = validate_token_count(
            len(tokens), min_users, max_users,
        )
        errors.extend(validation_errors)

    model_errors = validate_models(models)
    errors.extend(model_errors)

    rate_errors = validate_rate_schedule(
        initial_rate, max_rate, scaling_factor, time_increment,
    )
    errors.extend(rate_errors)

    user_errors = validate_user_schedule(
        min_users, max_users, users_increment,
    )
    errors.extend(user_errors)

    if errors:
        st.error("Validation errors detected:")
        for error in errors:
            st.error(error)
        st.stop()

    # ── Build config ─────────────────────────────────────────────
    config = TestConfig(
        base_url=base_url,
        api_path=api_path,
        tokens=tokens,
        models=models,
        rate_unit=rate_unit,
        initial_rate=initial_rate,
        max_rate=max_rate,
        min_users=min_users,
        max_users=max_users,
        users_increment=users_increment,
        scaling_factor=scaling_factor,
        time_increment=time_increment,
        benchmark_suite=BenchmarkSuite(benchmark_suite),
        timeout=timeout,
        is_public=is_public,
    )

    # ── Display config summary ──────────────────────────────────
    st.header("Test Configuration Summary")
    with st.expander("View Configuration", expanded=False):
        st.json(
            {
                "endpoint": {"base_url": base_url, "api_path": api_path},
                "tokens": len(tokens),
                "rate": {
                    "unit": rate_unit.value,
                    "initial": initial_rate,
                    "max": max_rate,
                    "scaling_factor": scaling_factor,
                    "time_increment": time_increment,
                },
                "users": {
                    "min": min_users,
                    "max": max_users,
                    "increment": users_increment,
                },
                "models": [
                    {"model": m.model, "percentage": m.percentage}
                    for m in models
                ],
                "benchmark": {
                    "suite": benchmark_suite,
                    "description": SUITES_DESCRIPTIONS.get(
                        benchmark_suite, ("Unknown", ""),
                    )[0],
                },
                "timeout": timeout,
            },
        )

    # ── Determine total stages ──────────────────────────────────
    try:
        stages = build_schedule(
            initial_rate,
            max_rate,
            min_users,
            max_users,
            users_increment,
            scaling_factor,
            time_increment,
        )
        total_stages = len(stages)
    except Exception:
        stages = []
        total_stages = 0

    # ── Progress placeholders (visible while running) ────────────
    progress_bar = st.empty()
    live_metrics = st.empty()
    status_col = st.empty()

    # ── Check on the running future ───────────────────────────────
    future: Future | None = st.session_state.future
    if st.session_state.running and future is not None and future.done():
        # Test finished (or errored). Pull the result.
        try:
            st.session_state.summary = future.result()
        except Exception as exc:
            # Build a synthetic error summary so the UI can show it
            summary = RunSummary(config=config, status="error")
            summary.error_message = f"{type(exc).__name__}: {exc}"
            st.session_state.summary = summary
        st.session_state.running = False
        st.session_state.future = None
        st.rerun()

    # ── Submit button ────────────────────────────────────────────
    if st.session_state.running:
        holder: _ProgressHolder = st.session_state.progress_holder
        live = holder.get() if holder else None

        if live:
            pct = min(live.stage_index / max(total_stages, 1), 1.0)
            progress_bar.progress(
                pct,
                text=f"Stage {live.stage_index}/{max(total_stages, 1)} completed",
            )

            with live_metrics.container():
                cols = st.columns(5)
                cols[0].metric("Target RPS", f"{live.target_rps:.0f}")
                cols[1].metric("Achieved RPS", f"{live.achieved_rps:.0f}")
                cols[2].metric("Active Users", live.active_users)
                cols[3].metric("Collected", f"{live.total_metrics:,}")
                cols[4].metric("Failed", f"{live.failed:,}")

                elapsed_s = live.elapsed_ms / 1000
                info_text = (
                    f"Stage {live.stage_index}/{total_stages} -- "
                    f"{elapsed_s:.0f}s elapsed -- "
                    f"{live.total_metrics:,}/{live.total_requests:,} "
                    f"requests -- {live.successful:,} ok, "
                    f"{live.failed:,} fail"
                )
                status_col.caption(info_text)
        else:
            progress_bar.progress(0.05, text="Starting test...")
            status_col.caption(
                f"Connecting to {config.base_url.rstrip('/')}/"
                f"{config.api_path.lstrip('/')}",
            )

        # Auto-refresh while running so live metrics update
        time.sleep(2)
        st.rerun()

    elif st.button(
        "Start Load Test", type="primary", disabled=len(stages) == 0,
    ):
        # Spin up a background thread for the test
        holder = _ProgressHolder()
        st.session_state.progress_holder = holder
        st.session_state.summary = None
        st.session_state.running = True
        st.session_state.future = _EXECUTOR.submit(
            _run_test_in_thread, config, holder,
        )
        st.rerun()

    elif len(stages) > 0:
        st.success(
            "Ready to test! "
            f"{total_stages} stages in schedule. "
            f"Reach max RPS -- {max_rate:.1f} "
            f"-- and max users -- {max_users}.",
        )

    # ── Display results ──────────────────────────────────────────
    summary = st.session_state.summary

    if summary and summary.status == "error":
        st.error("Test completed with errors.")
        endpoint_url = (
            f"{summary.config.base_url.rstrip('/')}/"
            f"{summary.config.api_path.lstrip('/')}"
        )
        st.write("**Endpoint:**", endpoint_url)
        if summary.error_message:
            st.code(summary.error_message, language="text")
        else:
            st.write(
                f"No requests were sent. {len(summary.metrics)} metrics collected.",
            )

    elif summary and summary.status in ("completed", "running"):
        st.success("Load test completed!")

        # ── Metrics cards ─────────────────────────────────────
        cols = st.columns(4)
        total_metrics = len(summary.metrics)
        successful = sum(
            1 for m in summary.metrics if m.status == "success"
        )
        failed = total_metrics - successful
        avg_latency = (
            sum(m.latency_ms for m in summary.metrics) / total_metrics
            if total_metrics
            else 0
        )

        with cols[0]:
            st.metric("Total Requests", total_metrics)
        with cols[1]:
            st.metric("Successful", successful)
        with cols[2]:
            st.metric("Failed", failed)
        with cols[3]:
            st.metric("Avg Latency (ms)", f"{avg_latency:.1f}")

        # ── Charts ─────────────────────────────────────────────
        if summary.stage_metrics and summary.metrics:
            with st.expander("⚡ View Charts", expanded=True):
                render_charts(summary, num_rows)

        # ── Raw metrics table ──────────────────────────────────
        if summary.metrics:
            with st.expander("📋 Raw Metrics Table"):
                render_raw_metrics(summary, num_rows)

        # ── Export buttons ───────────────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export XLSX"):
                xlsx_bytes = export_xlsx(summary)
                st.download_button(
                    label="Download XLSX",
                    data=xlsx_bytes,
                    file_name=f"llm_test_{benchmark_suite}_{_now()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        with col2:
            if st.button("📥 Export PDF"):
                pdf_bytes = export_pdf(summary)
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"llm_test_{benchmark_suite}_{_now()}.pdf",
                    mime="application/pdf",
                )


def _now():
    """Format current time for file names."""
    import datetime
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


if __name__ == "__main__":
    main()
