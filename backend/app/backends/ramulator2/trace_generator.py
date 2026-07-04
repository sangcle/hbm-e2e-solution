import random
from pathlib import Path

from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.workload import WorkloadProfile


def generate_load_store_trace(
    architecture: HBMArchitecture,
    workload: WorkloadProfile,
    path: Path,
    request_count: int = 4096,
    seed: int = 12345,
) -> dict[str, int | float | str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    request_size = max(1, workload.request_size_bytes)
    raw_capacity_bytes = max(1, int((architecture.total_capacity_gb or 1.0) * 1_000_000_000))
    working_set_bytes = max(1, int(max(0.001, workload.working_set_size_gb) * 1_000_000_000))
    address_space = max(request_size, min(raw_capacity_bytes, working_set_bytes))
    address_space -= address_space % request_size
    address_space = max(request_size, address_space)

    current_address = 0
    read_count = 0
    write_count = 0
    with path.open("w", encoding="utf-8") as trace_file:
        for _ in range(request_count):
            is_read = rng.random() <= workload.read_ratio
            if is_read:
                op = "LD"
                read_count += 1
            else:
                op = "ST"
                write_count += 1

            locality_roll = rng.random()
            if locality_roll <= workload.sequential_ratio or locality_roll <= workload.row_buffer_locality:
                current_address = (current_address + request_size) % address_space
            else:
                current_address = rng.randrange(0, address_space, request_size)
            trace_file.write(f"{op} 0x{current_address:x}\n")

    return {
        "path": str(path),
        "request_count": request_count,
        "read_count": read_count,
        "write_count": write_count,
        "request_size_bytes": request_size,
        "address_space_bytes": address_space,
        "seed": seed,
    }
