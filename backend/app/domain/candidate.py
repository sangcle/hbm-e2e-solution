from typing import Any

from pydantic import BaseModel, Field

from .architecture import HBMArchitecture
from .assumptions import SimulationAssumptions
from .constraints import ConstraintResult
from .enums import SimulationMode
from .metadata import RunMetadata
from .metrics import Recommendation, SimulationMetrics
from .process import ProcessParameters
from .target import ProductTarget
from .workload import WorkloadProfile


class CandidateInput(BaseModel):
    candidate_label: str | None = None
    architecture_preset: str | None = None
    architecture: HBMArchitecture | None = None
    workload_preset: str | None = None
    workload: WorkloadProfile | None = None
    assumption_preset: str = "public_hbm_mvp_v0"
    simulation_mode: SimulationMode = SimulationMode.ANALYTICAL
    backend_options: dict[str, Any] = Field(default_factory=dict)
    process_parameters: ProcessParameters | None = None


class SimulateRequest(CandidateInput):
    target: ProductTarget = Field(default_factory=ProductTarget)


class CompareRequest(BaseModel):
    target: ProductTarget = Field(default_factory=ProductTarget)
    candidates: list[CandidateInput] = Field(min_length=1)


class DesignCandidate(BaseModel):
    run_id: str
    candidate_id: str
    label: str
    target: ProductTarget
    architecture: HBMArchitecture
    workload: WorkloadProfile
    assumptions: SimulationAssumptions
    metrics: SimulationMetrics
    constraints: ConstraintResult
    feasibility_score: float
    score_breakdown: dict[str, float]
    bottlenecks: list[str]
    recommendations: list[Recommendation]
    metadata: RunMetadata


class CompareResponse(BaseModel):
    results: list[DesignCandidate]
