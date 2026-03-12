# ============================================================================
# setup-portable.ps1 - AiTao Portable Setup for Windows x64 (amd64)
#
# Downloads and assembles a fully portable AiTao environment:
#   - Python 3.13 (embedded, no system install)
#   - Meilisearch (standalone binary, native amd64)
#   - Ollama (standalone binary, native amd64)
#   - All Python dependencies (pre-installed locally)
#
# Usage: .\setup-portable.ps1
# Target: Windows 10+ x64 (amd64)
# ============================================================================

$ErrorActionPreference = "Stop"

# ============================================================================
# Configuration - Frozen versions
# ============================================================================
$ARCH           = "amd64"
$PYTHON_VERSION = "3.13.1"
$MEILI_VERSION  = "1.12.8"
$OLLAMA_VERSION = "0.5.7"

# Download URLs
$PYTHON_URL     = "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-embed-amd64.zip"
$MEILI_URL      = "https://github.com/meilisearch/meilisearch/releases/download/v$MEILI_VERSION/meilisearch-windows-amd64.exe"
$OLLAMA_URL     = "https://github.com/ollama/ollama/releases/download/v$OLLAMA_VERSION/ollama-windows-amd64.zip"
$GETPIP_URL     = "https://bootstrap.pypa.io/get-pip.py"

# AiTao source (adjust if different location)
$AITAO_SOURCE   = ""

# Paths relative to this script
$BASE_DIR       = $PSScriptRoot
$PYTHON_DIR     = Join-Path $BASE_DIR "python"
$MEILI_DIR      = Join-Path $BASE_DIR "meilisearch"
$OLLAMA_DIR     = Join-Path $BASE_DIR "ollama"
$AITAO_DIR      = Join-Path $BASE_DIR "aitao"
$DATA_DIR       = Join-Path $BASE_DIR "data"
$TEMP_DIR       = Join-Path $BASE_DIR "_temp"

# ============================================================================
# Helper functions
# ============================================================================
function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host ""
    Write-Host "[$Step] $Message" -ForegroundColor Cyan
    Write-Host ("-" * 50)
}

function Download-File {
    param([string]$Url, [string]$Destination)
    Write-Host "  Downloading: $Url"
    Write-Host "  To: $Destination"
    try {
        Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
        Write-Host "  OK" -ForegroundColor Green
    }
    catch {
        Write-Host "  FAIL: $_" -ForegroundColor Red
        throw
    }
}

# ============================================================================
# Banner
# ============================================================================
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   AiTao Portable Setup - Windows x64"         -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Versions:"
Write-Host "  Python:      $PYTHON_VERSION (amd64)"
Write-Host "  Meilisearch: $MEILI_VERSION (amd64 native)"
Write-Host "  Ollama:      $OLLAMA_VERSION (amd64 native)"
Write-Host ""

# ============================================================================
# Step 1: Create directory structure
# ============================================================================
Write-Step "1/7" "Creating directory structure..."

$dirs = @($PYTHON_DIR, $MEILI_DIR, $OLLAMA_DIR, $AITAO_DIR, $DATA_DIR, $TEMP_DIR,
          (Join-Path $DATA_DIR "meilisearch"),
          (Join-Path $DATA_DIR "ollama"),
          (Join-Path $DATA_DIR "aitao"),
          (Join-Path $DATA_DIR "aitao\config"),
          (Join-Path $DATA_DIR "aitao\logs"))

foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "  Created: $d"
    }
}
Write-Host "  OK - Directories ready" -ForegroundColor Green

# ============================================================================
# Step 2: Download and setup Python embedded
# ============================================================================
Write-Step "2/7" "Setting up Python $PYTHON_VERSION (amd64)..."

