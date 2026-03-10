@echo off
REM ============================================================================
REM stop.bat - Launcher for stop-aitao.ps1
REM
REM Bypasses PowerShell ExecutionPolicy restriction on fresh Windows installs.
REM ============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-aitao.ps1" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] Stop failed with code %ERRORLEVEL%
    echo.
    pause
)
