from typing import Any

from pydantic import BaseModel, Field

from .assumptions import AssumptionCoverage
from .enums import TrafficLimitedBy


class SimulationMetrics(BaseModel):
    raw_capacity_gb: float
    usable_capacity_gb: float

    raw_peak_bandwidth_GBps: float
    sustained_peak_bandwidth_GBps: float
    effective_utilization: float
    effective_bandwidth_GBps: float
    offered_bandwidth_GBps: float
    achieved_bandwidth_GBps: float
    demand_satisfaction_ratio: float
    bandwidth_utilization: float
    effective_to_sustained_efficiency: float
    traffic_limited_by: TrafficLimitedBy

    average_latency_ns: float
    p50_latency_ns: float
    p95_latency_ns: float
    p99_latency_ns: float
    latency_histogram: list[dict[str, float]] | None = None

    dynamic_power_w: float
    static_power_w: float
    logic_power_w: float
    total_power_w: float
    estimated_temperature_c: float
    thermal_margin_c: float | None = None
    thermal_throttle_factor: float = Field(1.0, ge=0, le=1)

    row_hit_rate: float | None = None
    read_request_count: int | None = None
    write_request_count: int | None = None
    simulated_cycles: int | None = None

    assumption_coverage: AssumptionCoverage
    backend_metadata: dict[str, Any] = Field(default_factory=dict)


class Recommendation(BaseModel):
    code: str
    severity: str
    message: str
    related_metrics: dict[str, float | str | bool | None] = Field(default_factory=dict)
    suggested_actions: list[str] = Field(default_factory=list)
