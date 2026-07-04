import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from .config_generator import (
    bundled_ramulator2_home,
    cpp_extension_available,
    default_ramulator2_home,
    ramulator_python_path,
    source_ramulator2_home,
)


def ramulator2_build_diagnostics() -> dict[str, Any]:
    ramulator_home = default_ramulator2_home()
    python_path = ramulator_python_path(ramulator_home)
    extension_available, extension_error = cpp_extension_available(ramulator_home) if python_path.exists() else (False, "Ramulator2 Python path not found")
    source_home = source_ramulator2_home()
    runtime_home = bundled_ramulator2_home()
    tools = {
        "cmake": _tool("cmake"),
        "ninja": _tool("ninja"),
        "cl": _tool("cl"),
        "g++": _tool("g++"),
        "clang++": _tool("clang++"),
    }
    compiler_available = any(tools[name]["available"] for name in ("cl", "g++", "clang++"))
    cmake_available = tools["cmake"]["available"]
    source_ready = (source_home / "CMakeLists.txt").exists() and (source_home / "python" / "ramulator").exists()
    runtime_ready = (runtime_home / "python" / "ramulator").exists()
    build_ready = source_ready and cmake_available and compiler_available
    return {
        "ramulator_home": str(ramulator_home),
        "ramulator_python_path": str(python_path),
        "source_home": str(source_home),
        "runtime_home": str(runtime_home),
        "source_ready": source_ready,
        "runtime_ready": runtime_ready,
        "runtime_lib_path": str(runtime_home / "lib" / "win_amd64" / "ramulator.lib"),
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
        },
        "tools": tools,
        "compiler_available": compiler_available,
        "cmake_available": cmake_available,
        "cpp_extension_available": extension_available,
        "cpp_extension_error": extension_error,
        "build_ready": build_ready,
        "build_commands": [
            f"cd {source_home}",
            "cmake -S . -B build-msvc -G Ninja -DCMAKE_BUILD_TYPE=Release -DRAMULATOR_PYTHON_BINDINGS=ON",
            "cmake --build build-msvc --config Release",
            "cd C:\\E2E",
            f".\\.venv\\Scripts\\python -c \"import sys; sys.path.insert(0, r'{python_path}'); import ramulator._ramulator\"",
        ],
    }


def _tool(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {
        "available": bool(path),
        "path": path,
    }
