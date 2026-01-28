#!/usr/bin/env bash

# =================================================================================
# ☯️ AI Tao - Orchestrator
# =================================================================================

# --- Configuration ---
VENV_DIR="./.venv"
PYTHON="$VENV_DIR/bin/python"
CONFIG_FILE="config/config.toml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Docker Container Name
CONTAINER_NAME="aitao-ui"
IMAGE_NAME="mintplexlabs/anythingllm"

# --- Helper Functions ---

# Python helper to extract config strictly
# Note: we escape \$storage_root so that bash passes literal $storage_root to python
PYTHON_GET_CONFIG="
import toml, os, sys
try:
    config = toml.load('$CONFIG_FILE')
    section = sys.argv[1]
    key = sys.argv[2]
    val = config[section][key]
    # Simple variable expansion
    if 'storage_root' in config['system']:
        val = val.replace('\$storage_root', config['system']['storage_root'])
    print(val)
except Exception:
    print('')
"

get_conf() {
    $PYTHON -c "$PYTHON_GET_CONFIG" "$1" "$2"
}

get_api_port() {
    port=$(get_conf "server" "api_port")
    echo "${port:-8247}"  # Default 8247 si non défini
}

get_ui_port() {
    port=$(get_conf "server" "ui_port")
    echo "${port:-3001}"  # Default 3001 si non défini
}

resolve_paths() {
    # Load configuration once
    export STORAGE_ROOT=$(get_conf "system" "storage_root")
    export LOGS_DIR=$(get_conf "system" "logs_path")

    # Default fallbacks
    if [ -z "$STORAGE_ROOT" ]; then
        echo -e "${RED}Erreur: 'storage_root' non défini dans config.toml${NC}"
        exit 1
    fi

    if [ -z "$LOGS_DIR" ]; then
        LOGS_DIR="./logs"
        echo -e "${BLUE}Info: 'logs_path' non défini, utilisation de défaut: $LOGS_DIR${NC}"
    fi

    mkdir -p "$STORAGE_ROOT"
    mkdir -p "$LOGS_DIR"
}

check_deps() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}Erreur: $CONFIG_FILE introuvable.${NC}"
        echo "Copiez config/config.toml.template vers config/config.toml et configurez-le."
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker n'est pas installé. Veuillez l'installer via https://www.docker.com/products/docker-desktop${NC}"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo -e "${BLUE}⚠️  Docker n'est pas lancé. Tentative de démarrage...${NC}"
        if command -v open &> /dev/null; then
            open --background -a Docker
            echo -e "${BLUE}⏳ Attente du démarrage de Docker Desktop...${NC}"
            
            # Timeout counter to prevent infinite loop
            count=0
            while ! docker info &> /dev/null; do
                if [ $count -gt 60 ]; then
                    echo ""
                    echo -e "${RED}Timeout: Docker met trop de temps à démarrer.${NC}"
                    exit 1
                fi
                sleep 2
                echo -n "."
                ((count++))
            done
            echo ""
            echo -e "${GREEN}✅ Docker est maintenant prêt.${NC}"
        else
            echo -e "${RED}Impossible de démarrer Docker automatiquement. Lancez-le manuellement.${NC}"
            exit 1
        fi
    fi
}

start_codex_api() {
    echo -e "${BLUE}🚀 Démarrage du moteur d'IA (API Python)...${NC}"
    # Start in background, log to defined logs dir
    nohup $PYTHON -m src.core.server > "$LOGS_DIR/api.log" 2>&1 &
    PID=$!
    echo $PID > "$LOGS_DIR/api.pid"
    echo -e "${GREEN}✅ API démarrée (PID: $PID). Logs: $LOGS_DIR/api.log${NC}"
}

