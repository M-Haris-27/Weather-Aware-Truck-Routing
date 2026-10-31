from datetime import datetime, timezone

import pytest

from routing_app.domain.recommend import recommend
from routing_app.domain.scoring import average_risk, miles_by_level
from routing_app.domain.types import Checkpoint, RiskLevel, RouteAnalysis

DEPARTURE = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
L, M, H, S, N = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)


def cps(*pairs):
    """(risk, owned_miles) pairs -> assessed checkpoints."""
    return [
        Checkpoint(index=i, lat=0, lon=0, mile=0, eta=DEPARTURE, owned_miles=miles, risk=risk)
        for i, (risk, miles) in enumerate(pairs)
    ]


def route(route_id, *pairs, minutes=600):
    checkpoints = cps(*pairs)
    return RouteAnalysis(
        id=route_id,
        summary=route_id,
        coordinates=[],
        distance_mi=sum(m for _, m in pairs),
        duration_s=minutes * 60,
        departure=DEPARTURE,
        checkpoints=checkpoints,
        miles_by_level=miles_by_level(checkpoints),
        avg_risk=average_risk(checkpoints),
    )


def test_miles_by_level_and_distance_weighted_average():
    checkpoints = cps((L, 50), (H, 25), (S, 25))
    totals = miles_by_level(checkpoints)
    assert totals[L] == 50 and totals[H] == 25 and totals[S] == 25 and totals[N] == 0
    assert average_risk(checkpoints) == pytest.approx((0 * 50 + 2 * 25 + 3 * 25) / 100)


def test_average_risk_of_zero_length_route():
    assert average_risk(cps((H, 0))) == 2


def test_fewest_severe_miles_beats_everything_below_it():
    a = route("a", (S, 10), (L, 90), minutes=300)  # fastest but has Severe miles
    b = route("b", (H, 80), (L, 20), minutes=900)  # slow, lots of High, no Severe
    rec = recommend([a, b])
    assert rec.route_id == "b"
    assert rec.reason.startswith("Fewest Severe miles")


def test_high_miles_break_a_severe_tie():
    a = route("a", (H, 40), (L, 60))
    b = route("b", (H, 10), (L, 90))
    assert recommend([a, b]).route_id == "b"


def test_average_risk_breaks_a_high_tie():
    a = route("a", (M, 50), (L, 50))
    b = route("b", (M, 10), (L, 90))
    rec = recommend([a, b])
    assert rec.route_id == "b"
    assert rec.reason.startswith("Lowest average risk")


def test_travel_time_is_the_last_tiebreaker():
    a = route("a", (L, 100), minutes=700)
    b = route("b", (L, 100), minutes=650)
    rec = recommend([a, b])
    assert rec.route_id == "b"
    assert rec.reason.startswith("Shortest travel time")


def test_no_travel_miles_rank_above_severe_miles():
    blocked = route("blocked", (N, 5), (L, 95))
    severe = route("severe", (S, 60), (L, 40))
    assert recommend([blocked, severe]).route_id == "severe"


def test_all_routes_blocked_is_flagged():
    rec = recommend([route("a", (N, 30), (L, 70)), route("b", (N, 10), (L, 90))])
    assert rec.route_id == "b"
    assert rec.all_blocked
    assert "No Travel" in rec.reason


def test_single_route_and_empty_input():
    assert recommend([route("only", (L, 10))]).reason == "Only one route was available"
    with pytest.raises(ValueError):
        recommend([])
