from datetime import datetime, timedelta, timezone

import pytest
import requests

from routing_app.domain.types import HourlySeries, Weather, grid_key
from routing_app.errors import UpstreamError
from routing_app.services import weather as weather_module
from routing_app.services.weather import OpenMeteoProvider, SyntheticWeatherProvider

UTC = timezone.utc
START = datetime(2026, 11, 5, 12, tzinfo=UTC)
END = datetime(2026, 11, 6, 12, tzinfo=UTC)


def hourly_block(wind=10.0, rain=0.0, showers=0.0, snow=0.0):
    times = [f"2026-11-05T{h:02d}:00" for h in range(24)] + [f"2026-11-06T{h:02d}:00" for h in range(24)]
    n = len(times)
    return {
        "time": times,
        "wind_speed_10m": [wind] * n,
        "rain": [rain] * n,
        "showers": [showers] * n,
        "snowfall": [snow] * n,
    }


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def json(self):
        return self._payload


class FakeSession:
    """Mimics requests.Session.get for Open-Meteo: one result per requested coordinate."""

    def __init__(self, status=200, **hourly):
        self.calls, self.status, self.hourly = [], status, hourly

    def get(self, url, params, timeout):
        self.calls.append(params)
        if self.status != 200:
            return FakeResponse({"error": True, "reason": "Date out of range"}, self.status)
        count = len(params["latitude"].split(","))
        items = [{"hourly": hourly_block(**self.hourly)} for _ in range(count)]
        return FakeResponse(items[0] if count == 1 else items)


class DictCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, timeout=None):
        self.data[key] = value


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(weather_module.time, "sleep", lambda s: None)


def test_parses_single_location_and_merges_rain_with_showers():
    session = FakeSession(wind=38.0, rain=0.05, showers=0.05, snow=0.4)
    provider = OpenMeteoProvider(session=session, cache=DictCache())
    result = provider.fetch([(35.0, -100.0)], START, END)

    series = result[grid_key(35.0, -100.0)]
    assert len(series.values) == 48
    assert series.start == datetime(2026, 11, 5, 0, tzinfo=UTC)
    assert series.values[0] == Weather(38.0, 0.1, 0.4)

    params = session.calls[0]
    assert params["wind_speed_unit"] == "mph" and params["precipitation_unit"] == "inch"
    assert params["start_date"] == "2026-11-05" and params["end_date"] == "2026-11-06"


def test_null_values_become_zero():
    provider = OpenMeteoProvider(session=FakeSession(wind=None, rain=None, showers=None, snow=None), cache=DictCache())
    series = provider.fetch([(35.0, -100.0)], START, END)[grid_key(35.0, -100.0)]
    assert series.values[5] == Weather(0.0, 0.0, 0.0)


def test_series_lookup_rounds_to_nearest_hour():
    # a series where each hour is distinguishable (wind speed == hour index)
    start = datetime(2026, 11, 5, 0, tzinfo=UTC)
    distinct = HourlySeries(start=start, values=tuple(Weather(float(i), 0, 0) for i in range(48)))
    base = datetime(2026, 11, 5, 12, tzinfo=UTC)
    assert distinct.at(base).wind_mph == 12
    assert distinct.at(base + timedelta(minutes=29)).wind_mph == 12
    assert distinct.at(base + timedelta(minutes=30)).wind_mph == 13  # half-hours round up
    assert distinct.at(base - timedelta(days=5)).wind_mph == 0  # clamped
    assert distinct.at(base + timedelta(days=5)).wind_mph == 47


def test_many_points_are_batched_into_chunks():
    session = FakeSession()
    provider = OpenMeteoProvider(session=session, cache=DictCache())
    points = [(30.0 + i * 0.05, -100.0) for i in range(120)]
    result = provider.fetch(points, START, END)

    assert len(result) == 120
    sizes = sorted(len(call["latitude"].split(",")) for call in session.calls)
    assert sizes == [20, 50, 50]


def test_duplicate_and_nearby_points_share_one_lookup():
    session = FakeSession()
    provider = OpenMeteoProvider(session=session, cache=DictCache())
    provider.fetch([(35.001, -100.001), (35.0, -100.0), (35.004, -100.004)], START, END)
    assert len(session.calls) == 1
    assert session.calls[0]["latitude"] == "35.00"


def test_cache_prevents_repeat_requests():
    session, cache = FakeSession(), DictCache()
    provider = OpenMeteoProvider(session=session, cache=cache)
    provider.fetch([(35.0, -100.0), (36.0, -99.0)], START, END)
    provider.fetch([(35.0, -100.0), (36.0, -99.0)], START, END)
    assert len(session.calls) == 1


def test_http_error_becomes_upstream_error_with_reason():
    provider = OpenMeteoProvider(session=FakeSession(status=400), cache=DictCache())
    with pytest.raises(UpstreamError, match="Date out of range"):
        provider.fetch([(35.0, -100.0)], START, END)


def test_retries_then_gives_up_on_server_errors():
    session = FakeSession(status=503)
    provider = OpenMeteoProvider(session=session, cache=DictCache())
    with pytest.raises(UpstreamError, match="unavailable"):
        provider.fetch([(35.0, -100.0)], START, END)
    assert len(session.calls) == OpenMeteoProvider.RETRIES + 1


def test_network_failure_becomes_upstream_error():
    class Boom:
        def get(self, *args, **kwargs):
            raise requests.ConnectionError("down")

    provider = OpenMeteoProvider(session=Boom(), cache=DictCache())
    with pytest.raises(UpstreamError):
        provider.fetch([(35.0, -100.0)], START, END)


def test_malformed_payload_becomes_upstream_error():
    class Bad:
        def get(self, *args, **kwargs):
            return FakeResponse({"hourly": {"time": ["2026-11-05T00:00"]}})

    provider = OpenMeteoProvider(session=Bad(), cache=DictCache())
    with pytest.raises(UpstreamError, match="malformed"):
        provider.fetch([(35.0, -100.0)], START, END)


def test_synthetic_provider_covers_requested_dates():
    result = SyntheticWeatherProvider().fetch([(35.0, -100.0)], START, END)
    series = result[grid_key(35.0, -100.0)]
    assert series.start == datetime(2026, 11, 5, 0, tzinfo=UTC)
    assert len(series.values) == 48
