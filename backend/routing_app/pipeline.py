"""Orchestrates one analysis: routes -> checkpoints -> weather -> risk -> recommendation.

All I/O is injected (`routing`, `weather`), so the whole flow runs offline in tests.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from .domain.checkpoints import build_checkpoints, choose_interval, sample_points
from .domain.geometry import cumulative_miles
from .domain.recommend import Recommendation, recommend
from .domain.risk import assess
from .domain.scoring import average_risk, miles_by_level
from .domain.types import (
    Heatmap,
    HeatmapPoint,
    Place,
    RouteAnalysis,
    grid_key,
)
from .errors import InputError, NoRouteError, UpstreamError
from .services.routing.base import RoutingProvider
from .services.weather import WeatherProvider

UTC = timezone.utc

MAX_ROUTES = 3
HEATMAP_HOURS = 48  # slider covers hour 0 .. 48 after departure
HEATMAP_MAX_SPACING_MI = 25
HEATMAP_MAX_POINTS = 400  # protects the weather API on very long trips
PAST_TOLERANCE = timedelta(hours=24)
FORECAST_MAX_DAYS_AHEAD = 15  # Open-Meteo serves up to 16 days


@dataclass(frozen=True)
class AnalyzeInput:
    origin: Place
    destination: Place
    departure: datetime
    load_lb: float
    interval_miles: int | None = None


@dataclass(frozen=True)
class AnalysisResult:
    request: AnalyzeInput
    interval_miles: int
    routes: list[RouteAnalysis]
    recommendation: Recommendation
    heatmap: Heatmap


def analyze(
    request: AnalyzeInput,
    *,
    routing: RoutingProvider,
    weather: WeatherProvider,
    now: datetime | None = None,
) -> AnalysisResult:
    now = now or datetime.now(UTC)
    departure = request.departure.astimezone(UTC)
    if departure < now - PAST_TOLERANCE:
        raise InputError("Departure time is in the past; pick a current or future time")

    # 1. Routes (full-resolution geometry; distance comes from the geometry itself)
    raw_routes = routing.get_routes(request.origin, request.destination)[:MAX_ROUTES]
    if not raw_routes:
        raise NoRouteError("No drivable route found between those places")
    cums = {r.id: cumulative_miles(r.coordinates) for r in raw_routes}

    # 2. One checkpoint spacing for every route, so they are compared like for like
    interval = choose_interval(cums[raw_routes[0].id][-1], request.interval_miles)

    # 3. Checkpoints + ETAs
    skeletons = {
        r.id: build_checkpoints(r.coordinates, cums[r.id], r.duration_s, departure, interval)
        for r in raw_routes
    }

    # 4. Heatmap grid along the corridor (denser than checkpoints when they are sparse)
    total_miles = sum(cums[r.id][-1] for r in raw_routes)
    spacing = max(min(interval, HEATMAP_MAX_SPACING_MI), total_miles / HEATMAP_MAX_POINTS)
    heatmap_points = {}
    for r in raw_routes:
        for lat, lon in sample_points(r.coordinates, cums[r.id], spacing):
            heatmap_points.setdefault(grid_key(lat, lon), (lat, lon))

    # 5. One batched weather fetch covering the 48h heatmap window and every ETA
    latest_eta = max(cp.eta for cps in skeletons.values() for cp in cps)
    window_start = departure.replace(minute=0, second=0, microsecond=0)
    window_end = max(departure + timedelta(hours=HEATMAP_HOURS), latest_eta) + timedelta(hours=1)
    if window_end.date() > (now + timedelta(days=FORECAST_MAX_DAYS_AHEAD)).date():
        raise InputError(
            "Forecast data only extends about two weeks ahead; "
            "choose an earlier departure so the trip and the 48-hour heatmap fit"
        )
    points = [(cp.lat, cp.lon) for cps in skeletons.values() for cp in cps] + list(heatmap_points.values())
    grid = weather.fetch(points, window_start, window_end)

    def series_for(lat: float, lon: float):
        try:
            return grid[grid_key(lat, lon)]
        except KeyError as exc:
            raise UpstreamError("Weather service returned no data for part of the route") from exc

    # 6. Risk at each checkpoint, using the forecast for the hour the truck gets there
    routes = []
    for r in raw_routes:
        assessed = []
        for cp in skeletons[r.id]:
            forecast = series_for(cp.lat, cp.lon).at(cp.eta)
            result = assess(forecast, request.load_lb)
            assessed.append(replace(cp, weather=forecast, risk=result.level, reason=result.reason))
        routes.append(
            RouteAnalysis(
                id=r.id,
                summary=r.summary,
                coordinates=r.coordinates,
                distance_mi=cums[r.id][-1],
                duration_s=r.duration_s,
                departure=departure,
                checkpoints=assessed,
                miles_by_level=miles_by_level(assessed),
                avg_risk=average_risk(assessed),
            )
        )

    # 7. Heatmap: same risk rules, evaluated at each hour after departure
    heat = []
    for lat, lon in heatmap_points.values():
        series = series_for(lat, lon)
        risks = tuple(
            int(assess(series.at(departure + timedelta(hours=h)), request.load_lb).level)
            for h in range(HEATMAP_HOURS + 1)
        )
        heat.append(HeatmapPoint(lat=lat, lon=lon, risk=risks))

    return AnalysisResult(
        request=request,
        interval_miles=interval,
        routes=routes,
        recommendation=recommend(routes),
        heatmap=Heatmap(start=departure, hours=HEATMAP_HOURS, spacing_miles=round(spacing, 1), points=heat),
    )
