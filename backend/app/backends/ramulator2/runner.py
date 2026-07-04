import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.workload import WorkloadProfile

from .config_replay import replay_config_trace
from .config_generator import (
    build_ramulator2_config,
    cpp_extension_available,
    default_ramulator2_home,
    import_ramulator,
    ramulator_python_path,
    write_config_artifacts,
    write_runner_script,
)
from .stats_parser import parse_stats_file
from .trace_generator import generate_load_store_trace


@dataclass
class Ramulator2RunResult:
    status: str
    stats: dict[str, Any] | None
    metadata: dict[str, Any]
    artifacts: dict[str, str]
    error: str | None = None


class LocalRamulator2Runner:
    def __init__(self, ramulator_home: Path | None = None) -> None:
        self.ramulator_home = (ramulator_home or default_ramulator2_home()).resolve()

    def run(
        self,
        architecture: HBMArchitecture,
        workload: WorkloadProfile,
        backend_options: dict[str, Any],
        backend_dir: Path,
    ) -> Ramulator2RunResult:
        prepared = self.prepare(architecture, workload, backend_options, backend_dir)
        extension_ok, extension_error = cpp_extension_available(self.ramulator_home)
        prepared.metadata["cpp_extension_available"] = extension_ok
        if not extension_ok:
            if bool(backend_options.get("allow_config_replay", True)):
                stats = self._run_config_replay(prepared, backend_dir)
                prepared.metadata["cpp_extension_error"] = extension_error
                prepared.metadata["cycle_accurate"] = False
                prepared.metadata["config_replay"] = True
                return Ramulator2RunResult(
                    status="config_replay_completed",
                    stats=stats,
                    metadata=prepared.metadata,
                    artifacts=prepared.artifacts,
                )
            prepared.metadata["cpp_extension_error"] = extension_error
            return Ramulator2RunResult(
                status="unavailable_cpp_extension",
                stats=None,
                metadata=prepared.metadata,
                artifacts=prepared.artifacts,
                error=extension_error,
            )

        timeout_s = int(backend_options.get("timeout_s", 30))
        env = os.environ.copy()
        python_path = str(ramulator_python_path(self.ramulator_home))
        project_root = str(Path(__file__).resolve().parents[4])
        env["PYTHONPATH"] = os.pathsep.join(
            item for item in (project_root, python_path, env.get("PYTHONPATH", "")) if item
        )
        command = [sys.executable, str(Path(prepared.artifacts["runner_script"]).resolve())]

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=str(backend_dir.resolve()),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            _write_log(backend_dir / "stdout.log", exc.stdout or "")
            _write_log(backend_dir / "stderr.log", exc.stderr or "")
            prepared.metadata["duration_ms"] = (time.perf_counter() - started) * 1000.0
            return Ramulator2RunResult(
                status="timeout",
                stats=None,
                metadata=prepared.metadata,
                artifacts=prepared.artifacts,
                error=f"Ramulator2 timed out after {timeout_s}s",
            )

        _write_log(backend_dir / "stdout.log", completed.stdout)
        _write_log(backend_dir / "stderr.log", completed.stderr)
        prepared.metadata["duration_ms"] = (time.perf_counter() - started) * 1000.0
        prepared.metadata["return_code"] = completed.returncode
        prepared.artifacts["stdout"] = str((backend_dir / "stdout.log").resolve())
        prepared.artifacts["stderr"] = str((backend_dir / "stderr.log").resolve())

        if completed.returncode != 0:
            return Ramulator2RunResult(
                status="failed",
                stats=None,
                metadata=prepared.metadata,
                artifacts=prepared.artifacts,
                error=(completed.stderr or completed.stdout or "Ramulator2 returned non-zero exit code")[:4000],
            )

        stats_path = Path(prepared.artifacts["stats_json"])
        stats = parse_stats_file(stats_path)
        stats.setdefault("tck_ps", self._config_tick_ps(prepared))
        return Ramulator2RunResult(
            status="completed",
            stats=stats,
            metadata=prepared.metadata,
            artifacts=prepared.artifacts,
        )

    def _run_config_replay(
        self,
        prepared: Ramulator2RunResult,
        backend_dir: Path,
    ) -> dict[str, Any]:
        config_path = Path(prepared.artifacts["ramulator_config_json"])
        trace_path = Path(prepared.artifacts["trace"])
        stats_json_path = Path(prepared.artifacts["stats_json"])
        stats_yaml_path = Path(prepared.artifacts["stats_yaml"])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        replay_config_trace(config, trace_path, stats_json_path, stats_yaml_path)
        stats = parse_stats_file(stats_json_path)
        stats.setdefault("tck_ps", self._config_tick_ps(prepared))
        _write_log(
            backend_dir / "stdout.log",
            "Ramulator2 C++ extension unavailable; generated config_replay stats from Ramulator2 config and trace.\n",
        )
        _write_log(backend_dir / "stderr.log", "")
        prepared.artifacts["stdout"] = str((backend_dir / "stdout.log").resolve())
        prepared.artifacts["stderr"] = str((backend_dir / "stderr.log").resolve())
        return stats

    def _config_tick_ps(self, prepared: Ramulator2RunResult) -> float | None:
        try:
            config_path = Path(prepared.artifacts["ramulator_config_json"])
            config = json.loads(config_path.read_text(encoding="utf-8"))
            controller = config["memory_system"]["controllers"][0]
            timing = controller["dram"]["timing"]
            return float(timing[-1])
        except Exception:
            return None

    def prepare(
        self,
        architecture: HBMArchitecture,
        workload: WorkloadProfile,
        backend_options: dict[str, Any],
        backend_dir: Path,
    ) -> Ramulator2RunResult:
        backend_dir.mkdir(parents=True, exist_ok=True)
        request_count = int(backend_options.get("trace_request_count", 4096))
        seed = int(backend_options.get("seed", 12345))
        trace_path = backend_dir / "trace.txt"
        trace_metadata = generate_load_store_trace(architecture, workload, trace_path, request_count, seed)
        config, config_metadata = build_ramulator2_config(
            architecture,
            workload,
            trace_path,
            backend_options,
            self.ramulator_home,
        )
        write_config_artifacts(config, backend_dir)
        payload = {
            "architecture": architecture.model_dump(mode="json"),
            "workload": workload.model_dump(mode="json"),
            "backend_options": backend_options,
            "trace_path": str(trace_path.resolve()),
            "ramulator_home": str(self.ramulator_home),
        }
        input_path = backend_dir / "ramulator_hbm_input.json"
        input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        write_runner_script(backend_dir)

        artifacts = {
            "trace": str(trace_path.resolve()),
            "ramulator_hbm_input": str(input_path.resolve()),
            "ramulator_config_json": str((backend_dir / "ramulator_config.json").resolve()),
            "ramulator_config_yaml": str((backend_dir / "ramulator_config.yaml").resolve()),
            "runner_script": str((backend_dir / "run_ramulator2.py").resolve()),
            "stats_json": str((backend_dir / "sim.stats.json").resolve()),
            "stats_yaml": str((backend_dir / "sim.stats.yaml").resolve()),
        }
        metadata = {
            "backend": "ramulator2",
            "runner": "local_python",
            "interface": "python",
            "ramulator_home": str(self.ramulator_home),
            "trace": trace_metadata,
            **config_metadata,
        }
        return Ramulator2RunResult(
            status="prepared",
            stats=None,
            metadata=metadata,
            artifacts=artifacts,
        )


