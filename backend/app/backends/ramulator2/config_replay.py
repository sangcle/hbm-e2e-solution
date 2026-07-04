import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


TIMING_PARAMS = {
    "HBM2": [
        "rate", "nBL", "nCL", "nRCDRD", "nRCDWR",
        "nRP", "nRAS", "nRC", "nWR", "nRTPL", "nCWL",
        "nCCDS", "nCCDL", "nRRDS", "nRRDL",
        "nWTRS", "nWTRL",
        "nFAW", "nRFC", "nRFCpb", "nRREFD",
        "nREFI", "nREFIpb",
        "tCK_ps",
    ],
    "HBM3": [
        "rate", "nBL", "nCL", "nRCDRD", "nRCDWR",
        "nRP", "nRAS", "nRC", "nWR", "nRTP", "nCWL",
        "nCCDS", "nCCDL", "nCCDR", "nRRDS", "nRRDL",
        "nWTRS", "nWTRL", "nRTW",
        "nFAW", "nPPD",
        "nRFC", "nRFCpb", "nRFMab", "nRFMpb",
        "nRREFD",
        "nREFI", "nREFIpb",
        "tCK_ps",
    ],
    "HBM4": [
        "rate", "nBL", "nCL", "nRCDRD", "nRCDWR",
        "nRP", "nRAS", "nRC", "nWR", "nRTP", "nCWL",
        "nCCDS", "nCCDL", "nCCDR", "nRRDS", "nRRDL",
        "nWTRS", "nWTRL", "nRTW",
        "nFAW", "nPPD",
        "nRFC", "nRFCpb", "nRFMab", "nRFMpb",
        "nRREFD",
        "nREFI", "nREFIpb",
        "tCK_ps",
    ],
}


def replay_config_trace(
    config: dict[str, Any],
    trace_path: Path,
    stats_json_path: Path,
    stats_yaml_path: Path,
) -> dict[str, Any]:
    """Generate Ramulator2-shaped stats from the generated config and trace.

    This is not a replacement for the compiled Ramulator2 backend. It is a
    deterministic timing replay fallback used when ramulator._ramulator is
    unavailable. It reads the expanded Ramulator2 DRAM config and applies a
    small open-row scheduler with ACT/PRE/CAS timing so the E2E pipeline still
    produces inspectable backend evidence.
    """
    controllers = config["memory_system"].get("controllers", [])
    controller_count = max(1, len(controllers))
    controller_states = [_new_controller_state(index, controllers[index]) for index in range(controller_count)]
    arrival_interval = max(1, int(config.get("frontend", {}).get("clock_ratio", 1)))
    for state in controller_states:
        state["timing"]["arrival_interval"] = float(arrival_interval)

    requests = _read_load_store_trace(trace_path)
    for index, request in enumerate(requests):
        controller_index = _controller_index(request["address"], controller_count)
        _apply_request(controller_states[controller_index], request)

    controller_stats = [_finalize_controller_state(state) for state in controller_states]
    total_reads = sum(item["num_read_reqs"] for item in controller_stats)
    total_writes = sum(item["num_write_reqs"] for item in controller_stats)
    stats = {
        "frontend": {
            "impl": config["frontend"].get("impl", "unknown"),
            "trace_path": str(trace_path),
            "num_trace_requests": len(requests),
        },
        "memory_system": {
            "impl": config["memory_system"].get("impl", "GenericDRAM"),
            "total_num_read_requests": total_reads,
            "total_num_write_requests": total_writes,
            "controller": controller_stats[0] if len(controller_stats) == 1 else controller_stats,
        },
        "backend": {
            "impl": "python_timing_replay",
            "cycle_accurate": False,
            "source": "ramulator2_config_and_trace",
            "timing_source": "expanded_ramulator2_config",
        },
    }
    stats_json_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    if yaml is not None:
        stats_yaml_path.write_text(yaml.safe_dump(stats, sort_keys=False), encoding="utf-8")
    else:
        stats_yaml_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def _new_controller_state(index: int, controller: dict[str, Any]) -> dict[str, Any]:
    dram = controller.get("dram", {})
    timing = _timing_map(dram)
    org_count = dram.get("org", {}).get("count", [1, 1, 1, 1, 1, 16384, 256])
    num_rows = max(1, int(org_count[-2])) if len(org_count) >= 2 else 16384
    num_cols = max(1, int(org_count[-1])) if org_count else 256
    bank_counts = [max(1, int(value)) for value in org_count[1:-2]] or [1]
    total_banks = 1
    for count in bank_counts:
        total_banks *= count
    read_latency_ticks = float(dram.get("read_latency", timing.get("nCL", 40) + timing.get("nBL", 4)))
    tick_ps = float(timing.get("tCK_ps", 1000.0))
    return {
        "id": f"Channel {index}",
        "num_rows": num_rows,
        "num_cols": num_cols,
        "total_banks": total_banks,
        "timing": timing,
        "read_latency_ticks": read_latency_ticks,
        "tick_ps": tick_ps,
        "open_rows": {},
        "bank_ready": {},
        "next_act_cycle": 0,
        "next_col_cycle": 0,
        "read_reqs": 0,
        "write_reqs": 0,
        "row_hits": 0,
        "row_misses": 0,
        "row_conflicts": 0,
        "cycles": 0,
        "read_latency_accum": 0.0,
        "max_queue_depth": 0,
    }


