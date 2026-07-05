# HBM E2E Portable App

The portable package is a Windows folder/zip distribution that runs without installing Node.js or using the Vite development server.

## Build

From PowerShell:

```powershell
cd C:\E2E
.\scripts\package_portable.ps1
```

The script creates:

- `dist-portable/HBM-E2E-Portable-<timestamp>/`
- `dist-portable/HBM-E2E-Portable-<timestamp>.zip`

By default, the package excludes `runtime/ramulator2/lib/win_amd64/ramulator.lib` because it is only needed for relinking, not for running the app.

To include that import library:

```powershell
.\scripts\package_portable.ps1 -IncludeRamulatorImportLib
```

## Run

Unzip the package and run:

```powershell
.\start-hbm-e2e.bat
```

Open:

```text
http://127.0.0.1:8000
```

The portable launcher sets:

- `RAMULATOR2_HOME=<portable>\runtime\ramulator2`
- `HBM_E2E_STATIC_DIR=<portable>\frontend-dist`
- `HBM_E2E_RESULTS_DIR=<portable>\results`
- `HBM_E2E_CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000`

## Stop

Run:

```powershell
.\stop-hbm-e2e.bat
```

or close the backend console window.

## Expected Size

The default package is expected to be roughly:

- Folder: 35-50 MB
- Zip: 15-25 MB

The exact size depends on Python package wheels and whether the Ramulator2 import library is included.
Including `ramulator.lib` adds about 11 MB to the uncompressed folder.
