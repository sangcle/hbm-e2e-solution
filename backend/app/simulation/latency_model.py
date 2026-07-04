from backend.app.domain.assumptions import SimulationAssumptions
from backend.app.domain.workload import WorkloadProfile

from .math_utils import safe_div


def calculate_latency(
    workload: WorkloadProfile,
    assumptions: SimulationAssumptions,
    achieved_bandwidth_GBps: float,
    effective_bandwidth_GBps: float,
) -> dict[str, float | list[dict[str, float]]]:
    row_miss_rate = 1.0 - workload.row_buffer_locality
    queue_penalty_ns = assumptions.queue_latency_ns_per_128_concurrency * workload.concurrency / 128.0
    burst_penalty_ns = workload.burstiness * 10.0
    load_factor = safe_div(achieved_bandwidth_GBps, max(1.0, effective_bandwidth_GBps), default=0.0)
    if load_factor < 0.70:
        saturation_penalty_ns = 0.0
    else:
        saturation_penalty_ns = assumptions.saturation_coefficient_ns * ((load_factor - 0.70) / 0.30) ** 2

    average_latency_ns = (
        assumptions.latency_base_ns
        + row_miss_rate * assumptions.row_miss_penalty_ns
        + queue_penalty_ns
        + burst_penalty_ns
        + saturation_penalty_ns
    )
    p95 = average_latency_ns * (1.25 + workload.tail_latency_sensitivity * 0.25)
    p99 = average_latency_ns * (1.50 + workload.tail_latency_sensitivity * 0.50)
    histogram = [
        {"percentile": 50, "latency_ns": average_latency_ns},
        {"percentile": 95, "latency_ns": p95},
        {"percentile": 99, "latency_ns": p99},
    ]
    return {
        "average_latency_ns": average_latency_ns,
        "p50_latency_ns": average_latency_ns,
        "p95_latency_ns": p95,
        "p99_latency_ns": p99,
        "latency_histogram": histogram,
    }
