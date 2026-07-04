from typing import Protocol

from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.assumptions import SimulationAssumptions
from backend.app.domain.metrics import SimulationMetrics
from backend.app.domain.workload import WorkloadProfile


class MetricsBackend(Protocol):
    def run(
        self,
        architecture: HBMArchitecture,
        workload: WorkloadProfile,
        assumptions: SimulationAssumptions,
    ) -> SimulationMetrics:
        ...
