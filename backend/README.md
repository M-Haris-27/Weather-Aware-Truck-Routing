# Weather-Aware Truck Routing: Backend

Django + DRF API that generates up to 3 truck routes, samples weather at checkpoints using the
truck's **estimated arrival time** at each one, classifies risk using the load rules, and
recommends the safest route. It also returns a 0-48 h corridor heatmap.

## Quick start

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # then add MAPBOX_ACCESS_TOKEN (see below)
python manage.py runserver    # http://localhost:8000
pytest                        # 100+ tests, no network needed
```

**No key yet?** Set `ROUTING_PROVIDER=mock` and `WEATHER_PROVIDER=mock` in `.env`. The API then runs
fully offline with deterministic fake routes and weather, which is handy for building the frontend.

## Providers

| Concern   | Setting              | Options                  | Notes |
|-----------|----------------------|--------------------------|-------|
| Routing   | `ROUTING_PROVIDER`   | `mapbox`, `ors`, `mock`  | Mapbox returns the primary route + up to 2 alternatives. ORS has a truck profile (`driving-hgv`) but its public API only allows alternatives on short routes, so long trips fall back to one route. |
| Geocoding | `GEOCODING_PROVIDER` | `mapbox`, `ors`, `mock`  | Defaults to the routing provider. |
| Weather   | `WEATHER_PROVIDER`   | `open_meteo`, `mock`     | Open-Meteo needs no key. |

Keys: `MAPBOX_ACCESS_TOKEN`, `ORS_API_KEY`. A missing key returns HTTP 503 with a clear message.

## API

`GET /api/health` returns status and the active providers.

`GET /api/geocode?q=dall` returns `{"results": [{"label", "lat", "lon"}]}` (empty for queries under 2 characters).

`POST /api/analyze`

```json
{
  "origin": {"lat": 32.78, "lon": -96.8, "label": "Dallas, TX"},
  "destination": "Denver, CO",
  "departure": "2026-11-05T14:00:00Z",
  "load_lb": 42000,
  "interval_miles": null
}
```

`origin` / `destination` can be a `{lat, lon, label}` object or free text (geocoded server-side).
`interval_miles` is optional (`10`, `25` or `50`).

The response contains `recommended_route_id`, `recommendation_reason`, `routes[]` (summary, distance,
duration, `miles_by_level`, `avg_risk`, `blocked`, simplified GeoJSON-order `geometry`, and `checkpoints[]` with
ETA, wind/rain/snow, risk and the reason), and `heatmap` (`points[]` each with 49 hourly risk values, hours 0-48).

Errors are `{"error": "..."}`: 400 bad input / no route, 502 upstream API failure, 503 missing config.
Validation errors add a `details` object keyed by field.

## How it works

```
routing_app/
  domain/      pure Python (no Django, no HTTP): risk, geometry, checkpoints, scoring, recommend
  services/    all external I/O: routing/, weather, geocoding, factory (builds providers from settings)
  pipeline.py  orchestrates one analysis (providers are injected, so tests run offline)
  api/         serializers, views, presenters (domain objects -> JSON)
  tests/
```

1. Get up to 3 routes. 2. Pick one checkpoint spacing for all routes. 3. Place checkpoints along each
route and compute ETAs. 4. Fetch weather for all checkpoints + heatmap points in **one batched call**
(chunks of 50, cached per ~1 km grid cell and date). 5. For each checkpoint, read the forecast for
the hour of its ETA and classify risk. 6. Score each route. 7. Rank routes.

## Assumptions (please keep in the final README)

- **Boundaries:** lower bounds are inclusive (e.g. 25 mph is Moderate). The No Travel bounds follow the spec
  literally: wind >= 55 mph, but rain > 1.00 in/hr and snow > 3.0 in/hr (exactly 1.00 / 3.0 is Severe).
- **Risk per checkpoint** = worst of wind, rain, snow, then the load rules (wind >= 55 -> No Travel;
  45-54 mph with load > 30,000 lb -> No Travel; 35-44 mph with load > 40,000 lb -> at least Severe).
  Load thresholds are strict ("over").
- **Wind** is the 10 m sustained wind speed (not gusts). **Rain** = Open-Meteo `rain + showers`; **snow** = `snowfall`
  (an hourly total in inches, i.e. in/hr).
- **Checkpoint spacing** (the spec says "10 / 25 / 50 miles"): chosen by route length (<=150 mi -> 10,
  <=500 mi -> 25, otherwise 50), taken from the first route and used for all routes so they are compared like for
  like. Override with `interval_miles`.
- **ETA** assumes constant average speed (route duration spread evenly over the route's length). Weather is read
  at the **nearest forecast hour** to the ETA (half-hours round up).
- **Distance** is measured along the route geometry (haversine sum). Each checkpoint "owns" half the gap to
  its neighbours, so risk-level miles add up to the route length.
- **Ranking:** No Travel miles, then Severe miles, High miles, average risk (distance-weighted), travel time.
  No Travel comes first because a route you can't drive shouldn't win on a technicality. Values are rounded
  (0.1 mi, 0.01 risk, 1 min) before comparing.
- **Heatmap** points are spaced at min(interval, 25) miles (capped at 400 points) and use the same
  risk rules and load as the checkpoints. All 49 hours come back in the single response, so the slider needs no further requests.
- **Departure** may be up to 24 h in the past and must leave room for the trip plus 48 h of heatmap within
  Open-Meteo's ~16-day forecast window.
- Mapbox's `driving` profile is not truck-specific (no height / weight / hazmat restrictions).