stop_codex_api() {
    if [ -f "$LOGS_DIR/api.pid" ]; then
        PID=$(cat "$LOGS_DIR/api.pid")
        echo -e "${BLUE}🛑 Arrêt de l'API (PID: $PID)...${NC}"
        kill $PID 2>/dev/null || true
        rm "$LOGS_DIR/api.pid"
    else
        # Fallback check for local logs/ if user just switched config
        if [ -f "logs/api.pid" ]; then
             PID=$(cat "logs/api.pid")
             echo -e "${BLUE}🛑 Arrêt de l'API (Anciennement PID: $PID)...${NC}"
             kill $PID 2>/dev/null || true
             rm "logs/api.pid"
        fi
    fi
}

start_sync_agent() {
    echo -e "${BLUE}🔄 Démarrage du Sync Agent...${NC}"
    nohup $PYTHON -m src.core.sync_agent > "$LOGS_DIR/sync.log" 2>&1 &
    PID=$!
    echo $PID > "$LOGS_DIR/sync.pid"
    echo -e "${GREEN}✅ Sync Agent démarré (PID: $PID). Logs: $LOGS_DIR/sync.log${NC}"
}

stop_sync_agent() {
    if [ -f "$LOGS_DIR/sync.pid" ]; then
        PID=$(cat "$LOGS_DIR/sync.pid")
        echo -e "${BLUE}🛑 Arrêt du Sync Agent (PID: $PID)...${NC}"
        kill $PID 2>/dev/null || true
        rm "$LOGS_DIR/sync.pid"
    else
        # Fallback
        if [ -f "logs/sync.pid" ]; then
             PID=$(cat "logs/sync.pid")
             echo -e "${BLUE}🛑 Arrêt du Sync Agent (Anciennement PID: $PID)...${NC}"
             kill $PID 2>/dev/null || true
             rm "logs/sync.pid"
        fi
    fi
}

start_rag_server() {
    echo -e "${BLUE}📚 Démarrage du RAG Server (port 8200)...${NC}"
    nohup $PYTHON -m src.core.rag_server > "$LOGS_DIR/rag_server.log" 2>&1 &
    PID=$!
    echo $PID > "$LOGS_DIR/rag_server.pid"
    echo -e "${GREEN}✅ RAG Server démarré (PID: $PID). Logs: $LOGS_DIR/rag_server.log${NC}"
}

stop_rag_server() {
    if [ -f "$LOGS_DIR/rag_server.pid" ]; then
        PID=$(cat "$LOGS_DIR/rag_server.pid")
        echo -e "${BLUE}🛑 Arrêt du RAG Server (PID: $PID)...${NC}"
        kill $PID 2>/dev/null || true
        rm "$LOGS_DIR/rag_server.pid"
    fi
}

start_ui() {
    echo -e "${BLUE}🚀 Démarrage de l'interface (AnythingLLM Docker)...${NC}"
    echo -e "   📂 Storage: $STORAGE_ROOT/anythingllm-storage"

    mkdir -p "$STORAGE_ROOT/anythingllm-storage"
    
    # Get ports from config
    API_PORT=$(get_api_port)
    UI_PORT=$(get_ui_port)

    # Check if running
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        echo -e "${GREEN}✅ L'interface tourne déjà.${NC}"
    else
        # Remove old stopped container if exists to refresh mounts/config
        docker rm $CONTAINER_NAME >/dev/null 2>&1 || true

        # Using $STORAGE_ROOT from resolve_paths
        CID=$(docker run -d \
            -p $UI_PORT:3001 \
            --cap-add SYS_ADMIN \
            -v "$STORAGE_ROOT/anythingllm-storage:/app/server/storage" \
            -v "$PWD/config:/app/server/storage/aitao_config_mount" \
            -e STORAGE_DIR="/app/server/storage" \
            -e LLM_PROVIDER="generic-openai" \
            -e GENERIC_OPEN_AI_BASE_PATH="http://host.docker.internal:$API_PORT/v1" \
            -e GENERIC_OPEN_AI_API_KEY="sk-aitao-local" \
            -e GENERIC_OPEN_AI_MODEL_PREF="aitao-model" \
            -e GENERIC_OPEN_AI_MODEL_TOKEN_LIMIT="8192" \
            -e GENERIC_OPEN_AI_MAX_TOKENS="4096" \
            --name $CONTAINER_NAME \
            $IMAGE_NAME)

        SHORT_CID=${CID:0:12}
        echo -e "${GREEN}✅ Interface lancée sur http://localhost:3001 (ID: $SHORT_CID)${NC}"
    fi
}

