import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.domain.enums import ConfidenceLevel
from backend.app.domain.process import ProcessParameters


class ProcessCalibrationProfile(BaseModel):
    artifact_id: str
    model_mode: Literal["proxy", "calibrated"] = "proxy"
    dataset_id: str | None = None
    model_version: str
    sample_count: int | None = Field(default=None, ge=0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    stage_weights: dict[str, float] = Field(default_factory=dict)
    scale_factors: dict[str, float] = Field(default_factory=dict)
    effect_coefficients: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


PROFILE_DIR = Path(__file__).resolve().parents[1] / "calibration" / "process"
PUBLIC_PROXY_ARTIFACT_ID = "public_proxy_v0"
DEFAULT_CALIBRATED_ARTIFACT_ID = "hbm_process_calibrated_v0"


@lru_cache(maxsize=16)
def load_process_calibration_profile(artifact_id: str) -> ProcessCalibrationProfile:
    safe_name = artifact_id.replace("/", "_").replace("\\", "_")
    path = PROFILE_DIR / f"{safe_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Process calibration artifact not found: {artifact_id}")
    return ProcessCalibrationProfile.model_validate(json.loads(path.read_text(encoding="utf-8")))


def resolve_process_calibration_profile(process: ProcessParameters) -> tuple[ProcessCalibrationProfile, list[str]]:
    notes: list[str] = []
    requested_mode = process.calculation_mode
    use_calibrated = requested_mode == "calibrated" or (
        requested_mode == "auto" and process.calibration_status == "calibrated"
    )
    artifact_id = process.calibration_artifact_id
    if use_calibrated and not artifact_id:
        artifact_id = DEFAULT_CALIBRATED_ARTIFACT_ID
        notes.append("No calibration_artifact_id was supplied; bundled calibrated example profile was used.")
    if not use_calibrated:
        artifact_id = artifact_id or PUBLIC_PROXY_ARTIFACT_ID

    try:
        profile = load_process_calibration_profile(artifact_id)
    except FileNotFoundError as exc:
        profile = load_process_calibration_profile(PUBLIC_PROXY_ARTIFACT_ID)
        notes.append(f"{exc}; public proxy profile was used instead.")

    if use_calibrated and profile.model_mode != "calibrated":
        notes.append("Requested calibrated mode, but selected artifact is not calibrated.")
    if not use_calibrated and profile.model_mode == "calibrated":
        notes.append("A calibrated artifact was supplied while calculation_mode is proxy/auto.")

    return profile, notes
