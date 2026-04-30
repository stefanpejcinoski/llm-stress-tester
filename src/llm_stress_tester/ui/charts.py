"""Streamlit chart rendering for LLM stress test results.

Uses matplotlib under the hood (Agg backend) and renders via
st.pyplot so no external charting library is needed.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.ticker import FuncFormatter

matplotlib.use("Agg")

from llm_stress_tester.enums import RateUnit
from llm_stress_tester.schemas import RunSummary
from llm_stress_tester.utils.rate_units import column_suffix, to_display


def _rate_fmt(val: float, _pos: int) -> str:
    """Adaptive rate tick: 2 decimals <10, 1 decimal <100, integers above."""
    if val >= 100:
        return f"{val:.0f}"
    if val >= 10:
        return f"{val:.1f}"
    return f"{val:.2f}"


def render_charts(summary: RunSummary, num_rows: int) -> None:
    """Render a 3x2 grid of charts showing test results.

    Arguments:
        summary: The completed RunSummary object.
        num_rows: Unused placeholder (kept for API compat).

    """
    stage_metrics = summary.stage_metrics
    if not stage_metrics:
        return

    # ── 1. RPS over time (target vs achieved) ──────────────────
    fig, axes = plt.subplots(3, 2, figsize=(16, 18))
    fig.suptitle("LLM Stress Test Results", fontsize=16)

    elapsed = [s.elapsed_seconds for s in stage_metrics]

    ax00 = axes[0, 0]
    unit = summary.config.rate_unit if summary.config else RateUnit.RPS
    target_raw = [s.target_rps for s in stage_metrics]
    achieved_raw = [s.achieved_rps for s in stage_metrics]
    target_disp = [to_display(v, unit)[0] for v in target_raw]
    achieved_disp = [to_display(v, unit)[0] for v in achieved_raw]
    _, rate_label = to_display(1.0, unit)  # "RPS" or "RPM"

    # Left axis: Target rate
    (line_t,) = ax00.plot(
        elapsed, target_disp, marker="o", color="steelblue", label=f"Target {rate_label}",
    )
    ax00.set_xlabel("Elapsed (s)")
    ax00.set_ylabel(f"Target {rate_label}", color="steelblue")
    ax00.tick_params(axis="y", labelcolor="steelblue")
    ax00.yaxis.set_major_formatter(FuncFormatter(_rate_fmt))
    ax00.grid(True, alpha=0.4)

    # Right axis: Achieved rate — independently scaled, never a flat line
    ax00b = ax00.twinx()
    (line_a,) = ax00b.plot(
        elapsed, achieved_disp, marker="s", color="crimson", label=f"Achieved {rate_label}",
    )
    ax00b.set_ylabel(f"Achieved {rate_label}", color="crimson")
    ax00b.tick_params(axis="y", labelcolor="crimson")
    ax00b.yaxis.set_major_formatter(FuncFormatter(_rate_fmt))

    ax00.set_title(f"{rate_label} Over Time (Target vs Achieved)")
    ax00.legend(handles=[line_t, line_a], loc="upper left")

    # ── 2. Latency percentiles ─────────────────────────────────
    ax01 = axes[0, 1]
    p50 = [s.p50_latency_ms for s in stage_metrics]
    p95 = [s.p95_latency_ms for s in stage_metrics]
    p99 = [s.p99_latency_ms for s in stage_metrics]
    ax01.plot(elapsed, p50, label="P50", color="green", marker="o")
    ax01.plot(elapsed, p95, label="P95", color="orange", marker="s")
    ax01.plot(elapsed, p99, label="P99", color="red", marker="^")
    ax01.set_xlabel("Elapsed (s)")
    ax01.set_ylabel("Latency (ms)")
    ax01.set_title("Latency Percentiles")
    ax01.legend()
    ax01.grid(True)

    # ── 3. Error rate over time ────────────────────────────────
    ax10 = axes[1, 0]
    error_rates = [s.error_rate * 100 for s in stage_metrics]
    ax10.plot(elapsed, error_rates, marker="x", color="red", label="Error Rate (%)")
    ax10.set_xlabel("Elapsed (s)")
    ax10.set_ylabel("Error Rate (%)")
    ax10.set_title("Error Rate Over Time")
    ax10.legend()
    ax10.grid(True)

    # ── 4. Requests per stage ──────────────────────────────────
    ax11 = axes[1, 1]
    stages = list(range(len(stage_metrics)))
    totals = [s.total_requests for s in stage_metrics]
    colors = ["steelblue" if s.successful >= s.total_requests * 0.95 else "coral"
              for s in stage_metrics]
    ax11.bar(stages, totals, color=colors)
    ax11.set_xlabel("Stage Index")
    ax11.set_ylabel("Total Requests")
    ax11.set_title("Requests Per Stage")
    ax11.grid(axis="y")

    # ── 5. Model comparison (avg latency) ──────────────────────
    ax20 = axes[2, 0]
    per_model: dict[str, list[float]] = {}
    for m in summary.metrics:
        per_model.setdefault(m.model, []).append(m.latency_ms)

    if per_model:
        model_names = sorted(per_model.keys())
        avg_latencies = [
            sum(v) / len(v) for v in per_model.values()
        ]
        jitter = np.random.uniform(-0.15, 0.15, len(model_names))
        ax20.scatter(
            np.array(range(len(model_names))) + jitter,
            avg_latencies,
            color="purple",
            s=80,
        )
        ax20.set_xticks(range(len(model_names)))
        ax20.set_xticklabels(model_names, rotation=45, ha="right")
        ax20.set_xlabel("Model")
        ax20.set_ylabel("Avg Latency (ms)")
        ax20.set_title("Model Comparison (Avg Latency)")

    # ── 6. Success rate by model ───────────────────────────────
    ax21 = axes[2, 1]
    if per_model:
        success_rates = []
        for model_name in model_names:
            model_reqs = per_model[model_name]
            total = len(model_reqs)
            # Reuse summary.metrics to count successes
            from llm_stress_tester.enums import RequestStatus
            model_metrics = [
                m for m in summary.metrics if m.model == model_name
            ]
            successful = sum(
                1 for m in model_metrics
                if m.status == RequestStatus.SUCCESS
            )
            success_rates.append(
                (successful / total) * 100 if total else 0,
            )

        jitter = np.random.uniform(-0.15, 0.15, len(model_names))
        ax21.scatter(
            np.array(range(len(model_names))) + jitter,
            success_rates,
            color="teal",
            s=80,
        )
        ax21.set_xticks(range(len(model_names)))
        ax21.set_xticklabels(model_names, rotation=45, ha="right")
        ax21.set_xlabel("Model")
        ax21.set_ylabel("Success Rate (%)")
        ax21.set_title("Per-Model Success Rate")

    plt.tight_layout()
    st.pyplot(fig)


def render_raw_metrics(summary: RunSummary, num_rows: int) -> None:
    """Render raw request metrics as a Streamlit dataframe.

    Capped at num_rows.
    """
    if not summary.metrics:
        st.text("No raw metrics to display.")
        return

    unit = summary.config.rate_unit if summary.config else RateUnit.RPS
    sfx = column_suffix(unit)
    achieved_by_stage = {s.stage_index: s.achieved_rps for s in (summary.stage_metrics or [])}
    data = [
        {
            "stage": m.stage_index,
            "model": m.model,
            "token_idx": m.token_index,
            "token_label": m.token_label,
            "active_users": m.active_users,
            f"target_{sfx}": round(to_display(m.target_rps, unit)[0], 2),
            f"achieved_{sfx}": round(to_display(achieved_by_stage.get(m.stage_index, 0.0), unit)[0], 2),
            "status": m.status,
            "status_code": m.status_code,
            "latency_ms": round(m.latency_ms, 2),
            "error_type": m.error_type or "",
            "suite_id": m.suite_id,
            "prompt_id": m.prompt_id,
        }
        for m in summary.metrics
    ]

    df = pd.DataFrame(data)
    st.dataframe(df.head(num_rows), use_container_width=True)
