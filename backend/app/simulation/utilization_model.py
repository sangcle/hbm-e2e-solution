from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.assumptions import SimulationAssumptions
from backend.app.domain.workload import WorkloadProfile

from .math_utils import clamp


def calculate_effective_utilization(
    architecture: HBMArchitecture,
    workload: WorkloadProfile,
    assumptions: SimulationAssumptions,
    thermal_throttle_factor: float,
) -> tuple[float, dict[str, float]]:
    base_workload_utilization = clamp(
        0.70
        + workload.sequential_ratio * 0.10
        + workload.row_buffer_locality * 0.10
        - workload.burstiness * 0.07,
        0.35,
        0.97,
    )
    channel_factor = workload.channel_balance
    pseudo_channel_balance_factor = workload.pseudo_channel_balance
    bank_factor = workload.bank_parallelism
    row_factor = clamp(0.72 + workload.row_buffer_locality * 0.26, 0.72, 0.98)
    mixing_pressure = 1.0 - abs(workload.read_ratio - workload.write_ratio)
    read_write_turnaround_factor = clamp(
        assumptions.read_write_turnaround_base - 0.08 * mixing_pressure + 0.03 * workload.sequential_ratio,
        0.78,
        0.99,
    )
    stack_factor = clamp(0.86 + 0.035 * architecture.stack_count, 0.86, 1.0)
    burst_factor = clamp(1.0 - 0.12 * workload.burstiness, 0.80, 1.0)

    factors = {
        "base_workload_utilization": base_workload_utilization,
        "channel_factor": channel_factor,
        "pseudo_channel_balance_factor": pseudo_channel_balance_factor,
        "bank_factor": bank_factor,
        "row_factor": row_factor,
        "read_write_turnaround_factor": read_write_turnaround_factor,
        "refresh_availability_factor": assumptions.refresh_availability_factor,
        "controller_efficiency_factor": assumptions.controller_efficiency_factor,
        "stack_factor": stack_factor,
        "thermal_throttle_factor": thermal_throttle_factor,
        "burst_factor": burst_factor,
    }

    utilization = 1.0
    for factor in factors.values():
        utilization *= factor
    return clamp(utilization, 0.02, 1.0), factors
