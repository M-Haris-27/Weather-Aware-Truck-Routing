"""Weather risk classification. Pure functions, easy to test.

Boundary convention (documented in the README): every lower bound is inclusive.
The top "No Travel" bound follows the spec literally:
    wind  >= 55 mph        -> No Travel
    rain  >  1.00 in/hr    -> No Travel   (exactly 1.00 is still Severe)
    snow  >  3.0  in/hr    -> No Travel   (exactly 3.0  is still Severe)
"""
from __future__ import annotations

from dataclasses import dataclass

from .types import RiskLevel, Weather

# Load rules
HEAVY_LOAD_LB = 30_000  # wind 45-54 mph above this load -> No Travel
VERY_HEAVY_LOAD_LB = 40_000  # wind 35-44 mph above this load -> Severe


@dataclass(frozen=True)
class Assessment:
    level: RiskLevel
    reason: str


def wind_level(mph: float) -> RiskLevel:
    if mph >= 55:
        return RiskLevel.NO_TRAVEL
    if mph >= 45:
        return RiskLevel.SEVERE
    if mph >= 35:
        return RiskLevel.HIGH
    if mph >= 25:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def rain_level(in_per_hr: float) -> RiskLevel:
    if in_per_hr > 1.00:
        return RiskLevel.NO_TRAVEL
    if in_per_hr >= 0.50:
        return RiskLevel.SEVERE
    if in_per_hr >= 0.25:
        return RiskLevel.HIGH
    if in_per_hr >= 0.10:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def snow_level(in_per_hr: float) -> RiskLevel:
    if in_per_hr > 3.0:
        return RiskLevel.NO_TRAVEL
    if in_per_hr >= 2.0:
        return RiskLevel.SEVERE
    if in_per_hr >= 1.0:
        return RiskLevel.HIGH
    if in_per_hr >= 0.5:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def assess(weather: Weather, load_lb: float) -> Assessment:
    """Classify one checkpoint: worst of wind/rain/snow, then apply the load rules."""
    wind = wind_level(weather.wind_mph)
    rain = rain_level(weather.rain_in_hr)
    snow = snow_level(weather.snow_in_hr)
    base = max(wind, rain, snow)
    level = base
    load_rule = ""

    if weather.wind_mph >= 55:
        level = RiskLevel.NO_TRAVEL  # any load
    elif weather.wind_mph >= 45 and load_lb > HEAVY_LOAD_LB:
        level = RiskLevel.NO_TRAVEL
        load_rule = f"load over {HEAVY_LOAD_LB:,} lb"
    elif weather.wind_mph >= 35 and load_lb > VERY_HEAVY_LOAD_LB:
        level = max(base, RiskLevel.SEVERE)
        load_rule = f"load over {VERY_HEAVY_LOAD_LB:,} lb"

    return Assessment(level=level, reason=_explain(weather, wind, rain, snow, base, level, load_rule))


def _explain(
    weather: Weather,
    wind: RiskLevel,
    rain: RiskLevel,
    snow: RiskLevel,
    base: RiskLevel,
    level: RiskLevel,
    load_rule: str,
) -> str:
    if level == RiskLevel.LOW:
        return "Conditions within normal limits"

    if load_rule and level > base:
        return (
            f"Wind {weather.wind_mph:.0f} mph ({wind.label}) raised to {level.label}: {load_rule}"
        )

    drivers = []
    if wind == level:
        drivers.append(f"wind {weather.wind_mph:.0f} mph")
    if rain == level:
        drivers.append(f"rain {weather.rain_in_hr:.2f} in/hr")
    if snow == level:
        drivers.append(f"snow {weather.snow_in_hr:.2f} in/hr")
    text = ", ".join(drivers)
    return f"{text[0].upper()}{text[1:]} ({level.label})"
