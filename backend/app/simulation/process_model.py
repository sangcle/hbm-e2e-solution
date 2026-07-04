from collections.abc import Iterable

from backend.app.domain.assumptions import SimulationAssumptions
from backend.app.domain.enums import TrafficLimitedBy
from backend.app.domain.metrics import SimulationMetrics
from backend.app.domain.process import ProcessEffects, ProcessParameterValue, ProcessParameters

from .math_utils import clamp, safe_div


def apply_process_effects(
    metrics: SimulationMetrics,
    assumptions: SimulationAssumptions,
    process: ProcessParameters | None,
    capacity_accounting_mode: str = "shipped_good_unit",
) -> SimulationMetrics:
    if process is None:
        return metrics

    effects = calculate_process_effects(process, metrics)
    if effects is None:
        return metrics

    metrics.effective_bandwidth_GBps *= effects.bandwidth_derating_factor
    if metrics.offered_bandwidth_GBps <= 0:
        metrics.achieved_bandwidth_GBps = metrics.effective_bandwidth_GBps
        metrics.demand_satisfaction_ratio = 1.0
        metrics.traffic_limited_by = TrafficLimitedBy.BENCHMARK
    else:
        metrics.achieved_bandwidth_GBps = min(metrics.effective_bandwidth_GBps, metrics.offered_bandwidth_GBps)
        metrics.demand_satisfaction_ratio = clamp(
            safe_div(metrics.achieved_bandwidth_GBps, metrics.offered_bandwidth_GBps),
            0.0,
            1.0,
        )
        metrics.traffic_limited_by = (
            TrafficLimitedBy.MEMORY
            if metrics.effective_bandwidth_GBps < metrics.offered_bandwidth_GBps
            else TrafficLimitedBy.DEMAND
        )
    metrics.bandwidth_utilization = clamp(
        safe_div(metrics.achieved_bandwidth_GBps, metrics.sustained_peak_bandwidth_GBps),
        0.0,
        1.0,
    )
    metrics.effective_to_sustained_efficiency = clamp(
        safe_div(metrics.effective_bandwidth_GBps, metrics.sustained_peak_bandwidth_GBps),
        0.0,
        1.0,
    )

    metrics.average_latency_ns += effects.latency_penalty_ns
    metrics.p50_latency_ns += effects.latency_penalty_ns
    metrics.p95_latency_ns += effects.latency_penalty_ns
    metrics.p99_latency_ns += effects.latency_penalty_ns
    if metrics.latency_histogram:
        for bucket in metrics.latency_histogram:
            if "latency_ns" in bucket:
                bucket["latency_ns"] += effects.latency_penalty_ns

    metrics.total_power_w += effects.power_delta_w
    thermal_resistance = assumptions.thermal_resistance_c_per_w + effects.thermal_resistance_delta_c_per_w
    metrics.estimated_temperature_c = assumptions.ambient_temperature_c + metrics.total_power_w * thermal_resistance
    if metrics.estimated_temperature_c <= assumptions.thermal_throttle_start_c:
        metrics.thermal_throttle_factor = 1.0
    else:
        metrics.thermal_throttle_factor = clamp(
            1.0 - (metrics.estimated_temperature_c - assumptions.thermal_throttle_start_c) / 50.0,
            0.50,
            1.0,
        )

    if capacity_accounting_mode in {"population_expected", "repair_binning", "binning", "yield_adjusted"}:
        metrics.usable_capacity_gb *= effects.capacity_good_die_ratio

    metrics.process_yield_score = effects.yield_score
    metrics.process_defect_risk = effects.defect_risk
    metrics.capacity_good_die_ratio = effects.capacity_good_die_ratio
    metrics.process_bandwidth_derating_factor = effects.bandwidth_derating_factor
    metrics.process_latency_penalty_ns = effects.latency_penalty_ns
    metrics.process_power_delta_w = effects.power_delta_w
    metrics.process_thermal_resistance_delta_c_per_w = effects.thermal_resistance_delta_c_per_w
    metrics.reliability_margin = effects.reliability_margin
    metrics.process_confidence_level = effects.confidence_level.value
    metrics.process_calibration_required = effects.calibration_required
    metrics.process_public_proxy_used = effects.public_proxy_used
    metrics.process_stage_risks = effects.stage_risks
    metrics.process_notes = effects.notes
    metrics.backend_metadata["process_model"] = {
        "schema_version": process.schema_version,
        "process_flow_id": process.process_flow_id,
        "source_type": process.source_type.value,
        "capacity_accounting_mode": capacity_accounting_mode,
        "effects": effects.model_dump(mode="json"),
    }
    return metrics


