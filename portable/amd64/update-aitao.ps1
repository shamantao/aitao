# ============================================================================
# update-aitao.ps1 - AiTao auto-update (Windows x64, portable mode)
#
# Checks GitHub Releases for a newer version, downloads the x64 archive,
# and replaces only the source code (src/, pyproject.toml, config template).
# User data (data/), configuration (aitao/config/config.toml) and binaries
# (python/, meilisearch/, ollama/) are NEVER touched.
#
# Usage: .\update-aitao.ps1
# Usage (pre-releases): .\update-aitao.ps1 -IncludePrerelease
# ============================================================================

param(
    [switch]$IncludePrerelease = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

$GITHUB_REPO  = "shamantao/aitao"
$PLATFORM     = "windows-x64"
$BASE_DIR     = $PSScriptRoot
$AITAO_DIR    = Join-Path $BASE_DIR "aitao"
$VERSION_FILE = Join-Path $AITAO_DIR "VERSION"
$TEMP_DIR     = Join-Path $BASE_DIR "_update_temp"

# ============================================================================
# Colors & helpers
# ============================================================================
function Write-Step { param([string]$Msg) Write-Host "`n$Msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$Msg) Write-Host "  OK  $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "  WARN $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "  ERR  $Msg" -ForegroundColor Red }

# ============================================================================
# Banner
# ============================================================================
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   AiTao Portable - Update check"                -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. Read current version
# ============================================================================
Write-Step "[1/5] Reading current version..."

$currentVersion = "0.0.0"
if (Test-Path $VERSION_FILE) {
    $currentVersion = (Get-Content -Path $VERSION_FILE -Raw).Trim()
    Write-OK "Installed: v$currentVersion"
} else {
    Write-Warn "No VERSION file found - assuming fresh install, will apply latest."
    $Force = $true
}

# ============================================================================
# 2. Fetch latest release from GitHub API
# ============================================================================
Write-Step "[2/5] Checking GitHub for latest release..."

try {
    $apiUrl = "https://api.github.com/repos/$GITHUB_REPO/releases"
    $headers = @{ "User-Agent" = "aitao-updater/1.0" }
    $releases = Invoke-RestMethod -Uri $apiUrl -Headers $headers -UseBasicParsing

    # Filter out pre-releases unless allowed
    if ($IncludePrerelease) {
        $targetRelease = $releases | Select-Object -First 1
    } else {
        $targetRelease = $releases | Where-Object { -not $_.prerelease } | Select-Object -First 1
    }

    if (-not $targetRelease) {
        Write-Warn "No suitable release found on GitHub."
        exit 0
    }

    $latestVersion = $targetRelease.tag_name -replace '^v', ''
    Write-OK "Latest: v$latestVersion"

} catch {
    Write-Fail "Cannot reach GitHub API: $_"
    Write-Host "  Check your internet connection and try again."
    exit 1
}

# ============================================================================
# 3. Compare versions
# ============================================================================
Write-Step "[3/5] Comparing versions..."

if (-not $Force) {
    try {
        $current = [System.Version]($currentVersion -replace '-.*', '')
        $latest  = [System.Version]($latestVersion  -replace '-.*', '')

        if ($current -ge $latest) {
            Write-Host ""
            Write-Host "  AiTao is already up to date (v$currentVersion)." -ForegroundColor Green
            Write-Host ""
            exit 0
        }
    } catch {
        Write-Warn "Could not compare versions — will download anyway."
    }
}

Write-OK "Update available: v$currentVersion -> v$latestVersion"

# ============================================================================
# 4. Download archive
# ============================================================================
Write-Step "[4/5] Downloading aitao-v$latestVersion-$PLATFORM.zip..."

$assetName = "aitao-v$latestVersion-$PLATFORM.zip"
$asset = $targetRelease.assets | Where-Object { $_.name -eq $assetName }

if (-not $asset) {
    Write-Fail "Asset '$assetName' not found in release v$latestVersion."
    Write-Host "  Available assets:"
    $targetRelease.assets | ForEach-Object { Write-Host "    - $($_.name)" }
    exit 1
}

if (Test-Path $TEMP_DIR) { Remove-Item $TEMP_DIR -Recurse -Force }
New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null

$zipPath = Join-Path $TEMP_DIR $assetName

try {
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -UseBasicParsing
    Write-OK "Downloaded to $zipPath"
} catch {
    Write-Fail "Download failed: $_"
    Remove-Item $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# ============================================================================
# 5. Apply update (replace only source code, preserve user data)
# ============================================================================
Write-Step "[5/5] Applying update..."

$extractDir = Join-Path $TEMP_DIR "extracted"
New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

# Find the root folder inside the zip (e.g. aitao-v2.6.0-windows-x64/)
$archiveRoot = Get-ChildItem -Path $extractDir -Directory | Select-Object -First 1

if (-not $archiveRoot) {
    Write-Fail "Unexpected archive structure."
    Remove-Item $TEMP_DIR -Recurse -Force
    exit 1
}

$newAitaoDir = Join-Path $archiveRoot.FullName "aitao"

# -- Replace src/ --
$srcTarget = Join-Path $AITAO_DIR "src"
$srcSource = Join-Path $newAitaoDir "src"
if (Test-Path $srcSource) {
    if (Test-Path $srcTarget) { Remove-Item $srcTarget -Recurse -Force }
    Copy-Item -Path $srcSource -Destination $AITAO_DIR -Recurse
    Write-OK "src/ updated"
}

# -- Replace pyproject.toml --
$pyprojectSource = Join-Path $newAitaoDir "pyproject.toml"
if (Test-Path $pyprojectSource) {
    Copy-Item -Path $pyprojectSource -Destination $AITAO_DIR -Force
    Write-OK "pyproject.toml updated"
}

# -- Update config template (never overwrite config.toml itself) --
$templateSource = Join-Path $newAitaoDir "config\config.toml.template"
$templateTarget = Join-Path $AITAO_DIR "config\config.toml.template"
if (Test-Path $templateSource) {
    $configDir = Split-Path $templateTarget -Parent
    if (-not (Test-Path $configDir)) { New-Item -ItemType Directory -Path $configDir -Force | Out-Null }
    Copy-Item -Path $templateSource -Destination $templateTarget -Force
    Write-OK "config.toml.template updated"
}

# -- Update PS1 scripts in the root portable folder --
$scriptsSource = $archiveRoot.FullName
foreach ($script in @("start-aitao.ps1","stop-aitao.ps1","update-aitao.ps1","uninstall-aitao.ps1")) {
    $src = Join-Path $scriptsSource $script
    $dst = Join-Path $BASE_DIR $script
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Force
        Write-OK "$script updated"
    }
}

# -- Write new VERSION --
$newVersionFile = Join-Path $newAitaoDir "VERSION"
if (Test-Path $newVersionFile) {
    Copy-Item -Path $newVersionFile -Destination $AITAO_DIR -Force
}
$latestVersion | Set-Content -Path $VERSION_FILE -Encoding UTF8
Write-OK "VERSION set to $latestVersion"

# -- Cleanup --
Remove-Item $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue

# ============================================================================
# Summary
# ============================================================================
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "   Update complete: v$latestVersion"             -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Restart AiTao to use the new version:"
Write-Host "    .\stop-aitao.ps1"
Write-Host "    .\start-aitao.ps1"
Write-Host ""
Write-Host "  Your data and configuration were NOT modified."
Write-Host ""
