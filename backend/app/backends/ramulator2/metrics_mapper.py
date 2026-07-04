from typing import Any

from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.metrics import SimulationMetrics


def map_stats_to_metrics(
    baseline: SimulationMetrics,
    stats: dict[str, Any],
    architecture: HBMArchitecture,
) -> SimulationMetrics:
    updates: dict[str, Any] = {
        "backend_metadata": {
            **baseline.backend_metadata,
            "backend": "ramulator2",
            "stats_schema_detected": stats.get("stats_schema_detected", "unknown"),
            "interface": "stats_adapter",
            "runner": "local",
        }
    }

    read_reqs = _int_or_none(stats.get("read_reqs"))
    write_reqs = _int_or_none(stats.get("write_reqs"))
    cycles = _int_or_none(stats.get("cycles"))
    if read_reqs is not None:
        updates["read_request_count"] = read_reqs
    if write_reqs is not None:
        updates["write_request_count"] = write_reqs
    if cycles is not None:
        updates["simulated_cycles"] = cycles

    row_hits = _float(stats.get("row_hits"))
    row_misses = _float(stats.get("row_misses"))
    row_conflicts = _float(stats.get("row_conflicts"))
    row_total = row_hits + row_misses + row_conflicts
    if row_total > 0:
        updates["row_hit_rate"] = row_hits / row_total

    avg_latency_ns = _float(stats.get("avg_read_latency_ns"))
    if avg_latency_ns <= 0 and _float(stats.get("avg_read_latency")) > 0:
        tck_ps = _float(stats.get("tck_ps")) or _resolve_tck_ps(architecture)
        avg_latency_ns = _float(stats.get("avg_read_latency")) * tck_ps / 1000.0
    if avg_latency_ns > 0:
        updates["average_latency_ns"] = avg_latency_ns
        updates["p50_latency_ns"] = avg_latency_ns
        updates["p95_latency_ns"] = avg_latency_ns * 1.35
        updates["p99_latency_ns"] = avg_latency_ns * 1.65
        updates["latency_histogram"] = [
            {"percentile": 50, "latency_ns": avg_latency_ns},
            {"percentile": 95, "latency_ns": avg_latency_ns * 1.35},
            {"percentile": 99, "latency_ns": avg_latency_ns * 1.65},
        ]

    return baseline.model_copy(update=updates)


def _resolve_tck_ps(architecture: HBMArchitecture) -> float:
    if architecture.backend_tck_ps:
        return architecture.backend_tck_ps
    return 1000.0 / architecture.data_rate_gbps_per_pin


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _int_or_none(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
