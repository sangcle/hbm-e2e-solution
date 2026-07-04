import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.enums import HBMGeneration
from backend.app.domain.workload import WorkloadProfile


@dataclass(frozen=True)
class Ramulator2PresetMapping:
    dram_class: str
    controller_class: str
    org_preset: str
    timing_preset: str
    frontend_clock_ratio: int
    scheduler_class: str
    refresh_manager_class: str
    addr_mapper_class: str
    channel_mapper_class: str
    mapping_notes: list[str]


def default_ramulator2_home() -> Path:
    configured = os.getenv("RAMULATOR2_HOME")
    if configured:
        return Path(configured).resolve()
    bundled = bundled_ramulator2_home()
    if (bundled / "python" / "ramulator").exists():
        return bundled
    return source_ramulator2_home()


def bundled_ramulator2_home() -> Path:
    return Path(__file__).resolve().parents[4] / "runtime" / "ramulator2"


def source_ramulator2_home() -> Path:
    return Path(__file__).resolve().parents[4] / "ramulator2"


def ramulator_python_path(ramulator_home: Path | None = None) -> Path:
    return (ramulator_home or default_ramulator2_home()).resolve() / "python"


def import_ramulator(ramulator_home: Path | None = None):
    python_path = str(ramulator_python_path(ramulator_home))
    if python_path not in sys.path:
        sys.path.insert(0, python_path)
    import ramulator  # type: ignore[import-not-found]

    return ramulator


def cpp_extension_available(ramulator_home: Path | None = None) -> tuple[bool, str | None]:
    try:
        import_ramulator(ramulator_home)
        import ramulator._ramulator  # type: ignore[import-not-found]  # noqa: F401
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def resolve_preset_mapping(
    architecture: HBMArchitecture,
    backend_options: dict[str, Any] | None = None,
) -> Ramulator2PresetMapping:
    options = backend_options or {}
    scheduler = str(options.get("scheduler_class", "FRFCFSRowHit"))
    refresh_enabled = bool(options.get("refresh_enabled", False))
    generation = architecture.generation
    notes: list[str] = []

    if generation in (HBMGeneration.HBM2E,):
        notes.append("HBM2E is approximated with the closest local Ramulator2 HBM2 preset.")
        org = _closest_hbm2_org(architecture)
        timing = _closest_timing(architecture.data_rate_gbps_per_pin, {
            "HBM2_1600Mbps": 1.6,
            "HBM2_2000Mbps": 2.0,
            "HBM2_2400Mbps": 2.4,
        }, notes)
        refresh = "AllBank" if refresh_enabled else "NoRefresh"
        return Ramulator2PresetMapping(
            dram_class="HBM2",
            controller_class="HBM12",
            org_preset=org,
            timing_preset=timing,
            frontend_clock_ratio=4,
            scheduler_class=scheduler,
            refresh_manager_class=refresh,
            addr_mapper_class="RoBaRaCoCh",
            channel_mapper_class="CacheLineInterleave",
            mapping_notes=notes,
        )

    if generation in (HBMGeneration.HBM3, HBMGeneration.HBM3E):
        if generation == HBMGeneration.HBM3E:
            notes.append("HBM3E is approximated with local Ramulator2 HBM3 device/timing presets.")
        org = _closest_hbm3_org(architecture, notes)
        timing = "HBM3_6400Mbps"
        if architecture.data_rate_gbps_per_pin > 6.4:
            notes.append("Data rate is capped to HBM3_6400Mbps in Ramulator2; analytical bandwidth still uses the candidate data rate.")
        refresh = "HBM34PerBankRefresh" if refresh_enabled else "NoRefresh"
        return Ramulator2PresetMapping(
            dram_class="HBM3",
            controller_class="HBM34",
            org_preset=org,
            timing_preset=timing,
            frontend_clock_ratio=16,
            scheduler_class=scheduler,
            refresh_manager_class=refresh,
            addr_mapper_class="RoBaRaCoCh",
            channel_mapper_class="CacheLineInterleave",
            mapping_notes=notes,
        )

    if generation == HBMGeneration.HBM4:
        org = _closest_hbm4_org(architecture)
        timing = _closest_timing(architecture.data_rate_gbps_per_pin, {
            "HBM4_8000Mbps": 8.0,
            "HBM4_16000Mbps": 16.0,
        }, notes)
        refresh = "HBM34PerBankRefresh" if refresh_enabled else "NoRefresh"
        return Ramulator2PresetMapping(
            dram_class="HBM4",
            controller_class="HBM34",
            org_preset=org,
            timing_preset=timing,
            frontend_clock_ratio=16,
            scheduler_class=scheduler,
            refresh_manager_class=refresh,
            addr_mapper_class="RoBaRaCoCh",
            channel_mapper_class="CacheLineInterleave",
            mapping_notes=notes,
        )

    raise ValueError(f"Ramulator2 mapping is not available for generation {generation}")


