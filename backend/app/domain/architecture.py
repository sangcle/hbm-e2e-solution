from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .enums import HBMGeneration


class HBMArchitecture(BaseModel):
    generation: HBMGeneration
    stack_count: int = Field(1, ge=1, le=16)
    stack_height: Literal[4, 8, 12, 16] = 8
    die_count_per_stack: int | None = Field(default=None, ge=1)
    die_capacity_gb: float = Field(..., gt=0)
    capacity_per_stack_gb: float | None = Field(default=None, gt=0)
    total_capacity_gb: float | None = Field(default=None, gt=0)
    io_width_bits_per_stack: int = Field(1024, gt=0)
    channel_count_per_stack: int = Field(16, gt=0)
    pseudo_channels_per_channel: int = Field(2, gt=0)
    pseudo_channel_width_bits: float | None = Field(default=None, gt=0)
    data_rate_gbps_per_pin: float = Field(..., gt=0)
    on_die_ecc: bool = True
    host_ecc: bool = False
    package_class: Literal["unknown", "compact", "standard", "large"] = "unknown"
    backend_tck_ps: float | None = Field(default=None, gt=0)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_and_validate_consistency(self) -> "HBMArchitecture":
        if self.die_count_per_stack is None:
            self.die_count_per_stack = self.stack_height

        computed_capacity_per_stack = self.die_capacity_gb * self.die_count_per_stack
        if self.capacity_per_stack_gb is None:
            self.capacity_per_stack_gb = computed_capacity_per_stack
        elif abs(self.capacity_per_stack_gb - computed_capacity_per_stack) > max(0.05, computed_capacity_per_stack * 0.01):
            raise ValueError("capacity_per_stack_gb must match die_capacity_gb * die_count_per_stack")

        computed_total_capacity = self.capacity_per_stack_gb * self.stack_count
        if self.total_capacity_gb is None:
            self.total_capacity_gb = computed_total_capacity
        elif abs(self.total_capacity_gb - computed_total_capacity) > max(0.05, computed_total_capacity * 0.01):
            raise ValueError("total_capacity_gb must match capacity_per_stack_gb * stack_count")

        computed_pseudo_width = (
            self.io_width_bits_per_stack
            / self.channel_count_per_stack
            / self.pseudo_channels_per_channel
        )
        if self.pseudo_channel_width_bits is None:
            self.pseudo_channel_width_bits = computed_pseudo_width
        elif abs(self.pseudo_channel_width_bits - computed_pseudo_width) > 0.01:
            raise ValueError("pseudo_channel_width_bits is inconsistent with io/channel structure")

        return self
