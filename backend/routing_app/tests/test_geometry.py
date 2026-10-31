import pytest

from routing_app.domain.geometry import (
    cumulative_miles,
    haversine_miles,
    point_at_distance,
    simplify,
)


def test_haversine_one_degree_of_latitude():
    assert haversine_miles((0, 0), (1, 0)) == pytest.approx(69.09, abs=0.1)


def test_cumulative_and_point_at_distance():
    coords = [(35.0, -100.0), (35.0, -99.0), (35.0, -98.0)]
    cum = cumulative_miles(coords)
    assert cum[0] == 0
    assert cum[-1] == pytest.approx(2 * cum[1])
    lat, lon = point_at_distance(coords, cum, cum[1] / 2)
    assert (lat, lon) == pytest.approx((35.0, -99.5))
    assert point_at_distance(coords, cum, -5) == coords[0]
    assert point_at_distance(coords, cum, 1e9) == coords[-1]


def test_point_at_distance_handles_duplicate_vertices():
    coords = [(35.0, -100.0), (35.0, -100.0), (35.0, -99.0)]
    cum = cumulative_miles(coords)
    lat, lon = point_at_distance(coords, cum, cum[-1] / 2)
    assert lon == pytest.approx(-99.5)


def test_simplify_collapses_straight_line_and_keeps_corners():
    line = [(35.0, -100 + i * 0.01) for i in range(200)]
    assert simplify(line, 0.0005) == [line[0], line[-1]]

    corner = [(35.0, -100.0), (35.0, -99.0), (36.0, -99.0)]
    assert simplify(corner, 0.0005) == corner
    assert simplify(corner, 0) == corner
