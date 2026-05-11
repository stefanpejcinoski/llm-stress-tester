"""Export service for test results (XLSX + PDF)."""

from __future__ import annotations

from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")

from llm_stress_tester.enums import RateUnit
from llm_stress_tester.schemas import RequestMetric, RunSummary
from llm_stress_tester.utils.rate_units import column_suffix, to_display


def export_xlsx(summary: RunSummary) -> bytes:
    """Export all run data as an XLSX workbook."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        _write_config_sheet(summary, writer)
        _write_stage_sheet(summary, writer)
        _write_model_sheet(summary, writer)
        _write_raw_sheet(summary, writer)
        _write_errors_sheet(summary, writer)
    buf.seek(0)
    return buf.read()


def export_pdf(summary: RunSummary) -> bytes:
    """Export target vs achieved RPM chart as a PDF file."""
    fig, ax = plt.subplots(figsize=(12, 6))

    stage_metrics = summary.stage_metrics
    stage_idx = [s.stage_index for s in stage_metrics]
    target_rpm = [s.target_rps * 60.0 for s in stage_metrics]
    achieved_rpm = [s.achieved_rps * 60.0 for s in stage_metrics]

    ax.plot(stage_idx, target_rpm, marker="o", color="steelblue", label="Target RPM")
    ax.plot(stage_idx, achieved_rpm, marker="s", color="crimson", label="Achieved RPM")
    ax.set_xlabel("Stage Index")
    ax.set_ylabel("RPM")
    ax.set_title("Target vs Achieved RPM")
    ax.grid(True, alpha=0.4)
    ax.legend()

    plt.tight_layout()
    pdf_buf = BytesIO()
    fig.savefig(pdf_buf, format="pdf")
    plt.close(fig)
    pdf_buf.seek(0)
    return pdf_buf.read()


def _write_config_sheet(
    summary: RunSummary, writer: pd.ExcelWriter,
) -> None:
    """Write configuration sheet."""
    config = summary.config
    data = {
        "key": [
            "base_url",
            "api_path",
            "rate_unit",
            "initial_rate_rps",
            "max_rate_rps",
            "scaling_factor",
            "time_increment_s",
            "min_users",
            "max_users",
            "users_increment",
            "benchmark_suite",
            "timeout_s",
            "model_count",
            "token_count",
        ],
        "value": [
            config.base_url,
            config.api_path,
            config.rate_unit.value,
            config.initial_rate,
            config.max_rate,
            config.scaling_factor,
            config.time_increment,
            config.min_users,
            config.max_users,
            config.users_increment,
            config.benchmark_suite.value,
            config.timeout,
            len(config.models),
            len(config.tokens),
        ],
    }
    pd.DataFrame(data).to_excel(
        writer, sheet_name="config", index=False,
    )


def _write_raw_sheet(
    summary: RunSummary, writer: pd.ExcelWriter,
) -> None:
    """Write raw request metrics sheet.

    Columns match the UI raw metrics table exactly. All rows are written
    (no display cap). Summary sheets appear before this sheet in the workbook.
    """
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
    if not data:
        cols = [
            "stage", "model", "token_idx", "token_label", "active_users",
            f"target_{sfx}", f"achieved_{sfx}",
            "status", "status_code", "latency_ms", "error_type", "suite_id", "prompt_id",
        ]
        pd.DataFrame(columns=cols).to_excel(writer, sheet_name="raw_requests", index=False)
    else:
        pd.DataFrame(data).to_excel(writer, sheet_name="raw_requests", index=False)


def _write_stage_sheet(
    summary: RunSummary, writer: pd.ExcelWriter,
) -> None:
    """Write per-stage aggregated metrics sheet."""
    unit = summary.config.rate_unit if summary.config else RateUnit.RPS
    sfx = column_suffix(unit)
    data = [
        {
            "stage_index": s.stage_index,
            "elapsed_seconds": s.elapsed_seconds,
            f"target_{sfx}": round(to_display(s.target_rps, unit)[0], 4),
            f"achieved_{sfx}": round(to_display(s.achieved_rps, unit)[0], 4),
            "active_users": s.active_users,
            "total_requests": s.total_requests,
            "successful": s.successful,
            "failed": s.failed,
            "avg_latency_ms": s.avg_latency_ms,
            "p50_latency_ms": s.p50_latency_ms,
            "p95_latency_ms": s.p95_latency_ms,
            "p99_latency_ms": s.p99_latency_ms,
            "error_rate": s.error_rate,
        }
        for s in summary.stage_metrics
    ]
    if not data:
        data = [
            {**dict.fromkeys(
                ["stage_index", "elapsed_seconds", f"target_{sfx}", f"achieved_{sfx}",
                 "active_users", "total_requests", "successful", "failed",
                 "avg_latency_ms", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms",
                 "error_rate"],
                "",
            )},
        ]
    pd.DataFrame(data).to_excel(
        writer, sheet_name="stage_summary", index=False,
    )


def _write_model_sheet(
    summary: RunSummary, writer: pd.ExcelWriter,
) -> None:
    """Write per-model summary sheet."""
    data: list[dict] = []
    per_model: dict[str, list[RequestMetric]] = {}
    for m in summary.metrics:
        per_model.setdefault(m.model, []).append(m)

    for model_name, model_metrics in per_model.items():
        total = len(model_metrics)
        success = sum(
            1 for mm in model_metrics if mm.status.value == "success"
        )
        latencies = sorted([mm.latency_ms for mm in model_metrics])
        pct50 = latencies[len(latencies) // 2] if latencies else 0
        pct95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
        pct99 = latencies[min(int(len(latencies) * 0.99), len(latencies) - 1)] if latencies else 0
        data.append({
            "model": model_name,
            "total_requests": total,
            "successful": success,
            "failed": total - success,
            "success_rate": success / total if total else 0,
            "avg_latency_ms": sum(latencies) / total if total else 0,
            "p50_latency_ms": pct50,
            "p95_latency_ms": pct95,
            "p99_latency_ms": pct99,
        })
    if not data:
        data = [{"model": ""} for _ in range(1)]
    pd.DataFrame(data).to_excel(
        writer, sheet_name="model_summary", index=False,
    )


def _write_errors_sheet(
    summary: RunSummary, writer: pd.ExcelWriter,
) -> None:
    """Write error details sheet (non-success requests)."""
    errors = [
        {
            "stage_index": m.stage_index,
            "model": m.model,
            "status_code": m.status_code,
            "error_type": m.error_type,
            "active_users": m.active_users,
        }
        for m in summary.metrics
        if m.status.value != "success" and m.error_type is not None
    ]
    pd.DataFrame(errors).to_excel(
        writer, sheet_name="errors", index=False,
    )
