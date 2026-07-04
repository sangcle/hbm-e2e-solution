from pathlib import Path
from typing import Any

from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.assumptions import SimulationAssumptions
from backend.app.domain.metrics import SimulationMetrics
from backend.app.domain.workload import WorkloadProfile

from .metrics_mapper import map_stats_to_metrics
from .runner import LocalRamulator2Runner
from .stats_parser import parse_stats_file, parse_stats_payload, parse_stats_text


class Ramulator2Adapter:
    def __init__(self, runner: LocalRamulator2Runner | None = None) -> None:
        self.runner = runner or LocalRamulator2Runner()

    def run_or_map(
        self,
        architecture: HBMArchitecture,
        workload: WorkloadProfile,
        assumptions: SimulationAssumptions,
        backend_options: dict[str, Any],
        analytical_fallback,
    ) -> SimulationMetrics:
        baseline = analytical_fallback.run(architecture, workload, assumptions)
        stats: dict[str, Any] | None = None
        backend_metadata: dict[str, Any] = {
            **baseline.backend_metadata,
            "backend": "ramulator2",
            "runner": "adapter",
        }

        if "stats_payload" in backend_options:
            stats = parse_stats_payload(backend_options["stats_payload"])
            backend_metadata["status"] = "mapped_from_stats_payload"
        elif "stats_text" in backend_options:
            stats = parse_stats_text(str(backend_options["stats_text"]))
            backend_metadata["status"] = "mapped_from_stats_text"
        elif "stats_path" in backend_options:
            stats_path = Path(str(backend_options["stats_path"]))
            stats = parse_stats_file(stats_path)
            backend_metadata["status"] = "mapped_from_stats_path"
        else:
            backend_dir_value = backend_options.get("_backend_dir")
            if backend_dir_value is not None:
                run_result = self.runner.run(
                    architecture=architecture,
                    workload=workload,
                    backend_options=backend_options,
                    backend_dir=Path(str(backend_dir_value)),
                )
                backend_metadata.update(run_result.metadata)
                backend_metadata["status"] = run_result.status
                backend_metadata["artifacts"] = run_result.artifacts
                if run_result.error:
                    backend_metadata["error"] = run_result.error
                stats = run_result.stats

        if stats is None:
            backend_metadata.setdefault("status", "analytical_fallback_no_stats")
            return baseline.model_copy(update={"backend_metadata": backend_metadata})

        mapped = map_stats_to_metrics(baseline, stats, architecture)
        return mapped.model_copy(
            update={
                "backend_metadata": {
                    **mapped.backend_metadata,
                    **backend_metadata,
                }
            }
        )
