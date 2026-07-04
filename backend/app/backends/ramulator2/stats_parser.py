import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised when optional dependency is absent
    yaml = None


KEY_ALIASES = {
    "cycles": ["cycles", "num_cycles", "total_cycles"],
    "read_reqs": ["read_reqs", "read_requests", "num_read_reqs", "num_read_requests", "total_num_read_requests", "read_count"],
    "write_reqs": ["write_reqs", "write_requests", "num_write_reqs", "num_write_requests", "total_num_write_requests", "write_count"],
    "row_hits": ["row_hits", "num_row_hits"],
    "row_misses": ["row_misses", "row_misses_closed", "num_row_misses"],
    "row_conflicts": ["row_conflicts", "num_row_conflicts"],
    "avg_read_latency": ["avg_read_latency", "average_read_latency", "read_latency_avg"],
    "avg_read_latency_ns": ["avg_read_latency_ns", "average_read_latency_ns"],
    "tck_ps": ["tck_ps", "tCK_ps"],
}


def parse_stats_file(path: str | Path) -> dict[str, float | int | str]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(str(path))
    return parse_stats_text(file_path.read_text(encoding="utf-8", errors="replace"))


def parse_stats_text(text: str) -> dict[str, float | int | str]:
    structured = _parse_structured(text)
    if structured is not None:
        return parse_stats_payload(structured)
    return _parse_plain_text(text)


def parse_stats_payload(payload: Any) -> dict[str, float | int | str]:
    controller = _find_controller_collection(payload)
    if isinstance(controller, list):
        return _aggregate_channels([parse_stats_payload(item) for item in controller])

    result: dict[str, float | int | str] = {}
    source = controller if isinstance(controller, dict) else payload
    for canonical, aliases in KEY_ALIASES.items():
        value = _find_by_tail(source, aliases)
        if isinstance(value, (int, float)):
            result[canonical] = value
        elif isinstance(value, str):
            try:
                result[canonical] = float(value)
            except ValueError:
                result[canonical] = value
    result["stats_schema_detected"] = "structured"
    return result


def _parse_structured(text: str) -> Any | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    if yaml is not None:
        try:
            parsed = yaml.safe_load(text)
            if isinstance(parsed, (dict, list)):
                return parsed
        except Exception:
            return None
    return None


def _parse_plain_text(text: str) -> dict[str, float | int | str]:
    result: dict[str, float | int | str] = {"stats_schema_detected": "plain_text"}
    for canonical, aliases in KEY_ALIASES.items():
        pattern = r"(?:^|\s|\.|:)(?:" + "|".join(re.escape(alias) for alias in aliases) + r")\s*[:=]\s*([-+]?\d+(?:\.\d+)?)"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            number = float(match.group(1))
            result[canonical] = int(number) if number.is_integer() else number
    return result


def _find_controller_collection(payload: Any) -> Any | None:
    if isinstance(payload, dict):
        for key in ("controllers", "controller", "memory_system", "dram_system"):
            if key in payload:
                value = payload[key]
                if key in ("memory_system", "dram_system"):
                    nested = _find_controller_collection(value)
                    if nested is not None:
                        return nested
                return value
        for value in payload.values():
            nested = _find_controller_collection(value)
            if nested is not None:
                return nested
    return None


def _find_by_tail(payload: Any, aliases: list[str]) -> Any | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized_key = str(key).lower().replace("-", "_")
            if any(normalized_key.endswith(alias.lower()) for alias in aliases):
                return value
        for value in payload.values():
            found = _find_by_tail(value, aliases)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_by_tail(item, aliases)
            if found is not None:
                return found
    return None


def _aggregate_channels(channels: list[dict[str, float | int | str]]) -> dict[str, float | int | str]:
    result: dict[str, float | int | str] = {"stats_schema_detected": "structured_multichannel"}
    result["cycles"] = max(float(item.get("cycles", 0.0)) for item in channels) if channels else 0
    for key in ("read_reqs", "write_reqs", "row_hits", "row_misses", "row_conflicts"):
        result[key] = sum(float(item.get(key, 0.0)) for item in channels)

    total_reads = sum(float(item.get("read_reqs", 0.0)) for item in channels)
    if total_reads > 0:
        weighted = 0.0
        for item in channels:
            weighted += float(item.get("avg_read_latency", 0.0)) * float(item.get("read_reqs", 0.0))
        result["avg_read_latency"] = weighted / total_reads
    return result
