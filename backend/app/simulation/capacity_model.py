from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.assumptions import SimulationAssumptions


def calculate_capacity(
    architecture: HBMArchitecture,
    assumptions: SimulationAssumptions,
) -> tuple[float, float]:
    raw_capacity_gb = architecture.total_capacity_gb or 0.0
    usable_capacity_gb = raw_capacity_gb * assumptions.usable_capacity_fraction
    return raw_capacity_gb, usable_capacity_gb
