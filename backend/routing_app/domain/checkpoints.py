"""Checkpoint sampling along a route, with ETAs and "owned" miles."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from .geometry import point_at_distance
from .types import Checkpoint, Coord

ALLOWED_INTERVALS = (10, 25, 50)
# (route length up to, interval): short trips are sampled densely, long hauls sparsely.
INTERVAL_BY_LENGTH = ((150.0, 10), (500.0, 25))
DEFAULT_LONG_INTERVAL = 50
# Don't place a regular checkpoint closer than this to the destination.
MIN_GAP_TO_END_MI = 0.5


def choose_interval(total_miles: float, override: int | None = None) -> int:
    """Checkpoint spacing: an explicit 10/25/50 override, else picked by route length."""
    if override is not None:
        if override not in ALLOWED_INTERVALS:
            raise ValueError(f"interval must be one of {ALLOWED_INTERVALS}")
        return override
    for max_miles, interval in INTERVAL_BY_LENGTH:
        if total_miles <= max_miles:
            return interval
    return DEFAULT_LONG_INTERVAL


def sample_distances(total_miles: float, interval_miles: float) -> list[float]:
    """Mile marks: 0, I, 2I, ... and always the final mile (the destination)."""
    if total_miles <= 0:
        return [0.0]
    marks = [0.0]
    k = 1
    while k * interval_miles < total_miles - MIN_GAP_TO_END_MI:
        marks.append(k * interval_miles)
        k += 1
    marks.append(total_miles)
    return marks


def owned_miles(marks: Sequence[float]) -> list[float]:
    """Each checkpoint owns half the gap on each side of it.

    The values always sum to the route length, so "miles at each risk level" adds up.
    """
    n = len(marks)
    owned = []
    for i, mark in enumerate(marks):
        before = mark - marks[i - 1] if i > 0 else 0.0
        after = marks[i + 1] - mark if i < n - 1 else 0.0
        owned.append((before + after) / 2)
    return owned


def build_checkpoints(
    coords: Sequence[Coord],
    cum: Sequence[float],
    duration_s: float,
    departure: datetime,
    interval_miles: float,
) -> list[Checkpoint]:
    """Checkpoints with position, ETA and owned miles (weather/risk are filled in later).

    ETA assumes a constant average speed: departure + duration * (mile / total).
    """
    total = cum[-1]
    marks = sample_distances(total, interval_miles)
    owned = owned_miles(marks)
    checkpoints = []
    for i, (mark, share) in enumerate(zip(marks, owned)):
        lat, lon = point_at_distance(coords, cum, mark)
        fraction = mark / total if total > 0 else 0.0
        checkpoints.append(
            Checkpoint(
                index=i,
                lat=lat,
                lon=lon,
                mile=mark,
                eta=departure + timedelta(seconds=duration_s * fraction),
                owned_miles=share,
            )
        )
    return checkpoints


def sample_points(coords: Sequence[Coord], cum: Sequence[float], interval_miles: float) -> list[Coord]:
    """Just the positions (used for the heatmap grid)."""
    return [point_at_distance(coords, cum, mark) for mark in sample_distances(cum[-1], interval_miles)]
