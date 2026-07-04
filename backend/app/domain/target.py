from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import ConstraintPolicy, HBMGeneration, Priority


class ProductTarget(BaseModel):
    capacity_gb: float = Field(24.0, gt=0)
    target_bandwidth_GBps: float = Field(1000.0, gt=0)
    min_effective_bandwidth_GBps: float | None = Field(default=None, gt=0)
    min_peak_bandwidth_GBps: float | None = Field(default=None, gt=0)
    max_average_latency_ns: float | None = Field(default=None, gt=0)
    power_budget_w: float | None = Field(default=60.0, gt=0)
    max_temperature_c: float | None = Field(default=95.0, gt=-273.15)
    target_generation: HBMGeneration | None = None
    compatible_generation_set: list[HBMGeneration] = Field(default_factory=list)
    allowed_data_rate_gbps: tuple[float, float] | None = None
    min_stack_count: int | None = Field(default=None, ge=1)
    max_stack_count: int | None = Field(default=None, ge=1)
    max_stack_height: int | None = Field(default=None, ge=1)
    allowed_stack_heights: list[int] | None = None
    require_ecc: bool = False
    package_constraint: Literal["unknown", "compact", "standard", "large"] = "unknown"
    power_policy: ConstraintPolicy = ConstraintPolicy.WARN
    thermal_policy: ConstraintPolicy = ConstraintPolicy.HARD_LIMIT
    priority: Priority = Priority.BALANCED
    priority_weights: dict[str, float] | None = None
    bandwidth_constraint_metric: Literal["effective", "achieved"] = "effective"

    @field_validator("allowed_stack_heights")
    @classmethod
    def validate_allowed_stack_heights(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        invalid = sorted(set(value) - {4, 8, 12, 16})
        if invalid:
            raise ValueError(f"allowed_stack_heights contains unsupported values: {invalid}")
        return value

    @model_validator(mode="after")
    def validate_ranges(self) -> "ProductTarget":
        if self.allowed_data_rate_gbps is not None:
            low, high = self.allowed_data_rate_gbps
            if low <= 0 or high <= 0 or low > high:
                raise ValueError("allowed_data_rate_gbps must be a positive (min, max) range")
        if self.min_stack_count and self.max_stack_count and self.min_stack_count > self.max_stack_count:
            raise ValueError("min_stack_count cannot be greater than max_stack_count")
        if self.priority_weights:
            total = sum(self.priority_weights.values())
            if total <= 0:
                raise ValueError("priority_weights must have a positive total")
        return self

    @property
    def required_effective_bandwidth_GBps(self) -> float:
        return self.min_effective_bandwidth_GBps or self.target_bandwidth_GBps
