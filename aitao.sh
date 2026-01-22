#!/bin/bash

# Configuration
VENV_DIR="./.venv"
PYTHON="$VENV_DIR/bin/python"

# Load Dynamic Config from PathManager
if [ -f "scripts/get_config_env.py" ]; then
    eval $($PYTHON scripts/get_config_env.py)
else
    export AITAO_LOGS_DIR="./logs"
    export AITAO_STORAGE_ROOT="./data"
fi

# Ensure dirs exist
mkdir -p "$AITAO_LOGS_DIR"
mkdir -p "$AITAO_STORAGE_ROOT/anythingllm-storage"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

CONTAINER_NAME="aitao-ui"

function show_help {
    echo "Usage: ./aitao.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       Démarrer tout (Moteur API + UI AnythingLLM)"
    echo "  stop        Arrêter tous les services"
    echo "  status      Voir l'état des services"
    echo "  api         Démarrer seulement le Moteur API (Python)"
    echo "  ui          Démarrer seulement l'UI (Docker)"
    echo "  logs        Voir les logs de l'API"
    echo ""
}

function check_docker {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker n'est pas installé. Veuillez installer Docker Desktop.${NC}"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker n'est pas lancé. Veuillez démarrer Docker Desktop.${NC}"
        exit 1
    fi
}

function start_api {
    echo -e "${BLUE}🚀 Démarrage Moteur API (Port 18000)...${NC}"
    if pgrep -f "src/core/server.py" > /dev/null; then
        echo "✅ API déjà en cours d'exécution."
    else
        nohup $PYTHON src/core/server.py --port 18000 > "$AITAO_LOGS_DIR/api.log" 2>&1 &
        sleep 2
        if pgrep -f "src/core/server.py" > /dev/null; then
            echo "✅ API démarrée."
        else
            echo -e "${RED}❌ Échec du démarrage de l'API. Voir logs: $AITAO_LOGS_DIR/api.log${NC}"
        fi
    fi
}

function start_ui {
    check_docker
    echo -e "${GREEN}💬 Démarrage Interface AnythingLLM (Port 3001)...${NC}"
    
    if [ ! "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
            echo "Redémarrage du conteneur existant..."
            docker start $CONTAINER_NAME
        else
            echo "Création et lancement du conteneur..."
            # Note: host.docker.internal permet à AnythingLLM de voir notre API Python
            docker run -d \
                -p 3001:3001 \
                --cap-add SYS_ADMIN \
                --name $CONTAINER_NAME \
                --add-host=host.docker.internal:host-gateway \
                -v "$AITAO_STORAGE_ROOT/anythingllm-storage:/app/server/storage" \
                mintplexlabs/anythingllm
        fi
    else
        echo "✅ UI déjà en cours d'exécution."
    fi
    
    echo -e "👉 Interface accessible sur : ${BLUE}http://localhost:3001${NC}"
}

function stop_services {
    echo -e "${RED}🛑 Arrêt des services...${NC}"
    
    # Stop API
    if pgrep -f "src/core/server.py" > /dev/null; then
        pkill -f "src/core/server.py"
        echo "API (Python) arrêtée."
    fi
    
    # Stop Docker
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        echo "Arrêt du conteneur Docker..."
        docker stop $CONTAINER_NAME
        echo "UI (Docker) arrêtée."
    else
        echo "Conteneur Docker déjà arrêté."
    fi
}

function status {
    echo -e "${BLUE}--- État du système ---${NC}"
    
    echo -n "API Python : "
    if pgrep -f "src/core/server.py" > /dev/null; then
        echo -e "${GREEN}ON (PID $(pgrep -f "src/core/server.py"))${NC}"
    else
        echo -e "${RED}OFF${NC}"
    fi
    
    echo -n "UI Docker  : "
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        echo -e "${GREEN}ON (Running)${NC}"
    else
        if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
            echo -e "${RED}OFF (Stopped)${NC}"
        else
            echo -e "${RED}Non installé${NC}"
        fi
    fi
}

case "$1" in
    start)
        start_api
        start_ui
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_api
        start_ui
        ;;
    status)
        status
        ;;
    api)
        start_api
        ;;
    ui)
        start_ui
        ;;
    logs)
        tail -f "$AITAO_LOGS_DIR/api.log"
        ;;
    *)
        show_help
        ;;
esac

