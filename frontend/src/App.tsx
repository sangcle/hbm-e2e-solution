import {
  Activity,
  BarChart3,
  Database,
  FileText,
  GitCompare,
  Play,
  RefreshCw,
  Server,
  Thermometer,
  Zap
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

type Target = {
  capacity_gb: number;
  target_bandwidth_GBps: number;
  power_budget_w: number;
  max_temperature_c: number;
  priority: string;
  power_policy: string;
  thermal_policy: string;
  bandwidth_constraint_metric: string;
};

type Architecture = {
  generation: string;
  stack_count: number;
  stack_height: 4 | 8 | 12 | 16;
  die_count_per_stack?: number;
  die_capacity_gb: number;
  capacity_per_stack_gb?: number;
  total_capacity_gb?: number;
  io_width_bits_per_stack: number;
  channel_count_per_stack: number;
  pseudo_channels_per_channel: number;
  pseudo_channel_width_bits?: number;
  data_rate_gbps_per_pin: number;
  on_die_ecc: boolean;
  host_ecc: boolean;
  package_class: string;
};

type Workload = {
  workload_id: string;
  name: string;
  bandwidth_demand_GBps: number;
};

type ProcessParameterValue = {
  value: number | string | Record<string, number> | number[] | null;
  unit?: string | null;
  data_type: "continuous" | "categorical" | "binary" | "distribution" | "image_derived" | "time_series";
  calibration_required: boolean;
};

type ProcessParameters = {
  schema_version: string;
  process_flow_id: string;
  source_type: string;
  confidence_level: string;
  calibration_status: string;
  calculation_mode: string;
  calibration_artifact_id?: string | null;
  calibration_dataset_id?: string | null;
  calibration_model_version?: string | null;
  calibration_sample_count?: number | null;
  dram_wafer_fab?: {
    wafer_good_die_ratio?: ProcessParameterValue;
    cell_repair_fraction?: ProcessParameterValue;
    leakage_current_distribution?: ProcessParameterValue;
  };
  tsv?: {
    tsv_continuity_fail_rate?: ProcessParameterValue;
    tsv_resistance_distribution_mohm?: ProcessParameterValue;
    tsv_void_fraction?: ProcessParameterValue;
  };
  wafer_thinning?: {
    post_thinning_ttv_um?: ProcessParameterValue;
    wafer_warpage_um?: ProcessParameterValue;
    backside_crack_chipping_density?: ProcessParameterValue;
  };
  rdl_micro_bump?: {
    micro_bump_height_coplanarity_sigma_um?: ProcessParameterValue;
    micro_bump_open_short_rate?: ProcessParameterValue;
  };
  bonding?: {
    bonding_technology?: ProcessParameterValue;
    die_to_die_overlay_error_um?: ProcessParameterValue;
    bond_void_fraction?: ProcessParameterValue;
  };
  underfill_molding?: {
    underfill_void_fraction?: ProcessParameterValue;
  };
  interposer_package?: {
    thermal_interface_void_fraction?: ProcessParameterValue;
  };
};

type ProcessInputState = {
  wafer_good_die_ratio: number;
  cell_repair_fraction: number;
  leakage_current_distribution: number;
  tsv_continuity_fail_rate: number;
  tsv_resistance_distribution_mohm: number;
  tsv_void_fraction: number;
  post_thinning_ttv_um: number;
  wafer_warpage_um: number;
  backside_crack_chipping_density: number;
  micro_bump_height_coplanarity_sigma_um: number;
  micro_bump_open_short_rate: number;
  die_to_die_overlay_error_um: number;
  bond_void_fraction: number;
  underfill_void_fraction: number;
  thermal_interface_void_fraction: number;
};

type Presets = {
  architecture_presets: Record<string, Architecture>;
  workload_presets: Record<string, Workload>;
  assumption_presets: Record<string, unknown>;
};

type DesignCandidate = {
  run_id: string;
  candidate_id: string;
  label: string;
  architecture: Architecture;
  workload: Workload;
  assumptions: { assumption_id: string; confidence_level: string; production_calibrated: boolean };
  metrics: {
    usable_capacity_gb: number;
    raw_capacity_gb: number;
    raw_peak_bandwidth_GBps: number;
    sustained_peak_bandwidth_GBps: number;
    effective_bandwidth_GBps: number;
    achieved_bandwidth_GBps: number;
    demand_satisfaction_ratio: number;
    bandwidth_utilization: number;
    effective_to_sustained_efficiency: number;
    traffic_limited_by: string;
    average_latency_ns: number;
    p95_latency_ns: number;
    total_power_w: number;
    estimated_temperature_c: number;
    thermal_throttle_factor: number;
    row_hit_rate?: number | null;
    read_request_count?: number | null;
    write_request_count?: number | null;
    simulated_cycles?: number | null;
    process_yield_score?: number | null;
    process_defect_risk?: number | null;
    capacity_good_die_ratio?: number | null;
    process_bandwidth_derating_factor?: number | null;
    process_latency_penalty_ns?: number | null;
    process_power_delta_w?: number | null;
    process_thermal_resistance_delta_c_per_w?: number | null;
    reliability_margin?: number | null;
    process_confidence_level?: string | null;
    process_calibration_required?: boolean | null;
    process_public_proxy_used?: boolean | null;
    process_model_mode?: string | null;
    process_calibration_artifact_id?: string | null;
    process_calibration_dataset_id?: string | null;
    process_calibration_model_version?: string | null;
    process_calibration_sample_count?: number | null;
    process_stage_risks?: Record<string, number> | null;
    process_notes?: string[] | null;
    backend_metadata: {
      status?: string;
      backend?: string;
      cycle_accurate?: boolean;
      artifacts?: Record<string, string>;
      [key: string]: unknown;
    };
    assumption_coverage: {
      coverage_ratio: number;
      missing_critical_factors: string[];
    };
  };
  constraints: {
    is_feasible: boolean;
    violated_constraints: string[];
    warnings: string[];
    margins: Record<string, number>;
  };
  feasibility_score: number;
  bottlenecks: string[];
  recommendations: Array<{
    code: string;
    severity: string;
    message: string;
    suggested_actions: string[];
  }>;
  metadata: {
    simulation_mode: string;
  };
};

type RunSummary = {
  run_id: string;
  label: string;
  generation: string;
  score: number;
  is_feasible: boolean;
  created_at: string;
};

const defaultTarget: Target = {
  capacity_gb: 64,
  target_bandwidth_GBps: 1400,
  power_budget_w: 150,
  max_temperature_c: 110,
  priority: "bandwidth_first",
  power_policy: "warn",
  thermal_policy: "hard_limit",
  bandwidth_constraint_metric: "effective"
};

const defaultProcessInputs: ProcessInputState = {
  wafer_good_die_ratio: 0.96,
  cell_repair_fraction: 0.02,
  leakage_current_distribution: 0.2,
  tsv_continuity_fail_rate: 0.001,
  tsv_resistance_distribution_mohm: 35,
  tsv_void_fraction: 0.01,
  post_thinning_ttv_um: 3,
  wafer_warpage_um: 60,
  backside_crack_chipping_density: 0.05,
  micro_bump_height_coplanarity_sigma_um: 1,
  micro_bump_open_short_rate: 0.001,
  die_to_die_overlay_error_um: 0.3,
  bond_void_fraction: 0.01,
  underfill_void_fraction: 0.01,
  thermal_interface_void_fraction: 0.02
};

const processFieldGroups: Array<{
  title: string;
  fields: Array<{ key: keyof ProcessInputState; label: string; unit: string }>;
}> = [
  {
    title: "DRAM Wafer Fab",
    fields: [
      { key: "wafer_good_die_ratio", label: "Good Die Ratio", unit: "ratio" },
      { key: "cell_repair_fraction", label: "Cell Repair", unit: "ratio" },
      { key: "leakage_current_distribution", label: "Leakage Index", unit: "index" }
    ]
  },
  {
    title: "TSV",
    fields: [
      { key: "tsv_continuity_fail_rate", label: "Continuity Fail", unit: "ratio" },
      { key: "tsv_resistance_distribution_mohm", label: "Resistance", unit: "mOhm" },
      { key: "tsv_void_fraction", label: "Void Fraction", unit: "ratio" }
    ]
  },
  {
    title: "Thinning",
    fields: [
      { key: "post_thinning_ttv_um", label: "TTV", unit: "um" },
      { key: "wafer_warpage_um", label: "Warpage", unit: "um" },
      { key: "backside_crack_chipping_density", label: "Crack Density", unit: "count/mm2" }
    ]
  },
  {
    title: "Bump/Bond",
    fields: [
      { key: "micro_bump_height_coplanarity_sigma_um", label: "Coplanarity Sigma", unit: "um" },
      { key: "micro_bump_open_short_rate", label: "Open/Short", unit: "ratio" },
      { key: "die_to_die_overlay_error_um", label: "Overlay Error", unit: "um" },
      { key: "bond_void_fraction", label: "Bond Void", unit: "ratio" }
    ]
  },
  {
    title: "Package",
    fields: [
      { key: "underfill_void_fraction", label: "Underfill Void", unit: "ratio" },
      { key: "thermal_interface_void_fraction", label: "TIM Void", unit: "ratio" }
    ]
  }
];

function App() {
  const [health, setHealth] = useState<"online" | "offline">("offline");
  const [ramulatorStatus, setRamulatorStatus] = useState("unknown");
  const [presets, setPresets] = useState<Presets | null>(null);
  const [target, setTarget] = useState<Target>(defaultTarget);
  const [architecture, setArchitecture] = useState<Architecture | null>(null);
  const [architecturePreset, setArchitecturePreset] = useState("hbm3e_8hi_24gb");
  const [workloadPreset, setWorkloadPreset] = useState("ai_training");
  const [assumptionPreset, setAssumptionPreset] = useState("public_hbm_mvp_v0");
  const [simulationMode, setSimulationMode] = useState<"analytical" | "ramulator2">("analytical");
  const [processEnabled, setProcessEnabled] = useState(false);
  const [processInputs, setProcessInputs] = useState<ProcessInputState>(defaultProcessInputs);
  const [result, setResult] = useState<DesignCandidate | null>(null);
  const [compareResults, setCompareResults] = useState<DesignCandidate[]>([]);
  const [report, setReport] = useState("");
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    if (!presets) return;
    const preset = presets.architecture_presets[architecturePreset];
    if (preset) {
      setArchitecture(scaleArchitecture(preset, Math.max(2, target.capacity_gb > 48 ? 4 : 2)));
    }
  }, [presets, architecturePreset]);

  const metricChart = useMemo(() => {
    if (!result) return [];
    return [
      {
        name: "Capacity",
        actual: round(result.metrics.usable_capacity_gb),
        target: target.capacity_gb
      },
      {
        name: "Bandwidth",
        actual: round(result.metrics.effective_bandwidth_GBps),
        target: target.target_bandwidth_GBps
      },
      {
        name: "Power",
        actual: round(result.metrics.total_power_w),
        target: target.power_budget_w
      },
      {
        name: "Thermal",
        actual: round(result.metrics.estimated_temperature_c),
        target: target.max_temperature_c
      }
    ];
  }, [result, target]);

  async function refreshAll() {
    await Promise.all([fetchHealth(), fetchPresets(), fetchRuns(), fetchRamulatorStatus()]);
  }

  async function fetchHealth() {
    try {
      const response = await fetch(`${API_BASE}/health`);
      setHealth(response.ok ? "online" : "offline");
    } catch {
      setHealth("offline");
    }
  }

  async function fetchPresets() {
    try {
      const response = await fetch(`${API_BASE}/presets`);
      const data = await response.json();
      setPresets(data);
    } catch {
      setError("Failed to load presets.");
    }
  }

  async function fetchRamulatorStatus() {
    try {
      const response = await fetch(`${API_BASE}/backends/ramulator2/status`);
      const data = await response.json();
      setRamulatorStatus(data.available ? "available" : data.config_replay_available ? "config replay" : "not installed");
    } catch {
      setRamulatorStatus("unknown");
    }
  }

  async function fetchRuns() {
    try {
      const response = await fetch(`${API_BASE}/runs`);
      const data = await response.json();
      setRuns(data.runs || []);
    } catch {
      setRuns([]);
    }
  }

  async function runSimulation() {
    if (!architecture) return;
    setBusy(true);
    setError("");
    setReport("");
    try {
      const response = await fetch(`${API_BASE}/simulate/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target,
          candidate_label: `${architecture.generation.toUpperCase()} ${architecture.stack_count}S`,
          architecture,
          workload_preset: workloadPreset,
          assumption_preset: assumptionPreset,
          simulation_mode: simulationMode,
          backend_options:
            simulationMode === "ramulator2"
              ? { trace_request_count: 4096, max_controllers: 4, frontend: "load_store_trace" }
              : {},
          process_parameters: buildProcessParameters()
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Simulation failed.");
      setResult(data);
      setCompareResults([]);
      await Promise.all([loadReport(data.run_id), fetchRuns()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function compareCandidates() {
    if (!architecture) return;
    setBusy(true);
    setError("");
    try {
      const variants = buildCompareVariants(architecture);
      const response = await fetch(`${API_BASE}/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target,
          candidates: variants.map((variant) => ({
            candidate_label: `${variant.generation.toUpperCase()} ${variant.stack_count}S`,
            architecture: variant,
            workload_preset: workloadPreset,
            assumption_preset: assumptionPreset,
            simulation_mode: simulationMode,
            backend_options:
              simulationMode === "ramulator2"
                ? { trace_request_count: 4096, max_controllers: 4, frontend: "load_store_trace" }
                : {},
            process_parameters: buildProcessParameters()
          }))
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Compare failed.");
      setCompareResults(data.results);
      setResult(data.results[0]);
      await Promise.all([loadReport(data.results[0].run_id), fetchRuns()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed.");
    } finally {
      setBusy(false);
    }
  }

  async function loadReport(runId: string) {
    const response = await fetch(`${API_BASE}/report/${runId}`);
    setReport(await response.text());
  }

  function updateTarget(key: keyof Target, value: number | string) {
    setTarget((current) => ({ ...current, [key]: value }));
  }

  function updateArchitecture(key: keyof Architecture, value: number | string | boolean) {
    setArchitecture((current) => {
      if (!current) return current;
      const updated = { ...current, [key]: value } as Architecture;
      return normalizeArchitecture(updated);
    });
  }

  function updateProcessInput(key: keyof ProcessInputState, value: number) {
    setProcessInputs((current) => ({ ...current, [key]: value }));
  }

  function buildProcessParameters(): ProcessParameters | undefined {
    if (!processEnabled) return undefined;
    return buildProcessParametersPayload(processInputs);
  }

  const activeResults = compareResults.length ? compareResults : result ? [result] : [];

  return (
    <main className="app-shell">
      <aside className="left-panel">
        <div className="brand-row">
          <Database size={24} />
          <div>
            <h1>HBM E2E</h1>
            <span>Design Workbench</span>
          </div>
        </div>

        <section className="panel-section">
          <SectionTitle icon={<Activity size={17} />} title="Product Target" />
          <NumberInput label="Capacity GB" value={target.capacity_gb} onChange={(value) => updateTarget("capacity_gb", value)} />
          <NumberInput label="Bandwidth GB/s" value={target.target_bandwidth_GBps} onChange={(value) => updateTarget("target_bandwidth_GBps", value)} />
          <NumberInput label="Power W" value={target.power_budget_w} onChange={(value) => updateTarget("power_budget_w", value)} />
          <NumberInput label="Temperature C" value={target.max_temperature_c} onChange={(value) => updateTarget("max_temperature_c", value)} />
          <SelectInput
            label="Priority"
            value={target.priority}
            options={["balanced", "bandwidth_first", "power_first", "capacity_first", "latency_first"]}
            onChange={(value) => updateTarget("priority", value)}
          />
        </section>

        <section className="panel-section">
          <SectionTitle icon={<Server size={17} />} title="Architecture" />
          <SelectInput
            label="Preset"
            value={architecturePreset}
            options={Object.keys(presets?.architecture_presets || {})}
            onChange={setArchitecturePreset}
          />
          {architecture && (
            <>
              <SelectInput
                label="Generation"
                value={architecture.generation}
                options={["hbm2e", "hbm3", "hbm3e"]}
                onChange={(value) => updateArchitecture("generation", value)}
              />
              <NumberInput label="Stacks" value={architecture.stack_count} onChange={(value) => updateArchitecture("stack_count", value)} />
              <SelectInput
                label="Stack Height"
                value={String(architecture.stack_height)}
                options={["4", "8", "12", "16"]}
                onChange={(value) => updateArchitecture("stack_height", Number(value))}
              />
              <NumberInput label="Die Capacity GB" value={architecture.die_capacity_gb} onChange={(value) => updateArchitecture("die_capacity_gb", value)} />
              <NumberInput label="Data Rate Gb/s" value={architecture.data_rate_gbps_per_pin} onChange={(value) => updateArchitecture("data_rate_gbps_per_pin", value)} />
              <NumberInput label="Channels/Stack" value={architecture.channel_count_per_stack} onChange={(value) => updateArchitecture("channel_count_per_stack", value)} />
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={architecture.on_die_ecc}
                  onChange={(event) => updateArchitecture("on_die_ecc", event.target.checked)}
                />
                <span>On-die ECC</span>
              </label>
            </>
          )}
        </section>

        <section className="panel-section">
          <SectionTitle icon={<BarChart3 size={17} />} title="Workload" />
          <SelectInput
            label="Workload"
            value={workloadPreset}
            options={Object.keys(presets?.workload_presets || {})}
            onChange={setWorkloadPreset}
          />
          <SelectInput
            label="Assumption"
            value={assumptionPreset}
            options={Object.keys(presets?.assumption_presets || {})}
            onChange={setAssumptionPreset}
          />
          <SelectInput
            label="Simulation"
            value={simulationMode}
            options={["analytical", "ramulator2"]}
            onChange={(value) => setSimulationMode(value as "analytical" | "ramulator2")}
          />
        </section>

        <section className="panel-section">
          <SectionTitle icon={<Activity size={17} />} title="Process Quality" />
          <label className="check-row">
            <input
              type="checkbox"
              checked={processEnabled}
              onChange={(event) => setProcessEnabled(event.target.checked)}
            />
            <span>Enable process proxy</span>
          </label>
          {processEnabled && (
            <div className="process-inputs">
              {processFieldGroups.map((group) => (
                <div key={group.title} className="process-group">
                  <h3>{group.title}</h3>
                  {group.fields.map((field) => (
                    <NumberInput
                      key={field.key}
                      label={`${field.label} ${field.unit}`}
                      value={processInputs[field.key]}
                      onChange={(value) => updateProcessInput(field.key, value)}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </section>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="status-group">
            <Badge tone={health === "online" ? "good" : "bad"}>API {health}</Badge>
            <Badge tone={ramulatorStatus === "available" ? "good" : "neutral"}>Ramulator2 {ramulatorStatus}</Badge>
            {result && <Badge tone={result.constraints.is_feasible ? "good" : "bad"}>{result.constraints.is_feasible ? "Feasible" : "Infeasible"}</Badge>}
          </div>
          <div className="actions">
            <button type="button" className="icon-button" onClick={refreshAll} title="Refresh">
              <RefreshCw size={17} />
            </button>
            <button type="button" onClick={compareCandidates} disabled={busy || !architecture}>
              <GitCompare size={17} />
              Compare
            </button>
            <button type="button" className="primary" onClick={runSimulation} disabled={busy || !architecture}>
              <Play size={17} />
              Run
            </button>
          </div>
        </header>

        {error && <div className="error-strip">{error}</div>}

        <section className="metric-grid">
          <MetricCard
            icon={<BarChart3 size={18} />}
            label="Effective Bandwidth"
            value={formatNumber(result?.metrics.effective_bandwidth_GBps, " GB/s")}
            detail={result ? marginText(result.metrics.effective_bandwidth_GBps - target.target_bandwidth_GBps, " GB/s") : "N/A"}
            tone={result && result.metrics.effective_bandwidth_GBps >= target.target_bandwidth_GBps ? "good" : "warn"}
          />
          <MetricCard
            icon={<Database size={18} />}
            label="Usable Capacity"
            value={formatNumber(result?.metrics.usable_capacity_gb, " GB")}
            detail={result ? marginText(result.metrics.usable_capacity_gb - target.capacity_gb, " GB") : "N/A"}
            tone={result && result.metrics.usable_capacity_gb >= target.capacity_gb ? "good" : "warn"}
          />
          <MetricCard
            icon={<Zap size={18} />}
            label="Total Power"
            value={formatNumber(result?.metrics.total_power_w, " W")}
            detail={result ? marginText(target.power_budget_w - result.metrics.total_power_w, " W") : "N/A"}
            tone={result && result.metrics.total_power_w <= target.power_budget_w ? "good" : "warn"}
          />
          <MetricCard
            icon={<Thermometer size={18} />}
            label="Thermal"
            value={formatNumber(result?.metrics.estimated_temperature_c, " C")}
            detail={result ? marginText(target.max_temperature_c - result.metrics.estimated_temperature_c, " C") : "N/A"}
            tone={result && result.metrics.estimated_temperature_c <= target.max_temperature_c ? "good" : "warn"}
          />
        </section>

        <section className="content-grid">
          <div className="main-column">
            <section className="work-section chart-section">
              <SectionTitle icon={<BarChart3 size={17} />} title="Metric Chart" />
              <div className="chart-box">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={metricChart}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="actual" fill="#2f7d6b" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="target" fill="#b66a2c" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="work-section">
              <SectionTitle icon={<GitCompare size={17} />} title="Candidate Ranking" />
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Candidate</th>
                      <th>Gen</th>
                      <th>Cap GB</th>
                      <th>BW GB/s</th>
                      <th>Power W</th>
                      <th>Temp C</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeResults.map((item) => (
                      <tr key={item.run_id} className={item.constraints.is_feasible ? "" : "muted-row"}>
                        <td>{item.label}</td>
                        <td>{item.architecture.generation.toUpperCase()}</td>
                        <td>{round(item.metrics.usable_capacity_gb)}</td>
                        <td>{round(item.metrics.effective_bandwidth_GBps)}</td>
                        <td>{round(item.metrics.total_power_w)}</td>
                        <td>{round(item.metrics.estimated_temperature_c)}</td>
                        <td>{round(item.feasibility_score * 100)}</td>
                      </tr>
                    ))}
                    {!activeResults.length && (
                      <tr>
                        <td colSpan={7} className="empty-cell">N/A</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <div className="side-column">
            <section className="work-section">
              <SectionTitle icon={<Activity size={17} />} title="Constraints" />
              <Badge tone={result?.constraints.is_feasible ? "good" : result ? "bad" : "neutral"}>
                {result ? (result.constraints.is_feasible ? "Feasible" : "Infeasible") : "N/A"}
              </Badge>
              <KeyValue label="Violations" value={result?.constraints.violated_constraints.join(", ") || "none"} />
              <KeyValue label="Warnings" value={result?.constraints.warnings.join(", ") || "none"} />
              <KeyValue label="Traffic" value={result?.metrics.traffic_limited_by || "N/A"} />
              <KeyValue label="Backend" value={result?.metrics.backend_metadata?.status || result?.metadata?.simulation_mode || "N/A"} />
              <KeyValue label="Confidence" value={result?.assumptions.confidence_level?.toUpperCase() || "N/A"} />
              <KeyValue label="Coverage" value={result ? `${round(result.metrics.assumption_coverage.coverage_ratio * 100)}%` : "N/A"} />
            </section>

            <section className="work-section">
              <SectionTitle icon={<Activity size={17} />} title="Process Quality" />
              <KeyValue label="Yield" value={formatOptionalPercent(result?.metrics.process_yield_score)} />
              <KeyValue label="Defect Risk" value={formatOptionalPercent(result?.metrics.process_defect_risk)} />
              <KeyValue label="Good Die" value={formatOptionalPercent(result?.metrics.capacity_good_die_ratio)} />
              <KeyValue label="BW Derating" value={formatOptionalNumber(result?.metrics.process_bandwidth_derating_factor)} />
              <KeyValue label="Latency Add" value={formatOptionalNumber(result?.metrics.process_latency_penalty_ns)} />
              <KeyValue label="Power Add" value={formatOptionalNumber(result?.metrics.process_power_delta_w)} />
              <KeyValue label="Reliability" value={formatOptionalPercent(result?.metrics.reliability_margin)} />
              <KeyValue label="Mode" value={result?.metrics.process_model_mode || "N/A"} />
              <KeyValue label="Dataset" value={result?.metrics.process_calibration_dataset_id || "N/A"} />
              <KeyValue label="Model Ver" value={result?.metrics.process_calibration_model_version || "N/A"} />
              <KeyValue label="Samples" value={formatOptionalNumber(result?.metrics.process_calibration_sample_count)} />
              <KeyValue label="Calibration" value={result?.metrics.process_calibration_required === undefined || result?.metrics.process_calibration_required === null ? "N/A" : String(result.metrics.process_calibration_required)} />
              <div className="stage-risk-list">
                {Object.entries(result?.metrics.process_stage_risks || {}).map(([stage, risk]) => (
                  <KeyValue key={stage} label={stageLabel(stage)} value={formatOptionalPercent(risk)} />
                ))}
                {!Object.keys(result?.metrics.process_stage_risks || {}).length && <div className="empty-cell">N/A</div>}
              </div>
            </section>

            <section className="work-section">
              <SectionTitle icon={<Server size={17} />} title="Backend Evidence" />
              <KeyValue label="Backend" value={result?.metrics.backend_metadata?.backend || "N/A"} />
              <KeyValue label="Status" value={result?.metrics.backend_metadata?.status || "N/A"} />
              <KeyValue
                label="Cycle Accurate"
                value={
                  result?.metrics.backend_metadata?.cycle_accurate === undefined
                    ? "N/A"
                    : String(result.metrics.backend_metadata.cycle_accurate)
                }
              />
              <KeyValue label="Cycles" value={formatOptionalNumber(result?.metrics.simulated_cycles)} />
              <KeyValue label="Reads" value={formatOptionalNumber(result?.metrics.read_request_count)} />
              <KeyValue label="Writes" value={formatOptionalNumber(result?.metrics.write_request_count)} />
              <KeyValue label="Row Hit" value={formatOptionalPercent(result?.metrics.row_hit_rate)} />
              <KeyValue
                label="Artifacts"
                value={String(Object.keys(result?.metrics.backend_metadata?.artifacts || {}).length || "N/A")}
              />
              <KeyValue
                label="Files"
                value={artifactNames(result?.metrics.backend_metadata?.artifacts)}
              />
            </section>

            <section className="work-section">
              <SectionTitle icon={<Zap size={17} />} title="Recommendations" />
              <div className="recommendation-list">
                {(result?.recommendations || []).slice(0, 5).map((rec) => (
                  <article key={rec.code} className={`rec rec-${rec.severity}`}>
                    <strong>{rec.code}</strong>
                    <p>{rec.message}</p>
                  </article>
                ))}
                {!result?.recommendations?.length && <div className="empty-cell">N/A</div>}
              </div>
            </section>

            <section className="work-section">
              <SectionTitle icon={<FileText size={17} />} title="Report" />
              <pre className="report-box">{report || "N/A"}</pre>
            </section>

            <section className="work-section">
              <SectionTitle icon={<RefreshCw size={17} />} title="Recent Runs" />
              <div className="run-list">
                {runs.slice(0, 8).map((run) => (
                  <button key={run.run_id} type="button" onClick={() => loadRun(run.run_id)}>
                    <span>{run.label}</span>
                    <Badge tone={run.is_feasible ? "good" : "bad"}>{round(run.score * 100)}</Badge>
                  </button>
                ))}
                {!runs.length && <div className="empty-cell">N/A</div>}
              </div>
            </section>
          </div>
        </section>
      </section>
    </main>
  );

  async function loadRun(runId: string) {
    const response = await fetch(`${API_BASE}/simulate/result/${runId}`);
    const data = await response.json();
    setResult(data);
    setCompareResults([]);
    await loadReport(runId);
  }
}

function SectionTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="section-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

function NumberInput({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="field-row">
      <span>{label}</span>
      <input type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function SelectInput({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="field-row">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option value={option} key={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function MetricCard({
  icon,
  label,
  value,
  detail,
  tone
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  tone: "good" | "warn" | "neutral" | false | null;
}) {
  return (
    <article className={`metric-card tone-${tone || "neutral"}`}>
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function Badge({ children, tone }: { children: React.ReactNode; tone: "good" | "bad" | "warn" | "neutral" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="key-value">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function scaleArchitecture(source: Architecture, stackCount: number): Architecture {
  return normalizeArchitecture({
    ...source,
    stack_count: stackCount
  });
}

function normalizeArchitecture(source: Architecture): Architecture {
  const dieCount = Number(source.stack_height);
  const capacityPerStack = Number(source.die_capacity_gb) * dieCount;
  const totalCapacity = capacityPerStack * Number(source.stack_count);
  const pseudoWidth = Number(source.io_width_bits_per_stack) / Number(source.channel_count_per_stack) / Number(source.pseudo_channels_per_channel);
  return {
    ...source,
    die_count_per_stack: dieCount,
    capacity_per_stack_gb: round(capacityPerStack),
    total_capacity_gb: round(totalCapacity),
    pseudo_channel_width_bits: round(pseudoWidth)
  };
}

function buildProcessParametersPayload(inputs: ProcessInputState): ProcessParameters {
  return {
    schema_version: "process_proxy_v0.1",
    process_flow_id: "public_hbm_process_proxy_v0",
    source_type: "proxy",
    confidence_level: "low",
    calibration_status: "uncalibrated",
    calculation_mode: "proxy",
    dram_wafer_fab: {
      wafer_good_die_ratio: processValue(inputs.wafer_good_die_ratio, "ratio"),
      cell_repair_fraction: processValue(inputs.cell_repair_fraction, "ratio"),
      leakage_current_distribution: processValue(inputs.leakage_current_distribution, "index")
    },
    tsv: {
      tsv_continuity_fail_rate: processValue(inputs.tsv_continuity_fail_rate, "ratio"),
      tsv_resistance_distribution_mohm: processValue(inputs.tsv_resistance_distribution_mohm, "mOhm"),
      tsv_void_fraction: processValue(inputs.tsv_void_fraction, "ratio")
    },
    wafer_thinning: {
      post_thinning_ttv_um: processValue(inputs.post_thinning_ttv_um, "um"),
      wafer_warpage_um: processValue(inputs.wafer_warpage_um, "um"),
      backside_crack_chipping_density: processValue(inputs.backside_crack_chipping_density, "count/mm2")
    },
    rdl_micro_bump: {
      micro_bump_height_coplanarity_sigma_um: processValue(inputs.micro_bump_height_coplanarity_sigma_um, "um"),
      micro_bump_open_short_rate: processValue(inputs.micro_bump_open_short_rate, "ratio")
    },
    bonding: {
      bonding_technology: {
        value: "hybrid_or_micro_bump_public_proxy",
        unit: null,
        data_type: "categorical",
        calibration_required: true
      },
      die_to_die_overlay_error_um: processValue(inputs.die_to_die_overlay_error_um, "um"),
      bond_void_fraction: processValue(inputs.bond_void_fraction, "ratio")
    },
    underfill_molding: {
      underfill_void_fraction: processValue(inputs.underfill_void_fraction, "ratio")
    },
    interposer_package: {
      thermal_interface_void_fraction: processValue(inputs.thermal_interface_void_fraction, "ratio")
    }
  };
}

function processValue(value: number, unit: string): ProcessParameterValue {
  return {
    value,
    unit,
    data_type: "continuous",
    calibration_required: true
  };
}

function buildCompareVariants(current: Architecture): Architecture[] {
  const stackCount = current.stack_count;
  return [
    normalizeArchitecture({
      ...current,
      generation: "hbm3e",
      stack_count: stackCount,
      stack_height: 8,
      die_capacity_gb: 3,
      io_width_bits_per_stack: 1024,
      channel_count_per_stack: 16,
      pseudo_channels_per_channel: 2,
      data_rate_gbps_per_pin: 9.2
    }),
    normalizeArchitecture({
      ...current,
      generation: "hbm3",
      stack_count: stackCount,
      stack_height: 12,
      die_capacity_gb: 2,
      io_width_bits_per_stack: 1024,
      channel_count_per_stack: 16,
      pseudo_channels_per_channel: 2,
      data_rate_gbps_per_pin: 6.4
    }),
    normalizeArchitecture({
      ...current,
      generation: "hbm2e",
      stack_count: stackCount,
      stack_height: 8,
      die_capacity_gb: 2,
      io_width_bits_per_stack: 1024,
      channel_count_per_stack: 8,
      pseudo_channels_per_channel: 2,
      data_rate_gbps_per_pin: 3.2
    })
  ];
}

function formatNumber(value: number | undefined, suffix: string) {
  if (value === undefined || Number.isNaN(value)) return "N/A";
  return `${round(value)}${suffix}`;
}

function formatOptionalNumber(value: number | null | undefined) {
  if (value === undefined || value === null || Number.isNaN(value)) return "N/A";
  return String(round(value));
}

function formatOptionalPercent(value: number | null | undefined) {
  if (value === undefined || value === null || Number.isNaN(value)) return "N/A";
  return `${round(value * 100)}%`;
}

function artifactNames(artifacts: Record<string, string> | undefined) {
  const names = Object.keys(artifacts || {});
  if (!names.length) return "N/A";
  return names.slice(0, 5).join(", ");
}

function stageLabel(stage: string) {
  return stage
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function marginText(value: number, suffix: string) {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${round(value)}${suffix}`;
}

function round(value: number) {
  return Math.round(value * 10) / 10;
}

export default App;
