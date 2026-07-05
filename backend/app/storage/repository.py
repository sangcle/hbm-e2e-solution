import json
import os
import re
from pathlib import Path
from typing import Any

from backend.app.domain.candidate import DesignCandidate, SimulateRequest
from backend.app.domain.metadata import RunMetadata

from .atomic_write import atomic_write_text


RUN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{8,80}$")


class ResultRepository:
    def __init__(self, results_root: Path | None = None) -> None:
        configured_root = os.getenv("HBM_E2E_RESULTS_DIR")
        default_root = Path(configured_root) if configured_root else Path(__file__).resolve().parents[3] / "results"
        self.results_root = (results_root or default_root).resolve()
        self.results_root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        request: SimulateRequest,
        result: DesignCandidate,
        report_markdown: str,
    ) -> None:
        run_dir = self.run_dir(result.run_id)
        atomic_write_text(run_dir / "result.json", result.model_dump_json(indent=2))
        atomic_write_text(run_dir / "metadata.json", result.metadata.model_dump_json(indent=2))
        atomic_write_text(run_dir / "input.json", request.model_dump_json(indent=2))
        atomic_write_text(run_dir / "report.md", report_markdown)
        self._upsert_index(result.metadata, result)

    def load_result(self, run_id: str) -> dict[str, Any]:
        path = self.run_dir(run_id) / "result.json"
        if not path.exists():
            raise FileNotFoundError(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def load_report(self, run_id: str) -> str:
        path = self.run_dir(run_id) / "report.md"
        if not path.exists():
            raise FileNotFoundError(run_id)
        return path.read_text(encoding="utf-8")

    def list_backend_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        backend_dir = self._backend_dir(run_id)
        if not backend_dir.exists():
            return []
        artifacts = []
        for path in sorted(item for item in backend_dir.rglob("*") if item.is_file()):
            relative = path.relative_to(backend_dir).as_posix()
            artifacts.append(
                {
                    "name": relative,
                    "size_bytes": path.stat().st_size,
                }
            )
        return artifacts

    def load_backend_artifact(self, run_id: str, artifact_path: str) -> tuple[str, str]:
        backend_dir = self._backend_dir(run_id)
        normalized = Path(artifact_path)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError("Invalid artifact path")
        path = (backend_dir / normalized).resolve()
        if not str(path).startswith(str(backend_dir)):
            raise ValueError("Invalid artifact path")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(artifact_path)
        return path.read_text(encoding="utf-8", errors="replace"), path.name

    def list_runs(self) -> list[dict[str, Any]]:
        index = self.results_root / "runs.json"
        if not index.exists():
            return []
        return json.loads(index.read_text(encoding="utf-8"))

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.match(run_id):
            raise ValueError("Invalid run_id")
        run_dir = (self.results_root / run_id).resolve()
        if not str(run_dir).startswith(str(self.results_root)):
            raise ValueError("Invalid run path")
        return run_dir

    def _backend_dir(self, run_id: str) -> Path:
        backend_dir = (self.run_dir(run_id) / "backend").resolve()
        if not str(backend_dir).startswith(str(self.run_dir(run_id))):
            raise ValueError("Invalid backend path")
        return backend_dir

    def _upsert_index(self, metadata: RunMetadata, result: DesignCandidate) -> None:
        index_path = self.results_root / "runs.json"
        runs = self.list_runs()
        summary = {
            "run_id": metadata.run_id,
            "candidate_id": metadata.candidate_id,
            "created_at": metadata.created_at,
            "simulation_mode": metadata.simulation_mode.value,
            "status": metadata.status.value,
            "label": result.label,
            "generation": result.architecture.generation.value,
            "score": result.feasibility_score,
            "is_feasible": result.constraints.is_feasible,
        }
        runs = [item for item in runs if item["run_id"] != metadata.run_id]
        runs.insert(0, summary)
        atomic_write_text(index_path, json.dumps(runs[:100], indent=2))