$pythonExe = Join-Path $PYTHON_DIR "python.exe"
if (Test-Path $pythonExe) {
    Write-Host "  Python already present, skipping download"
} else {
    $pythonZip = Join-Path $TEMP_DIR "python-embed.zip"
    Download-File -Url $PYTHON_URL -Destination $pythonZip

    Write-Host "  Extracting Python..."
    Expand-Archive -Path $pythonZip -DestinationPath $PYTHON_DIR -Force

    # Enable pip: uncomment 'import site' in ._pth file
    $pthFile = Join-Path $PYTHON_DIR "python313._pth"
    if (Test-Path $pthFile) {
        $content = Get-Content $pthFile -Raw
        $content = $content -replace '#import site', 'import site'
        Set-Content -Path $pthFile -Value $content
        Write-Host "  Enabled site-packages in _pth file"
    }

    # Download and install pip
    $getPipFile = Join-Path $TEMP_DIR "get-pip.py"
    Download-File -Url $GETPIP_URL -Destination $getPipFile

    Write-Host "  Installing pip..."
    & $pythonExe $getPipFile --no-warn-script-location 2>&1 | Out-Null
    Write-Host "  OK - pip installed" -ForegroundColor Green
}

# ============================================================================
# Step 3: Install Python dependencies
# ============================================================================
Write-Step "3/7" "Installing PyTorch (CPU-only, ~170 MB)..."

# Install PyTorch CPU first - the full CUDA version is ~2.5 GB and unnecessary
# since Ollama handles all GPU inference. CPU-only is sufficient for embeddings.
Write-Host "  Installing torch + torchvision (CPU-only from pytorch.org)..."
Write-Host ""
& $pythonExe -m pip install --no-warn-script-location `
    --trusted-host pypi.org `
    --trusted-host files.pythonhosted.org `
    --trusted-host download.pytorch.org `
    torch torchvision --index-url https://download.pytorch.org/whl/cpu 2>&1 | ForEach-Object {
    $line = $_.ToString()
    if ($line -match "^ERROR") {
        Write-Host "  $line" -ForegroundColor Red
    } elseif ($line -match "^(Successfully|Requirement already)") {
        Write-Host "  $line" -ForegroundColor DarkGray
    } elseif ($line -match "^(Collecting|Downloading|Installing|Building|Using cached)") {
        Write-Host "  $line" -ForegroundColor DarkGray
    }
}
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  FAIL: PyTorch CPU install failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
    Write-Host "  Tip: Run manually:" -ForegroundColor Yellow
    Write-Host "    .\python\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu" -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK - PyTorch CPU installed" -ForegroundColor Green

# ============================================================================
# Step 4: Install remaining Python dependencies
# ============================================================================
Write-Step "4/7" "Installing remaining Python dependencies..."

$requirementsFile = Join-Path $BASE_DIR "requirements-portable.txt"
if (-not (Test-Path $requirementsFile)) {
    Write-Host "  FAIL: requirements-portable.txt not found at $requirementsFile" -ForegroundColor Red
    exit 1
}

$pipExe = Join-Path $PYTHON_DIR "Scripts\pip.exe"
if (-not (Test-Path $pipExe)) {
    $pipExe = Join-Path $PYTHON_DIR "Scripts\pip3.exe"
}

Write-Host "  Installing sentence-transformers, LanceDB, FastAPI, etc...."
Write-Host ""
& $pythonExe -m pip install --no-warn-script-location `
    --trusted-host pypi.org `
    --trusted-host files.pythonhosted.org `
    --trusted-host pypi.python.org `
    -r $requirementsFile 2>&1 | ForEach-Object {
    $line = $_.ToString()
    if ($line -match "^ERROR") {
        Write-Host "  $line" -ForegroundColor Red
    } elseif ($line -match "^(Successfully|Requirement already)") {
        Write-Host "  $line" -ForegroundColor DarkGray
    } elseif ($line -match "^(Collecting|Downloading|Installing|Building|Using cached)") {
        Write-Host "  $line" -ForegroundColor DarkGray
    }
}
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  FAIL: pip install failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
    Write-Host "  Tip: Run manually for full output:" -ForegroundColor Yellow
    Write-Host "    .\python\python.exe -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements-portable.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK - Dependencies installed" -ForegroundColor Green

# ============================================================================
# Step 5: Download Meilisearch
# ============================================================================
Write-Step "5/7" "Setting up Meilisearch $MEILI_VERSION..."

$meiliExe = Join-Path $MEILI_DIR "meilisearch.exe"
if (Test-Path $meiliExe) {
    Write-Host "  Meilisearch already present, skipping download"
} else {
    Download-File -Url $MEILI_URL -Destination $meiliExe
}
Write-Host "  OK - Meilisearch ready" -ForegroundColor Green