def build_ramulator2_config(
    architecture: HBMArchitecture,
    workload: WorkloadProfile,
    trace_path: Path,
    backend_options: dict[str, Any] | None = None,
    ramulator_home: Path | None = None,
):
    options = backend_options or {}
    ramulator = import_ramulator(ramulator_home)
    mapping = resolve_preset_mapping(architecture, options)
    frontend_kind = str(options.get("frontend", "load_store_trace"))

    dram_cls = getattr(ramulator.dram, mapping.dram_class)
    scheduler_cls = getattr(ramulator.scheduler, mapping.scheduler_class)
    refresh_cls = getattr(ramulator.refresh_manager, mapping.refresh_manager_class)
    ctrl_cls = getattr(ramulator.controller, mapping.controller_class)

    max_controllers = int(options.get("max_controllers", 4))
    requested_controllers = architecture.stack_count * architecture.channel_count_per_stack
    controller_count = max(1, min(requested_controllers, max_controllers))

    def make_dram():
        return dram_cls(org_preset=mapping.org_preset, timing_preset=mapping.timing_preset)

    def make_controller(addr_mapper):
        return ctrl_cls(
            dram=make_dram(),
            scheduler=scheduler_cls(),
            row_policy=ramulator.row_policy.Open(),
            addr_mapper=addr_mapper,
            refresh_manager=refresh_cls(),
            read_buffer_size=int(options.get("read_buffer_size", 128)),
            write_buffer_size=int(options.get("write_buffer_size", 64)),
        )

    if frontend_kind == "latency_throughput":
        sample_dram = make_dram()
        layout = extract_dram_layout(sample_dram)
        frontend = ramulator.frontend.LatencyThroughputTrace(
            clock_ratio=int(options.get("frontend_clock_ratio", mapping.frontend_clock_ratio)),
            nop_counter=int(options.get("nop_counter", 20)),
            num_probe_requests=int(options.get("num_probe_requests", 2048)),
            latency_sample_count=int(options.get("latency_sample_count", 2048)),
            num_streaming_requests=int(options.get("num_streaming_requests", 0)),
            streaming_only=bool(options.get("streaming_only", False)),
            warmup_cycles=int(options.get("warmup_cycles", 1000)),
            seed=int(options.get("seed", 12345)),
            read_ratio=int(round(workload.read_ratio * 100)),
            stream_cls=int(options.get("stream_cls", layout["num_cls"])),
            stagger_stream_rows=bool(options.get("stagger_stream_rows", True)),
            **layout,
        )
        addr_mapper = ramulator.addr_mapper.PassThroughAddrMapper()
        channel_mapper = ramulator.channel_mapper.PassThroughChannelMapper()
        controller_count = 1
    else:
        frontend = ramulator.frontend.LoadStoreTrace(
            clock_ratio=int(options.get("frontend_clock_ratio", mapping.frontend_clock_ratio)),
            path=str(trace_path.resolve()),
        )
        addr_mapper = getattr(ramulator.addr_mapper, mapping.addr_mapper_class)()
        channel_mapper = getattr(ramulator.channel_mapper, mapping.channel_mapper_class)()

    controllers = [make_controller(addr_mapper) for _ in range(controller_count)]
    mem = ramulator.memory_system.GenericDRAM(
        clock_ratio=int(options.get("memory_clock_ratio", 1)),
        controllers=controllers,
        channel_mapper=channel_mapper,
    )

    config = {"frontend": frontend.to_config(), "memory_system": mem.to_config()}
    metadata = {
        "ramulator_home": str((ramulator_home or default_ramulator2_home()).resolve()),
        "ramulator_python_path": str(ramulator_python_path(ramulator_home)),
        "frontend": frontend_kind,
        "requested_controller_count": requested_controllers,
        "simulated_controller_count": controller_count,
        "controller_scale_factor": requested_controllers / controller_count,
        "mapping": asdict(mapping),
    }
    return config, metadata


