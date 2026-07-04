import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .build_diagnostics import ramulator2_build_diagnostics
from .config_generator import (
    bundled_ramulator2_home,
    cpp_extension_available,
    default_ramulator2_home,
    ramulator_python_path,
    source_ramulator2_home,
)


def ramulator2_status() -> dict[str, Any]:
    ramulator_home = default_ramulator2_home()
    python_path = ramulator_python_path(ramulator_home)
    dsl_available = python_path.exists()
    extension_available, extension_error = cpp_extension_available(ramulator_home) if dsl_available else (False, "Ramulator2 Python package path not found")
    configured = os.getenv("RAMULATOR2_BIN")
    candidate = configured or shutil.which("ramulator2") or shutil.which("Ramulator2")
    binary_available = bool(candidate)
    status: dict[str, Any] = {
        "available": extension_available or binary_available,
        "can_run": extension_available or dsl_available,
        "backend": "ramulator2",
        "runner": "local_python",
        "ramulator_home": str(ramulator_home),
        "python_path": str(python_path),
        "source_home": str(source_ramulator2_home()),
        "runtime_home": str(bundled_ramulator2_home()),
        "runtime_bundle_available": (bundled_ramulator2_home() / "python" / "ramulator").exists(),
        "python_dsl_available": dsl_available,
        "config_replay_available": dsl_available,
        "cpp_extension_available": extension_available,
        "cpp_extension_error": extension_error,
        "build": ramulator2_build_diagnostics(),
    }
    if not candidate:
        if extension_available:
            status["message"] = "Ramulator2 Python C++ extension detected."
        elif dsl_available:
            status["message"] = (
                "Ramulator2 Python DSL was found, but the C++ extension/binary is not available. "
                "Ramulator2 mode will generate config/trace artifacts and config_replay stats."
            )
        else:
            status["message"] = "Ramulator2 was not found. Analytical mode is still available."
        return status

    path = str(Path(candidate).resolve()) if Path(candidate).exists() else candidate
    version = "unknown"
    try:
        completed = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        version_output = (completed.stdout or completed.stderr).strip()
        if version_output:
            version = version_output.splitlines()[0][:120]
    except Exception:
        version = "detected"

    status.update(
        {
            "binary_available": True,
            "path": path,
            "version": version,
            "message": "Ramulator2 binary or Python extension detected.",
        }
    )
    return status
