from datetime import datetime, timedelta, timezone

import pytest

from routing_app.domain.checkpoints import (
    build_checkpoints,
    choose_interval,
    owned_miles,
    sample_distances,
)
from routing_app.domain.geometry import cumulative_miles

DEPARTURE = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def straight_route(lon_from=-100.0, lon_to=-92.0, lat=35.0, step=0.01):
    n = int(round((lon_to - lon_from) / step))
    return [(lat, lon_from + i * step) for i in range(n + 1)]


@pytest.mark.parametrize(
    "miles, expected", [(10, 10), (150, 10), (150.1, 25), (500, 25), (500.1, 50), (2000, 50)]
)
def test_interval_by_length(miles, expected):
    assert choose_interval(miles) == expected


def test_interval_override_and_validation():
    assert choose_interval(2000, override=10) == 10
    with pytest.raises(ValueError):
        choose_interval(100, override=30)


def test_sample_distances():
    assert sample_distances(100, 25) == [0, 25, 50, 75, 100]
    assert sample_distances(100.3, 25) == [0, 25, 50, 75, 100.3]
    assert sample_distances(10, 25) == [0, 10]
    assert sample_distances(0, 10) == [0.0]


def test_owned_miles_sum_to_total_length():
    marks = sample_distances(113.7, 25)
    assert sum(owned_miles(marks)) == pytest.approx(113.7)
    assert owned_miles([0, 25, 50]) == [12.5, 25.0, 12.5]


def test_build_checkpoints_positions_and_etas():
    coords = straight_route()
    cum = cumulative_miles(coords)
    duration_s = 8 * 3600
    cps = build_checkpoints(coords, cum, duration_s, DEPARTURE, 25)

    assert cps[0].mile == 0 and cps[0].eta == DEPARTURE
    assert cps[-1].mile == pytest.approx(cum[-1])
    assert cps[-1].eta == DEPARTURE + timedelta(seconds=duration_s)
    assert [cp.mile for cp in cps[:3]] == [0, 25, 50]
    # ETA is proportional to distance
    assert cps[1].eta == DEPARTURE + timedelta(seconds=duration_s * 25 / cum[-1])
    assert sum(cp.owned_miles for cp in cps) == pytest.approx(cum[-1])
    # checkpoints lie on the route (same latitude, increasing longitude)
    assert all(cp.lat == pytest.approx(35.0) for cp in cps)
    assert [cp.lon for cp in cps] == sorted(cp.lon for cp in cps)


def test_zero_length_route_yields_one_checkpoint():
    coords = [(35.0, -100.0), (35.0, -100.0)]
    cps = build_checkpoints(coords, cumulative_miles(coords), 60, DEPARTURE, 10)
    assert len(cps) == 1
    assert cps[0].eta == DEPARTURE
