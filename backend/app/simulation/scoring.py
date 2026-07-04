from backend.app.domain.constraints import ConstraintResult
from backend.app.domain.enums import Priority
from backend.app.domain.metrics import SimulationMetrics
from backend.app.domain.target import ProductTarget

from .math_utils import clamp


DEFAULT_WEIGHTS = {
    "capacity": 0.20,
    "bandwidth": 0.35,
    "latency": 0.15,
    "power": 0.15,
    "thermal": 0.15,
}


def requirement_score(value: float, target: float) -> float:
    return clamp(value / max(target, 1e-9), 0.0, 1.0)


def headroom_score(value: float, target: float) -> float:
    return clamp((value / max(target, 1e-9) - 1.0) / 0.2, 0.0, 1.0)


def combined_score(value: float, target: float) -> float:
    return 0.85 * requirement_score(value, target) + 0.15 * headroom_score(value, target)


def budget_score(limit: float, actual: float) -> float:
    ratio = limit / max(actual, 1e-9)
    requirement = clamp(ratio, 0.0, 1.0)
    headroom = clamp((ratio - 1.0) / 0.2, 0.0, 1.0)
    return 0.85 * requirement + 0.15 * headroom


class ScoringEngine:
    def score(
        self,
        target: ProductTarget,
        metrics: SimulationMetrics,
        constraints: ConstraintResult,
    ) -> tuple[float, dict[str, float]]:
        weights = self._weights(target)

        bandwidth_value = (
            metrics.achieved_bandwidth_GBps
            if target.bandwidth_constraint_metric == "achieved"
            else metrics.effective_bandwidth_GBps
        )
        capacity = combined_score(metrics.usable_capacity_gb, target.capacity_gb)
        bandwidth = combined_score(bandwidth_value, target.required_effective_bandwidth_GBps)

        if target.max_average_latency_ns is not None:
            latency = budget_score(target.max_average_latency_ns, metrics.average_latency_ns)
        else:
            latency = budget_score(140.0, metrics.average_latency_ns)

        power = 1.0 if target.power_budget_w is None else budget_score(target.power_budget_w, metrics.total_power_w)
        thermal = (
            1.0
            if target.max_temperature_c is None
            else budget_score(target.max_temperature_c, metrics.estimated_temperature_c)
        )

        raw_score = (
            capacity * weights["capacity"]
            + bandwidth * weights["bandwidth"]
            + latency * weights["latency"]
            + power * weights["power"]
            + thermal * weights["thermal"]
        )
        penalty = min(0.60, len(constraints.violated_constraints) * 0.12 + len(constraints.warnings) * 0.025)
        final = clamp(raw_score - penalty, 0.0, 1.0)
        breakdown = {
            "capacity": capacity,
            "bandwidth": bandwidth,
            "latency": latency,
            "power": power,
            "thermal": thermal,
            "raw_score": raw_score,
            "penalty": penalty,
            "final_score": final,
            **{f"weight_{key}": value for key, value in weights.items()},
        }
        return final, breakdown

    def _weights(self, target: ProductTarget) -> dict[str, float]:
        if target.priority_weights:
            weights = {**DEFAULT_WEIGHTS, **target.priority_weights}
        else:
            weights = DEFAULT_WEIGHTS.copy()
            multiplier_key = {
                Priority.BANDWIDTH_FIRST: "bandwidth",
                Priority.POWER_FIRST: "power",
                Priority.CAPACITY_FIRST: "capacity",
                Priority.LATENCY_FIRST: "latency",
            }.get(target.priority)
            if multiplier_key:
                weights[multiplier_key] *= 1.3
        total = sum(max(0.0, value) for value in weights.values())
        return {key: max(0.0, value) / total for key, value in weights.items()}
