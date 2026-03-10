# ============================================================================
# uninstall-aitao.ps1 - Complete uninstall of AiTao portable environment
#
# Stops all running services then removes installed components.
# Offers choice to keep or delete user data (models, indexes, config).
# ============================================================================

$ErrorActionPreference = "Stop"

$BASE_DIR   = $PSScriptRoot
$PYTHON_DIR = Join-Path $BASE_DIR "python"
$MEILI_DIR  = Join-Path $BASE_DIR "meilisearch"
$OLLAMA_DIR = Join-Path $BASE_DIR "ollama"
$AITAO_DIR  = Join-Path $BASE_DIR "aitao"
$DATA_DIR   = Join-Path $BASE_DIR "data"
$TEMP_DIR   = Join-Path $BASE_DIR "_temp"

# ============================================================================
# Banner
# ============================================================================
Write-Host ""
Write-Host "===============================================" -ForegroundColor Red
Write-Host "   AiTao Portable - Uninstall"                  -ForegroundColor Red
Write-Host "===============================================" -ForegroundColor Red
Write-Host ""
Write-Host "  Install location: $BASE_DIR"
Write-Host ""

# ============================================================================
# Confirmation
# ============================================================================
Write-Host "This will remove AiTao and all its components." -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "  Are you sure? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host ""
    Write-Host "  Uninstall cancelled." -ForegroundColor Green
    exit 0
}

# ============================================================================
# 1. Stop running services
# ============================================================================
Write-Host ""
Write-Host "[1/4] Stopping running services..." -ForegroundColor Cyan
Write-Host ("-" * 50)

# Stop by process name (reliable even without PID file)
$services = @(
    @{ Name = "meilisearch";         Label = "Meilisearch" },
    @{ Name = "ollama";              Label = "Ollama" },
    @{ Name = "ollama_llama_server"; Label = "Ollama LLM server" }
)

foreach ($svc in $services) {
    $procs = Get-Process -Name $svc.Name -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "  Stopped $($svc.Label)" -ForegroundColor Green
    } else {
        Write-Host "  $($svc.Label) not running"
    }
}

# Stop Python/uvicorn on port 8200
$netstat = netstat -ano 2>$null | Select-String ":8200\s"
if ($netstat) {
    foreach ($line in $netstat) {
        if ($line -match "\s+(\d+)$") {
            $pid = $Matches[1]
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  Stopped AiTao API (PID: $pid)" -ForegroundColor Green
            } catch { }
        }
    }
} else {
    Write-Host "  AiTao API not running"
}

# Remove PID file
$pidFile = Join-Path $DATA_DIR "pids.json"
if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Host "  OK - All services stopped" -ForegroundColor Green

# ============================================================================
# 2. Ask about user data
# ============================================================================
Write-Host ""
Write-Host "[2/4] User data decision..." -ForegroundColor Cyan
Write-Host ("-" * 50)

$keepData = $false
if (Test-Path $DATA_DIR) {
    # Calculate data size
    $dataSize = (Get-ChildItem -Path $DATA_DIR -Recurse -ErrorAction SilentlyContinue |
                 Measure-Object -Property Length -Sum).Sum
    $dataSizeMB = [math]::Round($dataSize / 1MB, 1)

    Write-Host ""
    Write-Host "  The data/ folder contains $dataSizeMB MB:" -ForegroundColor Yellow
    Write-Host "    - Ollama models (downloaded LLMs)"
    Write-Host "    - Meilisearch indexes (your documents)"
    Write-Host "    - AiTao config and logs"
    Write-Host ""
    $keepChoice = Read-Host "  Keep user data for a future reinstall? (y/N)"
    if ($keepChoice -eq "y" -or $keepChoice -eq "Y") {
        $keepData = $true
        Write-Host "  Data will be preserved in: $DATA_DIR" -ForegroundColor Green
    } else {
        Write-Host "  Data will be deleted." -ForegroundColor Yellow
    }
} else {
    Write-Host "  No data directory found."
}

# ============================================================================
# 3. Remove components
# ============================================================================
Write-Host ""
Write-Host "[3/4] Removing components..." -ForegroundColor Cyan
Write-Host ("-" * 50)

$dirsToRemove = @(
    @{ Path = $PYTHON_DIR; Label = "Python" },
    @{ Path = $MEILI_DIR;  Label = "Meilisearch" },
    @{ Path = $OLLAMA_DIR; Label = "Ollama" },
    @{ Path = $AITAO_DIR;  Label = "AiTao source" },
    @{ Path = $TEMP_DIR;   Label = "Temp files" }
)

if (-not $keepData) {
    $dirsToRemove += @{ Path = $DATA_DIR; Label = "User data" }
}

foreach ($dir in $dirsToRemove) {
    if (Test-Path $dir.Path) {
        try {
            Remove-Item -Path $dir.Path -Recurse -Force
            Write-Host "  Removed: $($dir.Label) ($($dir.Path))" -ForegroundColor Green
        } catch {
            Write-Host "  WARNING: Could not fully remove $($dir.Label): $_" -ForegroundColor Yellow
            Write-Host "  Try closing any open file explorer or terminal in that folder."
        }
    } else {
        Write-Host "  Skip: $($dir.Label) (not found)"
    }
}

# ============================================================================
# 4. Summary
# ============================================================================
Write-Host ""
Write-Host "[4/4] Cleanup complete." -ForegroundColor Cyan
Write-Host ("-" * 50)
Write-Host ""

if ($keepData) {
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "   AiTao uninstalled (data preserved)"          -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Kept: $DATA_DIR"
    Write-Host ""
    Write-Host "  To reinstall later, run setup.bat again."
    Write-Host "  Your models and indexes will be reused."
} else {
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "   AiTao completely uninstalled"                 -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Remaining files in this folder:"

$remaining = Get-ChildItem -Path $BASE_DIR -Force -ErrorAction SilentlyContinue
if ($remaining) {
    foreach ($item in $remaining) {
        $type = if ($item.PSIsContainer) { "[dir]" } else { "[file]" }
        Write-Host "    $type $($item.Name)"
    }
    Write-Host ""
    Write-Host "  To remove everything: delete this folder entirely."
} else {
    Write-Host "    (empty)"
}

Write-Host ""
