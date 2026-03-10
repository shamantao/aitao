# ============================================================================
# start-aitao.ps1 - Start all AiTao services (portable mode)
#
# Launches Meilisearch, Ollama, and AiTao API backend.
# All processes run locally, no system modification.
# ============================================================================

$ErrorActionPreference = "Stop"

# Paths relative to this script
$BASE_DIR   = $PSScriptRoot
$PYTHON_DIR = Join-Path $BASE_DIR "python"
$MEILI_DIR  = Join-Path $BASE_DIR "meilisearch"
$OLLAMA_DIR = Join-Path $BASE_DIR "ollama"
$AITAO_DIR  = Join-Path $BASE_DIR "aitao"
$DATA_DIR   = Join-Path $BASE_DIR "data"

$pythonExe  = Join-Path $PYTHON_DIR "python.exe"
$meiliExe   = Join-Path $MEILI_DIR  "meilisearch.exe"
$ollamaExe  = Join-Path $OLLAMA_DIR "ollama.exe"

# PID file to track processes
$PID_FILE   = Join-Path $DATA_DIR "pids.json"

# ============================================================================
# Pre-flight checks
# ============================================================================
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   AiTao Portable - Starting services"         -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$missing = @()
if (-not (Test-Path $pythonExe))  { $missing += "Python ($pythonExe)" }
if (-not (Test-Path $meiliExe))   { $missing += "Meilisearch ($meiliExe)" }
if (-not (Test-Path $ollamaExe))  { $missing += "Ollama ($ollamaExe)" }

if ($missing.Count -gt 0) {
    Write-Host "ERROR: Missing components:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Run setup-portable.ps1 first."
    exit 1
}

# ============================================================================
# 0. Generate config.toml if missing
# ============================================================================
$configFile    = Join-Path $AITAO_DIR "config\config.toml"
$configTemplate = Join-Path $AITAO_DIR "config\config.toml.template"

if (-not (Test-Path $configFile)) {
    Write-Host "[0/3] Generating config.toml..." -ForegroundColor Cyan

    if (Test-Path $configTemplate) {
        # Read template and replace paths for portable Windows layout
        $content = Get-Content -Path $configTemplate -Raw
        # Replace ${HOME}/.aitao/data with portable data directory
        $portableData = $DATA_DIR -replace '\\', '/'
        $content = $content -replace '\$\{HOME\}/\.aitao/data', $portableData
        $content = $content -replace '\$\{HOME\}/\.aitao/models', ($portableData + '/models')
        # Replace remaining ${HOME} with user profile
        $userHome = $env:USERPROFILE -replace '\\', '/'
        $content = $content -replace '\$\{HOME\}', $userHome
        # Write the generated config
        $configDir = Split-Path $configFile -Parent
        if (-not (Test-Path $configDir)) { New-Item -ItemType Directory -Path $configDir -Force | Out-Null }
        Set-Content -Path $configFile -Value $content -Encoding UTF8
        Write-Host "  Created: $configFile" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Template not found at $configTemplate" -ForegroundColor Yellow
        Write-Host "  AiTao may not start correctly without a config.toml"
    }
    Write-Host ""
}

# ============================================================================
# 1. Start Meilisearch
# ============================================================================
Write-Host "[1/3] Starting Meilisearch..." -ForegroundColor Cyan

$meiliDataDir = Join-Path $DATA_DIR "meilisearch"

# Check if already running
$meiliRunning = Get-Process -Name "meilisearch" -ErrorAction SilentlyContinue
if ($meiliRunning) {
    Write-Host "  Already running (PID: $($meiliRunning.Id))"
} else {
    $env:MEILI_DB_PATH = $meiliDataDir
    $env:MEILI_HTTP_ADDR = "127.0.0.1:7700"
    $env:MEILI_NO_ANALYTICS = "true"

    $meiliProcess = Start-Process -FilePath $meiliExe `
        -ArgumentList "--db-path", $meiliDataDir, "--http-addr", "127.0.0.1:7700", "--no-analytics" `
        -WindowStyle Hidden `
        -PassThru

    Write-Host "  Started (PID: $($meiliProcess.Id))" -ForegroundColor Green
    Write-Host "  URL: http://localhost:7700"
}

# ============================================================================
# 2. Start Ollama
# ============================================================================
Write-Host "[2/3] Starting Ollama..." -ForegroundColor Cyan

$ollamaDataDir = Join-Path $DATA_DIR "ollama"

# Check if already running
$ollamaRunning = Get-Process -Name "ollama*" -ErrorAction SilentlyContinue
if ($ollamaRunning) {
    Write-Host "  Already running (PID: $($ollamaRunning[0].Id))"
} else {
    # Redirect model storage to portable data dir
    $env:OLLAMA_MODELS = $ollamaDataDir
    $env:OLLAMA_HOST = "127.0.0.1:11434"

    $ollamaProcess = Start-Process -FilePath $ollamaExe `
        -ArgumentList "serve" `
        -WindowStyle Hidden `
        -PassThru

    # Wait for Ollama to be ready
    Write-Host "  Waiting for Ollama to start..."
    $ready = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 2
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch { }
    }

    if ($ready) {
        Write-Host "  Started (PID: $($ollamaProcess.Id))" -ForegroundColor Green
        Write-Host "  URL: http://localhost:11434"
    } else {
        Write-Host "  WARNING: Ollama may not be fully ready" -ForegroundColor Yellow
    }
}

# ============================================================================
# 3. Start AiTao API
# ============================================================================
Write-Host "[3/3] Starting AiTao API..." -ForegroundColor Cyan

$aitaoSrc = Join-Path $AITAO_DIR "src"
if (-not (Test-Path $aitaoSrc)) {
    Write-Host "  ERROR: AiTao source not found at $aitaoSrc" -ForegroundColor Red
    Write-Host "  Copy the src/ folder to $AITAO_DIR"
    exit 1
}

# Set environment for AiTao
$env:PYTHONPATH = $AITAO_DIR
$env:AITAO_CONFIG = Join-Path $AITAO_DIR "config\config.toml"

$aitaoProcess = Start-Process -FilePath $pythonExe `
    -ArgumentList "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8200" `
    -WorkingDirectory $AITAO_DIR `
    -WindowStyle Hidden `
    -PassThru

# Wait for API to be ready
Write-Host "  Waiting for API to start..."
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8200/api/health" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch { }
}

if ($ready) {
    Write-Host "  Started (PID: $($aitaoProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  WARNING: API may not be fully ready yet" -ForegroundColor Yellow
}

# ============================================================================
# Save PIDs for stop script
# ============================================================================
$pids = @{
    meilisearch = if ($meiliProcess)  { $meiliProcess.Id }  elseif ($meiliRunning)  { $meiliRunning.Id }  else { $null }
    ollama      = if ($ollamaProcess) { $ollamaProcess.Id } elseif ($ollamaRunning) { $ollamaRunning[0].Id } else { $null }
    aitao       = if ($aitaoProcess)  { $aitaoProcess.Id }  else { $null }
}

$pids | ConvertTo-Json | Set-Content -Path $PID_FILE
Write-Host ""
Write-Host "  PIDs saved to: $PID_FILE"

# ============================================================================
# Summary
# ============================================================================
Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "   All services started!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  AiTao API:     http://localhost:8200"
Write-Host "  Health Check:  http://localhost:8200/api/health"
Write-Host "  Meilisearch:   http://localhost:7700"
Write-Host "  Ollama:        http://localhost:11434"
Write-Host ""
Write-Host "  Stop all:  .\stop-aitao.ps1"
Write-Host ""
