from dataclasses import dataclass

from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.enums import HBMGeneration


@dataclass(frozen=True)
class GenerationRule:
    min_data_rate_gbps: float
    max_data_rate_gbps: float
    nominal_data_rate_gbps: float
    io_width_bits_per_stack: int
    channel_count_per_stack: int
    pseudo_channels_per_channel: int


GENERATION_RULES: dict[HBMGeneration, GenerationRule] = {
    HBMGeneration.HBM2E: GenerationRule(2.4, 3.6, 3.2, 1024, 8, 2),
    HBMGeneration.HBM3: GenerationRule(4.8, 6.4, 6.4, 1024, 16, 2),
    HBMGeneration.HBM3E: GenerationRule(6.4, 9.8, 9.2, 1024, 16, 2),
    HBMGeneration.HBM4: GenerationRule(6.4, 8.0, 8.0, 2048, 32, 2),
}


ARCHITECTURE_PRESETS: dict[str, HBMArchitecture] = {
    "hbm2e_8hi_16gb": HBMArchitecture(
        generation=HBMGeneration.HBM2E,
        stack_count=1,
        stack_height=8,
        die_capacity_gb=2.0,
        io_width_bits_per_stack=1024,
        channel_count_per_stack=8,
        pseudo_channels_per_channel=2,
        data_rate_gbps_per_pin=3.2,
        on_die_ecc=True,
    ),
    "hbm3_8hi_16gb": HBMArchitecture(
        generation=HBMGeneration.HBM3,
        stack_count=1,
        stack_height=8,
        die_capacity_gb=2.0,
        io_width_bits_per_stack=1024,
        channel_count_per_stack=16,
        pseudo_channels_per_channel=2,
        data_rate_gbps_per_pin=6.4,
        on_die_ecc=True,
    ),
    "hbm3_12hi_24gb": HBMArchitecture(
        generation=HBMGeneration.HBM3,
        stack_count=1,
        stack_height=12,
        die_capacity_gb=2.0,
        io_width_bits_per_stack=1024,
        channel_count_per_stack=16,
        pseudo_channels_per_channel=2,
        data_rate_gbps_per_pin=6.4,
        on_die_ecc=True,
    ),
    "hbm3e_8hi_24gb": HBMArchitecture(
        generation=HBMGeneration.HBM3E,
        stack_count=1,
        stack_height=8,
        die_capacity_gb=3.0,
        io_width_bits_per_stack=1024,
        channel_count_per_stack=16,
        pseudo_channels_per_channel=2,
        data_rate_gbps_per_pin=9.2,
        on_die_ecc=True,
    ),
    "hbm3e_12hi_36gb": HBMArchitecture(
        generation=HBMGeneration.HBM3E,
        stack_count=1,
        stack_height=12,
        die_capacity_gb=3.0,
        io_width_bits_per_stack=1024,
        channel_count_per_stack=16,
        pseudo_channels_per_channel=2,
        data_rate_gbps_per_pin=9.2,
        on_die_ecc=True,
    ),
}


def get_architecture_preset(preset_id: str) -> HBMArchitecture:
    try:
        return ARCHITECTURE_PRESETS[preset_id].model_copy(deep=True)
    except KeyError as exc:
        raise KeyError(f"Unknown architecture preset: {preset_id}") from exc


def generation_rule(generation: HBMGeneration) -> GenerationRule | None:
    return GENERATION_RULES.get(generation)