wait_for_ui() {
    echo -e "${BLUE}⏳ Attente de l'initialisation de l'interface (DB Check)...${NC}"
    # On attend que le fichier DB soit créé par le conteneur
    DB_FILE="$STORAGE_ROOT/anythingllm-storage/anythingllm.db"
    
    count=0
    while [ ! -f "$DB_FILE" ]; do
        if [ $count -gt 30 ]; then
            echo -e "${RED}⚠️ Timeout attente DB.${NC}"
            return
        fi
        sleep 1
        echo -n "."
        ((count++))
    done
    echo ""
    # On laisse un peu de temps pour les migrations
    sleep 5
    
    # Run bootstrap (creates API key if needed)
    echo -e "${BLUE}🔧 Configuration automatique de la DB...${NC}"
    # $PYTHON scripts/bootstrap_db.py
    
    # Run settings setup (customize UI appearance)
    echo -e "${BLUE}🎨 Application du thème et des messages...${NC}"
    $PYTHON scripts/setup_settings.py
    
    # Additional wait for API to be fully responsive
    echo -e "${BLUE}⏳ Vérification de l'API AnythingLLM...${NC}"
    UI_PORT=$(get_ui_port)
    count=0
    while ! curl -s "http://localhost:$UI_PORT/api/v1/workspace" > /dev/null 2>&1; do
        if [ $count -gt 20 ]; then
            echo -e "${RED}⚠️ API non responsive après 20s${NC}"
            break
        fi
        sleep 1
        echo -n "."
        ((count++))
    done
    echo ""
    echo -e "${GREEN}✅ AnythingLLM prêt !${NC}"
}

stop_ui() {
    echo -e "${BLUE}🛑 Arrêt de l'interface Docker...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || true
}

# --- Main Command Handler ---

case "$1" in
    start)
        check_deps
        resolve_paths
        start_codex_api
        start_ui
        wait_for_ui
        start_sync_agent
        start_rag_server
        echo -e "${GREEN}✨ Tout est opérationnel !${NC}"
        ;;
    stop)
        resolve_paths
        stop_codex_api
        stop_sync_agent
        stop_rag_server
        stop_ui
        echo -e "${GREEN}😴 Tout est arrêté.${NC}"
        ;;
    restart)
        resolve_paths
        echo -e "${BLUE}🔄 Redémarrage...${NC}"
        stop_codex_api
        stop_sync_agent
        stop_rag_server
        stop_ui
        sleep 2
        start_codex_api
        start_ui
        wait_for_ui
        start_sync_agent
        start_rag_server
        echo -e "${GREEN}✨ Redémarrage terminé !${NC}"
        ;;
    status)
        resolve_paths
        echo "--- API Python ---"
        if [ -f "$LOGS_DIR/api.pid" ] && ps -p $(cat "$LOGS_DIR/api.pid") > /dev/null; then
            echo -e "${GREEN}En ligne (PID: $(cat "$LOGS_DIR/api.pid"))${NC}"
        else
            echo -e "${RED}Arrêté${NC}"
        fi
        
        echo "--- Sync Agent ---"
        if [ -f "$LOGS_DIR/sync.pid" ] && ps -p $(cat "$LOGS_DIR/sync.pid") > /dev/null; then
            echo -e "${GREEN}En ligne (PID: $(cat "$LOGS_DIR/sync.pid"))${NC}"
        else
            echo -e "${RED}Arrêté${NC}"
        fi

        echo "--- RAG Server ---"
        if [ -f "$LOGS_DIR/rag_server.pid" ] && ps -p $(cat "$LOGS_DIR/rag_server.pid") > /dev/null; then
            echo -e "${GREEN}En ligne (PID: $(cat "$LOGS_DIR/rag_server.pid"))${NC}"
        else
            echo -e "${RED}Arrêté${NC}"
        fi

        echo "--- UI Docker ---"
        CID=$(docker ps -q -f name=$CONTAINER_NAME)
        if [ -n "$CID" ]; then
            echo -e "${GREEN}En ligne (ID: $CID)${NC}"
        else
             echo -e "${RED}Arrêté${NC}"
        fi
        
        echo "--- Config ---"
        echo "Logs: $LOGS_DIR"
        echo "Storage: $STORAGE_ROOT"
        ;;
    check)
        case "$2" in
            config)
                echo -e "${BLUE}🔍 Validation de $CONFIG_FILE...${NC}"
                $PYTHON -c "