def calculate_process_effects(
    process: ProcessParameters,
    metrics: SimulationMetrics,
) -> ProcessEffects | None:
    stage_risks = _stage_risks(process)
    if not stage_risks:
        return None

    defect_risk = clamp(_weighted_average(stage_risks.items(), _STAGE_WEIGHTS), 0.0, 0.95)
    yield_score = clamp(1.0 - defect_risk, 0.0, 1.0)

    wafer_good_die_ratio = _fraction(_getattr(process.dram_wafer_fab, "wafer_good_die_ratio"))
    capacity_good_die_ratio = (
        wafer_good_die_ratio
        if wafer_good_die_ratio is not None
        else clamp(1.0 - defect_risk * 0.35, 0.0, 1.0)
    )

    dram_risk = stage_risks.get("dram_wafer_fab", 0.0)
    tsv_risk = stage_risks.get("tsv", 0.0)
    micro_bump_risk = stage_risks.get("rdl_micro_bump", 0.0)
    bonding_risk = stage_risks.get("bonding", 0.0)
    underfill_risk = stage_risks.get("underfill_molding", 0.0)
    package_risk = stage_risks.get("interposer_package", 0.0)
    thermal_risk = _average_present(
        [
            stage_risks.get("bonding"),
            stage_risks.get("underfill_molding"),
            stage_risks.get("interposer_package"),
        ]
    ) or 0.0
    interconnect_risk = _average_present(
        [
            stage_risks.get("tsv"),
            stage_risks.get("rdl_micro_bump"),
            stage_risks.get("bonding"),
        ]
    ) or 0.0

    bandwidth_derating = clamp(
        1.0
        - (
            0.045 * tsv_risk
            + 0.035 * micro_bump_risk
            + 0.035 * bonding_risk
            + 0.020 * package_risk
        ),
        0.80,
        1.0,
    )
    repair_fraction = _fraction(_getattr(process.dram_wafer_fab, "cell_repair_fraction")) or 0.0
    latency_penalty_ns = clamp(6.0 * interconnect_risk + 3.0 * repair_fraction + 4.0 * thermal_risk, 0.0, 20.0)
    power_delta_w = clamp(
        metrics.total_power_w * (0.025 * interconnect_risk + 0.018 * thermal_risk + 0.012 * dram_risk),
        0.0,
        max(2.0, metrics.total_power_w * 0.08),
    )
    thermal_resistance_delta = clamp(0.75 * thermal_risk + 0.10 * underfill_risk, 0.0, 1.5)
    reliability_margin = clamp(1.0 - 0.80 * defect_risk - 0.35 * thermal_risk, 0.0, 1.0)

    notes = [
        "Process model uses generalized public/proxy quality and metrology variables, not equipment recipe setpoints.",
        "Capacity is not reduced unless backend_options.capacity_accounting_mode requests population/binning accounting.",
    ]
    if process.calibration_status != "calibrated":
        notes.append("Process coefficients require calibration before sign-off use.")

    return ProcessEffects(
        yield_score=yield_score,
        defect_risk=defect_risk,
        capacity_good_die_ratio=capacity_good_die_ratio,
        bandwidth_derating_factor=bandwidth_derating,
        latency_penalty_ns=latency_penalty_ns,
        power_delta_w=power_delta_w,
        thermal_resistance_delta_c_per_w=thermal_resistance_delta,
        reliability_margin_delta=reliability_margin - 1.0,
        reliability_margin=reliability_margin,
        confidence_level=process.confidence_level,
        calibration_required=process.calibration_status != "calibrated" or _requires_calibration(process),
        public_proxy_used=process.source_type.value != "internal_measurement",
        stage_risks={key: round(value, 6) for key, value in stage_risks.items()},
        notes=notes,
    )


_STAGE_WEIGHTS = {
    "dram_wafer_fab": 1.20,
    "tsv": 1.35,
    "wafer_thinning": 0.85,
    "rdl_micro_bump": 1.15,
    "bonding": 1.25,
    "underfill_molding": 0.80,
    "interposer_package": 0.80,
    "inspection_test_burn_in": 1.00,
}


