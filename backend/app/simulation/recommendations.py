from backend.app.domain.constraints import ConstraintResult
from backend.app.domain.enums import ConfidenceLevel, TrafficLimitedBy
from backend.app.domain.metrics import Recommendation, SimulationMetrics
from backend.app.domain.target import ProductTarget


class RecommendationEngine:
    def generate(
        self,
        target: ProductTarget,
        metrics: SimulationMetrics,
        constraints: ConstraintResult,
    ) -> tuple[list[str], list[Recommendation]]:
        bottlenecks: list[str] = []
        recommendations: list[Recommendation] = []

        for constraint in constraints.violated_constraints:
            bottlenecks.append(constraint)
            recommendations.append(self._for_constraint(constraint, target, metrics))

        if metrics.effective_to_sustained_efficiency < 0.45:
            bottlenecks.append("low_effective_utilization")
            recommendations.append(
                Recommendation(
                    code="low_effective_utilization",
                    severity="medium",
                    message="Improve channel balance, bank parallelism, row locality, or controller efficiency.",
                    related_metrics={
                        "effective_to_sustained_efficiency": metrics.effective_to_sustained_efficiency,
                    },
                    suggested_actions=[
                        "improve_channel_balance",
                        "increase_bank_parallelism",
                        "calibrate_controller_efficiency",
                    ],
                )
            )

        thermal_margin = constraints.margins.get("thermal_limit")
        if thermal_margin is not None and thermal_margin < 5.0:
            recommendations.append(
                Recommendation(
                    code="thermal_margin_low",
                    severity="medium" if thermal_margin >= 0 else "high",
                    message="Reduce achieved traffic, improve cooling assumptions, or lower stack count/power.",
                    related_metrics={
                        "estimated_temperature_c": metrics.estimated_temperature_c,
                        "thermal_margin_c": thermal_margin,
                    },
                    suggested_actions=["improve_cooling", "reduce_power", "validate_thermal_model"],
                )
            )

        if metrics.assumption_coverage.missing_critical_factors:
            recommendations.append(
                Recommendation(
                    code="missing_critical_factors",
                    severity="medium",
                    message="Add internal calibration measurements before using this result for sign-off.",
                    related_metrics={
                        "missing_factor_count": len(metrics.assumption_coverage.missing_critical_factors),
                        "coverage_ratio": metrics.assumption_coverage.coverage_ratio,
                    },
                    suggested_actions=["import_calibration_dataset", "record_factor_sources"],
                )
            )

        if metrics.backend_metadata.get("confidence_level") == ConfidenceLevel.LOW.value:
            recommendations.append(
                Recommendation(
                    code="low_confidence_assumption",
                    severity="low",
                    message="Treat public/proxy assumption results as directional comparisons.",
                    related_metrics={"coverage_ratio": metrics.assumption_coverage.coverage_ratio},
                    suggested_actions=["replace_public_proxy_assumptions"],
                )
            )

        if metrics.traffic_limited_by == TrafficLimitedBy.MEMORY:
            recommendations.append(
                Recommendation(
                    code="memory_limited",
                    severity="medium",
                    message="Increase stack count, data rate, or effective utilization to satisfy workload demand.",
                    related_metrics={
                        "effective_bandwidth_GBps": metrics.effective_bandwidth_GBps,
                        "offered_bandwidth_GBps": metrics.offered_bandwidth_GBps,
                    },
                    suggested_actions=["increase_stack_count", "increase_data_rate", "improve_utilization"],
                )
            )
        elif metrics.traffic_limited_by == TrafficLimitedBy.DEMAND:
            recommendations.append(
                Recommendation(
                    code="demand_limited",
                    severity="low",
                    message="The candidate has bandwidth headroom for the selected workload demand.",
                    related_metrics={
                        "effective_bandwidth_GBps": metrics.effective_bandwidth_GBps,
                        "offered_bandwidth_GBps": metrics.offered_bandwidth_GBps,
                    },
                    suggested_actions=["evaluate_smaller_or_lower_power_candidate"],
                )
            )

        deduped_bottlenecks = list(dict.fromkeys(bottlenecks))
        deduped_recommendations = list({rec.code: rec for rec in recommendations}.values())
        return deduped_bottlenecks, deduped_recommendations

    def _for_constraint(
        self,
        constraint: str,
        target: ProductTarget,
        metrics: SimulationMetrics,
    ) -> Recommendation:
        if "bandwidth" in constraint:
            return Recommendation(
                code=constraint,
                severity="high",
                message="Increase stack count or data rate, improve channel balance, or select a bandwidth-oriented generation.",
                related_metrics={
                    "effective_bandwidth_GBps": metrics.effective_bandwidth_GBps,
                    "achieved_bandwidth_GBps": metrics.achieved_bandwidth_GBps,
                    "target_bandwidth_GBps": target.required_effective_bandwidth_GBps,
                },
                suggested_actions=["increase_stack_count", "increase_data_rate", "improve_channel_balance"],
            )
        if constraint == "capacity":
            return Recommendation(
                code=constraint,
                severity="high",
                message="Increase stack count, stack height, or die capacity.",
                related_metrics={
                    "usable_capacity_gb": metrics.usable_capacity_gb,
                    "target_capacity_gb": target.capacity_gb,
                },
                suggested_actions=["increase_stack_count", "increase_stack_height", "increase_die_capacity"],
            )
        if constraint == "power_budget":
            return Recommendation(
                code=constraint,
                severity="high",
                message="Reduce traffic, choose a lower power assumption set, or reduce stack count.",
                related_metrics={
                    "total_power_w": metrics.total_power_w,
                    "power_budget_w": target.power_budget_w,
                },
                suggested_actions=["reduce_traffic", "calibrate_io_energy", "reduce_stack_count"],
            )
        if constraint == "thermal_limit":
            return Recommendation(
                code=constraint,
                severity="high",
                message="Improve cooling, reduce power, or apply a lower sustained bandwidth target.",
                related_metrics={
                    "estimated_temperature_c": metrics.estimated_temperature_c,
                    "max_temperature_c": target.max_temperature_c,
                },
                suggested_actions=["improve_cooling", "reduce_power", "lower_sustained_target"],
            )
        return Recommendation(
            code=constraint,
            severity="medium",
            message="Adjust the candidate architecture or target constraint and rerun the comparison.",
            related_metrics={},
            suggested_actions=["review_constraint"],
        )
