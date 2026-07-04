from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.assumptions import SimulationAssumptions
from backend.app.domain.metrics import SimulationMetrics
from backend.app.domain.workload import WorkloadProfile

from .bandwidth_model import calculate_bandwidth
from .capacity_model import calculate_capacity
from .latency_model import calculate_latency
from .power_model import calculate_power
from .thermal_model import calculate_thermal


class AnalyticalEngine:
    def run(
        self,
        architecture: HBMArchitecture,
        workload: WorkloadProfile,
        assumptions: SimulationAssumptions,
    ) -> SimulationMetrics:
        raw_capacity_gb, usable_capacity_gb = calculate_capacity(architecture, assumptions)

        bandwidth, _ = calculate_bandwidth(
            architecture,
            workload,
            assumptions,
            thermal_throttle_factor=1.0,
        )
        latency = calculate_latency(
            workload,
            assumptions,
            bandwidth["achieved_bandwidth_GBps"],  # type: ignore[arg-type]
            bandwidth["effective_bandwidth_GBps"],  # type: ignore[arg-type]
        )
        power = calculate_power(
            architecture,
            workload,
            assumptions,
            bandwidth["achieved_bandwidth_GBps"],  # type: ignore[arg-type]
        )
        thermal = calculate_thermal(assumptions, power["total_power_w"])

        if thermal["thermal_throttle_factor"] < 1.0:
            bandwidth, _ = calculate_bandwidth(
                architecture,
                workload,
                assumptions,
                thermal_throttle_factor=thermal["thermal_throttle_factor"],
            )
            latency = calculate_latency(
                workload,
                assumptions,
                bandwidth["achieved_bandwidth_GBps"],  # type: ignore[arg-type]
                bandwidth["effective_bandwidth_GBps"],  # type: ignore[arg-type]
            )
            power = calculate_power(
                architecture,
                workload,
                assumptions,
                bandwidth["achieved_bandwidth_GBps"],  # type: ignore[arg-type]
            )
            thermal = calculate_thermal(assumptions, power["total_power_w"])

        return SimulationMetrics(
            raw_capacity_gb=raw_capacity_gb,
            usable_capacity_gb=usable_capacity_gb,
            **bandwidth,
            **latency,
            **power,
            estimated_temperature_c=thermal["estimated_temperature_c"],
            thermal_throttle_factor=thermal["thermal_throttle_factor"],
            assumption_coverage=assumptions.coverage(),
            backend_metadata={"backend": "analytical"},
        )
