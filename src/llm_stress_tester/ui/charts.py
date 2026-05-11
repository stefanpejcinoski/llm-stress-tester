"""Streamlit chart rendering for LLM stress test results."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from llm_stress_tester.enums import RateUnit
from llm_stress_tester.schemas import RunSummary
from llm_stress_tester.utils.rate_units import column_suffix, to_display


def _build_rate_chart_df(summary: RunSummary) -> pd.DataFrame:
    """Build long-form dataframe for target vs achieved RPM chart."""
    rows: list[dict[str, float | int | str]] = []
    for stage in summary.stage_metrics:
        target_rpm = stage.target_rps * 60.0
        achieved_rpm = stage.achieved_rps * 60.0
        common = {
            "stage_index": stage.stage_index,
            "active_users": stage.active_users,
            "total_requests": stage.total_requests,
        }
        rows.append({
            **common,
            "series": "Target RPM",
            "rpm": target_rpm,
        })
        rows.append({
            **common,
            "series": "Achieved RPM",
            "rpm": achieved_rpm,
        })
    return pd.DataFrame(rows)


def _compute_scale_info(df: pd.DataFrame) -> dict[str, float | bool]:
    """Compute y-axis scaling behavior from target/achieved peaks."""
    target_df = df.loc[df["series"] == "Target RPM", ["stage_index", "rpm"]]
    target_max = float(target_df["rpm"].max())
    target_peak_stage = int(target_df.loc[target_df["rpm"].idxmax(), "stage_index"])
    achieved_max = float(df.loc[df["series"] == "Achieved RPM", "rpm"].max())

    if achieved_max <= 0:
        return {
            "use_achieved_scale": target_max > 0,
            "y_max": 1.0,
            "target_max": target_max,
            "target_peak_stage": target_peak_stage,
            "achieved_max": achieved_max,
        }

    ratio = target_max / achieved_max
    use_achieved_scale = ratio > 10.0
    y_max = max(1.0, achieved_max * 1.15) if use_achieved_scale else max(target_max, achieved_max)
    return {
        "use_achieved_scale": use_achieved_scale,
        "y_max": y_max,
        "target_max": target_max,
        "target_peak_stage": target_peak_stage,
        "achieved_max": achieved_max,
    }


def render_charts(summary: RunSummary, num_rows: int) -> None:
    """Render native Streamlit chart(s) for test results."""
    del num_rows  # API compatibility placeholder

    stage_metrics = summary.stage_metrics
    if not stage_metrics:
        return

    df = _build_rate_chart_df(summary)
    if df.empty:
        return

    scale = _compute_scale_info(df)
    y_encoding = alt.Y("rpm:Q", title="RPM")
    if scale["use_achieved_scale"]:
        y_encoding = alt.Y("rpm:Q", title="RPM", scale=alt.Scale(domain=[0, scale["y_max"]]))

    line_chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("stage_index:O", title="Stage Index"),
            y=y_encoding,
            color=alt.Color("series:N", title="Series"),
            tooltip=[
                alt.Tooltip("stage_index:O", title="Stage"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("rpm:Q", title="RPM", format=".2f"),
                alt.Tooltip("active_users:Q", title="Active Users"),
                alt.Tooltip("total_requests:Q", title="Requests"),
            ],
        )
    )

    chart = line_chart
    if scale["use_achieved_scale"]:
        peak_stage = int(scale["target_peak_stage"])
        note_df = pd.DataFrame([
            {
                "stage_index": peak_stage,
                "rpm": float(scale["y_max"]) * 0.98,
                "note": f"Target peak: {float(scale['target_max']):.2f} RPM (off-scale)",
            },
        ])
        marker_df = pd.DataFrame([
            {
                "stage_index": peak_stage,
                "rpm": float(scale["y_max"]),
            },
        ])
        marker_layer = (
            alt.Chart(marker_df)
            .mark_point(shape="triangle-up", size=90, color="crimson")
            .encode(
                x=alt.X("stage_index:O"),
                y=alt.Y("rpm:Q"),
            )
        )
        note_layer = (
            alt.Chart(note_df)
            .mark_text(align="left", baseline="bottom", dx=8, dy=-6, color="crimson")
            .encode(
                x=alt.X("stage_index:O"),
                y=alt.Y("rpm:Q"),
                text=alt.Text("note:N"),
            )
        )
        chart = line_chart + marker_layer + note_layer

    chart = chart.properties(title="Target vs Achieved RPM", height=420).interactive()
    st.altair_chart(chart, use_container_width=True)
    if scale["use_achieved_scale"]:
        st.caption("Y-axis auto-scaled to achieved RPM (target peak is >10x achieved peak).")


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
