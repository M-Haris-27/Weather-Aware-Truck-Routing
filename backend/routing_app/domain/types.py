"""Plain data types shared across the domain layer. No Django, no HTTP."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum

Coord = tuple[float, float]  # (lat, lon)
GridKey = tuple[float, float]  # a coordinate rounded to the weather grid


class RiskLevel(IntEnum):
    """Ordered so that max() and comparisons mean "worse"."""

    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


def grid_key(lat: float, lon: float) -> GridKey:
    """Round to ~1 km so nearby checkpoints share one forecast lookup."""
    return (round(lat, 2), round(lon, 2))


@dataclass(frozen=True)
class Place:
    lat: float
    lon: float
    label: str = ""


@dataclass(frozen=True)
class Weather:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class HourlySeries:
    """Contiguous hourly forecast for one grid point. `start` is hour-aligned UTC."""

    start: datetime
    values: tuple[Weather, ...]

    def at(self, when: datetime) -> Weather:
        """Forecast for the hour nearest to `when` (half-hours round up)."""
        hours = (when - self.start).total_seconds() / 3600
        index = math.floor(hours + 0.5)
        index = max(0, min(len(self.values) - 1, index))
        return self.values[index]


@dataclass(frozen=True)
class RawRoute:
    """A route as returned by a routing provider, before any analysis."""

    id: str
    summary: str
    coordinates: list[Coord]
    duration_s: float


@dataclass(frozen=True)
class Checkpoint:
    index: int
    lat: float
    lon: float
    mile: float  # miles from the start of the route
    eta: datetime
    owned_miles: float  # stretch of road this checkpoint is responsible for
    weather: Weather | None = None
    risk: RiskLevel | None = None
    reason: str = ""


@dataclass
class RouteAnalysis:
    id: str
    summary: str
    coordinates: list[Coord]
    distance_mi: float
    duration_s: float
    departure: datetime
    checkpoints: list[Checkpoint]
    miles_by_level: dict[RiskLevel, float]
    avg_risk: float

    @property
    def arrival(self) -> datetime:
        return self.departure + timedelta(seconds=self.duration_s)

    @property
    def blocked(self) -> bool:
        return self.miles_by_level[RiskLevel.NO_TRAVEL] > 0

    @property
    def worst_level(self) -> RiskLevel:
        return max((cp.risk for cp in self.checkpoints if cp.risk is not None), default=RiskLevel.LOW)


@dataclass(frozen=True)
class HeatmapPoint:
    lat: float
    lon: float
    risk: tuple[int, ...]  # risk level (0-4) for each hour 0..N after departure


@dataclass(frozen=True)
class Heatmap:
    start: datetime
    hours: int
    spacing_miles: float
    points: list[HeatmapPoint]
