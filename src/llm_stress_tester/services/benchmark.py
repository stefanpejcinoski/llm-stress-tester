"""Benchmark catalog service."""

from __future__ import annotations

from llm_stress_tester.data.prompts import get_all_suites


def list_available_suites() -> list[str]:
    """Return list of available benchmark suite IDs."""
    return get_all_suites()
