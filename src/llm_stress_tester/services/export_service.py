"""Export service for test results (XLSX + PDF)."""

from __future__ import annotations

from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

matplotlib.use("Agg")

from llm_stress_tester.schemas import RequestMetric, RunSummary


def _rps_fmt(val: float, _pos: int) -> str:
    """Adaptive RPS tick: 2 decimals <10, 1 decimal <100, integers above."""
    if val >= 100:
        return f"{val:.0f}"
    if val >= 10:
        return f"{val:.1f}"
    return f"{val:.2f}"


def export_xlsx(summary: RunSummary) -> bytes:
    """Export all run data as an XLSX workbook."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        _write_config_sheet(summary, writer)
        _write_raw_sheet(summary, writer)
        _write_stage_sheet(summary, writer)
        _write_model_sheet(summary, writer)
        _write_errors_sheet(summary, writer)
    buf.seek(0)
    return buf.read()


def export_pdf(summary: RunSummary) -> bytes:
    """Export graphs as a PDF file."""
    fig, axes = plt.subplots(3, 2, figsize=(16, 18))
    fig.suptitle("LLM Stress Test Results", fontsize=16)

    stage_metrics = summary.stage_metrics
    base_url = [s.elapsed_seconds for s in stage_metrics]

    ax0 = axes[0, 0]
    target_rps_vals = [s.target_rps for s in stage_metrics]
    achieved_rps_vals = [s.achieved_rps for s in stage_metrics]

    # Left axis: Target RPS
    (line_t,) = ax0.plot(
        base_url, target_rps_vals, marker="o", color="steelblue", label="Target RPS",
    )
    ax0.set_xlabel("Time (s)")
    ax0.set_ylabel("Target RPS", color="steelblue")
    ax0.tick_params(axis="y", labelcolor="steelblue")
    ax0.yaxis.set_major_formatter(FuncFormatter(_rps_fmt))
    ax0.grid(True, alpha=0.4)

    # Right axis: Achieved RPS — independently scaled so it is never a flat line
    ax0b = ax0.twinx()
    (line_a,) = ax0b.plot(
        base_url, achieved_rps_vals, marker="s", color="crimson", label="Achieved RPS",
    )
    ax0b.set_ylabel("Achieved RPS", color="crimson")
    ax0b.tick_params(axis="y", labelcolor="crimson")
    ax0b.yaxis.set_major_formatter(FuncFormatter(_rps_fmt))

    ax0.set_title("Aggregate RPS Over Time")
    ax0.legend(handles=[line_t, line_a], loc="upper left")

    ax1 = axes[0, 1]
    ax1.plot(base_url, [s.p50_latency_ms for s in stage_metrics], label="P50")
    ax1.plot(base_url, [s.p95_latency_ms for s in stage_metrics], label="P95")
    ax1.plot(base_url, [s.p99_latency_ms for s in stage_metrics], label="P99")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Latency (ms)")
    ax1.legend()
    ax1.set_title("Latency Over Time")

    ax2 = axes[1, 0]
    ax2.plot(base_url, [s.error_rate * 100 for s in stage_metrics])
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Error Rate (%)")
    ax2.set_title("Error Rate Over Time")

    ax3 = axes[1, 1]
    ax3.bar(
        [s.active_users for s in stage_metrics],
        [s.total_requests for s in stage_metrics],
    )
    ax3.set_xlabel("Stage (Active Users)")
    ax3.set_ylabel("Total Requests")
    ax3.set_title("Per-Stage Request Count")

    per_model: dict[str, list[RequestMetric]] = {}
    for m in summary.metrics:
        per_model.setdefault(m.model, []).append(m)

    ax4 = axes[2, 0]
    for model_key, model_metrics in per_model.items():
        if not model_metrics:
            continue
        latencies = sorted([
            mm.latency_ms for mm in model_metrics
        ])
        pct50 = latencies[len(latencies) // 2]
        pct95 = latencies[int(len(latencies) * 0.95)]
        pct99 = latencies[min(int(len(latencies) * 0.99), len(latencies) - 1)]
        ax4.plot(
            [pct50, pct95, pct99],
            label=f"{model_key} (p50={pct50:.0f}ms)",
            marker="o",
        )
    ax4.set_ylabel("Latency (ms)")
    ax4.set_title("Latency by Model (P50/P95/P99)")
    ax4.legend()
    ax4.set_xticklabels(["P50", "P95", "P99"])

    ax5 = axes[2, 1]
    for model_key, model_metrics in per_model.items():
        if not model_metrics:
            continue
        success = sum(
            1 for mm in model_metrics if mm.status == "success"
        )
        total = len(model_metrics)
        ax5.bar(
            model_key,
            (success / total) * 100 if total else 0,
            label=f"{model_key}",
        )
    ax5.set_ylabel("Success Rate (%)")
    ax5.set_title("Per-Model Success Rate")
    if per_model:
        ax5.legend()

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
    """Write raw request metrics sheet."""
    data = [
        {
            "stage_index": m.stage_index,
            "model": m.model,
            "model_percentage": m.model_percentage,
            "token_index": m.token_index,
            "token_label": m.token_label,
            "active_users": m.active_users,
            "target_rps": m.target_rps,
            "aggregate_rps": m.aggregate_rps,
            "status": m.status,
            "status_code": m.status_code,
            "latency_ms": m.latency_ms,
            "error_type": m.error_type,
            "suite_id": m.suite_id,
            "prompt_id": m.prompt_id,
        }
        for m in summary.metrics
    ]
    if data:
        pd.DataFrame(data).to_excel(
            writer, sheet_name="raw_requests", index=False,
        )


def _write_stage_sheet(
    summary: RunSummary, writer: pd.ExcelWriter,
) -> None:
    """Write per-stage aggregated metrics sheet."""
    data = [
        {
            "stage_index": s.stage_index,
            "elapsed_seconds": s.elapsed_seconds,
            "target_rps": s.target_rps,
            "achieved_rps": s.achieved_rps,
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
            {**dict.fromkeys(["stage_index", "elapsed_seconds", "target_rps", "achieved_rps", "active_users", "total_requests", "successful", "failed", "avg_latency_ms", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "error_rate"], "")},
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
