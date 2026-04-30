"""Tests for rate schedule builder."""

from llm_stress_tester.services.schedule import build_schedule


def test_build_schedule_single_stage():
    stages = build_schedule(
        initial_rps=10.0,
        max_rps=10.0,
        min_users=1,
        max_users=5,
        users_increment=1,
        scaling_factor=2.0,
        time_increment=60.0,
    )
    assert len(stages) == 1
    assert stages[0].stage_index == 0
    assert stages[0].target_rps == 10.0
    assert stages[0].active_users == 1


def test_build_schedule_multiple_stages():
    stages = build_schedule(
        initial_rps=1.0,
        max_rps=8.0,
        min_users=1,
        max_users=10,
        users_increment=1,
        scaling_factor=2.0,
        time_increment=60.0,
    )
    assert len(stages) == 4
    assert stages[0].stage_index == 0
    assert stages[1].stage_index == 1
    assert stages[2].stage_index == 2
    assert stages[3].stage_index == 3
    assert stages[0].target_rps == 1.0
    assert stages[1].target_rps == 2.0
    assert stages[2].target_rps == 4.0
    assert stages[3].target_rps == 8.0
    for s in stages:
        assert s.duration == 60.0


def test_build_schedule_max_users_capped():
    stages = build_schedule(
        initial_rps=1.0,
        max_rps=10.0,
        min_users=2,
        max_users=2,
        users_increment=1,
        scaling_factor=2.0,
        time_increment=30.0,
    )
    for s in stages:
        assert s.active_users == 2


def test_build_schedule_caps_at_max_rps():
    stages = build_schedule(
        initial_rps=1.0,
        max_rps=5.0,
        min_users=1,
        max_users=10,
        users_increment=1,
        scaling_factor=2.0,
        time_increment=10.0,
    )
    for s in stages:
        assert s.target_rps <= 5.0


def test_build_schedule_duration_constant():
    stages = build_schedule(
        initial_rps=1.0,
        max_rps=100.0,
        min_users=1,
        max_users=20,
        users_increment=2,
        scaling_factor=2.5,
        time_increment=45.0,
    )
    for s in stages:
        assert s.duration == 45.0

    assert stages[0].stage_index == 0
    assert stages[1].stage_index == 1
    