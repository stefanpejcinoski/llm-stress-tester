"""Tests for benchmark catalogue service."""

from llm_stress_tester.data.prompts import (
    BENCHMARK_PROMPTS,
    SUITES_DESCRIPTIONS,
    SUITES_ORDER,
)
from llm_stress_tester.enums import BenchmarkSuite
from llm_stress_tester.services.benchmark import list_available_suites


def test_suites_order():
    """SUITES_ORDER should list all suites."""
    assert len(SUITES_ORDER) == len(BenchmarkSuite)
    for suitename in SUITES_ORDER:
        assert suitename in [s.value for s in BenchmarkSuite]


def test_suite_descriptions():
    """Each suite should have a description tuple."""
    for suitename in SUITES_ORDER:
        desc = SUITES_DESCRIPTIONS.get(suitename)
        assert desc is not None
        assert isinstance(desc, tuple)
        assert len(desc) == 2
        label, detail = desc
        assert len(label) > 0
        assert len(detail) > 0


def test_benchmark_prompts_exist():
    """Each suite should have prompts defined."""
    for suitename in SUITES_ORDER:
        prompts = BENCHMARK_PROMPTS.get(suitename, [])
        assert len(prompts) > 0


def test_list_available_suites():
    """list_available_suites returns matching list."""
    result = list_available_suites()
    assert isinstance(result, list)
    assert len(result) == len(BenchmarkSuite)
    for item in result:
        assert item in [s.value for s in BenchmarkSuite]


def test_coding_prompts():
    """Coding suite should contain expected prompts."""
    prompts = BENCHMARK_PROMPTS.get(BenchmarkSuite.CODING.value, [])
    assert len(prompts) > 0
    assert "Implement" in prompts[0].lower() or "implement" in prompts[0].lower()


def test_math_prompts():
    """Math suite should contain math-related prompts."""
    prompts = BENCHMARK_PROMPTS.get(BenchmarkSuite.MATH.value, [])
    assert len(prompts) > 0
    first = prompts[0].lower()
    assert any(w in first for w in ["solve", "probability", "calculate"])


def test_description_keys_are_suites():
    """Descriptions keys are valid suite IDs."""
    for k in SUITES_DESCRIPTIONS:
        assert k in [s.value for s in BenchmarkSuite]
