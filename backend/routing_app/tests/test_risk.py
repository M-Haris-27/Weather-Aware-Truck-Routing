import pytest

from routing_app.domain.risk import assess, rain_level, snow_level, wind_level
from routing_app.domain.types import RiskLevel as R
from routing_app.domain.types import Weather

L, M, H, S, N = R.LOW, R.MODERATE, R.HIGH, R.SEVERE, R.NO_TRAVEL


@pytest.mark.parametrize(
    "mph, expected",
    [(0, L), (24.9, L), (25, M), (34.9, M), (35, H), (44.9, H), (45, S), (54.9, S), (55, N), (90, N)],
)
def test_wind_levels(mph, expected):
    assert wind_level(mph) == expected


@pytest.mark.parametrize(
    "rate, expected",
    [(0, L), (0.099, L), (0.10, M), (0.249, M), (0.25, H), (0.499, H), (0.50, S), (1.00, S), (1.001, N)],
)
def test_rain_levels(rate, expected):
    assert rain_level(rate) == expected


@pytest.mark.parametrize(
    "rate, expected",
    [(0, L), (0.499, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, N)],
)
def test_snow_levels(rate, expected):
    assert snow_level(rate) == expected


def calm(**overrides):
    return Weather(**{"wind_mph": 0.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0, **overrides})


def test_calm_is_low():
    result = assess(calm(), 80_000)
    assert result.level == L
    assert "normal" in result.reason


def test_worst_condition_wins():
    result = assess(calm(wind_mph=20, rain_in_hr=0.6), 10_000)  # wind Low, rain Severe
    assert result.level == S
    assert "rain" in result.reason.lower()


@pytest.mark.parametrize("load", [0, 10_000, 80_000])
def test_wind_55_is_no_travel_for_any_load(load):
    assert assess(calm(wind_mph=55), load).level == N


def test_wind_45_to_54_with_heavy_load_is_no_travel():
    assert assess(calm(wind_mph=54.9), 30_000).level == S  # exactly 30,000 is not "over"
    assert assess(calm(wind_mph=54.9), 30_001).level == N
    assert assess(calm(wind_mph=45), 30_001).level == N


def test_wind_35_to_44_with_very_heavy_load_is_severe():
    assert assess(calm(wind_mph=44.9), 40_000).level == H  # exactly 40,000 is not "over"
    result = assess(calm(wind_mph=44.9), 40_001)
    assert result.level == S
    assert "40,000" in result.reason
    assert assess(calm(wind_mph=35), 40_001).level == S


def test_load_rule_never_lowers_a_worse_condition():
    # rain alone is Severe; the 35-44 mph load rule can't push it anywhere but Severe,
    # and a No Travel rain stays No Travel.
    assert assess(calm(wind_mph=40, rain_in_hr=0.6), 45_000).level == S
    assert assess(calm(wind_mph=40, rain_in_hr=1.5), 45_000).level == N


def test_load_rule_does_not_apply_below_35_mph():
    assert assess(calm(wind_mph=34.9), 100_000).level == M
