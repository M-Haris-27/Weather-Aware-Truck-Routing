"""End-to-end pipeline tests with scripted routing and weather (no network)."""
from datetime import datetime, timedelta, timezone

import pytest

from routing_app.domain.types import Place, RawRoute, Weather
from routing_app.errors import InputError, NoRouteError
from routing_app.pipeline import HEATMAP_HOURS, AnalyzeInput, analyze
from routing_app.services.routing import MockRoutingProvider
from routing_app.services.weather import SyntheticWeatherProvider

UTC = timezone.utc
DEPARTURE = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
NOW = DEPARTURE - timedelta(hours=1)
CALM = Weather(10.0, 0.0, 0.0)


class StubRouting:
    name = "stub"

    def __init__(self, routes):
        self.routes = routes

    def get_routes(self, origin, destination):
        return self.routes


def line(route_id, lat, hours, lon_from=-100.0, lon_to=-92.0, step=0.05):
    n = int(round((lon_to - lon_from) / step))
    coords = [(lat, lon_from + i * step) for i in range(n + 1)]
    return RawRoute(route_id, f"Route {route_id}", coords, hours * 3600)


def request(load_lb=30_000, interval=None, departure=DEPARTURE):
    return AnalyzeInput(Place(35, -100, "A"), Place(35, -92, "B"), departure, load_lb, interval)


def run(routes, fn, **kwargs):
    return analyze(
        request(**kwargs),
        routing=StubRouting(routes),
        weather=SyntheticWeatherProvider(fn),
        now=NOW,
    )


def test_weather_is_read_at_each_checkpoints_eta_not_at_departure():
    bad_hour = DEPARTURE + timedelta(hours=3)

    def fn(lat, lon, when):
        return Weather(60.0, 0.0, 0.0) if when == bad_hour else CALM

    result = run([line("r1", 35.0, 7.5)], fn)
    route = result.routes[0]

    stormy = [cp for cp in route.checkpoints if cp.risk == 4]
    assert stormy, "some checkpoints should be reached during the storm hour"
    for cp in route.checkpoints:
        hours_in = (cp.eta - DEPARTURE).total_seconds() / 3600
        if 2.6 <= hours_in <= 3.4:
            assert cp.risk == 4, f"mile {cp.mile} (ETA +{hours_in:.2f}h) should be No Travel"
        elif hours_in < 2.4 or hours_in > 3.6:
            assert cp.risk == 0
    assert route.blocked
    assert 0 < route.miles_by_level[4] < route.distance_mi


def test_departure_time_changes_the_outcome():
    storm_start = DEPARTURE + timedelta(hours=2)
    storm_end = DEPARTURE + timedelta(hours=4)

    def fn(lat, lon, when):
        return Weather(60.0, 0.0, 0.0) if storm_start <= when <= storm_end else CALM

    leave_now = run([line("r1", 35.0, 7.5)], fn)
    leave_late = run([line("r1", 35.0, 7.5)], fn, departure=DEPARTURE + timedelta(hours=6))
    assert leave_now.routes[0].blocked
    assert not leave_late.routes[0].blocked


def _load_scenario_weather(lat, lon, when):
    if abs(lat - 35.0) < 0.2:  # route A: 40 mph gusts over ~110 miles
        return Weather(40.0, 0, 0) if -98 <= lon <= -96 else CALM
    if abs(lat - 36.0) < 0.2:  # route B: heavy rain over ~55 miles (Severe at any load)
        return Weather(10.0, 0.6, 0) if -98 <= lon <= -97 else CALM
    return Weather(10.0, 0.8, 0)  # route C: heavy rain the whole way


def _scenario_routes():
    return [line("A", 35.0, 7.0), line("B", 36.0, 7.5), line("C", 37.0, 8.0)]


def test_load_weight_flips_the_recommendation():
    # 40 mph is only High for a 30k lb load, but Severe above 40k lb.
    light = run(_scenario_routes(), _load_scenario_weather, load_lb=30_000)
    heavy = run(_scenario_routes(), _load_scenario_weather, load_lb=45_000)

    assert light.recommendation.route_id == "A"  # no Severe miles at all
    assert heavy.recommendation.route_id == "B"  # A is now Severe for ~110 mi, B only ~55
    assert light.routes[0].miles_by_level[3] == 0
    assert heavy.routes[0].miles_by_level[3] > heavy.routes[1].miles_by_level[3] > 0
    assert "Severe" in heavy.recommendation.reason


def test_owned_miles_add_up_to_route_distance():
    result = run(_scenario_routes(), _load_scenario_weather)
    for route in result.routes:
        assert sum(route.miles_by_level.values()) == pytest.approx(route.distance_mi)
        assert sum(cp.owned_miles for cp in route.checkpoints) == pytest.approx(route.distance_mi)


def test_same_interval_for_all_routes_and_override():
    auto = run(_scenario_routes(), lambda *a: CALM)
    assert auto.interval_miles == 25
    forced = run(_scenario_routes(), lambda *a: CALM, interval=50)
    assert forced.interval_miles == 50
    assert all(r.checkpoints[1].mile == 50 for r in forced.routes)


def test_heatmap_has_hourly_risk_for_every_point():
    result = run(_scenario_routes(), _load_scenario_weather)
    heat = result.heatmap
    assert heat.start == DEPARTURE and heat.hours == HEATMAP_HOURS
    assert heat.points
    assert all(len(p.risk) == HEATMAP_HOURS + 1 for p in heat.points)
    assert any(max(p.risk) > 0 for p in heat.points)


def test_heatmap_changes_over_time():
    def fn(lat, lon, when):  # storm only 10-12 hours after departure
        hours = (when - DEPARTURE).total_seconds() / 3600
        return Weather(60.0, 0, 0) if 10 <= hours <= 12 else CALM

    result = run([line("r1", 35.0, 7.5)], fn)
    for point in result.heatmap.points:
        assert point.risk[0] == 0
        assert point.risk[11] == 4
        assert point.risk[20] == 0


def test_weather_for_long_trips_extends_past_48_hours():
    seen = {}

    class Spy(SyntheticWeatherProvider):
        def fetch(self, points, start, end):
            seen["start"], seen["end"] = start, end
            return super().fetch(points, start, end)

    analyze(
        request(),
        routing=StubRouting([line("r1", 35.0, 72)]),  # a 3-day crawl
        weather=Spy(lambda *a: CALM),
        now=NOW,
    )
    assert seen["start"] == DEPARTURE
    assert seen["end"] >= DEPARTURE + timedelta(hours=72)


def test_mock_provider_gives_three_distinct_routes():
    result = analyze(
        AnalyzeInput(Place(32.78, -96.8, "Dallas"), Place(39.74, -104.99, "Denver"), DEPARTURE, 42_000),
        routing=MockRoutingProvider(),
        weather=SyntheticWeatherProvider(),
        now=NOW,
    )
    assert [r.id for r in result.routes] == ["r1", "r2", "r3"]
    assert len({round(r.distance_mi) for r in result.routes}) == 3
    assert result.recommendation.route_id in {"r1", "r2", "r3"}


def test_rejects_departure_in_the_past():
    with pytest.raises(InputError, match="past"):
        run([line("r1", 35.0, 7)], lambda *a: CALM, departure=NOW - timedelta(days=3))


def test_rejects_departure_beyond_forecast_window():
    with pytest.raises(InputError, match="two weeks"):
        run([line("r1", 35.0, 7)], lambda *a: CALM, departure=NOW + timedelta(days=15))


def test_no_routes_is_an_error():
    with pytest.raises(NoRouteError):
        run([], lambda *a: CALM)
