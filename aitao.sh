#!/bin/bash

# Configuration
VENV_DIR="./.venv"
PYTHON="$VENV_DIR/bin/python"
CHAINLIT="$VENV_DIR/bin/chainlit"
STREAMLIT="$VENV_DIR/bin/streamlit"

# Load Dynamic Config from PathManager
if [ -f "scripts/get_config_env.py" ]; then
    eval $($PYTHON scripts/get_config_env.py)
else
    # Fallback default
    export AITAO_LOGS_DIR="./logs"
fi

# Ensure logs dir exists (it might be absolute now)
mkdir -p "$AITAO_LOGS_DIR"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

function show_help {
    echo "Usage: ./aitao.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       Démarrer tout (API + Chat + Admin)"
    echo "  restart     Redémarrer tout (Stop + Start + Status)"
    echo "  stop        Arrêter tous les services"
    echo "  status      Voir l'état des services"
    echo "  process     Lister les processus en cours (PID)"
    echo "  chat        Démarrer seulement le Chat (Chainlit)"
    echo "  admin       Démarrer seulement l'Admin (Streamlit)"
    echo "  api         Démarrer seulement le Moteur API"
    echo "  scan        Scanner les dossiers de données pour l'indexation"
    echo ""
}

function list_processes {
    echo -e "${BLUE}📋 Processus AI Tao en cours :${NC}"
    echo "PID    COMMAND"
    echo "---------------------------------------------------"
    ps aux | grep -E "src/core/server.py|run_chat_custom.py|streamlit run" | grep -v grep | awk '{print $2, $11, $12, $13, $14}'
    echo ""
    echo "Pour arrêter manuellement: kill -9 [PID]"
}

function stop_services {
    echo -e "${RED}🛑 Arrêt des services...${NC}"
    
    # Kill specific patterns individually
    pkill -f "src/core/server.py"
    pkill -f "run_chat_custom.py"
    pkill -f "streamlit run"
    
    # Wait loop
    for i in {1..5}; do
        if ! pgrep -f "src/core/server.py" > /dev/null && \
           ! pgrep -f "run_chat_custom.py" > /dev/null && \
           ! pgrep -f "streamlit run" > /dev/null; then
            echo "Services arrêtés."
            return
        fi
        sleep 1
    done
    
    # Force kill if still running
    echo "⚠️ Services récalcitrants, force kill..."
    pkill -9 -f "src/core/server.py"
    pkill -9 -f "run_chat_custom.py"
    pkill -9 -f "streamlit run"
    echo "Services tués (SIGKILL)."
}

function start_api {
    echo -e "${BLUE}🚀 Démarrage Moteur API (Port 18000)...${NC}"
    # Lancement en tâche de fond avec log vers le dossier configuré
    nohup $PYTHON src/core/server.py --model llama3-8b --port 18000 > "$AITAO_LOGS_DIR/api.log" 2>&1 &
    echo "Log: tail -f $AITAO_LOGS_DIR/api.log"
}

function start_chat {
    echo -e "${GREEN}💬 Démarrage Chat (Port 18001)...${NC}"
    # Chargement des variables d'environnement (.env) si présent
    if [ -f .env ]; then
        export $(cat .env | xargs)
    fi
    # Utilisation du launcher custom pour forcer la loop asyncio
    nohup $PYTHON src/run_chat_custom.py > "$AITAO_LOGS_DIR/chat.log" 2>&1 &
    sleep 2
    # Open désactivé car géré par Nginx potentiellement
    # open http://localhost:18001
}

function start_admin {
    echo -e "${BLUE}🎛️ Démarrage Admin (Port 18002)...${NC}"
    nohup $STREAMLIT run src/admin_app.py --server.port 18002 --server.headless true > "$AITAO_LOGS_DIR/admin.log" 2>&1 &
    sleep 2
    # open http://localhost:18002
}

function scan_folders {
        # Vérifier que l'API tourne
        API_PID=$(pgrep -f "src/core/server.py")
        if [ -z "$API_PID" ]; then
            echo -e "${RED}⚠️ API non démarrée. Lancez ./aitao.sh start ou ./aitao.sh api avant le scan.${NC}"
            exit 1
        fi

        # Optionnel : vérifier aussi que l'API répond sur le port
        if ! curl --max-time 2 -s http://localhost:18000/v1/system/status >/dev/null; then
            echo -e "${RED}⚠️ API démarrée mais non accessible sur http://localhost:18000.${NC}"
            exit 1
        fi

    echo -e "${BLUE}🔍 Scan des dossiers de données...${NC}"
    $PYTHON scripts/scan_folder.py
}

function check_status {
    API_PID=$(pgrep -f "src/core/server.py")
    if [ ! -z "$API_PID" ]; then
        echo -e "✅ API Running (PID: $API_PID)"
        
        # Test connection with timeout
        RESPONSE=$(curl --max-time 2 -s http://localhost:18000/v1/system/status)
        CURL_EXIT=$?
        
        if [ $CURL_EXIT -eq 0 ] && [ ! -z "$RESPONSE" ]; then
             # Parse JSON safely
             STATE=$(echo "$RESPONSE" | $PYTHON -c "import sys, json; print(json.load(sys.stdin).get('state', 'unknown'))" 2>/dev/null)
             PROGRESS=$(echo "$RESPONSE" | $PYTHON -c "import sys, json; print(int(float(json.load(sys.stdin).get('progress', 0))*100))" 2>/dev/null)
             MSG=$(echo "$RESPONSE" | $PYTHON -c "import sys, json; print(json.load(sys.stdin).get('message', ''))" 2>/dev/null)
             
             if [ "$STATE" == "running" ]; then
                 echo -e "   ↳ 🔄 Indexation en cours : ${PROGRESS}%"
                 echo -e "   ↳ 📝 $MSG"
             elif [ "$STATE" == "idle" ]; then
                 echo -e "   ↳ 💤 Système RAG en attente (Idle)"
             else
                 echo -e "   ↳ ❓ Etat: $STATE - $MSG"
             fi
        else
             echo -e "   ↳ ❌ API inaccessible (Port 18000 fermé ou bloqué ?)"
        fi
    else
        echo "🔴 API Stopped"
    fi
    
    pgrep -f "src/run_chat_custom.py" > /dev/null && echo "✅ Chat Running" || echo "🔴 Chat Stopped"
    pgrep -f "src/admin_app.py" > /dev/null && echo "✅ Admin Running" || echo "🔴 Admin Stopped"
}

case "$1" in
    start)
        stop_services
        start_api
        sleep 5 # Attendre que l'API chauffe un peu
        start_chat
        start_admin
        echo " Vérification du status:"
        check_status
        ;;
    restart)
        stop_services
        sleep 2
        start_api
        sleep 5
        start_chat
        start_admin
        sleep 2
        echo " Vérification du status:"
        check_status
        ;;
    stop)
        stop_services
        ;;
    chat)
        start_chat
        ;;
    process)
        list_processes
        ;;
    admin)
        start_admin
        ;;
    api)
        start_api
        ;;
    scan)
        scan_folders
        check_status
        ;;
    status)
        check_status
        ;;
    *)
        show_help
        ;;
esac