def write_config_artifacts(config: dict[str, Any], backend_dir: Path) -> None:
    backend_dir.mkdir(parents=True, exist_ok=True)
    (backend_dir / "ramulator_config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )
    try:
        ramulator = import_ramulator()
        yaml_text = ramulator.export.dict_to_yaml(config)
    except Exception:
        yaml_text = _simple_yaml(config)
    (backend_dir / "ramulator_config.yaml").write_text(yaml_text, encoding="utf-8")


def write_runner_script(backend_dir: Path) -> None:
    project_root = Path(__file__).resolve().parents[4]
    ramulator_home = default_ramulator2_home()
    payload_path = (backend_dir / "ramulator_hbm_input.json").resolve()
    stats_json_path = (backend_dir / "sim.stats.json").resolve()
    stats_yaml_path = (backend_dir / "sim.stats.yaml").resolve()
    script = f"""import sys

sys.path.insert(0, r"{project_root}")
sys.path.insert(0, r"{ramulator_python_path(ramulator_home)}")

from backend.app.backends.ramulator2.runner import run_payload_file

run_payload_file(
    r"{payload_path}",
    r"{stats_json_path}",
    r"{stats_yaml_path}",
)
"""
    (backend_dir / "run_ramulator2.py").write_text(script, encoding="utf-8")


def extract_dram_layout(dram) -> dict[str, Any]:
    cls = type(dram)
    level_names = list(cls.levels.keys())
    org_dict, _ = dram.resolve()
    org_counts = [org_dict.get(name.lower(), 1) for name in level_names]
    row_idx = level_names.index("Row")
    col_idx = level_names.index("Column")
    bank_positions = list(range(1, row_idx))
    bank_counts = [org_counts[i] for i in bank_positions]

    if "BankGroup" in level_names:
        bg_idx = level_names.index("BankGroup") - 1
        if bg_idx < len(bank_positions) - 1:
            pos = bank_positions.pop(bg_idx)
            cnt = bank_counts.pop(bg_idx)
            bank_positions.append(pos)
            bank_counts.append(cnt)

    if "PseudoChannel" in level_names:
        pc_idx = [i for i, pos in enumerate(bank_positions) if pos == level_names.index("PseudoChannel")][0]
        pos = bank_positions.pop(pc_idx)
        cnt = bank_counts.pop(pc_idx)
        bank_positions.append(pos)
        bank_counts.append(cnt)

    total_bank_units = 1
    for count in bank_counts:
        total_bank_units *= count

    internal_prefetch_size = cls.internal_prefetch_size
    num_cols = org_counts[col_idx]
    return {
        "addr_vec_size": len(level_names),
        "bank_positions": bank_positions,
        "bank_counts": bank_counts,
        "total_bank_units": total_bank_units,
        "row_pos": row_idx,
        "col_pos": col_idx,
        "num_rows": org_counts[row_idx],
        "num_cols": num_cols,
        "internal_prefetch_size": internal_prefetch_size,
        "num_cls": num_cols // internal_prefetch_size,
    }


def _closest_hbm2_org(architecture: HBMArchitecture) -> str:
    die_gb = architecture.die_capacity_gb * 8
    choices = {"HBM2_1Gb": 1.0, "HBM2_2Gb": 2.0, "HBM2_4Gb": 4.0, "HBM2_8Gb": 8.0}
    return min(choices, key=lambda key: abs(choices[key] - die_gb))


def _closest_hbm3_org(architecture: HBMArchitecture, notes: list[str]) -> str:
    die_gb = architecture.die_capacity_gb * 8
    choices = {
        "HBM3_4Gb": (4.0, 4),
        "HBM3_8Gb_8hi": (8.0, 8),
        "HBM3_16Gb_8hi": (16.0, 8),
        "HBM3_32Gb_8hi": (32.0, 8),
        "HBM3_32Gb_16hi": (32.0, 16),
    }
    selected = min(
        choices,
        key=lambda key: abs(choices[key][0] - die_gb) + abs(choices[key][1] - architecture.stack_height) * 2,
    )
    if choices[selected][1] != architecture.stack_height:
        notes.append(f"Stack height {architecture.stack_height} is approximated with {choices[selected][1]}Hi Ramulator2 org preset.")
    return selected


def _closest_hbm4_org(architecture: HBMArchitecture) -> str:
    choices = {"HBM4_32Gb_4Hi": 4, "HBM4_32Gb_8Hi": 8, "HBM4_32Gb_16Hi": 16}
    return min(choices, key=lambda key: abs(choices[key] - architecture.stack_height))


def _closest_timing(data_rate_gbps: float, choices: dict[str, float], notes: list[str]) -> str:
    selected = min(choices, key=lambda key: abs(choices[key] - data_rate_gbps))
    if abs(choices[selected] - data_rate_gbps) > 0.05:
        notes.append(f"Data rate {data_rate_gbps:g} Gb/s is approximated with {selected}.")
    return selected


def _simple_yaml(data: Any, indent: int = 0) -> str:
    prefix = "  " * indent
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_simple_yaml(value, indent + 1).rstrip())
            else:
                lines.append(f"{prefix}{key}: {json.dumps(value)}")
        return "\n".join(lines) + "\n"
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_simple_yaml(item, indent + 1).rstrip())
            else:
                lines.append(f"{prefix}- {json.dumps(item)}")
        return "\n".join(lines) + "\n"
    return f"{prefix}{json.dumps(data)}\n"
