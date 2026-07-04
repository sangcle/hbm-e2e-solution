from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.backends.ramulator2.stats_parser import parse_stats_payload, parse_stats_text
from backend.app.backends.ramulator2.config_generator import build_ramulator2_config
from backend.app.backends.ramulator2.config_replay import replay_config_trace
from backend.app.backends.ramulator2.build_diagnostics import ramulator2_build_diagnostics
from backend.app.domain.architecture import HBMArchitecture
from backend.app.domain.candidate import CompareRequest, CandidateInput, SimulateRequest
from backend.app.domain.enums import HBMGeneration
from backend.app.domain.target import ProductTarget
from backend.app.domain.workload import WorkloadProfile
from backend.app.main import app
from backend.app.simulation.bandwidth_model import calculate_bandwidth
from backend.app.simulation.service import SimulationService
from backend.app.storage.repository import ResultRepository
from backend.app.presets.assumption_presets import get_assumption_preset
from backend.app.presets.workload_presets import get_workload_preset


def test_golden_raw_bandwidth_formulas():
    assumptions = get_assumption_preset("public_hbm_mvp_v0")
    workload = get_workload_preset("hpc_stream")
    cases = [
        (HBMGeneration.HBM2E, 3.2, 409.6),
        (HBMGeneration.HBM3, 6.4, 819.2),
        (HBMGeneration.HBM3E, 9.2, 1177.6),
    ]
    for generation, data_rate, expected in cases:
        arch = HBMArchitecture(
            generation=generation,
            stack_count=1,
            stack_height=8,
            die_capacity_gb=2.0,
            io_width_bits_per_stack=1024,
            channel_count_per_stack=16 if generation != HBMGeneration.HBM2E else 8,
            data_rate_gbps_per_pin=data_rate,
        )
        metrics, _ = calculate_bandwidth(arch, workload, assumptions, thermal_throttle_factor=1.0)
        assert metrics["raw_peak_bandwidth_GBps"] == pytest.approx(expected)


def test_workload_ratio_validation():
    with pytest.raises(ValueError):
        WorkloadProfile(read_ratio=0.8, write_ratio=0.3)


def test_result_and_report_are_persisted(tmp_path: Path):
    service = SimulationService(repository=ResultRepository(tmp_path))
    request = SimulateRequest(
        target=ProductTarget(capacity_gb=16, target_bandwidth_GBps=800, power_policy="warn"),
        architecture_preset="hbm3e_8hi_24gb",
        workload_preset="ai_inference",
    )
    result = service.run(request, persist=True)

    run_dir = tmp_path / result.run_id
    assert (run_dir / "result.json").exists()
    assert (run_dir / "metadata.json").exists()
    assert (run_dir / "input.json").exists()
    assert (run_dir / "report.md").exists()
    assert result.metrics.raw_peak_bandwidth_GBps == pytest.approx(1177.6)
    assert "## Backend Evidence" in (run_dir / "report.md").read_text(encoding="utf-8")


def test_infeasible_target_marks_constraint(tmp_path: Path):
    service = SimulationService(repository=ResultRepository(tmp_path))
    result = service.run(
        SimulateRequest(
            target=ProductTarget(capacity_gb=256, target_bandwidth_GBps=5000),
            architecture_preset="hbm3e_8hi_24gb",
            workload_preset="ai_training",
        ),
        persist=False,
    )
    assert not result.constraints.is_feasible
    assert "capacity" in result.constraints.violated_constraints
    assert "effective_bandwidth" in result.constraints.violated_constraints


def test_empty_process_parameters_do_not_affect_metrics(tmp_path: Path):
    service = SimulationService(repository=ResultRepository(tmp_path))
    base_request = SimulateRequest(
        target=ProductTarget(capacity_gb=16, target_bandwidth_GBps=700, power_policy="warn"),
        architecture_preset="hbm3e_8hi_24gb",
        workload_preset="ai_inference",
    )
    base_result = service.run(base_request, persist=False)
    process_result = service.run(
        SimulateRequest(
            target=base_request.target,
            architecture_preset=base_request.architecture_preset,
            workload_preset=base_request.workload_preset,
            process_parameters={
                "tsv": {
                    "tsv_void_fraction": {
                        "value": None,
                        "unit": "ratio",
                        "data_type": "continuous",
                        "calibration_required": True,
                    }
                }
            },
        ),
        persist=False,
    )

    assert process_result.metrics.process_yield_score is None
    assert process_result.metrics.effective_bandwidth_GBps == pytest.approx(base_result.metrics.effective_bandwidth_GBps)
    assert process_result.metrics.total_power_w == pytest.approx(base_result.metrics.total_power_w)


