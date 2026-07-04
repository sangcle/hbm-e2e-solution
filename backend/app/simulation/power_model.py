from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.assumptions import SimulationAssumptions
from backend.app.domain.workload import WorkloadProfile


def calculate_power(
    architecture: HBMArchitecture,
    workload: WorkloadProfile,
    assumptions: SimulationAssumptions,
    achieved_bandwidth_GBps: float,
) -> dict[str, float]:
    weighted_io_energy_pj_per_bit = (
        workload.read_ratio * assumptions.io_energy_pj_per_bit_read
        + workload.write_ratio * assumptions.io_energy_pj_per_bit_write
    )
    dynamic_power_w = achieved_bandwidth_GBps * 0.008 * weighted_io_energy_pj_per_bit
    static_power_w = architecture.stack_count * assumptions.static_power_w_per_stack
    logic_power_w = architecture.stack_count * assumptions.logic_power_w_per_stack
    total_power_w = dynamic_power_w + static_power_w + logic_power_w
    return {
        "dynamic_power_w": dynamic_power_w,
        "static_power_w": static_power_w,
        "logic_power_w": logic_power_w,
        "total_power_w": total_power_w,
    }
