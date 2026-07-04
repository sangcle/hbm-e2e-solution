from typing import Any

from .assumption_presets import ASSUMPTION_PRESETS, get_assumption_preset
from .generation_presets import ARCHITECTURE_PRESETS, GENERATION_RULES, get_architecture_preset
from .workload_presets import WORKLOAD_PRESETS, get_workload_preset


def all_presets() -> dict[str, Any]:
    return {
        "architecture_presets": {
            key: value.model_dump(mode="json") for key, value in ARCHITECTURE_PRESETS.items()
        },
        "generation_rules": {
            key.value: value.__dict__ for key, value in GENERATION_RULES.items()
        },
        "workload_presets": {
            key: value.model_dump(mode="json") for key, value in WORKLOAD_PRESETS.items()
        },
        "assumption_presets": {
            key: value.model_dump(mode="json") for key, value in ASSUMPTION_PRESETS.items()
        },
    }


__all__ = [
    "all_presets",
    "get_architecture_preset",
    "get_workload_preset",
    "get_assumption_preset",
]