def _stage_risks(process: ProcessParameters) -> dict[str, float]:
    risks: dict[str, float] = {}

    if process.dram_wafer_fab:
        risks["dram_wafer_fab"] = _average_present(
            [
                _inverse_fraction_risk(process.dram_wafer_fab.wafer_good_die_ratio),
                _scale(_fraction(process.dram_wafer_fab.cell_repair_fraction), 0.20),
                _scale(_scalar(process.dram_wafer_fab.leakage_current_distribution), 1.0),
            ]
        )
    if process.tsv:
        risks["tsv"] = _average_present(
            [
                _scale(_fraction(process.tsv.tsv_continuity_fail_rate), 0.02),
                _scale(_scalar(process.tsv.tsv_resistance_distribution_mohm), 150.0),
                _scale(_fraction(process.tsv.tsv_void_fraction), 0.08),
            ]
        )
    if process.wafer_thinning:
        risks["wafer_thinning"] = _average_present(
            [
                _scale(_scalar(process.wafer_thinning.post_thinning_ttv_um), 15.0),
                _scale(_scalar(process.wafer_thinning.wafer_warpage_um), 250.0),
                _scale(_scalar(process.wafer_thinning.backside_crack_chipping_density), 1.0),
            ]
        )
    if process.rdl_micro_bump:
        risks["rdl_micro_bump"] = _average_present(
            [
                _scale(_scalar(process.rdl_micro_bump.micro_bump_height_coplanarity_sigma_um), 5.0),
                _scale(_fraction(process.rdl_micro_bump.micro_bump_open_short_rate), 0.02),
            ]
        )
    if process.bonding:
        risks["bonding"] = _average_present(
            [
                _scale(_scalar(process.bonding.die_to_die_overlay_error_um), 5.0),
                _scale(_fraction(process.bonding.bond_void_fraction), 0.08),
            ]
        )
    if process.underfill_molding:
        risks["underfill_molding"] = _average_present(
            [_scale(_fraction(process.underfill_molding.underfill_void_fraction), 0.08)]
        )
    if process.interposer_package:
        risks["interposer_package"] = _average_present(
            [_scale(_fraction(process.interposer_package.thermal_interface_void_fraction), 0.08)]
        )
    if process.inspection_test_burn_in:
        risks["inspection_test_burn_in"] = _average_present(
            [
                _inverse_fraction_risk(process.inspection_test_burn_in.stack_test_pass_rate),
                _scale(_fraction(process.inspection_test_burn_in.burn_in_fallout_rate), 0.05),
            ]
        )

    return {key: value for key, value in risks.items() if value is not None}


def _getattr(section: object | None, name: str) -> ProcessParameterValue | None:
    return getattr(section, name, None) if section is not None else None


def _scalar(parameter: ProcessParameterValue | None) -> float | None:
    if parameter is None or parameter.value is None:
        return None
    value = parameter.value
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        return _average_present([float(item) for item in value])
    if isinstance(value, dict):
        for key in ("mean", "avg", "average", "p50", "median", "value"):
            if key in value:
                return float(value[key])
        return _average_present([float(item) for item in value.values()])
    return None


def _fraction(parameter: ProcessParameterValue | None) -> float | None:
    value = _scalar(parameter)
    if value is None:
        return None
    if parameter and parameter.unit and "%" in parameter.unit:
        value /= 100.0
    return clamp(value, 0.0, 1.0)


def _inverse_fraction_risk(parameter: ProcessParameterValue | None) -> float | None:
    value = _fraction(parameter)
    if value is None:
        return None
    return clamp(1.0 - value, 0.0, 1.0)


def _scale(value: float | None, full_scale: float) -> float | None:
    if value is None:
        return None
    return clamp(value / max(full_scale, 1e-9), 0.0, 1.0)


def _average_present(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _weighted_average(values: Iterable[tuple[str, float]], weights: dict[str, float]) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for key, value in values:
        weight = weights.get(key, 1.0)
        weighted_sum += value * weight
        total_weight += weight
    return safe_div(weighted_sum, total_weight)


def _requires_calibration(process: ProcessParameters) -> bool:
    for section in (
        process.dram_wafer_fab,
        process.tsv,
        process.wafer_thinning,
        process.rdl_micro_bump,
        process.bonding,
        process.underfill_molding,
        process.interposer_package,
        process.inspection_test_burn_in,
    ):
        if section is None:
            continue
        for parameter in section.model_dump().values():
            if isinstance(parameter, dict) and parameter.get("value") is not None and parameter.get("calibration_required"):
                return True
    return False
