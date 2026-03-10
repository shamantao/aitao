# ============================================================================
# stop-aitao.ps1 - Stop all AiTao services (portable mode)
#
# Stops Meilisearch, Ollama, and AiTao API processes.
# ============================================================================

$BASE_DIR = $PSScriptRoot
$DATA_DIR = Join-Path $BASE_DIR "data"
$PID_FILE = Join-Path $DATA_DIR "pids.json"

Write-Host ""
Write-Host "===============================================" -ForegroundColor Yellow
Write-Host "   AiTao Portable - Stopping services"         -ForegroundColor Yellow
Write-Host "===============================================" -ForegroundColor Yellow
Write-Host ""

# Try to stop by saved PIDs first
if (Test-Path $PID_FILE) {
    $pids = Get-Content $PID_FILE | ConvertFrom-Json

    foreach ($service in @("aitao", "ollama", "meilisearch")) {
        $pid = $pids.$service
        if ($pid) {
            try {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($proc) {
                    Stop-Process -Id $pid -Force
                    Write-Host "  Stopped $service (PID: $pid)" -ForegroundColor Green
                } else {
                    Write-Host "  $service not running (PID $pid already gone)"
                }
            } catch {
                Write-Host "  $service: could not stop PID $pid" -ForegroundColor Yellow
            }
        }
    }

    Remove-Item $PID_FILE -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  No PID file found, stopping by process name..."
}

# Fallback: stop by process name
$processNames = @("meilisearch", "ollama", "ollama_llama_server")

foreach ($name in $processNames) {
    $procs = Get-Process -Name $name -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | Stop-Process -Force
        Write-Host "  Stopped $name (by name)" -ForegroundColor Green
    }
}

# Stop Python/uvicorn processes running on port 8200
$netstat = netstat -ano 2>$null | Select-String ":8200\s"
if ($netstat) {
    foreach ($line in $netstat) {
        if ($line -match "\s+(\d+)$") {
            $pid = $Matches[1]
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  Stopped process on port 8200 (PID: $pid)" -ForegroundColor Green
            } catch { }
        }
    }
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "   All services stopped." -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