import toml
try:
    config = toml.load('$CONFIG_FILE')
    print('✅ Syntaxe TOML valide')
    print(f\"\\nStorage Root: {config['system']['storage_root']}\")
    print(f\"Models Dir: {config['models']['models_dir']}\")
    if 'server' in config:
        print(f\"\\nAPI Port: {config['server'].get('api_port', 8247)}\")
        print(f\"UI Port: {config['server'].get('ui_port', 3001)}\")
except Exception as e:
    print(f'❌ Erreur: {e}')
    exit(1)
"
                ;;
            scan)
                echo -e "${BLUE}🔍 Dry-run indexation...${NC}"
                $PYTHON -c "
import sys
import os
sys.path.insert(0, os.getcwd())
from src.core.path_manager import path_manager
config = path_manager.get_indexing_config()
paths = config.get('include_paths', [])
if not paths:
    print('⚠️  Aucun chemin configuré dans config.toml [indexing.include_paths]')
    exit(0)
print(f'📂 {len(paths)} chemin(s) à indexer:\\n')
for p in paths:
    if os.path.exists(p):
        print(f'  ✅ {p}')
    else:
        print(f'  ❌ {p} (inexistant)')
"
                ;;
            system|compatibility|*)
                echo -e "${BLUE}🔍 Vérification de la compatibilité système...${NC}"
                $PYTHON scripts/check_system.py
                ;;
        esac
        ;;
    restart)
        echo -e "${BLUE}🔄 Redémarrage d'AI Tao...${NC}"
        $0 stop
        sleep 2
        $0 start
        ;;
    help|--help|-h)
        cat << EOF
${BLUE}☯️  AI Tao - Assistant IA Local${NC}

${GREEN}Usage:${NC}
  ./aitao.sh <command> [options]

${GREEN}Commandes:${NC}
  start              Démarre tous les services (API + UI + Sync)
  stop               Arrête tous les services
  restart            Redémarre tous les services
  status             Affiche l'état des services

  check config       Valide la syntaxe du config.toml
  check scan         Affiche les chemins à indexer (dry-run)
  check system       Vérifie la compatibilité système (ports, Docker, etc.)

  help               Affiche cette aide

${GREEN}Exemples:${NC}
  ./aitao.sh start
  ./aitao.sh check system
  ./aitao.sh status
  ./aitao.sh restart

${GREEN}Configuration:${NC}
  Fichier: config/config.toml
  Template: config/config.toml.template

${GREEN}Logs:${NC}
  Emplacement: Défini dans config.toml [system.logs_path]
  Par défaut: \$storage_root/logs

${GREEN}Plus d'infos:${NC}
  README.md - Documentation complète
  PRD: prd/PRD.md
EOF
        ;;
    *)
        echo -e "${RED}Commande inconnue: $1${NC}"
        echo "Utilisez './aitao.sh help' pour voir les commandes disponibles"
        exit 1
        ;;
esac

