"""Geometry helpers: distances along a polyline, interpolation, simplification."""
from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence

from .types import Coord

EARTH_RADIUS_MI = 3958.7613


def haversine_miles(a: Coord, b: Coord) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(coords: Sequence[Coord]) -> list[float]:
    """Distance from the start to every vertex. cum[0] == 0, cum[-1] == total length."""
    cum = [0.0]
    for prev, cur in zip(coords, coords[1:]):
        cum.append(cum[-1] + haversine_miles(prev, cur))
    return cum


def point_at_distance(coords: Sequence[Coord], cum: Sequence[float], target_mi: float) -> Coord:
    """Coordinate `target_mi` miles along the polyline (clamped to its ends)."""
    if target_mi <= 0:
        return coords[0]
    if target_mi >= cum[-1]:
        return coords[-1]
    i = bisect_right(cum, target_mi) - 1  # cum[i] <= target < cum[i + 1]
    segment = cum[i + 1] - cum[i]
    if segment == 0:
        return coords[i]
    f = (target_mi - cum[i]) / segment
    (lat1, lon1), (lat2, lon2) = coords[i], coords[i + 1]
    return (lat1 + (lat2 - lat1) * f, lon1 + (lon2 - lon1) * f)


def _distance_to_segment(p: Coord, a: Coord, b: Coord, lon_scale: float) -> float:
    """Planar point-to-segment distance in degrees (longitude scaled by cos(lat))."""
    px, py = p[1] * lon_scale, p[0]
    ax, ay = a[1] * lon_scale, a[0]
    bx, by = b[1] * lon_scale, b[0]
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify(coords: Sequence[Coord], tolerance_deg: float) -> list[Coord]:
    """Ramer-Douglas-Peucker (iterative, so long routes can't overflow the stack).

    Used only for the geometry sent to the browser; sampling always uses the full line.
    """
    n = len(coords)
    if n <= 2 or tolerance_deg <= 0:
        return list(coords)
    lon_scale = math.cos(math.radians(sum(c[0] for c in coords) / n))
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        start, end = stack.pop()
        far_index, far_dist = -1, 0.0
        for i in range(start + 1, end):
            d = _distance_to_segment(coords[i], coords[start], coords[end], lon_scale)
            if d > far_dist:
                far_index, far_dist = i, d
        if far_index != -1 and far_dist > tolerance_deg:
            keep[far_index] = True
            stack.append((start, far_index))
            stack.append((far_index, end))
    return [c for c, k in zip(coords, keep) if k]
