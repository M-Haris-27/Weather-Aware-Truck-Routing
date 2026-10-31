"""Per-route statistics computed from assessed checkpoints."""
from __future__ import annotations

from collections.abc import Sequence

from .types import Checkpoint, RiskLevel


def miles_by_level(checkpoints: Sequence[Checkpoint]) -> dict[RiskLevel, float]:
    totals = {level: 0.0 for level in RiskLevel}
    for cp in checkpoints:
        assert cp.risk is not None, "checkpoint has not been assessed"
        totals[cp.risk] += cp.owned_miles
    return totals


def average_risk(checkpoints: Sequence[Checkpoint]) -> float:
    """Distance-weighted mean of the numeric risk level (Low=0 ... No Travel=4)."""
    total = sum(cp.owned_miles for cp in checkpoints)
    if total <= 0:  # degenerate zero-length route
        return sum(int(cp.risk) for cp in checkpoints) / len(checkpoints)
    return sum(int(cp.risk) * cp.owned_miles for cp in checkpoints) / total