def _read_load_store_trace(path: Path) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid trace line {line_number}: expected '<LD|ST> <address>'")
        op, raw_address = parts
        if op not in {"LD", "ST"}:
            raise ValueError(f"Invalid trace op on line {line_number}: {op}")
        requests.append(
            {
                "is_write": op == "ST",
                "address": int(raw_address, 0),
            }
        )
    return requests


def _controller_index(address: int, controller_count: int) -> int:
    cache_line = max(0, address // 64)
    return cache_line % controller_count


def _apply_request(state: dict[str, Any], request: dict[str, Any]) -> None:
    line = max(0, request["address"] // 64)
    column = line % state["num_cols"]
    row_linear = line // state["num_cols"]
    bank = row_linear % state["total_banks"]
    row = (row_linear // state["total_banks"]) % state["num_rows"]
    timing = state["timing"]
    arrival_cycle = state.get("request_index", 0) * max(1, int(timing.get("arrival_interval", 1)))
    state["request_index"] = state.get("request_index", 0) + 1

    opened = state["open_rows"].get(bank)
    bank_ready = state["bank_ready"].get(bank, 0)
    n_bl = int(timing.get("nBL", 4))
    n_ccd = int(timing.get("nCCDS", n_bl))
    n_rrd = int(timing.get("nRRDS", 4))
    n_rp = int(timing.get("nRP", 20))
    n_rcd = int(timing.get("nRCDWR" if request["is_write"] else "nRCDRD", 24))
    n_cl = int(timing.get("nCL", state["read_latency_ticks"]))
    n_cwl = int(timing.get("nCWL", max(1, n_cl // 2)))
    n_wr = int(timing.get("nWR", n_bl))

    if opened == row:
        state["row_hits"] += 1
        cas_cycle = max(arrival_cycle, bank_ready, state["next_col_cycle"])
    elif opened is None:
        state["row_misses"] += 1
        act_cycle = max(arrival_cycle, bank_ready, state["next_act_cycle"])
        state["next_act_cycle"] = act_cycle + n_rrd
        cas_cycle = max(act_cycle + n_rcd, state["next_col_cycle"])
        state["open_rows"][bank] = row
    else:
        state["row_conflicts"] += 1
        pre_cycle = max(arrival_cycle, bank_ready)
        act_cycle = max(pre_cycle + n_rp, state["next_act_cycle"])
        state["next_act_cycle"] = act_cycle + n_rrd
        cas_cycle = max(act_cycle + n_rcd, state["next_col_cycle"])
        state["open_rows"][bank] = row

    state["next_col_cycle"] = cas_cycle + max(1, n_ccd)
    state["bank_ready"][bank] = cas_cycle + n_bl
    if request["is_write"]:
        state["write_reqs"] += 1
        completion_cycle = cas_cycle + n_cwl + n_bl + n_wr
    else:
        state["read_reqs"] += 1
        completion_cycle = cas_cycle + state["read_latency_ticks"] + (column % 4) * 0.25
        state["read_latency_accum"] += max(0.0, completion_cycle - arrival_cycle)
    queue_depth_estimate = max(0, int(cas_cycle - arrival_cycle))
    state["max_queue_depth"] = max(state["max_queue_depth"], queue_depth_estimate)
    state["cycles"] = max(state["cycles"], int(completion_cycle))


def _finalize_controller_state(state: dict[str, Any]) -> dict[str, Any]:
    read_reqs = state["read_reqs"]
    avg_read_latency = (
        state["read_latency_accum"] / read_reqs
        if read_reqs > 0
        else state["read_latency_ticks"]
    )
    return {
        "id": state["id"],
        "cycles": state["cycles"],
        "num_read_reqs": read_reqs,
        "num_write_reqs": state["write_reqs"],
        "row_hits": state["row_hits"],
        "row_misses": state["row_misses"],
        "row_conflicts": state["row_conflicts"],
        "avg_read_latency": avg_read_latency,
        "avg_read_latency_ns": avg_read_latency * state["tick_ps"] / 1000.0,
        "max_queue_depth": state["max_queue_depth"],
        "timing_source": "expanded_ramulator2_config",
    }


def _timing_map(dram: dict[str, Any]) -> dict[str, float]:
    impl = str(dram.get("impl", ""))
    names = TIMING_PARAMS.get(impl)
    values = dram.get("timing", [])
    if not names or not isinstance(values, list):
        return {}
    timing = {
        name: float(values[index])
        for index, name in enumerate(names)
        if index < len(values)
    }
    timing["arrival_interval"] = 1.0
    return timing
