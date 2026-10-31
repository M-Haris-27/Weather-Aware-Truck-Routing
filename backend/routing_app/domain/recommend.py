"""Route recommendation.

Ranking (lower is better, compared in this order):
    1. No Travel miles   (a route you can't legally drive shouldn't win on a technicality)
    2. Severe miles
    3. High miles
    4. Average risk
    5. Travel time
Values are rounded before comparing so float noise can't decide a tie.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .types import RiskLevel, RouteAnalysis


def _miles(v: float) -> str:
    return f"{v:.1f} mi"


def _minutes(v: float) -> str:
    hours, minutes = divmod(int(round(v)), 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


@dataclass(frozen=True)
class _Criterion:
    phrase: str
    value: Callable[[RouteAnalysis], float]
    precision: int
    fmt: Callable[[float], str]


_CRITERIA = (
    _Criterion("Fewest No Travel miles", lambda r: r.miles_by_level[RiskLevel.NO_TRAVEL], 1, _miles),
    _Criterion("Fewest Severe miles", lambda r: r.miles_by_level[RiskLevel.SEVERE], 1, _miles),
    _Criterion("Fewest High miles", lambda r: r.miles_by_level[RiskLevel.HIGH], 1, _miles),
    _Criterion("Lowest average risk", lambda r: r.avg_risk, 2, lambda v: f"{v:.2f}"),
    _Criterion("Shortest travel time", lambda r: r.duration_s / 60, 0, _minutes),
)


@dataclass(frozen=True)
class Recommendation:
    route_id: str
    reason: str
    all_blocked: bool


def sort_key(route: RouteAnalysis) -> tuple[float, ...]:
    return tuple(round(c.value(route), c.precision) for c in _CRITERIA)


def recommend(routes: Sequence[RouteAnalysis]) -> Recommendation:
    if not routes:
        raise ValueError("no routes to recommend from")
    ranked = sorted(routes, key=sort_key)
    best = ranked[0]
    all_blocked = all(r.blocked for r in routes)

    if len(ranked) == 1:
        reason = "Only one route was available"
    else:
        reason = _explain(best, ranked[1])
    if all_blocked:
        reason = f"Every route hits No Travel conditions; least-bad option. {reason}"
    return Recommendation(route_id=best.id, reason=reason, all_blocked=all_blocked)


def _explain(best: RouteAnalysis, runner_up: RouteAnalysis) -> str:
    """Name the first criterion that separates the winner from the runner-up."""
    best_key, other_key = sort_key(best), sort_key(runner_up)
    for criterion, mine, theirs in zip(_CRITERIA, best_key, other_key):
        if mine != theirs:
            return f"{criterion.phrase}: {criterion.fmt(mine)} vs {criterion.fmt(theirs)}"
    return "Routes are equivalent on risk and travel time"
