@echo off
REM ============================================================================
REM install-aitao.bat - AiTao Installation Script for Windows
REM 
REM This script checks for Docker Desktop, creates necessary directories,
REM sets up environment configuration, and launches all AiTao services.
REM Target: Windows 10+ (x64)
REM ============================================================================

setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

REM ============================================================================
REM Configuration
REM ============================================================================
set "SCRIPT_DIR=%~dp0"
set "CONFIG_DIR=%USERPROFILE%\.aitao"
set "DOCKER_DOWNLOAD_URL=https://www.docker.com/products/docker-desktop/"

REM Color codes (Windows 10+)
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM ============================================================================
REM Banner
REM ============================================================================
echo.
echo %BLUE%===============================================%NC%
echo %BLUE%       AiTao - Installation Windows          %NC%
echo %BLUE%===============================================%NC%
echo.

REM ============================================================================
REM Check Docker Desktop
REM ============================================================================
echo %YELLOW%[1/5]%NC% Verification de Docker Desktop...

where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo %RED%ERREUR: Docker Desktop n'est pas installe!%NC%
    echo.
    echo Pour installer Docker Desktop:
    echo   1. Telechargez Docker Desktop depuis:
    echo      %DOCKER_DOWNLOAD_URL%
    echo.
    echo   2. Installez Docker Desktop
    echo   3. Redemarrez votre ordinateur si demande
    echo   4. Lancez Docker Desktop
    echo   5. Relancez ce script
    echo.
    echo %YELLOW%Appuyez sur une touche pour ouvrir la page de telechargement...%NC%
    pause >nul
    start "" "%DOCKER_DOWNLOAD_URL%"
    exit /b 1
)

REM Check if Docker daemon is running
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo %RED%ERREUR: Docker Desktop n'est pas demarre!%NC%
    echo.
    echo Veuillez:
    echo   1. Lancer Docker Desktop depuis le menu Demarrer
    echo   2. Attendre que l'icone Docker soit stable (baleine)
    echo   3. Relancer ce script
    echo.
    exit /b 1
)

for /f "tokens=3" %%v in ('docker --version 2^>nul') do set "DOCKER_VERSION=%%v"
set "DOCKER_VERSION=%DOCKER_VERSION:,=%"
echo %GREEN%OK%NC% - Docker %DOCKER_VERSION% detecte et operationnel

REM ============================================================================
REM Check Docker Compose
REM ============================================================================
echo %YELLOW%[2/5]%NC% Verification de Docker Compose...

docker compose version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo %RED%ERREUR: Docker Compose n'est pas disponible!%NC%
    echo.
    echo Docker Compose est normalement inclus avec Docker Desktop.
    echo Veuillez reinstaller Docker Desktop.
    echo.
    exit /b 1
)

for /f "tokens=4" %%v in ('docker compose version 2^>nul') do set "COMPOSE_VERSION=%%v"
echo %GREEN%OK%NC% - Docker Compose %COMPOSE_VERSION% detecte

REM ============================================================================
REM Create directories
REM ============================================================================
echo %YELLOW%[3/5]%NC% Creation des repertoires...

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%CONFIG_DIR%\config" mkdir "%CONFIG_DIR%\config"
if not exist "%CONFIG_DIR%\data" mkdir "%CONFIG_DIR%\data"
if not exist "%CONFIG_DIR%\logs" mkdir "%CONFIG_DIR%\logs"

echo %GREEN%OK%NC% - Repertoires crees dans %CONFIG_DIR%

REM ============================================================================
REM Setup environment file
REM ============================================================================
echo %YELLOW%[4/5]%NC% Configuration de l'environnement...

if not exist "%SCRIPT_DIR%.env" (
    if exist "%SCRIPT_DIR%.env.template" (
        copy "%SCRIPT_DIR%.env.template" "%SCRIPT_DIR%.env" >nul
        
        REM Generate random master key (32 chars)
        set "CHARS=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        set "MASTER_KEY="
        for /L %%i in (1,1,32) do (
            set /a "idx=!random! %% 62"
            for %%j in (!idx!) do set "MASTER_KEY=!MASTER_KEY!!CHARS:~%%j,1!"
        )
        
        REM Update .env file with generated key
        powershell -Command "(Get-Content '%SCRIPT_DIR%.env') -replace 'MEILISEARCH_MASTER_KEY=changeme', 'MEILISEARCH_MASTER_KEY=!MASTER_KEY!' | Set-Content '%SCRIPT_DIR%.env'"
        
        echo %GREEN%OK%NC% - Fichier .env cree avec cle Meilisearch generee
    ) else (
        echo %YELLOW%ATTENTION%NC% - Pas de .env.template trouve, utilisation des valeurs par defaut
    )
) else (
    echo %GREEN%OK%NC% - Fichier .env existant conserve
)

REM ============================================================================
REM Start services
REM ============================================================================
echo %YELLOW%[5/5]%NC% Demarrage des services Docker...
echo.
echo     Cette operation peut prendre plusieurs minutes lors du premier lancement
echo     (telechargement des images Docker: ~3-5 GB)
echo.

cd /d "%SCRIPT_DIR%"
docker compose up -d

if %ERRORLEVEL% neq 0 (
    echo.
    echo %RED%ERREUR: Echec du demarrage des services!%NC%
    echo.
    echo Verifiez les logs avec: docker compose logs
    echo.
    exit /b 1
)

REM ============================================================================
REM Wait for services to be ready
REM ============================================================================
echo.
echo Attente du demarrage des services...

REM Wait for API
set "API_READY=0"
for /L %%i in (1,1,30) do (
    if !API_READY! equ 0 (
        curl -s http://localhost:8200/api/health >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            set "API_READY=1"
        ) else (
            timeout /t 2 /nobreak >nul
        )
    )
)

REM ============================================================================
REM Display success message
REM ============================================================================
echo.
echo %GREEN%===============================================%NC%
echo %GREEN%     Installation terminee avec succes!       %NC%
echo %GREEN%===============================================%NC%
echo.
echo Services disponibles:
echo.
echo   %BLUE%API AiTao:%NC%        http://localhost:8200
echo   %BLUE%Health Check:%NC%    http://localhost:8200/api/health
echo   %BLUE%Meilisearch:%NC%     http://localhost:7700
echo   %BLUE%Ollama:%NC%          http://localhost:11434
echo   %BLUE%Open WebUI:%NC%      http://localhost:3000
echo.
echo Commandes utiles:
echo.
echo   Voir les logs:      docker compose logs -f
echo   Arreter:            docker compose down
echo   Redemarrer:         docker compose restart
echo   Desinstaller:       uninstall-aitao.bat
echo.
echo %YELLOW%Configuration:%NC% %CONFIG_DIR%
echo.

REM Open browser
echo Ouverture du navigateur...
timeout /t 2 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo %GREEN%Bon usage d'AiTao!%NC%
echo.

endlocal