def run_payload_file(payload_path: str, stats_json_path: str, stats_yaml_path: str) -> None:
    payload_file = Path(payload_path).resolve()
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    ramulator_home = Path(payload["ramulator_home"]).resolve()
    import_ramulator(ramulator_home)
    import ramulator  # type: ignore[import-not-found]

    architecture = HBMArchitecture.model_validate(payload["architecture"])
    workload = WorkloadProfile.model_validate(payload["workload"])
    backend_options = payload["backend_options"]
    trace_path = Path(payload["trace_path"])
    config, _ = build_ramulator2_config(
        architecture,
        workload,
        trace_path,
        backend_options,
        ramulator_home,
    )
    sim = ramulator.Simulation(config["frontend"], config["memory_system"])
    sim.run()
    stats = sim.stats
    stats_yaml = sim.stats_yaml
    sim.finalize()
    Path(stats_json_path).write_text(json.dumps(stats, indent=2), encoding="utf-8")
    Path(stats_yaml_path).write_text(stats_yaml, encoding="utf-8")


def _write_log(path: Path, content: str | bytes | None, max_chars: int = 200_000) -> None:
    if content is None:
        text = ""
    elif isinstance(content, bytes):
        text = content.decode("utf-8", errors="replace")
    else:
        text = content
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[truncated]\n"
    path.write_text(text, encoding="utf-8")
