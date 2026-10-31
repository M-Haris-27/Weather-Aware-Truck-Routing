"""Turns domain objects into the JSON shape the frontend consumes."""
from __future__ import annotations

from datetime import datetime, timezone

from ..domain.geometry import simplify
from ..domain.types import Checkpoint, Place, RiskLevel, RouteAnalysis
from ..pipeline import AnalysisResult

DISPLAY_SIMPLIFY_TOLERANCE_DEG = 0.0005  # ~50 m; keeps the polyline light for the browser


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _place(place: Place) -> dict:
    return {"label": place.label, "lat": round(place.lat, 5), "lon": round(place.lon, 5)}


def _checkpoint(cp: Checkpoint) -> dict:
    assert cp.weather is not None and cp.risk is not None
    return {
        "index": cp.index,
        "lat": round(cp.lat, 5),
        "lon": round(cp.lon, 5),
        "mile": round(cp.mile, 1),
        "eta": _iso(cp.eta),
        "owned_miles": round(cp.owned_miles, 1),
        "risk": cp.risk.name,
        "risk_level": int(cp.risk),
        "wind_mph": round(cp.weather.wind_mph, 1),
        "rain_in_hr": round(cp.weather.rain_in_hr, 3),
        "snow_in_hr": round(cp.weather.snow_in_hr, 3),
        "reason": cp.reason,
    }


def _route(route: RouteAnalysis, recommended_id: str) -> dict:
    display = simplify(route.coordinates, DISPLAY_SIMPLIFY_TOLERANCE_DEG)
    return {
        "id": route.id,
        "summary": route.summary,
        "is_recommended": route.id == recommended_id,
        "distance_mi": round(route.distance_mi, 1),
        "duration_min": round(route.duration_s / 60),
        "arrival": _iso(route.arrival),
        "miles_by_level": {level.name: round(route.miles_by_level[level], 1) for level in RiskLevel},
        "avg_risk": round(route.avg_risk, 2),
        "worst_risk": route.worst_level.name,
        "blocked": route.blocked,
        "geometry": [[round(lon, 5), round(lat, 5)] for lat, lon in display],  # GeoJSON order
        "checkpoints": [_checkpoint(cp) for cp in route.checkpoints],
    }


def present_analysis(result: AnalysisResult) -> dict:
    req = result.request
    rec = result.recommendation
    return {
        "recommended_route_id": rec.route_id,
        "recommendation_reason": rec.reason,
        "all_routes_blocked": rec.all_blocked,
        "interval_miles": result.interval_miles,
        "request": {
            "origin": _place(req.origin),
            "destination": _place(req.destination),
            "departure": _iso(req.departure),
            "load_lb": req.load_lb,
        },
        "routes": [_route(r, rec.route_id) for r in result.routes],
        "heatmap": {
            "start": _iso(result.heatmap.start),
            "hours": result.heatmap.hours,
            "spacing_miles": result.heatmap.spacing_miles,
            "points": [
                {"lat": round(p.lat, 4), "lon": round(p.lon, 4), "risk": list(p.risk)}
                for p in result.heatmap.points
            ],
        },
    }
