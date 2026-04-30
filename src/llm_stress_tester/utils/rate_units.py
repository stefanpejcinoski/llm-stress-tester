"""RPS/RPM conversion utilities."""

from llm_stress_tester.constants import MAX_RATE_SLIDER_VALUE, MIN_RATE_SLIDER_VALUE
from llm_stress_tester.enums import RateUnit


def slider_to_internal_rate(value: int, unit: RateUnit) -> float:
    """Convert slider value (1-2000) to internal RPS float.

    Slider always uses MIN_RATE_SLIDER_VALUE..MAX_RATE_SLIDER_VALUE.
    If unit is RPM, divide by 60 to get RPS.
    """
    if unit == RateUnit.RPM:
        return value / 60.0
    return float(value)


def internal_to_slider_rate(rate: float, unit: RateUnit) -> int:
    """Convert internal RPS float back to slider display value.

    If unit is RPM, multiply by 60 to get RPM.
    """
    if unit == RateUnit.RPM:
        return round(rate * 60)
    return round(rate)


def format_rate_value(rate: float, unit: RateUnit) -> str:
    """Format a rate value for display with unit."""
    if unit == RateUnit.RPM:
        return f"{rate * 60:.1f} RPM"
    return f"{rate:.2f} RPS"


def format_rate_conversion(slider_val: int, unit: RateUnit) -> str:
    """Show both slider value and converted rate for clarity."""
    internal = slider_to_internal_rate(slider_val, unit)
    if unit == RateUnit.RPM:
        return f"{slider_val} RPM = {internal:.2f} RPS"
    return f"{slider_val} RPS = {slider_val:.2f} RPS"


VALID_SLIDER_RANGE: tuple[int, int] = (MIN_RATE_SLIDER_VALUE, MAX_RATE_SLIDER_VALUE)
