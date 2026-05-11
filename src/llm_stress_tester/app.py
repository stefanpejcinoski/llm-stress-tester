"""Streamlit entry point for LLM Stress Tester."""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import streamlit as st

from llm_stress_tester.data.prompts import SUITES_DESCRIPTIONS
from llm_stress_tester.enums import BenchmarkSuite, RateUnit
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
from llm_stress_tester.utils.rate_units import to_display
from llm_stress_tester.utils.validation import (
    validate_models,
    validate_rate_schedule,
    validate_token_count,
    validate_user_schedule,
)

# Module-level executor lives across Streamlit reruns
_EXECUTOR = ThreadPoolExecutor(max_workers=4)


# Thread-safe progress holder. The background thread writes; the main thread reads.
# A simple lock + slot is enough for this one-writer, one-reader pattern.
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class _ProgressHolder:
    """Thread-safe holder for live progress updates."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._info: ProgressInfo | None = None
        self._set_at: float | None = None

    def set(self, info: ProgressInfo) -> None:
        with self._lock:
            self._info = info
            self._set_at = time.monotonic()

    def get(self) -> ProgressInfo | None:
        with self._lock:
            return self._info

    def get_age_s(self) -> float | None:
        """Seconds since last update, or None if never updated."""
        with self._lock:
            if self._set_at is None:
                return None
            return time.monotonic() - self._set_at


def _run_test_in_thread(
    config: TestConfig,
    holder: _ProgressHolder,
    cancel_event: threading.Event,
) -> RunSummary:
    """Run the async load test in this worker thread's event loop.

    Returns the RunSummary when complete. Exceptions inside run_test
    are captured in summary.error_message.
    """
    def _on_progress(info: ProgressInfo) -> None:
        holder.set(info)

    async def _runner() -> RunSummary:
        return await run_test(config, on_progress=_on_progress, cancel_event=cancel_event)

    return asyncio.run(_runner())


def _render_progress(
    holder: _ProgressHolder | None,
    total_stages: int,
    base_url: str,
    api_path: str,
    running_flag_name: str,
    future_flag_name: str,
    summary_flag_name: str,
    rate_unit: object = None,
    cancel_event_key: str = "cancel_event",
) -> None:
    """Render live progress inside an auto-refreshing fragment."""

    @st.fragment(run_every=2)
    def _fragment():
        future: Future | None = st.session_state[future_flag_name]
        running: bool = st.session_state[running_flag_name]

        # Advance spinner tick each fragment refresh
        tick = st.session_state.get("_progress_tick", 0) + 1
        st.session_state["_progress_tick"] = tick
        spinner = _SPINNER[tick % len(_SPINNER)]

        # Check if the future has completed
        if future is not None and future.done():
            try:
                st.session_state[summary_flag_name] = future.result()
            except Exception as exc:
                last_config = st.session_state.get("_last_config")
                if last_config is None:
                    last_config = st.session_state.get("_last_config")
                summary = RunSummary(config=last_config, status="error")  # type: ignore[arg-type]
                summary.error_message = f"{type(exc).__name__}: {exc}"
                st.session_state[summary_flag_name] = summary
            st.session_state[running_flag_name] = False
            st.session_state[future_flag_name] = None
            st.rerun()

        live = holder.get() if holder else None
        age_s = holder.get_age_s() if holder else None

        if live:
            # Smooth progress: interpolate within the current stage
            within_stage = min(
                live.stage_elapsed_s / max(live.stage_duration_s, 0.001), 1.0,
            )
            pct = (live.stage_index + within_stage) / max(total_stages, 1)
            pct = min(pct, 1.0)

            stage_display = live.stage_index + 1  # 1-indexed for humans
            st.progress(
                pct,
                text=f"{spinner} Stage {stage_display}/{total_stages} — "
                     f"{live.stage_elapsed_s:.0f}s / {live.stage_duration_s:.0f}s",
            )

            _unit = rate_unit if isinstance(rate_unit, RateUnit) else RateUnit.RPS
            target_disp, rate_label = to_display(live.target_rps, _unit)
            achieved_disp, _ = to_display(live.achieved_rps, _unit)

            cols = st.columns(5)
            cols[0].metric(f"Target {rate_label}", f"{target_disp:.2f}")
            rate_delta = achieved_disp - target_disp
            cols[1].metric(
                f"Achieved {rate_label}",
                f"{achieved_disp:.2f}",
                delta=f"{rate_delta:+.2f} vs target",
                delta_color="off",
            )
            cols[2].metric("Active Users", live.active_users)
            cols[3].metric("Collected", f"{live.total_metrics:,}")
            cols[4].metric("Failed", f"{live.failed:,}")

            elapsed_s = live.elapsed_ms / 1000
            age_str = f"{age_s:.1f}s ago" if age_s is not None else "—"
            st.caption(
                f"{spinner} Stage {stage_display}/{total_stages} — "
                f"{elapsed_s:.0f}s elapsed — "
                f"{live.total_metrics:,}/{live.total_requests:,} requests — "
                f"{live.successful:,} ok, {live.failed:,} fail — "
                f"last update {age_str}",
            )
        else:
            st.progress(0.05, text=f"{spinner} Starting test...")
            st.caption(
                f"Connecting to {base_url.rstrip('/')}/"
                f"{api_path.lstrip('/')}...",
            )

        # Stop Test button — signals the background thread to exit early
        # and returns whatever partial results have been collected so far.
        if running:
            if st.button("Stop Test", type="secondary", key="stop_btn"):
                evt: threading.Event | None = st.session_state.get(cancel_event_key)
                if evt is not None:
                    evt.set()
                # Don't clear future — let it finish naturally and return
                # partial RunSummary; the future.done() check above will
                # pick it up on the next fragment refresh.
            st.stop()

    _fragment()


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
    for key in ("running", "future", "progress_holder", "summary", "stages", "cancel_event"):
        if key not in st.session_state:
            setattr(st.session_state, key, None)

    # ── Forms ────────────────────────────────────────────────────
    st.header("1. Endpoint")
    base_url, api_path, is_public = render_endpoint_form()

    if is_public:
        st.header("2. Authentication")
        st.info("Public endpoint selected - no tokens required.")
        tokens: list = []
    else:
        st.header("2. API Tokens")
        tokens = render_tokens_form()

    st.header("3. Rate & Schedule")
    rate_unit, initial_rate, max_rate, scaling_factor, time_increment = (
        render_rate_form()
    )

    st.header("4. Users")
    min_users, max_users, users_increment = render_users_form()

    st.header("5. Models & Traffic Split")
    models = render_models_form()

    st.header("6. Benchmark Suite")
    benchmark_suite_key = render_benchmark_form()

    st.header("7. Advanced Settings")
    timeout, num_rows = render_advanced_form(timeout=60, num_rows=100)

    # ── Validate ─────────────────────────────────────────────────
    errors: list[str] = []

    if tokens:
        errors.extend(
            validate_token_count(len(tokens), min_users, max_users),
        )

    errors.extend(validate_models(models))
    errors.extend(
        validate_rate_schedule(
            initial_rate, max_rate, scaling_factor, time_increment, rate_unit,
        ),
    )
    errors.extend(
        validate_user_schedule(min_users, max_users, users_increment),
    )

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
        benchmark_suite=BenchmarkSuite(benchmark_suite_key),
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
                    "suite": benchmark_suite_key,
                    "description": SUITES_DESCRIPTIONS.get(
                        benchmark_suite_key, ("Unknown", ""),
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
        st.session_state.stages = stages
    except Exception:
        stages = []
        total_stages = 0

    # ── Store config for fragment access ─────────────────────────
    st.session_state["_last_config"] = config

    # ── Progress fragment (auto-refresh every 2s) ────────────────
    if st.session_state.running:
        _render_progress(
            st.session_state.progress_holder,
            total_stages,
            base_url,
            api_path,
            "running",
            "future",
            "summary",
            rate_unit=rate_unit,
            cancel_event_key="cancel_event",
        )
        return  # Halt main flow while running — fragment handles rendering

    # ── Submit button ────────────────────────────────────────────
    if st.button(
        "Start Load Test", type="primary", disabled=len(stages) == 0,
    ):
        cancel_event = threading.Event()
        holder = _ProgressHolder()
        st.session_state.progress_holder = holder
        st.session_state.cancel_event = cancel_event
        st.session_state.summary = None
        st.session_state.running = True
        st.session_state["_progress_tick"] = 0
        st.session_state.future = _EXECUTOR.submit(
            _run_test_in_thread, config, holder, cancel_event,
        )
        st.rerun()

    elif len(stages) > 0:
        max_disp, rate_label = to_display(max_rate, rate_unit)
        st.success(
            "Ready to test! "
            f"{total_stages} stages in schedule. "
            f"Reach max {rate_label} -- {max_disp:.2f} "
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
                    file_name=f"llm_test_{benchmark_suite_key}_{_now()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        with col2:
            if st.button("📥 Export PDF"):
                pdf_bytes = export_pdf(summary)
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"llm_test_{benchmark_suite_key}_{_now()}.pdf",
                    mime="application/pdf",
                )


def _now() -> str:
    """Format current time for file names."""
    import datetime
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


if __name__ == "__main__":
    main()
