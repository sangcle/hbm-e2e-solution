from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.assumptions import SimulationAssumptions
from backend.app.domain.enums import TrafficLimitedBy
from backend.app.domain.workload import WorkloadProfile

from .math_utils import clamp, safe_div
from .utilization_model import calculate_effective_utilization


def calculate_bandwidth(
    architecture: HBMArchitecture,
    workload: WorkloadProfile,
    assumptions: SimulationAssumptions,
    thermal_throttle_factor: float,
) -> tuple[dict[str, float | TrafficLimitedBy], dict[str, float]]:
    raw_peak = (
        architecture.stack_count
        * architecture.io_width_bits_per_stack
        * architecture.data_rate_gbps_per_pin
        / 8.0
    )
    sustained_peak = (
        raw_peak
        * assumptions.data_rate_derating_factor
        * (1.0 - assumptions.training_overhead_fraction)
        * (1.0 - assumptions.calibration_penalty_fraction)
    )
    effective_utilization, utilization_factors = calculate_effective_utilization(
        architecture,
        workload,
        assumptions,
        thermal_throttle_factor,
    )
    effective_bandwidth = sustained_peak * effective_utilization
    offered_bandwidth = workload.bandwidth_demand_GBps

    if offered_bandwidth <= 0:
        achieved_bandwidth = effective_bandwidth
        demand_satisfaction_ratio = 1.0
        traffic_limited_by = TrafficLimitedBy.BENCHMARK
    else:
        achieved_bandwidth = min(effective_bandwidth, offered_bandwidth)
        demand_satisfaction_ratio = clamp(safe_div(achieved_bandwidth, offered_bandwidth), 0.0, 1.0)
        traffic_limited_by = (
            TrafficLimitedBy.MEMORY
            if effective_bandwidth < offered_bandwidth
            else TrafficLimitedBy.DEMAND
        )

    metrics = {
        "raw_peak_bandwidth_GBps": raw_peak,
        "sustained_peak_bandwidth_GBps": sustained_peak,
        "effective_utilization": effective_utilization,
        "effective_bandwidth_GBps": effective_bandwidth,
        "offered_bandwidth_GBps": offered_bandwidth,
        "achieved_bandwidth_GBps": achieved_bandwidth,
        "demand_satisfaction_ratio": demand_satisfaction_ratio,
        "bandwidth_utilization": clamp(safe_div(achieved_bandwidth, sustained_peak), 0.0, 1.0),
        "effective_to_sustained_efficiency": clamp(safe_div(effective_bandwidth, sustained_peak), 0.0, 1.0),
        "traffic_limited_by": traffic_limited_by,
    }
    return metrics, utilization_factors
