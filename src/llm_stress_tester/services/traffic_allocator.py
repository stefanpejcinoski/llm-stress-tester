"""Traffic allocator: computes per-model and per-step statistics."""

from __future__ import annotations

from llm_stress_tester.schemas import ModelEntry


def compute_allocated_rps(base_rps: float, percentage: float) -> float:
    """Compute RPS allocated to a specific model."""
    return base_rps * percentage / 100.0


def pick_model(
    round_total: int, models: list[ModelEntry],
) -> dict[str, object]:
    """Choose a model based on round-robin from valid entries."""
    active = [m for m in models if m.percentage > 0 or m.percentage == 100]
    if not active:
        return {"model": models[0].model, "percentage": models[0].percentage}
    return {
        "model": active[round_total % len(active)].model,
        "percentage": active[round_total % len(active)].percentage,
    }
