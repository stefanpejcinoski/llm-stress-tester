"""Rate schedule service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScheduleStage:
    """One stage in the load test schedule."""

    stage_index: int
    target_rps: float
    active_users: int
    duration: float  # seconds


def build_schedule(
    initial_rps: float,
    max_rps: float,
    min_users: int,
    max_users: int,
    users_increment: int,
    scaling_factor: float,
    time_increment: float,
) -> list[ScheduleStage]:
    """Build schedule of stages from initial rate to max rate."""
    stages: list[ScheduleStage] = []
    current_rps = initial_rps
    current_users = min_users
    idx = 0

    while True:
        actual_users = min(current_users, max_users)
        effective_rps = min(current_rps, max_rps)
        stages.append(
            ScheduleStage(
                stage_index=idx,
                target_rps=effective_rps,
                active_users=actual_users,
                duration=time_increment,
            ),
        )

        if effective_rps >= max_rps:
            break

        next_rps = current_rps * scaling_factor
        if next_rps <= current_rps:
            break

        current_rps = next_rps
        current_users += users_increment
        idx += 1

    return stages
