@echo off
REM ============================================================================
REM setup.bat - Launcher for setup-portable.ps1
REM
REM Bypasses PowerShell ExecutionPolicy restriction on fresh Windows installs.
REM ============================================================================
echo.
echo  AiTao Portable - Setup (arm64)
echo  ===============================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-portable.ps1" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] Setup failed with code %ERRORLEVEL%
    echo.
    pause
)
