"""Tests for traffic allocator."""

from llm_stress_tester.schemas import ModelEntry
from llm_stress_tester.services.traffic_allocator import (
    compute_allocated_rps,
    compute_total_outgoing_rps,
    pick_model,
)


def test_compute_allocated_rps():
    assert compute_allocated_rps(10.0, 50.0) == 5.0


def test_compute_allocated_rps_zero():
    assert compute_allocated_rps(10.0, 0.0) == 0.0


def test_compute_total_outgoing_rps_single_model():
    models = [ModelEntry(model="gpt-4", percentage=100.0)]
    total = compute_total_outgoing_rps(10.0, models)
    assert total == 20.0


def test_compute_total_outgoing_rps_split():
    models = [
        ModelEntry(model="gpt-4", percentage=50.0),
        ModelEntry(model="claude", percentage=50.0),
    ]
    total = compute_total_outgoing_rps(10.0, models)
    assert total == 20.0


def test_compute_total_outgoing_rps_mixed():
    # 100% model duplicates base (10+10), 50% adds 5 => total 25
    models = [
        ModelEntry(model="gpt-4", percentage=100.0),
        ModelEntry(model="claude", percentage=50.0),
    ]
    total = compute_total_outgoing_rps(10.0, models)
    assert total == 25.0


def test_pick_model_round_robin():
    models = [
        ModelEntry(model="a", percentage=50.0),
        ModelEntry(model="b", percentage=50.0),
    ]
    result0 = pick_model(0, models)
    result1 = pick_model(1, models)
    result2 = pick_model(2, models)
    assert result0["model"] == "a"
    assert result1["model"] == "b"
    assert result2["model"] == "a"