# ============================================================================
# Step 6: Download Ollama
# ============================================================================
Write-Step "6/7" "Setting up Ollama $OLLAMA_VERSION..."

$ollamaExe = Join-Path $OLLAMA_DIR "ollama.exe"
if (Test-Path $ollamaExe) {
    Write-Host "  Ollama already present, skipping download"
} else {
    $ollamaZip = Join-Path $TEMP_DIR "ollama.zip"
    Download-File -Url $OLLAMA_URL -Destination $ollamaZip

    Write-Host "  Extracting Ollama..."
    Expand-Archive -Path $ollamaZip -DestinationPath $OLLAMA_DIR -Force
    Write-Host "  OK - Ollama extracted" -ForegroundColor Green
}

# ============================================================================
# Step 7: Copy AiTao source
# ============================================================================
Write-Step "7/7" "Setting up AiTao core..."

$aitaoSrc = Join-Path $AITAO_DIR "src"
if (Test-Path $aitaoSrc) {
    Write-Host "  AiTao source already present, skipping copy"
} else {
    if ($AITAO_SOURCE -and (Test-Path $AITAO_SOURCE)) {
        Write-Host "  Copying from: $AITAO_SOURCE"
        # Copy source code
        Copy-Item -Path (Join-Path $AITAO_SOURCE "src") -Destination $AITAO_DIR -Recurse
        Copy-Item -Path (Join-Path $AITAO_SOURCE "config") -Destination $AITAO_DIR -Recurse
        Copy-Item -Path (Join-Path $AITAO_SOURCE "pyproject.toml") -Destination $AITAO_DIR
        Copy-Item -Path (Join-Path $AITAO_SOURCE "aitao_cli.py") -Destination $AITAO_DIR
    } else {
        Write-Host "  NOTE: AiTao source not auto-copied." -ForegroundColor Yellow
        Write-Host "  Please copy manually:"
        Write-Host "    - src/           -> $AITAO_DIR\src\"
        Write-Host "    - config/        -> $AITAO_DIR\config\"
        Write-Host "    - pyproject.toml -> $AITAO_DIR\"
        Write-Host "    - aitao_cli.py   -> $AITAO_DIR\"
    }
}

# ============================================================================
# Step 8: Install AiTao as editable package (generates aitao.exe)
# ============================================================================
Write-Step "8/8" "Registering AiTao CLI entry point..."

$aitaoPyproject = Join-Path $AITAO_DIR "pyproject.toml"
if (Test-Path $aitaoPyproject) {
    Push-Location $AITAO_DIR
    & $pythonExe -m pip install -e . --no-deps --quiet 2>&1 | Out-Null
    Pop-Location
    $aitaoExe = Join-Path $PYTHON_DIR "Scripts\aitao.exe"
    if (Test-Path $aitaoExe) {
        Write-Host "  OK - aitao.exe ready at $aitaoExe" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: aitao.exe not generated, CLI entry point unavailable" -ForegroundColor Yellow
    }
} else {
    Write-Host "  SKIP - pyproject.toml not found, run after copying AiTao source" -ForegroundColor Yellow
}

# ============================================================================
# Cleanup temp files
# ============================================================================
if (Test-Path $TEMP_DIR) {
    Remove-Item -Path $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "  Cleaned up temp files"
}

# ============================================================================
# Summary
# ============================================================================
Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "   Setup complete!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Structure:"
Write-Host "  python/       Python $PYTHON_VERSION embedded (amd64)"
Write-Host "  meilisearch/  Meilisearch $MEILI_VERSION (amd64 native)"
Write-Host "  ollama/       Ollama $OLLAMA_VERSION (amd64 native)"
Write-Host "  aitao/        AiTao source code"
Write-Host "  data/         Runtime data (models, indexes, logs)"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run: .\start.bat            Start all services"
Write-Host "  2. Run: .\python\python.exe -m pip install -e aitao\ --no-deps" 
Write-Host "         (if aitao.exe was not auto-generated)"
Write-Host ""
Write-Host "Activate your licence:"
Write-Host "  .\python\Scripts\aitao license activate .\aitao-yourname.key"
Write-Host "  .\python\Scripts\aitao license status"
Write-Host ""
