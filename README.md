# Weather-Aware Truck Routing

A React + Django app that helps a truck driver choose the safest route. It generates up to three
routes, forecasts the weather at checkpoints **for the hour the truck will actually be there**, rates
the risk using the load rules, and recommends a route. The map shows every route, its checkpoints,
and a 0-48 hour weather heatmap.

```
React (Vite + TypeScript + MapLibre)  ->  Django REST API  ->  Mapbox / OpenRouteService (routes, geocoding)
                                               |                Open-Meteo (hourly weather)
                                  Risk engine + recommender (pure Python, unit tested)
```

## Run it locally

You need Python 3.10+ and Node 18+. Two terminals:

```bash
# 1. Backend  ->  http://localhost:8000
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # add MAPBOX_ACCESS_TOKEN (free signup at mapbox.com)
python manage.py runserver

# 2. Frontend ->  http://localhost:5173  (Vite proxies /api to the backend)
cd frontend
npm install
npm run dev
```

**No Mapbox token yet?** In `backend/.env` set `ROUTING_PROVIDER=mock` and `WEATHER_PROVIDER=mock`.
The whole app then works offline with deterministic fake routes and weather (Dallas, Denver, Seattle,
Atlanta and a dozen other US cities are available in the mock geocoder). The basemap tiles still load
from OpenFreeMap, so the browser needs internet access.

Tests: `cd backend && pytest` (105 tests, no network) and `cd frontend && npm test` (18 tests).
Type-check and production build: `npm run build`.

## What it does

| Requirement | Where |
|---|---|
| Origin, destination, departure time, load weight | `frontend/src/components/SearchForm.tsx` |
| 3 route options from a routing API | `backend/routing_app/services/routing/` (Mapbox, OpenRouteService, mock) |
| Weather every 10 / 25 / 50 miles at the truck's ETA | `domain/checkpoints.py`, `services/weather.py`, `pipeline.py` |
| Risk from the provided thresholds and load rules | `domain/risk.py` |
| Recommendation: Severe miles, High miles, avg risk, time | `domain/recommend.py` |
| Routes, checkpoints, risk, ETAs and summaries on a map | `MapView.tsx`, `RouteCards.tsx`, `CheckpointTable.tsx` |
| Heatmap with a 0-48 h slider | `MapView.tsx` (layer), `HeatmapControl.tsx` (slider) |

## Design decisions worth knowing

- **Risk logic is plain Python** with no Django imports (`backend/routing_app/domain/`), covered by boundary-value tests
  (e.g. 54.9 mph at 30,000 vs 30,001 lb, 44.9 mph at 40,000 vs 40,001 lb).
- **One weather request per analysis.** All checkpoints and heatmap points are fetched in batched Open-Meteo calls
  (chunks of 50, cached per ~1 km cell), covering the 48-hour heatmap window and every ETA.
- **The slider never hits the network.** The response carries 49 hourly risk values per heatmap point, so moving
  the slider only updates a small GeoJSON source (one update per animation frame).
- **Selecting a route is cheap.** Route and checkpoint geometry is loaded once; choosing a route swaps layer filters
  instead of re-uploading data. Checkpoints are map layers rather than DOM markers, so hundreds stay smooth.
- **Heatmap and checkpoints agree.** Both use the same `assess()` function and load weight.
- **Load weight can flip the answer.** There's a test for it: 40 mph wind is only High for a 30,000 lb load but
  Severe above 40,000 lb, so the recommended route changes.

## Assumptions

The full list is in [`backend/README.md`](backend/README.md#assumptions-please-keep-in-the-final-readme). The main ones:

- Lower bounds are inclusive; "No Travel" is wind >= 55 mph, rain > 1.00 in/hr, snow > 3.0 in/hr.
- The spec says "every 10 / 25 / 50 miles". Spacing is chosen by route length (<= 150 mi: 10, <= 500 mi: 25, otherwise 50)
  and can be overridden from the form.
- ETA assumes constant average speed; weather is read at the nearest forecast hour to the ETA.
- Routes are ranked by No Travel miles first, then Severe, High, average risk, travel time.
- Mapbox's driving profile is not truck-specific (no height, weight or hazmat restrictions). OpenRouteService offers a
  truck profile, but its public API only returns alternatives on short routes.

## Project layout

```
backend/    Django + DRF API (domain/, services/, pipeline.py, api/, tests/)
frontend/   Vite + React + TypeScript (api/, components/, lib/, hooks/)
```
