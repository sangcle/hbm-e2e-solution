param(
    [string]$PythonVersion = "3.11.8",
    [string]$PackageName = "",
    [switch]$IncludeRamulatorImportLib,
    [switch]$NoZip
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $PackageName) {
    $PackageName = "HBM-E2E-Portable-" + (Get-Date -Format "yyyyMMdd-HHmm")
}

$buildRoot = Join-Path $repoRoot "dist-portable"
$packageRoot = Join-Path $buildRoot $PackageName
$cacheRoot = Join-Path $repoRoot ".cache"
$pythonZip = Join-Path $cacheRoot "python-$PythonVersion-embed-amd64.zip"
$pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"

function Remove-DirectoryIfInside {
    param(
        [string]$Path,
        [string]$Parent
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $resolvedPath = (Resolve-Path -LiteralPath $Path).Path
    $resolvedParent = (Resolve-Path -LiteralPath $Parent).Path
    if (-not $resolvedPath.StartsWith($resolvedParent, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside build root: $resolvedPath"
    }
    Remove-Item -LiteralPath $resolvedPath -Recurse -Force
}

function Remove-DirectoryByName {
    param(
        [string]$Root,
        [string]$Name
    )
    Get-ChildItem -LiteralPath $Root -Recurse -Force -Directory -Filter $Name -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
}

New-Item -ItemType Directory -Force -Path $buildRoot, $cacheRoot | Out-Null
Remove-DirectoryIfInside -Path $packageRoot -Parent $buildRoot

New-Item -ItemType Directory -Force -Path `
    $packageRoot, `
    (Join-Path $packageRoot "app"), `
    (Join-Path $packageRoot "frontend-dist"), `
    (Join-Path $packageRoot "runtime"), `
    (Join-Path $packageRoot "results"), `
    (Join-Path $packageRoot "logs") | Out-Null

Write-Host "Building frontend..."
Push-Location (Join-Path $repoRoot "frontend")
try {
    npm run build
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $pythonZip)) {
    Write-Host "Downloading Python embeddable runtime $PythonVersion..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip
}

$portablePython = Join-Path $packageRoot "python"
Expand-Archive -LiteralPath $pythonZip -DestinationPath $portablePython -Force

$sitePackages = Join-Path $portablePython "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null

$pthFile = Get-ChildItem -LiteralPath $portablePython -Filter "python*._pth" | Select-Object -First 1
if (-not $pthFile) {
    throw "Could not find Python embedded ._pth file."
}
$stdlibZip = Get-ChildItem -LiteralPath $portablePython -Filter "python*.zip" | Select-Object -First 1
if (-not $stdlibZip) {
    throw "Could not find Python embedded standard library zip."
}
@(
    $stdlibZip.Name,
    ".",
    "Lib\site-packages",
    "..\app",
    "import site"
) | Set-Content -LiteralPath $pthFile.FullName -Encoding ASCII

Write-Host "Installing runtime Python dependencies..."
$hostPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $hostPython)) {
    $hostPython = "python"
}
& $hostPython -m pip install --upgrade --target $sitePackages --no-warn-script-location -r (Join-Path $repoRoot "backend\requirements-runtime.txt")

Write-Host "Copying application files..."
Copy-Item -LiteralPath (Join-Path $repoRoot "backend") -Destination (Join-Path $packageRoot "app\backend") -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "frontend\dist\*") -Destination (Join-Path $packageRoot "frontend-dist") -Recurse -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "runtime\ramulator2") -Destination (Join-Path $packageRoot "runtime\ramulator2") -Recurse -Force

if (-not $IncludeRamulatorImportLib) {
    $importLibDir = Join-Path $packageRoot "runtime\ramulator2\lib"
    if (Test-Path -LiteralPath $importLibDir) {
        Remove-Item -LiteralPath $importLibDir -Recurse -Force
    }
}

Copy-Item -LiteralPath (Join-Path $repoRoot "README.md") -Destination $packageRoot -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination $packageRoot -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "THIRD_PARTY_NOTICES.md") -Destination $packageRoot -Force
Copy-Item -LiteralPath (Join-Path $repoRoot ".env.example") -Destination $packageRoot -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "docs") -Destination (Join-Path $packageRoot "docs") -Recurse -Force

Remove-DirectoryByName -Root $packageRoot -Name "__pycache__"
Remove-DirectoryByName -Root $packageRoot -Name ".pytest_cache"

$startBat = @'
@echo off
setlocal
set "APP_DIR=%~dp0"
set "RAMULATOR2_HOME=%APP_DIR%runtime\ramulator2"
set "HBM_E2E_STATIC_DIR=%APP_DIR%frontend-dist"
set "HBM_E2E_RESULTS_DIR=%APP_DIR%results"
set "HBM_E2E_CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000"
set "HBM_E2E_CORS_ALLOW_LOCAL_DEV_PORTS=false"
if not exist "%HBM_E2E_RESULTS_DIR%" mkdir "%HBM_E2E_RESULTS_DIR%"
if not exist "%APP_DIR%logs" mkdir "%APP_DIR%logs"
echo Starting HBM E2E portable backend on http://127.0.0.1:8000
start "HBM E2E Backend" /D "%APP_DIR%" cmd /k ""%APP_DIR%python\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8000"
endlocal
'@
$startBat | Set-Content -LiteralPath (Join-Path $packageRoot "start-hbm-e2e.bat") -Encoding ASCII

$stopBat = @'
@echo off
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  echo Stopping process %%p on port 8000
  taskkill /PID %%p /F
)
'@
$stopBat | Set-Content -LiteralPath (Join-Path $packageRoot "stop-hbm-e2e.bat") -Encoding ASCII

$portableReadme = @"
# HBM E2E Portable

Run `start-hbm-e2e.bat` and open `http://127.0.0.1:8000`.

This portable package serves both the FastAPI backend and the built React frontend from one local backend process.

Included:

- `python/` - Python $PythonVersion embeddable runtime plus runtime dependencies
- `app/backend/` - HBM E2E backend source
- `frontend-dist/` - built frontend assets
- `runtime/ramulator2/` - Ramulator2 runtime bundle
- `results/` - local simulation outputs

Stop the backend with `stop-hbm-e2e.bat` or by closing the backend console window.

If port 8000 is already in use, edit `start-hbm-e2e.bat` and change the `--port` value.
"@
$portableReadme | Set-Content -LiteralPath (Join-Path $packageRoot "PORTABLE_README.md") -Encoding UTF8

$sizeBytes = (Get-ChildItem -LiteralPath $packageRoot -Recurse -Force -File | Measure-Object Length -Sum).Sum
$sizeMb = [Math]::Round($sizeBytes / 1MB, 2)
Write-Host "Portable folder: $packageRoot"
Write-Host "Portable folder size: $sizeMb MB"

if (-not $NoZip) {
    $zipPath = Join-Path $buildRoot "$PackageName.zip"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Write-Host "Creating zip: $zipPath"
    Compress-Archive -LiteralPath $packageRoot -DestinationPath $zipPath -Force
    $zipSizeBytes = (Get-Item -LiteralPath $zipPath).Length
    $zipSizeMb = [Math]::Round($zipSizeBytes / 1MB, 2)
    Write-Host "Zip size: $zipSizeMb MB"
}
