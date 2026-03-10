@echo off
REM ============================================================================
REM uninstall.bat - Launcher for uninstall-aitao.ps1
REM
REM Bypasses PowerShell ExecutionPolicy restriction on fresh Windows installs.
REM ============================================================================
echo.
echo  AiTao Portable - Uninstall
echo  ===========================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall-aitao.ps1" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] Uninstall failed with code %ERRORLEVEL%
    echo.
)
pause