def test_process_parameters_apply_proxy_effects_and_report(tmp_path: Path):
    service = SimulationService(repository=ResultRepository(tmp_path))
    base_request = SimulateRequest(
        target=ProductTarget(capacity_gb=16, target_bandwidth_GBps=700, power_policy="warn"),
        architecture_preset="hbm3e_8hi_24gb",
        workload_preset="ai_inference",
    )
    base_result = service.run(base_request, persist=False)
    request = SimulateRequest(
        target=base_request.target,
        architecture_preset=base_request.architecture_preset,
        workload_preset=base_request.workload_preset,
        process_parameters={
            "dram_wafer_fab": {
                "wafer_good_die_ratio": {
                    "value": 0.95,
                    "unit": "ratio",
                    "data_type": "continuous",
                    "calibration_required": True,
                }
            },
            "tsv": {
                "tsv_resistance_distribution_mohm": {
                    "value": {"mean": 60.0, "p95": 90.0},
                    "unit": "mOhm",
                    "data_type": "distribution",
                    "calibration_required": True,
                },
                "tsv_void_fraction": {
                    "value": 0.03,
                    "unit": "ratio",
                    "data_type": "continuous",
                    "calibration_required": True,
                },
            },
            "rdl_micro_bump": {
                "micro_bump_open_short_rate": {
                    "value": 0.003,
                    "unit": "ratio",
                    "data_type": "continuous",
                    "calibration_required": True,
                }
            },
            "bonding": {
                "die_to_die_overlay_error_um": {
                    "value": 0.8,
                    "unit": "um",
                    "data_type": "continuous",
                    "calibration_required": True,
                },
                "bond_void_fraction": {
                    "value": 0.02,
                    "unit": "ratio",
                    "data_type": "continuous",
                    "calibration_required": True,
                },
            },
            "interposer_package": {
                "thermal_interface_void_fraction": {
                    "value": 0.04,
                    "unit": "ratio",
                    "data_type": "continuous",
                    "calibration_required": True,
                }
            },
        },
    )
    result = service.run(request, persist=True)
    report = (tmp_path / result.run_id / "report.md").read_text(encoding="utf-8")

    assert result.metrics.process_yield_score is not None
    assert result.metrics.process_public_proxy_used is True
    assert result.metrics.process_calibration_required is True
    assert result.metrics.effective_bandwidth_GBps < base_result.metrics.effective_bandwidth_GBps
    assert result.metrics.average_latency_ns > base_result.metrics.average_latency_ns
    assert result.metrics.total_power_w > base_result.metrics.total_power_w
    assert result.metrics.usable_capacity_gb == pytest.approx(base_result.metrics.usable_capacity_gb)
    assert "## Process Quality" in report
    assert "Process model uses generalized public/proxy quality" in report


def test_compare_sorts_feasible_and_score(tmp_path: Path):
    service = SimulationService(repository=ResultRepository(tmp_path))
    request = CompareRequest(
        target=ProductTarget(capacity_gb=16, target_bandwidth_GBps=700, power_policy="warn"),
        candidates=[
            CandidateInput(candidate_label="small", architecture_preset="hbm2e_8hi_16gb", workload_preset="ai_inference"),
            CandidateInput(candidate_label="fast", architecture_preset="hbm3e_8hi_24gb", workload_preset="ai_inference"),
        ],
    )
    response = service.compare(request)
    assert response.results[0].feasibility_score >= response.results[1].feasibility_score


def test_ramulator2_structured_multichannel_parser():
    stats = parse_stats_payload(
        {
            "controllers": [
                {"cycles": 100, "read_reqs": 10, "write_reqs": 3, "row_hits": 6, "row_misses": 4, "avg_read_latency": 30},
                {"cycles": 120, "read_reqs": 30, "write_reqs": 5, "row_hits": 18, "row_misses": 12, "avg_read_latency": 50},
            ]
        }
    )
    assert stats["cycles"] == 120
    assert stats["read_reqs"] == 40
    assert stats["avg_read_latency"] == pytest.approx(45)


def test_ramulator2_plain_text_parser():
    stats = parse_stats_text("cycles: 10\nnum_read_reqs = 4\nrow_hits: 3\nrow_misses: 1\ntCK_ps: 500\n")
    assert stats["cycles"] == 10
    assert stats["read_reqs"] == 4
    assert stats["row_hits"] == 3
    assert stats["tck_ps"] == 500


def test_ramulator2_config_generation_uses_local_hbm3_mapping(tmp_path: Path):
    arch = HBMArchitecture(
        generation=HBMGeneration.HBM3E,
        stack_count=4,
        stack_height=8,
        die_capacity_gb=3.0,
        io_width_bits_per_stack=1024,
        channel_count_per_stack=16,
        data_rate_gbps_per_pin=9.2,
    )
    workload = get_workload_preset("ai_training")
    trace_path = tmp_path / "trace.txt"
    trace_path.write_text("LD 0x0\n", encoding="utf-8")
    config, metadata = build_ramulator2_config(arch, workload, trace_path, {"max_controllers": 2})

    assert config["frontend"]["impl"] == "LoadStoreTrace"
    assert config["memory_system"]["impl"] == "GenericDRAM"
    assert len(config["memory_system"]["controllers"]) == 2
    assert metadata["mapping"]["dram_class"] == "HBM3"
    assert metadata["mapping"]["timing_preset"] == "HBM3_6400Mbps"
    assert metadata["controller_scale_factor"] == pytest.approx(32)


