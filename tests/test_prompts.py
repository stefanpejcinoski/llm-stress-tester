"""Tests for data/prompts module."""

from llm_stress_tester.data.prompts import BENCHMARK_PROMPTS, SUITES_DESCRIPTIONS, SUITES_ORDER
from llm_stress_tester.enums import BenchmarkSuite


def test_all_suites_have_prompts():
    """Every enum suite value should have entries in BENCHMARK_PROMPTS."""
    for suitename in [s.value for s in BenchmarkSuite]:
        assert suitename in BENCHMARK_PROMPTS
        prompts = BENCHMARK_PROMPTS[suitename]
        assert len(prompts) > 0


def test_all_suites_have_descriptions():
    """Every enum suite value should have entries in SUITES_DESCRIPTIONS."""
    for suitename in [s.value for s in BenchmarkSuite]:
        assert suitename in SUITES_DESCRIPTIONS


def test_description_is_tuple_of_two():
    """Each description must be (label, detail)."""
    for suitename, desc in SUITES_DESCRIPTIONS.items():
        assert isinstance(desc, tuple), f"{suitename} desc not tuple"
        assert len(desc) == 2, f"{suitename} desc wrong length"
        assert isinstance(desc[0], str), f"{suitename} label not str"
        assert isinstance(desc[1], str), f"{suitename} detail not str"


def test_prompts_are_strings():
    """All prompts must be strings."""
    for suitename, prompts in BENCHMARK_PROMPTS.items():
        for p in prompts:
            assert isinstance(p, str)
            assert len(p) > 0


def test_suite_labels_different():
    """Suite labels must be unique."""
    labels = [desc[0] for desc in SUITES_DESCRIPTIONS.values()]
    assert len(labels) == len(set(labels))
    

def test_suite_details_different():
    """Suite details must be unique."""
    details = [desc[1] for desc in SUITES_DESCRIPTIONS.values()]
    assert len(details) == len(set(details))
