from enum import StrEnum


class HBMGeneration(StrEnum):
    HBM2E = "hbm2e"
    HBM3 = "hbm3"
    HBM3E = "hbm3e"
    HBM4 = "hbm4"
    CUSTOM = "custom"


class SimulationMode(StrEnum):
    ANALYTICAL = "analytical"
    RAMULATOR2 = "ramulator2"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceType(StrEnum):
    PUBLIC_VENDOR = "public_vendor"
    LITERATURE_PROXY = "literature_proxy"
    PROXY = "proxy"
    NEUTRAL_DEFAULT = "neutral_default"
    INTERNAL_MEASUREMENT = "internal_measurement"


class ConstraintPolicy(StrEnum):
    IGNORE = "ignore"
    WARN = "warn"
    HARD_LIMIT = "hard_limit"


class Priority(StrEnum):
    BALANCED = "balanced"
    BANDWIDTH_FIRST = "bandwidth_first"
    POWER_FIRST = "power_first"
    CAPACITY_FIRST = "capacity_first"
    LATENCY_FIRST = "latency_first"


class TrafficLimitedBy(StrEnum):
    MEMORY = "memory"
    DEMAND = "demand"
    BENCHMARK = "benchmark"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
