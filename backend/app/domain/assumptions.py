from pydantic import BaseModel, Field

from .enums import ConfidenceLevel, SourceType


class FactorSource(BaseModel):
    source_type: SourceType
    source_id: str
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW


class AssumptionCoverage(BaseModel):
    measured_factor_count: int
    external_proxy_factor_count: int
    neutralized_factor_count: int
    missing_critical_factors: list[str]
    coverage_ratio: float


class SimulationAssumptions(BaseModel):
    assumption_id: str = "public_hbm_mvp_v0"
    version: str = "0.1.0"
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    production_calibrated: bool = False

    usable_capacity_fraction: float = Field(0.94, gt=0, le=1)
    data_rate_derating_factor: float = Field(0.96, gt=0, le=1)
    training_overhead_fraction: float = Field(0.015, ge=0, lt=1)
    calibration_penalty_fraction: float = Field(0.02, ge=0, lt=1)
    refresh_availability_factor: float = Field(0.985, gt=0, le=1)
    controller_efficiency_factor: float = Field(0.90, gt=0, le=1)
    read_write_turnaround_base: float = Field(0.96, gt=0, le=1)

    latency_base_ns: float = Field(42.0, gt=0)
    row_miss_penalty_ns: float = Field(38.0, ge=0)
    queue_latency_ns_per_128_concurrency: float = Field(8.0, ge=0)
    saturation_coefficient_ns: float = Field(32.0, ge=0)

    io_energy_pj_per_bit_read: float = Field(3.8, ge=0)
    io_energy_pj_per_bit_write: float = Field(4.4, ge=0)
    static_power_w_per_stack: float = Field(5.5, ge=0)
    logic_power_w_per_stack: float = Field(2.0, ge=0)
    thermal_resistance_c_per_w: float = Field(0.72, gt=0)
    ambient_temperature_c: float = 35.0
    thermal_throttle_start_c: float = Field(90.0, gt=-273.15)

    factor_sources: dict[str, FactorSource] = Field(default_factory=dict)

    def coverage(self) -> AssumptionCoverage:
        measured = 0
        external_proxy = 0
        neutralized = 0
        for source in self.factor_sources.values():
            if source.source_type == SourceType.INTERNAL_MEASUREMENT:
                measured += 1
            elif source.source_type == SourceType.NEUTRAL_DEFAULT:
                neutralized += 1
            else:
                external_proxy += 1

        critical = [
            "internal_hbm_calibration_measurements",
            "validated_package_thermal_model",
            "controller_efficiency_measurement",
        ]
        missing = [] if self.production_calibrated else critical
        total = max(1, measured + external_proxy + neutralized)
        return AssumptionCoverage(
            measured_factor_count=measured,
            external_proxy_factor_count=external_proxy,
            neutralized_factor_count=neutralized,
            missing_critical_factors=missing,
            coverage_ratio=measured / total,
        )
