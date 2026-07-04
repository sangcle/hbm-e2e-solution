from typing import Any

from pydantic import BaseModel, Field

from .enums import RunStatus, SimulationMode
from .versions import (
    API_VERSION,
    ASSUMPTION_VERSION,
    BACKEND_ADAPTER_VERSION,
    FORMULA_VERSION,
    MODEL_VERSION,
    PRESET_VERSION,
    SCHEMA_VERSION,
)


class RuntimeMetadata(BaseModel):
    python_version: str
    dependency_versions: dict[str, str] = Field(default_factory=dict)


class RunMetadata(BaseModel):
    schema_version: str = SCHEMA_VERSION
    api_version: str = API_VERSION
    model_version: str = MODEL_VERSION
    formula_version: str = FORMULA_VERSION
    preset_version: str = PRESET_VERSION
    assumption_version: str = ASSUMPTION_VERSION
    backend_adapter_version: str = BACKEND_ADAPTER_VERSION
    simulation_mode: SimulationMode
    git_commit: str | None = None
    created_at: str
    runtime: RuntimeMetadata
    run_id: str
    candidate_id: str
    status: RunStatus = RunStatus.COMPLETED
    duration_ms: float | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
