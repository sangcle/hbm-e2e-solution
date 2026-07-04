from backend.app.domain.candidate import DesignCandidate


def render_markdown_report(result: DesignCandidate) -> str:
    metrics = result.metrics
    constraints = result.constraints
    lines = [
        f"# HBM E2E Report: {result.label}",
        "",
        "## Run",
        "",
        f"- Run ID: `{result.run_id}`",
        f"- Candidate ID: `{result.candidate_id}`",
        f"- Simulation mode: `{result.metadata.simulation_mode.value}`",
        f"- Created at: `{result.metadata.created_at}`",
        f"- Model version: `{result.metadata.model_version}`",
        f"- Formula version: `{result.metadata.formula_version}`",
        f"- Preset version: `{result.metadata.preset_version}`",
        f"- Assumption version: `{result.metadata.assumption_version}`",
        "",
        "## Architecture",
        "",
        f"- Generation: `{result.architecture.generation.value}`",
        f"- Stacks: {result.architecture.stack_count}",
        f"- Stack height: {result.architecture.stack_height}",
        f"- Capacity: {metrics.usable_capacity_gb:.2f} GB usable / {metrics.raw_capacity_gb:.2f} GB raw",
        f"- IO width per stack: {result.architecture.io_width_bits_per_stack} bits",
        f"- Data rate: {result.architecture.data_rate_gbps_per_pin:.2f} Gb/s per pin",
        "",
        "## Metrics",
        "",
        f"- Raw peak bandwidth: {metrics.raw_peak_bandwidth_GBps:.2f} GB/s",
        f"- Sustained peak bandwidth: {metrics.sustained_peak_bandwidth_GBps:.2f} GB/s",
        f"- Effective bandwidth: {metrics.effective_bandwidth_GBps:.2f} GB/s",
        f"- Achieved bandwidth: {metrics.achieved_bandwidth_GBps:.2f} GB/s",
        f"- Demand satisfaction: {metrics.demand_satisfaction_ratio * 100:.1f}%",
        f"- Average latency: {metrics.average_latency_ns:.2f} ns",
        f"- Total power: {metrics.total_power_w:.2f} W",
        f"- Estimated temperature: {metrics.estimated_temperature_c:.2f} C",
        f"- Thermal throttle factor: {metrics.thermal_throttle_factor:.3f}",
        f"- Feasibility score: {result.feasibility_score:.3f}",
        "",
        "## Backend Evidence",
        "",
        f"- Backend: `{metrics.backend_metadata.get('backend', 'unknown')}`",
        f"- Backend status: `{metrics.backend_metadata.get('status', 'not_applicable')}`",
        f"- Cycle accurate: `{metrics.backend_metadata.get('cycle_accurate', metrics.backend_metadata.get('backend') != 'ramulator2')}`",
        f"- Stats schema: `{metrics.backend_metadata.get('stats_schema_detected', 'N/A')}`",
        f"- Simulated cycles: {metrics.simulated_cycles if metrics.simulated_cycles is not None else 'N/A'}",
        f"- Read requests: {metrics.read_request_count if metrics.read_request_count is not None else 'N/A'}",
        f"- Write requests: {metrics.write_request_count if metrics.write_request_count is not None else 'N/A'}",
        f"- Row hit rate: {metrics.row_hit_rate if metrics.row_hit_rate is not None else 'N/A'}",
        "",
        "## Constraints",
        "",
        f"- Feasible: `{constraints.is_feasible}`",
        f"- Violations: {', '.join(constraints.violated_constraints) or 'none'}",
        f"- Warnings: {', '.join(constraints.warnings) or 'none'}",
        "",
        "## Assumptions",
        "",
        f"- Assumption ID: `{result.assumptions.assumption_id}`",
        f"- Confidence: `{result.assumptions.confidence_level.value}`",
        f"- Production calibrated: `{result.assumptions.production_calibrated}`",
        f"- Internal coverage ratio: {metrics.assumption_coverage.coverage_ratio:.2f}",
        f"- Missing critical factors: {', '.join(metrics.assumption_coverage.missing_critical_factors) or 'none'}",
        "",
        "## Recommendations",
        "",
    ]
    if metrics.process_yield_score is not None:
        process_lines = [
            "## Process Quality",
            "",
            f"- Yield score: {metrics.process_yield_score:.3f}",
            f"- Defect risk: {metrics.process_defect_risk:.3f}",
            f"- Good die ratio: {metrics.capacity_good_die_ratio:.3f}",
            f"- Bandwidth derating factor: {metrics.process_bandwidth_derating_factor:.3f}",
            f"- Latency penalty: {metrics.process_latency_penalty_ns:.2f} ns",
            f"- Power delta: {metrics.process_power_delta_w:.2f} W",
            f"- Thermal resistance delta: {metrics.process_thermal_resistance_delta_c_per_w:.3f} C/W",
            f"- Reliability margin: {metrics.reliability_margin:.3f}",
            f"- Confidence: `{metrics.process_confidence_level}`",
            f"- Calibration required: `{metrics.process_calibration_required}`",
            f"- Public proxy used: `{metrics.process_public_proxy_used}`",
            "",
        ]
        if metrics.process_stage_risks:
            process_lines.extend(["### Process Stage Risks", ""])
            for stage, risk in metrics.process_stage_risks.items():
                process_lines.append(f"- {stage}: {risk:.3f}")
            process_lines.append("")
        if metrics.process_notes:
            process_lines.extend(["### Process Notes", ""])
            for note in metrics.process_notes:
                process_lines.append(f"- {note}")
            process_lines.append("")
        backend_index = lines.index("## Backend Evidence")
        lines[backend_index:backend_index] = process_lines
    if result.recommendations:
        for rec in result.recommendations:
            lines.append(f"- **{rec.code}** ({rec.severity}): {rec.message}")
    else:
        lines.append("- No recommendations.")
    artifacts = metrics.backend_metadata.get("artifacts")
    if isinstance(artifacts, dict) and artifacts:
        lines.extend(["", "## Backend Artifacts", ""])
        for name, path in artifacts.items():
            lines.append(f"- {name}: `{path}`")
    lines.append("")
    return "\n".join(lines)
