from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.constraints import ConstraintResult
from backend.app.domain.enums import ConstraintPolicy
from backend.app.domain.metrics import SimulationMetrics
from backend.app.domain.target import ProductTarget
from backend.app.presets.generation_presets import generation_rule


class ConstraintEvaluator:
    def evaluate(
        self,
        target: ProductTarget,
        architecture: HBMArchitecture,
        metrics: SimulationMetrics,
    ) -> ConstraintResult:
        result = ConstraintResult()

        self._min_constraint(result, "capacity", metrics.usable_capacity_gb, target.capacity_gb)

        bandwidth_value = (
            metrics.achieved_bandwidth_GBps
            if target.bandwidth_constraint_metric == "achieved"
            else metrics.effective_bandwidth_GBps
        )
        self._min_constraint(
            result,
            f"{target.bandwidth_constraint_metric}_bandwidth",
            bandwidth_value,
            target.required_effective_bandwidth_GBps,
        )

        if target.min_peak_bandwidth_GBps is not None:
            self._min_constraint(
                result,
                "peak_bandwidth",
                metrics.raw_peak_bandwidth_GBps,
                target.min_peak_bandwidth_GBps,
            )

        if target.target_generation is not None:
            allowed = {target.target_generation, *target.compatible_generation_set}
            passed = architecture.generation in allowed
            result.margins["target_generation"] = 0.0 if passed else -1.0
            if not passed:
                self._violate(result, "target_generation", severity=1.0)

        if target.allowed_data_rate_gbps is not None:
            low, high = target.allowed_data_rate_gbps
            passed = low <= architecture.data_rate_gbps_per_pin <= high
            margin = min(architecture.data_rate_gbps_per_pin - low, high - architecture.data_rate_gbps_per_pin)
            result.margins["allowed_data_rate"] = margin if passed else -abs(margin)
            if not passed:
                self._violate(result, "allowed_data_rate", severity=1.0)

        rule = generation_rule(architecture.generation)
        if rule and not (rule.min_data_rate_gbps <= architecture.data_rate_gbps_per_pin <= rule.max_data_rate_gbps):
            result.warnings.append("data_rate_outside_generation_public_range")
            result.policy_results["generation_data_rate_range"] = ConstraintPolicy.WARN.value

        if target.min_stack_count is not None:
            self._min_constraint(result, "min_stack_count", architecture.stack_count, target.min_stack_count)
        if target.max_stack_count is not None:
            self._max_constraint(result, "max_stack_count", architecture.stack_count, target.max_stack_count)
        if target.max_stack_height is not None:
            self._max_constraint(result, "max_stack_height", architecture.stack_height, target.max_stack_height)
        if target.allowed_stack_heights is not None:
            passed = architecture.stack_height in target.allowed_stack_heights
            result.margins["allowed_stack_heights"] = 0.0 if passed else -1.0
            if not passed:
                self._violate(result, "allowed_stack_heights", severity=1.0)

        if target.require_ecc and not (architecture.on_die_ecc or architecture.host_ecc):
            result.margins["require_ecc"] = -1.0
            self._violate(result, "require_ecc", severity=1.0)

        if target.package_constraint != "unknown" and architecture.package_class != target.package_constraint:
            result.margins["package_constraint"] = -1.0
            self._violate(result, "package_constraint", severity=1.0)

        if target.power_budget_w is not None and target.power_policy != ConstraintPolicy.IGNORE:
            self._budget_policy_constraint(
                result,
                "power_budget",
                limit=target.power_budget_w,
                actual=metrics.total_power_w,
                policy=target.power_policy,
            )

        if target.max_temperature_c is not None and target.thermal_policy != ConstraintPolicy.IGNORE:
            self._budget_policy_constraint(
                result,
                "thermal_limit",
                limit=target.max_temperature_c,
                actual=metrics.estimated_temperature_c,
                policy=target.thermal_policy,
            )

        if metrics.assumption_coverage.missing_critical_factors:
            result.warnings.append("missing_critical_assumption_factors")
        if metrics.assumption_coverage.coverage_ratio < 0.25:
            result.warnings.append("low_assumption_coverage")

        return result

    def _min_constraint(
        self,
        result: ConstraintResult,
        name: str,
        actual: float,
        required: float,
    ) -> None:
        margin = actual - required
        result.margins[name] = margin
        if margin < 0:
            self._violate(result, name, severity=min(1.0, abs(margin) / max(required, 1e-9)))

    def _max_constraint(
        self,
        result: ConstraintResult,
        name: str,
        actual: float,
        limit: float,
    ) -> None:
        margin = limit - actual
        result.margins[name] = margin
        if margin < 0:
            self._violate(result, name, severity=min(1.0, abs(margin) / max(limit, 1e-9)))

    def _budget_policy_constraint(
        self,
        result: ConstraintResult,
        name: str,
        limit: float,
        actual: float,
        policy: ConstraintPolicy,
    ) -> None:
        margin = limit - actual
        result.margins[name] = margin
        result.policy_results[name] = policy.value
        if margin >= 0:
            return
        severity = min(1.0, abs(margin) / max(limit, 1e-9))
        if policy == ConstraintPolicy.WARN:
            result.warnings.append(name)
            result.severity[name] = severity
        elif policy == ConstraintPolicy.HARD_LIMIT:
            self._violate(result, name, severity)

    def _violate(self, result: ConstraintResult, name: str, severity: float) -> None:
        if name not in result.violated_constraints:
            result.violated_constraints.append(name)
        result.severity[name] = severity
        result.is_feasible = False
