# HBM E2E

HBM E2E is a local design exploration workbench for comparing HBM2E, HBM3, and HBM3E memory stack candidates against product targets, workload presets, and explicit modeling assumptions.

License: MIT. Third-party runtime notices are listed in `THIRD_PARTY_NOTICES.md`.

## Contact

- LinkedIn ID: `minyong-choi-a60645260`
- LinkedIn URL: `https://www.linkedin.com/in/minyong-choi-a60645260/`

The MVP includes:

- FastAPI backend with stable domain models, synchronous simulation APIs, result storage, Markdown reports, and Ramulator2 status/stats adapter hooks.
- Analytical simulation engine for capacity, bandwidth, utilization, latency, power, thermal, constraints, score, bottlenecks, and recommendations.
- React/Vite frontend workbench for target input, candidate editing, preset selection, metric cards, candidate comparison, charts, recommendations, reports, and recent runs.
- Pytest regression tests for golden bandwidth formulas, validation, result persistence, comparison ordering, and Ramulator2 stats parsing.

## Run Backend

```powershell
cd C:\E2E
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Run Frontend

```powershell
cd C:\E2E\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

The frontend expects the backend at `http://127.0.0.1:8000`. Override it with `VITE_API_BASE` if needed.

For alternate local frontend ports, set `HBM_E2E_CORS_ALLOW_LOCAL_DEV_PORTS=true` before starting the backend. For public deployment, set `HBM_E2E_CORS_ORIGINS` to the exact production frontend origin and leave local dev port expansion disabled.

## API

- `GET /health`
- `GET /presets`
- `GET /runs`
- `GET /runs/{run_id}/artifacts`
- `GET /runs/{run_id}/artifacts/{artifact_path}`
- `GET /backends/ramulator2/status`
- `POST /concept/evaluate`
- `POST /simulate/run`
- `POST /compare`
- `GET /simulate/result/{run_id}`
- `GET /report/{run_id}`

Results are written below `results/<run_id>/` with `result.json`, `metadata.json`, `input.json`, and `report.md`.
Ramulator2 backend artifacts are written below `results/<run_id>/backend/` and can be listed or read through the `/runs/{run_id}/artifacts` APIs.

## Deployment Manual

See `docs/DEPLOYMENT.md` for deployment steps, verification commands, release checklist, and the LinkedIn ID field used in release metadata.

See `docs/PUBLIC_RELEASE_REVIEW.md` for the latest private-to-public repository review notes.

## Ramulator2 Mode

The backend has a real Ramulator2 integration path. By default it uses the checked runtime bundle in `runtime/ramulator2`; set `RAMULATOR2_HOME` to point at a full source checkout when rebuilding or testing a different Ramulator2 tree.

- `simulation_mode: "ramulator2"` generates `results/<run_id>/backend/trace.txt`.
- It exports `ramulator_config.json` and `ramulator_config.yaml` using the bundled Ramulator2 Python DSL.
- It writes `ramulator_hbm_input.json` and a standalone `run_ramulator2.py` with absolute paths and Python path setup so the exact backend run is reproducible.
- If `ramulator._ramulator` is built, the local runner executes the generated script, captures `sim.stats.json` and `sim.stats.yaml`, and maps Ramulator2 stats back into `SimulationMetrics`.
- If the C++ extension is unavailable, the API uses a deterministic Python timing replay over the generated Ramulator2 config and trace, writes `sim.stats.json` and `sim.stats.yaml`, and records `backend_metadata.status = "config_replay_completed"`. This fallback reads the expanded HBM timing values from Ramulator2 config and models open-row hits, misses, conflicts, ACT/PRE/CAS timing, and queue delay. It is not the compiled Ramulator2 cycle engine and is marked with `cycle_accurate = false`.
- Set `backend_options.allow_config_replay = false` to require the real C++ extension and return `backend_metadata.status = "unavailable_cpp_extension"` when it is missing.

HBM3E is approximated through the closest bundled Ramulator2 HBM3 preset because this Ramulator2 runtime exposes HBM3/HBM4 standards, not a separate HBM3E class or HBM3E 9.2 Gb/s timing preset. Analytical capacity and bandwidth still use the requested HBM3E architecture; Ramulator2 evidence is used for latency, row-hit, and request counter normalization when stats are available.

`GET /backends/ramulator2/status` returns:

- `can_run`: true when either compiled Ramulator2 or Python timing replay is usable.
- `cpp_extension_available`: true only when `ramulator._ramulator` imports successfully.
- `config_replay_available`: true when the Ramulator2 Python DSL is available.
- `build`: runtime/source diagnostics plus build command hints.

The checked `runtime/ramulator2` bundle includes the Windows x64 Python 3.11 C++ extension, `ramulator.dll`, and `lib/win_amd64/ramulator.lib`. To refresh it, rebuild the full `ramulator2/` source checkout and copy the generated files back into the runtime bundle.
