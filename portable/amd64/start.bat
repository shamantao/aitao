@echo off
REM ============================================================================
REM start.bat - Launcher for start-aitao.ps1
REM
REM Bypasses PowerShell ExecutionPolicy restriction on fresh Windows installs.
REM ============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-aitao.ps1" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] Start failed with code %ERRORLEVEL%
    echo.
    pause
)
