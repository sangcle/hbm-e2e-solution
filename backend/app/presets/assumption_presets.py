from backend.app.domain.assumptions import FactorSource, SimulationAssumptions
from backend.app.domain.enums import ConfidenceLevel, SourceType


PUBLIC_FACTOR_SOURCES = {
    "io_energy_pj_per_bit_read": FactorSource(
        source_type=SourceType.PUBLIC_VENDOR,
        source_id="public_hbm_mvp_v0",
        confidence_level=ConfidenceLevel.LOW,
    ),
    "io_energy_pj_per_bit_write": FactorSource(
        source_type=SourceType.PUBLIC_VENDOR,
        source_id="public_hbm_mvp_v0",
        confidence_level=ConfidenceLevel.LOW,
    ),
    "thermal_resistance_c_per_w": FactorSource(
        source_type=SourceType.PROXY,
        source_id="mvp_default_thermal_proxy",
        confidence_level=ConfidenceLevel.LOW,
    ),
    "controller_efficiency_factor": FactorSource(
        source_type=SourceType.LITERATURE_PROXY,
        source_id="mvp_default_controller_proxy",
        confidence_level=ConfidenceLevel.LOW,
    ),
    "latency_base_ns": FactorSource(
        source_type=SourceType.LITERATURE_PROXY,
        source_id="mvp_default_latency_proxy",
        confidence_level=ConfidenceLevel.LOW,
    ),
}


ASSUMPTION_PRESETS: dict[str, SimulationAssumptions] = {
    "public_hbm_mvp_v0": SimulationAssumptions(
        assumption_id="public_hbm_mvp_v0",
        version="0.1.0",
        confidence_level=ConfidenceLevel.LOW,
        production_calibrated=False,
        factor_sources=PUBLIC_FACTOR_SOURCES,
    ),
    "balanced_lab_proxy_v0": SimulationAssumptions(
        assumption_id="balanced_lab_proxy_v0",
        version="0.1.0",
        confidence_level=ConfidenceLevel.MEDIUM,
        production_calibrated=False,
        usable_capacity_fraction=0.95,
        controller_efficiency_factor=0.93,
        io_energy_pj_per_bit_read=3.4,
        io_energy_pj_per_bit_write=4.0,
        thermal_resistance_c_per_w=0.60,
        factor_sources={
            **PUBLIC_FACTOR_SOURCES,
            "controller_efficiency_factor": FactorSource(
                source_type=SourceType.PROXY,
                source_id="lab_proxy_controller_efficiency",
                confidence_level=ConfidenceLevel.MEDIUM,
            ),
        },
    ),
}


def get_assumption_preset(preset_id: str) -> SimulationAssumptions:
    try:
        return ASSUMPTION_PRESETS[preset_id].model_copy(deep=True)
    except KeyError as exc:
        raise KeyError(f"Unknown assumption preset: {preset_id}") from exc
