@echo off
REM ============================================================================
REM update.bat - Launcher for update-aitao.ps1
REM
REM Bypasses PowerShell ExecutionPolicy restriction on fresh Windows installs.
REM ============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update-aitao.ps1" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] Update failed with code %ERRORLEVEL%
    echo.
    pause
)
