@echo off
REM ============================================================================
REM uninstall-aitao.bat - AiTao Uninstallation Script for Windows
REM 
REM This script removes all AiTao Docker containers, volumes, images,
REM and user configuration. Includes interactive confirmations.
REM Target: Windows 10+ (x64)
REM ============================================================================

setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

REM ============================================================================
REM Configuration
REM ============================================================================
set "SCRIPT_DIR=%~dp0"
set "CONFIG_DIR=%USERPROFILE%\.aitao"

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
echo %RED%===============================================%NC%
echo %RED%      AiTao - Desinstallation Windows         %NC%
echo %RED%===============================================%NC%
echo.
echo %YELLOW%ATTENTION: Ce script va supprimer AiTao et toutes ses donnees!%NC%
echo.

REM ============================================================================
REM Initial confirmation
REM ============================================================================
set /p "CONFIRM=Voulez-vous continuer? (oui/non): "
if /i not "%CONFIRM%"=="oui" (
    echo.
    echo Desinstallation annulee.
    exit /b 0
)

REM ============================================================================
REM Check Docker
REM ============================================================================
echo.
echo %YELLOW%[1/5]%NC% Verification de Docker...

where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %YELLOW%Docker non detecte - passage aux etapes de nettoyage fichiers%NC%
    goto :cleanup_files
)

docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %YELLOW%Docker non demarre - passage aux etapes de nettoyage fichiers%NC%
    goto :cleanup_files
)

echo %GREEN%OK%NC% - Docker detecte

REM ============================================================================
REM Stop and remove containers
REM ============================================================================
echo.
echo %YELLOW%[2/5]%NC% Arret des containers AiTao...

cd /d "%SCRIPT_DIR%"

REM Check if compose file exists
if exist "docker-compose.yml" (
    docker compose down 2>nul
    if %ERRORLEVEL% equ 0 (
        echo %GREEN%OK%NC% - Containers arretes
    ) else (
        echo %YELLOW%Aucun container actif%NC%
    )
) else (
    echo %YELLOW%Pas de docker-compose.yml trouve%NC%
)

REM ============================================================================
REM Remove volumes
REM ============================================================================
echo.
echo %YELLOW%[3/5]%NC% Suppression des volumes Docker...
echo.
echo     Les volumes contiennent:
echo       - Modeles Ollama telecharges
echo       - Index Meilisearch
echo       - Donnees Open WebUI
echo.

set /p "DEL_VOLUMES=Supprimer les volumes? Cela effacera tous les modeles telecharges (oui/non): "
if /i "%DEL_VOLUMES%"=="oui" (
    REM Remove named volumes
    for %%v in (aitao_ollama_data aitao_meilisearch_data aitao_openwebui_data) do (
        docker volume rm %%v 2>nul
        if !ERRORLEVEL! equ 0 (
            echo   - Volume %%v supprime
        )
    )
    
    REM Also remove via compose if available
    if exist "docker-compose.yml" (
        docker compose down -v 2>nul
    )
    
    echo %GREEN%OK%NC% - Volumes supprimes
) else (
    echo %BLUE%Volumes conserves%NC%
)

REM ============================================================================
REM Remove Docker images
REM ============================================================================
echo.
echo %YELLOW%[4/5]%NC% Suppression des images Docker...
echo.
echo     Les images prennent ~3-5 GB d'espace disque.
echo     Elles seront re-telechargees si vous reinstallez AiTao.
echo.

set /p "DEL_IMAGES=Supprimer les images Docker? (oui/non): "
if /i "%DEL_IMAGES%"=="oui" (
    REM Remove AiTao backend image
    for /f "tokens=*" %%i in ('docker images -q aitao-backend 2^>nul') do (
        docker rmi -f %%i 2>nul
        echo   - Image aitao-backend supprimee
    )
    
    REM Remove docker-aitao-backend (compose naming)
    for /f "tokens=*" %%i in ('docker images -q docker-aitao-backend 2^>nul') do (
        docker rmi -f %%i 2>nul
        echo   - Image docker-aitao-backend supprimee
    )
    
    echo.
    echo     Images tierces (Ollama, Meilisearch, Open WebUI):
    echo     Ces images sont partagees et peuvent etre utilisees par d'autres apps.
    echo.
    
    set /p "DEL_THIRD_PARTY=Supprimer aussi les images tierces? (oui/non): "
    if /i "!DEL_THIRD_PARTY!"=="oui" (
        REM Ollama
        for /f "tokens=*" %%i in ('docker images -q ollama/ollama 2^>nul') do (
            docker rmi -f %%i 2>nul
            echo   - Image Ollama supprimee
        )
        
        REM Meilisearch
        for /f "tokens=*" %%i in ('docker images -q getmeili/meilisearch 2^>nul') do (
            docker rmi -f %%i 2>nul
            echo   - Image Meilisearch supprimee
        )
        
        REM Open WebUI
        for /f "tokens=*" %%i in ('docker images -q ghcr.io/open-webui/open-webui 2^>nul') do (
            docker rmi -f %%i 2>nul
            echo   - Image Open WebUI supprimee
        )
    ) else (
        echo %BLUE%Images tierces conservees%NC%
    )
    
    echo %GREEN%OK%NC% - Images supprimees
) else (
    echo %BLUE%Images conservees%NC%
)

REM ============================================================================
REM Remove configuration files
REM ============================================================================
:cleanup_files
echo.
echo %YELLOW%[5/5]%NC% Suppression des fichiers de configuration...
echo.
echo     Repertoire de config: %CONFIG_DIR%
echo.

if exist "%CONFIG_DIR%" (
    set /p "DEL_CONFIG=Supprimer le repertoire de configuration? (oui/non): "
    if /i "!DEL_CONFIG!"=="oui" (
        rmdir /s /q "%CONFIG_DIR%" 2>nul
        if !ERRORLEVEL! equ 0 (
            echo %GREEN%OK%NC% - Configuration supprimee
        ) else (
            echo %RED%Erreur lors de la suppression de %CONFIG_DIR%%NC%
            echo Vous pouvez le supprimer manuellement.
        )
    ) else (
        echo %BLUE%Configuration conservee%NC%
    )
) else (
    echo %BLUE%Pas de repertoire de configuration trouve%NC%
)

REM ============================================================================
REM Remove Docker network
REM ============================================================================
echo.
echo Nettoyage du reseau Docker...
docker network rm aitao-network 2>nul
if %ERRORLEVEL% equ 0 (
    echo   - Reseau aitao-network supprime
)

REM ============================================================================
REM Final message
REM ============================================================================
echo.
echo %GREEN%===============================================%NC%
echo %GREEN%       Desinstallation terminee!              %NC%
echo %GREEN%===============================================%NC%
echo.
echo Resume:
echo   - Containers AiTao: supprimes
if /i "%DEL_VOLUMES%"=="oui" (
    echo   - Volumes Docker: supprimes
) else (
    echo   - Volumes Docker: conserves
)
if /i "%DEL_IMAGES%"=="oui" (
    echo   - Images Docker: supprimees
) else (
    echo   - Images Docker: conservees
)
if /i "%DEL_CONFIG%"=="oui" (
    echo   - Configuration: supprimee
) else (
    echo   - Configuration: conservee
)
echo.
echo %YELLOW%Note:%NC% Docker Desktop reste installe sur votre systeme.
echo Pour le desinstaller, utilisez "Ajout/Suppression de programmes".
echo.
echo Merci d'avoir utilise AiTao!
echo.

pause
endlocal
