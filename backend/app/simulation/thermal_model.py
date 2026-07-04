from backend.app.domain.assumptions import SimulationAssumptions

from .math_utils import clamp


def calculate_thermal(
    assumptions: SimulationAssumptions,
    total_power_w: float,
) -> dict[str, float]:
    estimated_temperature_c = (
        assumptions.ambient_temperature_c
        + total_power_w * assumptions.thermal_resistance_c_per_w
    )
    if estimated_temperature_c <= assumptions.thermal_throttle_start_c:
        throttle = 1.0
    else:
        throttle = clamp(
            1.0 - (estimated_temperature_c - assumptions.thermal_throttle_start_c) / 50.0,
            0.50,
            1.0,
        )
    return {
        "estimated_temperature_c": estimated_temperature_c,
        "thermal_throttle_factor": throttle,
    }
