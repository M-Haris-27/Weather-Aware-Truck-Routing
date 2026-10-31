"""Routing/geocoding adapters, tested against canned provider responses."""
import pytest

from routing_app.domain.types import Place
from routing_app.errors import ConfigError, NoRouteError, UpstreamError
from routing_app.services.geocoding import MapboxGeocoder, MockGeocoder, OrsGeocoder
from routing_app.services.routing import MapboxProvider, OrsProvider

A, B = Place(32.78, -96.8), Place(39.74, -104.99)


class Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code = payload, status

    def json(self):
        return self._p


class Session:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def _next(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.responses.pop(0)

    get = post = _next


def mapbox_route(duration, coords, summary="I-35 N"):
    return {"duration": duration, "geometry": {"coordinates": coords}, "legs": [{"summary": summary}]}


def test_mapbox_parses_routes_and_flips_coordinate_order():
    payload = {
        "code": "Ok",
        "routes": [
            mapbox_route(36000, [[-96.8, 32.78], [-100.0, 36.0], [-104.99, 39.74]]),
            mapbox_route(38000, [[-96.8, 32.78], [-104.99, 39.74]], summary=""),
        ],
    }
    session = Session(Resp(payload))
    routes = MapboxProvider("tok", session=session).get_routes(A, B)

    assert [r.id for r in routes] == ["r1", "r2"]
    assert routes[0].coordinates[0] == (32.78, -96.8)  # (lat, lon)
    assert routes[0].summary == "I-35 N" and routes[1].summary == "Route 2"
    assert routes[0].duration_s == 36000
    args, kwargs = session.calls[0]
    assert "-96.8,32.78;-104.99,39.74" in args[0]
    assert kwargs["params"]["alternatives"] == "true"


def test_mapbox_error_mapping():
    with pytest.raises(NoRouteError):
        MapboxProvider("tok", session=Session(Resp({"code": "NoRoute"}))).get_routes(A, B)
    with pytest.raises(UpstreamError, match="API key"):
        MapboxProvider("tok", session=Session(Resp({}, 401))).get_routes(A, B)
    with pytest.raises(UpstreamError):
        MapboxProvider("tok", session=Session(Resp({"code": "Error", "message": "boom"}, 500))).get_routes(A, B)
    with pytest.raises(ConfigError):
        MapboxProvider("")


def ors_feature(duration, coords):
    return {"geometry": {"coordinates": coords}, "properties": {"summary": {"duration": duration}}}


def test_ors_parses_alternatives():
    payload = {"features": [ors_feature(100, [[-96.8, 32.78], [-104.99, 39.74]]), ors_feature(120, [[-96.8, 32.78], [-104.99, 39.74]])]}
    session = Session(Resp(payload))
    routes = OrsProvider("key", session=session).get_routes(A, B)
    assert len(routes) == 2 and routes[0].coordinates[1] == (39.74, -104.99)
    assert session.calls[0][1]["json"]["alternative_routes"]["target_count"] == 3


def test_ors_retries_without_alternatives_when_route_is_too_long():
    too_long = Resp({"error": {"code": 2004, "message": "too long"}}, 400)
    ok = Resp({"features": [ors_feature(100, [[-96.8, 32.78], [-104.99, 39.74]])]})
    session = Session(too_long, ok)
    routes = OrsProvider("key", session=session).get_routes(A, B)
    assert len(routes) == 1
    assert "alternative_routes" not in session.calls[1][1]["json"]


def test_ors_no_route_and_config_errors():
    with pytest.raises(NoRouteError):
        OrsProvider("key", session=Session(Resp({"error": {"code": 2010, "message": "x"}}, 404))).get_routes(A, B)
    with pytest.raises(ConfigError):
        OrsProvider("")


def test_mapbox_geocoder_parses_features():
    payload = {
        "features": [
            {"geometry": {"coordinates": [-96.797, 32.7767]}, "properties": {"full_address": "Dallas, Texas, United States"}},
            {"geometry": {"coordinates": [-96.8, 32.8]}, "properties": {"name": "Dallas", "place_formatted": "Georgia"}},
        ]
    }
    places = MapboxGeocoder("tok", country="US", session=Session(Resp(payload))).search("dall")
    assert places[0] == Place(lat=32.7767, lon=-96.797, label="Dallas, Texas, United States")
    assert places[1].label == "Dallas, Georgia"


def test_ors_geocoder_parses_features():
    payload = {"features": [{"geometry": {"coordinates": [-104.99, 39.74]}, "properties": {"label": "Denver, CO, USA"}}]}
    places = OrsGeocoder("key", session=Session(Resp(payload))).search("denv")
    assert places == [Place(lat=39.74, lon=-104.99, label="Denver, CO, USA")]


def test_mock_geocoder_substring_match():
    assert [p.label for p in MockGeocoder().search("den")] == ["Denver, CO"]
    assert MockGeocoder().search("zzz") == []
