import importlib.metadata
import platform
import time
from datetime import datetime, timezone
from typing import Any

from backend.app.backends.ramulator2.adapter import Ramulator2Adapter
from backend.app.domain.candidate import CandidateInput, CompareRequest, CompareResponse, DesignCandidate, SimulateRequest
from backend.app.domain.enums import ConfidenceLevel, SimulationMode
from backend.app.domain.metadata import RunMetadata, RuntimeMetadata
from backend.app.domain.versions import (
    ASSUMPTION_VERSION,
    BACKEND_ADAPTER_VERSION,
    FORMULA_VERSION,
    MODEL_VERSION,
    PRESET_VERSION,
)
from backend.app.presets.preset_registry import (
    get_architecture_preset,
    get_assumption_preset,
    get_workload_preset,
)
from backend.app.reporting.markdown_report import render_markdown_report
from backend.app.storage.id_generator import stable_hash
from backend.app.storage.repository import ResultRepository

from .analytical_engine import AnalyticalEngine
from .constraint_evaluator import ConstraintEvaluator
from .recommendations import RecommendationEngine
from .scoring import ScoringEngine


class SimulationService:
    def __init__(self, repository: ResultRepository | None = None) -> None:
        self.repository = repository or ResultRepository()
        self.analytical_engine = AnalyticalEngine()
        self.ramulator2_adapter = Ramulator2Adapter()
        self.constraint_evaluator = ConstraintEvaluator()
        self.scoring_engine = ScoringEngine()
        self.recommendation_engine = RecommendationEngine()

    def run(self, request: SimulateRequest, persist: bool = True) -> DesignCandidate:
        start = time.perf_counter()
        architecture, workload, assumptions = self._resolve_input(request)
        candidate_id = self._candidate_id(request, architecture, workload, assumptions)
        run_id = self._run_id(request, candidate_id)

        if request.simulation_mode == SimulationMode.RAMULATOR2:
            backend_options = {
                **request.backend_options,
                "_backend_dir": str(self.repository.run_dir(run_id) / "backend"),
            }
            metrics = self.ramulator2_adapter.run_or_map(
                architecture=architecture,
                workload=workload,
                assumptions=assumptions,
                backend_options=backend_options,
                analytical_fallback=self.analytical_engine,
            )
        else:
            metrics = self.analytical_engine.run(architecture, workload, assumptions)

        metrics.backend_metadata.setdefault("confidence_level", assumptions.confidence_level.value)
        constraints = self.constraint_evaluator.evaluate(request.target, architecture, metrics)
        score, breakdown = self.scoring_engine.score(request.target, metrics, constraints)
        bottlenecks, recommendations = self.recommendation_engine.generate(request.target, metrics, constraints)

        created_at = datetime.now(timezone.utc).isoformat()
        metadata = RunMetadata(
            simulation_mode=request.simulation_mode,
            created_at=created_at,
            runtime=self._runtime_metadata(),
            run_id=run_id,
            candidate_id=candidate_id,
            duration_ms=(time.perf_counter() - start) * 1000.0,
        )
        label = request.candidate_label or request.architecture_preset or architecture.generation.value
        result = DesignCandidate(
            run_id=run_id,
            candidate_id=candidate_id,
            label=label,
            target=request.target,
            architecture=architecture,
            workload=workload,
            assumptions=assumptions,
            metrics=metrics,
            constraints=constraints,
            feasibility_score=score,
            score_breakdown=breakdown,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            metadata=metadata,
        )
        if persist:
            self.repository.save(request, result, render_markdown_report(result))
        return result

    def compare(self, request: CompareRequest) -> CompareResponse:
        results = []
        for index, candidate in enumerate(request.candidates):
            simulate_request = SimulateRequest(
                target=request.target,
                candidate_label=candidate.candidate_label or f"candidate-{index + 1}",
                architecture_preset=candidate.architecture_preset,
                architecture=candidate.architecture,
                workload_preset=candidate.workload_preset,
                workload=candidate.workload,
                assumption_preset=candidate.assumption_preset,
                simulation_mode=candidate.simulation_mode,
                backend_options=candidate.backend_options,
            )
            results.append(self.run(simulate_request, persist=True))
        results.sort(key=lambda item: (item.constraints.is_feasible, item.feasibility_score), reverse=True)
        return CompareResponse(results=results)

    def _resolve_input(self, request: CandidateInput):
        if request.architecture is not None:
            architecture = request.architecture.model_copy(deep=True)
        elif request.architecture_preset:
            architecture = get_architecture_preset(request.architecture_preset)
        else:
            architecture = get_architecture_preset("hbm3e_8hi_24gb")

        if request.workload is not None:
            workload = request.workload.model_copy(deep=True)
        elif request.workload_preset:
            workload = get_workload_preset(request.workload_preset)
        else:
            workload = get_workload_preset("ai_training")

        assumptions = get_assumption_preset(request.assumption_preset)
        return architecture, workload, assumptions

    def _candidate_id(self, request: SimulateRequest, architecture, workload, assumptions) -> str:
        payload: dict[str, Any] = {
            "architecture": architecture.model_dump(mode="json"),
            "workload": workload.model_dump(mode="json"),
            "assumptions": assumptions.model_dump(mode="json"),
            "model_version": MODEL_VERSION,
            "formula_version": FORMULA_VERSION,
            "preset_version": PRESET_VERSION,
            "assumption_version": ASSUMPTION_VERSION,
            "simulation_mode": request.simulation_mode.value,
            "backend_adapter_version": BACKEND_ADAPTER_VERSION,
        }
        return stable_hash(payload, "cand")

    def _run_id(self, request: SimulateRequest, candidate_id: str) -> str:
        payload: dict[str, Any] = {
            "target": request.target.model_dump(mode="json"),
            "candidate_id": candidate_id,
            "architecture_preset": request.architecture_preset,
            "workload_preset": request.workload_preset,
            "assumption_preset": request.assumption_preset,
            "simulation_mode": request.simulation_mode.value,
            "backend_options": request.backend_options,
            "model_version": MODEL_VERSION,
            "formula_version": FORMULA_VERSION,
            "preset_version": PRESET_VERSION,
            "assumption_version": ASSUMPTION_VERSION,
            "backend_adapter_version": BACKEND_ADAPTER_VERSION,
        }
        return stable_hash(payload, "run")

    def _runtime_metadata(self) -> RuntimeMetadata:
        dependency_versions = {}
        for name in ("fastapi", "pydantic", "uvicorn"):
            try:
                dependency_versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                dependency_versions[name] = "unknown"
        return RuntimeMetadata(
            python_version=platform.python_version(),
            dependency_versions=dependency_versions,
        )
