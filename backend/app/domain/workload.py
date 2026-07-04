from pydantic import BaseModel, Field, model_validator


class WorkloadProfile(BaseModel):
    workload_id: str = "custom"
    name: str = "Custom"
    bandwidth_demand_GBps: float = Field(1200.0, ge=0)
    read_ratio: float = Field(0.7, ge=0, le=1)
    write_ratio: float = Field(0.3, ge=0, le=1)
    sequential_ratio: float = Field(0.5, ge=0, le=1)
    random_ratio: float = Field(0.5, ge=0, le=1)
    row_buffer_locality: float = Field(0.55, ge=0, le=1)
    burstiness: float = Field(0.35, ge=0, le=1)
    concurrency: int = Field(256, ge=1)
    request_size_bytes: int = Field(128, ge=1)
    working_set_size_gb: float = Field(64.0, ge=0)
    channel_balance: float = Field(0.9, ge=0.1, le=1.0)
    bank_parallelism: float = Field(0.9, ge=0.1, le=1.0)
    pseudo_channel_balance: float = Field(0.92, ge=0.1, le=1.0)
    tail_latency_sensitivity: float = Field(0.5, ge=0, le=1)

    @model_validator(mode="after")
    def validate_ratios(self) -> "WorkloadProfile":
        if abs((self.read_ratio + self.write_ratio) - 1.0) > 1e-6:
            raise ValueError("read_ratio + write_ratio must equal 1.0")
        if abs((self.sequential_ratio + self.random_ratio) - 1.0) > 1e-6:
            raise ValueError("sequential_ratio + random_ratio must equal 1.0")
        return self
