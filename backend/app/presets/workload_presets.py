from backend.app.domain.workload import WorkloadProfile


WORKLOAD_PRESETS: dict[str, WorkloadProfile] = {
    "ai_training": WorkloadProfile(
        workload_id="ai_training",
        name="AI Training",
        bandwidth_demand_GBps=3200.0,
        read_ratio=0.68,
        write_ratio=0.32,
        sequential_ratio=0.42,
        random_ratio=0.58,
        row_buffer_locality=0.58,
        burstiness=0.48,
        concurrency=512,
        working_set_size_gb=160.0,
        channel_balance=0.92,
        bank_parallelism=0.90,
        pseudo_channel_balance=0.92,
        tail_latency_sensitivity=0.60,
    ),
    "ai_inference": WorkloadProfile(
        workload_id="ai_inference",
        name="AI Inference",
        bandwidth_demand_GBps=1400.0,
        read_ratio=0.82,
        write_ratio=0.18,
        sequential_ratio=0.62,
        random_ratio=0.38,
        row_buffer_locality=0.70,
        burstiness=0.30,
        concurrency=192,
        working_set_size_gb=48.0,
        channel_balance=0.94,
        bank_parallelism=0.88,
        pseudo_channel_balance=0.94,
        tail_latency_sensitivity=0.45,
    ),
    "hpc_stream": WorkloadProfile(
        workload_id="hpc_stream",
        name="HPC Stream",
        bandwidth_demand_GBps=2200.0,
        read_ratio=0.55,
        write_ratio=0.45,
        sequential_ratio=0.86,
        random_ratio=0.14,
        row_buffer_locality=0.78,
        burstiness=0.18,
        concurrency=256,
        working_set_size_gb=96.0,
        channel_balance=0.96,
        bank_parallelism=0.92,
        pseudo_channel_balance=0.96,
        tail_latency_sensitivity=0.30,
    ),
    "graph_analytics": WorkloadProfile(
        workload_id="graph_analytics",
        name="Graph Analytics",
        bandwidth_demand_GBps=900.0,
        read_ratio=0.76,
        write_ratio=0.24,
        sequential_ratio=0.20,
        random_ratio=0.80,
        row_buffer_locality=0.28,
        burstiness=0.62,
        concurrency=384,
        working_set_size_gb=128.0,
        channel_balance=0.78,
        bank_parallelism=0.80,
        pseudo_channel_balance=0.86,
        tail_latency_sensitivity=0.85,
    ),
}


def get_workload_preset(preset_id: str) -> WorkloadProfile:
    try:
        return WORKLOAD_PRESETS[preset_id].model_copy(deep=True)
    except KeyError as exc:
        raise KeyError(f"Unknown workload preset: {preset_id}") from exc
