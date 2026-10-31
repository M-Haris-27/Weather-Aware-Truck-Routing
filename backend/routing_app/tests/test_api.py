from datetime import datetime, timedelta, timezone

import pytest
from rest_framework.test import APIClient

DALLAS = {"lat": 32.7767, "lon": -96.797, "label": "Dallas, TX"}


@pytest.fixture
def client(settings):
    settings.ROUTING_PROVIDER = "mock"
    settings.GEOCODING_PROVIDER = "mock"
    settings.WEATHER_PROVIDER = "mock"
    return APIClient()


def departure(hours=24):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def payload(**overrides):
    body = {"origin": DALLAS, "destination": "Denver", "departure": departure(), "load_lb": 42_000}
    body.update(overrides)
    return body


def test_health_reports_providers(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok" and data["providers"]["routing"] == "mock"


def test_analyze_returns_routes_checkpoints_and_heatmap(client):
    response = client.post("/api/analyze", payload(), format="json")
    assert response.status_code == 200, response.content
    data = response.json()

    assert len(data["routes"]) == 3
    assert data["recommended_route_id"] in {r["id"] for r in data["routes"]}
    assert sum(r["is_recommended"] for r in data["routes"]) == 1
    assert data["request"]["destination"]["label"] == "Denver, CO"  # geocoded from text

    route = data["routes"][0]
    assert set(route["miles_by_level"]) == {"LOW", "MODERATE", "HIGH", "SEVERE", "NO_TRAVEL"}
    assert sum(route["miles_by_level"].values()) == pytest.approx(route["distance_mi"], abs=1.0)
    assert route["geometry"][0][0] < 0  # GeoJSON order: [lon, lat]
    assert len(route["geometry"]) <= 401
    cp = route["checkpoints"][0]
    assert {"eta", "risk", "wind_mph", "rain_in_hr", "snow_in_hr", "reason", "mile"} <= set(cp)

    heat = data["heatmap"]
    assert heat["hours"] == 48 and heat["points"]
    assert all(len(p["risk"]) == 49 for p in heat["points"])


def test_analyze_accepts_timestamps_with_a_utc_offset(client):
    soon = datetime.now(timezone.utc) + timedelta(hours=5)
    local = soon.astimezone(timezone(timedelta(hours=5))).replace(microsecond=0).isoformat()
    response = client.post("/api/analyze", payload(departure=local), format="json")
    assert response.status_code == 200
    assert response.json()["request"]["departure"].endswith("Z")


@pytest.mark.parametrize(
    "overrides",
    [
        {"load_lb": -1},
        {"load_lb": "heavy"},
        {"origin": {"lat": 200, "lon": 0}},
        {"departure": "not-a-date"},
        {"interval_miles": 30},
        {"destination": "x"},
    ],
)
def test_invalid_input_is_a_400_with_details(client, overrides):
    response = client.post("/api/analyze", payload(**overrides), format="json")
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "Invalid request" and body["details"]


def test_unknown_place_is_a_400(client):
    response = client.post("/api/analyze", payload(destination="Atlantis"), format="json")
    assert response.status_code == 400
    assert "Atlantis" in response.json()["error"]


def test_departure_too_far_ahead_is_a_400(client):
    response = client.post("/api/analyze", payload(departure=departure(24 * 30)), format="json")
    assert response.status_code == 400
    assert "two weeks" in response.json()["error"]


def test_missing_api_key_is_a_503(client, settings):
    settings.ROUTING_PROVIDER = "mapbox"
    settings.MAPBOX_ACCESS_TOKEN = ""
    response = client.post("/api/analyze", payload(origin=DALLAS, destination=DALLAS), format="json")
    assert response.status_code == 503
    assert "MAPBOX_ACCESS_TOKEN" in response.json()["error"]


def test_geocode_endpoint(client):
    data = client.get("/api/geocode", {"q": "Dal"}).json()
    assert data["results"][0]["label"] == "Dallas, TX"
    assert client.get("/api/geocode", {"q": "D"}).json() == {"results": []}
    assert client.get("/api/geocode").json() == {"results": []}
