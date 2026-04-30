"""Validation utilities for test configuration."""

from __future__ import annotations

from llm_stress_tester.schemas import ModelEntry


def validate_token_count(
    token_count: int, min_users: int, max_users: int,
) -> list[str]:
    """Validate that token count can support configured users."""
    errors: list[str] = []

    if min_users > token_count:
        errors.append(
            f"min_users ({min_users}) exceeds token count ({token_count}). "
            "Truncate to token count.",
        )

    effective_max = min(max_users, token_count)
    if effective_max < 1:
        errors.append(f"No usable tokens (token_count={token_count})")

    return errors


def validate_models(models: list[ModelEntry]) -> list[str]:
    """Validate model entries."""
    errors: list[str] = []

    if not models:
        return ["At least one model must be configured."]

    for entry in models:
        if not entry.model or not entry.model.strip():
            errors.append("All models must have a non-empty name.")
            continue
        if entry.percentage < 0 or entry.percentage > 100:
            errors.append(
                f"Model '{entry.model}': percentage must be 0-100.",
            )

    multicases = sorted(
        [e for e in models if e.percentage == 100], key=lambda e: e.model,
    )
    if len(multicases) >= 2:
        errors.append(
            f"Multiple models at 100% detected "
            f"({', '.join(e.model for e in multicases)}). "
            "Each will receive 100% of load (duplicated traffic).",
        )

    return errors


def validate_rate_schedule(
    initial: float,
    max_rate: float,
    scaling_factor: float,
    increment: float,
) -> list[str]:
    """Validate rate schedule parameters."""
    errors: list[str] = []

    if initial <= 0:
        errors.append("Initial RPS must be > 0")
    if max_rate < initial:
        errors.append("Max RPS must be >= Initial RPS")
    if scaling_factor <= 1.0:
        errors.append("Scaling factor must be > 1.0")
    if increment <= 0:
        errors.append("Time increment must be > 0")

    return errors


def validate_user_schedule(
    min_users: int,
    max_users: int,
    increment: int,
) -> list[str]:
    """Validate user schedule parameters."""
    errors: list[str] = []

    if min_users < 1:
        errors.append("min_users must be >= 1")
    if max_users < min_users:
        errors.append("max_users must be >= min_users")
    if increment < 1:
        errors.append("users_increment must be >= 1")

    return errors
