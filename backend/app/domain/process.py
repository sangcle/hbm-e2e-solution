import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ConfidenceLevel, SourceType


ProcessDataType = Literal[
    "continuous",
    "categorical",
    "binary",
    "distribution",
    "image_derived",
    "time_series",
]
CalibrationStatus = Literal["uncalibrated", "partially_calibrated", "calibrated"]


class ProcessParameterValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any = None
    unit: str | None = None
    data_type: ProcessDataType = "continuous"
    calibration_required: bool = True

    @field_validator("value")
    @classmethod
    def validate_supported_value(cls, value: Any) -> Any:
        if value is None or isinstance(value, str):
            return value
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                raise ValueError("Process parameter values must be finite.")
            return value
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, (int, float)) or not math.isfinite(float(item)):
                    raise ValueError("Process parameter lists must contain finite numbers.")
            return value
        if isinstance(value, dict):
            for item in value.values():
                if not isinstance(item, (int, float)) or not math.isfinite(float(item)):
                    raise ValueError("Process parameter distributions must contain finite numeric values.")
            return value
        raise ValueError("Process parameter value must be numeric, string, numeric list, numeric dict, or null.")


class DramWaferFabProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wafer_good_die_ratio: ProcessParameterValue | None = None
    cell_repair_fraction: ProcessParameterValue | None = None
    leakage_current_distribution: ProcessParameterValue | None = None


class TsvProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tsv_continuity_fail_rate: ProcessParameterValue | None = None
    tsv_resistance_distribution_mohm: ProcessParameterValue | None = None
    tsv_void_fraction: ProcessParameterValue | None = None


class WaferThinningProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    post_thinning_ttv_um: ProcessParameterValue | None = None
    wafer_warpage_um: ProcessParameterValue | None = None
    backside_crack_chipping_density: ProcessParameterValue | None = None


class RdlMicroBumpProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    micro_bump_height_coplanarity_sigma_um: ProcessParameterValue | None = None
    micro_bump_open_short_rate: ProcessParameterValue | None = None


class BondingProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bonding_technology: ProcessParameterValue | None = None
    die_to_die_overlay_error_um: ProcessParameterValue | None = None
    bond_void_fraction: ProcessParameterValue | None = None


class UnderfillMoldingProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    underfill_void_fraction: ProcessParameterValue | None = None


class InterposerPackageProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thermal_interface_void_fraction: ProcessParameterValue | None = None


class InspectionTestBurnInProcess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stack_test_pass_rate: ProcessParameterValue | None = None
    burn_in_fallout_rate: ProcessParameterValue | None = None


class ProcessParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "process_proxy_v0.1"
    process_flow_id: str = "public_hbm_process_proxy_v0"
    source_type: SourceType = SourceType.PROXY
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    calibration_status: CalibrationStatus = "uncalibrated"

    dram_wafer_fab: DramWaferFabProcess | None = None
    tsv: TsvProcess | None = None
    wafer_thinning: WaferThinningProcess | None = None
    rdl_micro_bump: RdlMicroBumpProcess | None = None
    bonding: BondingProcess | None = None
    underfill_molding: UnderfillMoldingProcess | None = None
    interposer_package: InterposerPackageProcess | None = None
    inspection_test_burn_in: InspectionTestBurnInProcess | None = None


class ProcessEffects(BaseModel):
    yield_score: float = Field(ge=0.0, le=1.0)
    defect_risk: float = Field(ge=0.0, le=1.0)
    capacity_good_die_ratio: float = Field(ge=0.0, le=1.0)
    bandwidth_derating_factor: float = Field(ge=0.0, le=1.0)
    latency_penalty_ns: float = Field(ge=0.0)
    power_delta_w: float
    thermal_resistance_delta_c_per_w: float
    reliability_margin_delta: float
    reliability_margin: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    calibration_required: bool = True
    public_proxy_used: bool = True
    stage_risks: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