def test_ramulator2_mode_creates_backend_artifacts_and_config_replay_stats(tmp_path: Path):
    service = SimulationService(repository=ResultRepository(tmp_path))
    request = SimulateRequest(
        target=ProductTarget(capacity_gb=16, target_bandwidth_GBps=500, power_policy="warn"),
        architecture_preset="hbm3e_8hi_24gb",
        workload_preset="ai_inference",
        simulation_mode="ramulator2",
        backend_options={"trace_request_count": 32, "max_controllers": 2},
    )
    result = service.run(request, persist=True)
    backend_dir = tmp_path / result.run_id / "backend"

    assert result.metrics.backend_metadata["backend"] == "ramulator2"
    assert result.metrics.backend_metadata["status"] in {"completed", "config_replay_completed"}
    assert (backend_dir / "trace.txt").exists()
    assert (backend_dir / "ramulator_config.json").exists()
    assert (backend_dir / "ramulator_config.yaml").exists()
    assert (backend_dir / "run_ramulator2.py").exists()
    assert (backend_dir / "ramulator_hbm_input.json").exists()
    assert (backend_dir / "sim.stats.json").exists()
    assert (backend_dir / "sim.stats.yaml").exists()
    assert result.metrics.read_request_count is not None
    assert result.metrics.row_hit_rate is not None
    runner_script = (backend_dir / "run_ramulator2.py").read_text(encoding="utf-8")
    assert str((backend_dir / "ramulator_hbm_input.json").resolve()) in runner_script
    assert "sys.path.insert" in runner_script


def test_ramulator2_config_replay_uses_timing_and_open_row_state(tmp_path: Path):
    arch = HBMArchitecture(
        generation=HBMGeneration.HBM3,
        stack_count=1,
        stack_height=8,
        die_capacity_gb=2.0,
        io_width_bits_per_stack=1024,
        channel_count_per_stack=16,
        data_rate_gbps_per_pin=6.4,
    )
    workload = get_workload_preset("ai_inference")
    trace_path = tmp_path / "trace.txt"
    trace_path.write_text("LD 0x0\nLD 0x40\nLD 0x100000\n", encoding="utf-8")
    config, _ = build_ramulator2_config(arch, workload, trace_path, {"max_controllers": 1})
    stats = replay_config_trace(
        config,
        trace_path,
        tmp_path / "sim.stats.json",
        tmp_path / "sim.stats.yaml",
    )
    parsed = parse_stats_payload(stats)

    assert parsed["read_reqs"] == 3
    assert parsed["row_hits"] == 1
    assert parsed["row_misses"] == 1
    assert parsed["row_conflicts"] == 1
    assert parsed["avg_read_latency_ns"] > 0
    assert (tmp_path / "sim.stats.json").exists()


def test_api_health_and_presets():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    presets = client.get("/presets").json()
    assert "hbm3e_8hi_24gb" in presets["architecture_presets"]


def test_process_schema_rejects_equipment_recipe_fields():
    client = TestClient(app)
    response = client.post(
        "/simulate/run",
        json={
            "target": {"capacity_gb": 16, "target_bandwidth_GBps": 700},
            "architecture_preset": "hbm3e_8hi_24gb",
            "workload_preset": "ai_inference",
            "process_parameters": {
                "tsv": {
                    "drie_gas_flow_sccm": {
                        "value": 120,
                        "unit": "sccm",
                        "data_type": "continuous",
                        "calibration_required": True,
                    }
                }
            },
        },
    )

    assert response.status_code == 422


def test_ramulator2_build_diagnostics_reports_current_environment():
    diagnostics = ramulator2_build_diagnostics()
    assert diagnostics["source_ready"] is True
    assert "cmake" in diagnostics["tools"]
    assert "build_ready" in diagnostics


def test_ramulator2_status_includes_build_readiness():
    client = TestClient(app)
    status = client.get("/backends/ramulator2/status").json()
    assert "can_run" in status
    assert "build" in status
    assert "build_ready" in status["build"]


def test_backend_artifact_api_exposes_run_artifacts(tmp_path: Path):
    service = SimulationService(repository=ResultRepository(tmp_path))
    request = SimulateRequest(
        target=ProductTarget(capacity_gb=16, target_bandwidth_GBps=500, power_policy="warn"),
        architecture_preset="hbm3e_8hi_24gb",
        workload_preset="ai_inference",
        simulation_mode="ramulator2",
        backend_options={"trace_request_count": 16, "max_controllers": 1},
    )
    result = service.run(request, persist=True)

    artifacts = service.repository.list_backend_artifacts(result.run_id)
    names = {item["name"] for item in artifacts}
    assert "ramulator_config.json" in names
    assert "sim.stats.json" in names

    content, name = service.repository.load_backend_artifact(result.run_id, "ramulator_config.json")
    assert name == "ramulator_config.json"
    assert "GenericDRAM" in content
    with pytest.raises(ValueError):
        service.repository.load_backend_artifact(result.run_id, "../result.json")
