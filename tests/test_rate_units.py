"""Tests for RPS/RPM conversion utilities."""

from llm_stress_tester.constants import MAX_RATE_SLIDER_VALUE, MIN_RATE_SLIDER_VALUE
from llm_stress_tester.enums import RateUnit
from llm_stress_tester.utils.rate_units import (
    format_rate_conversion,
    format_rate_value,
    internal_to_slider_rate,
    slider_to_internal_rate,
    VALID_SLIDER_RANGE,
)


def test_slider_to_internal_rate_rps():
    assert slider_to_internal_rate(10, RateUnit.RPS) == 10.0


def test_slider_to_internal_rate_rpm():
    assert slider_to_internal_rate(60, RateUnit.RPM) == 1.0


def test_internal_to_slider_rate_rps():
    assert internal_to_slider_rate(10.0, RateUnit.RPS) == 10


def test_internal_to_slider_rate_rpm():
    assert internal_to_slider_rate(1.0, RateUnit.RPM) == 60


def test_format_rate_value_rps():
    result = format_rate_value(1.5, RateUnit.RPS)
    assert result == "1.50 RPS"


def test_format_rate_value_rpm():
    result = format_rate_value(1.0, RateUnit.RPM)
    assert result == "60.0 RPM"


def test_format_rate_conversion_rps():
    result = format_rate_conversion(10, RateUnit.RPS)
    assert result == "10 RPS = 10.00 RPS"


def test_format_rate_conversion_rpm():
    result = format_rate_conversion(30, RateUnit.RPM)
    assert result == "30 RPM = 0.50 RPS"


def test_valid_slider_range_constants():
    assert VALID_SLIDER_RANGE == (MIN_RATE_SLIDER_VALUE, MAX_RATE_SLIDER_VALUE)
    assert VALID_SLIDER_RANGE == (1, 2000)
