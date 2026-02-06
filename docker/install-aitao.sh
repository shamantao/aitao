#!/bin/bash

# =============================================================================
# ☯️ AI Tao - macOS Installation Script
# =============================================================================
#
# This script checks for Docker Desktop, creates configuration directories,
# and starts all AiTao services using Docker Compose.
#
# Requirements:
#   - macOS 11+ (Big Sur or later)
#   - Apple Silicon (M1/M2/M3) or Intel Mac
#   - Docker Desktop installed
#
# Usage:
#   chmod +x install-aitao.sh
#   ./install-aitao.sh
#
# =============================================================================

set -e

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AITAO_HOME="${HOME}/.aitao"
CONFIG_DIR="${AITAO_HOME}/config"
DATA_DIR="${AITAO_HOME}/data"
LOGS_DIR="${AITAO_HOME}/logs"

# --- Helper functions ---
print_banner() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}              ${BOLD}☯️  AI Tao - Installation${NC}                     ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}         Local-First Document Search & Translation         ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# --- Check macOS version ---
check_macos_version() {
    print_step "Vérification de la version macOS..."
    
    if [[ "$(uname)" != "Darwin" ]]; then
        print_error "Ce script est conçu pour macOS uniquement."
        exit 1
    fi
    
    # Get macOS version (e.g., 11.0, 12.0, 13.0, 14.0)
    macos_version=$(sw_vers -productVersion | cut -d '.' -f 1)
    
    if [[ "$macos_version" -lt 11 ]]; then
        print_error "macOS 11 (Big Sur) ou supérieur requis."
        print_error "Version actuelle: $(sw_vers -productVersion)"
        exit 1
    fi
    
    print_success "macOS $(sw_vers -productVersion) - OK"
}

# --- Check CPU architecture ---
check_architecture() {
    print_step "Vérification de l'architecture CPU..."
    
    arch=$(uname -m)
    
    if [[ "$arch" == "arm64" ]]; then
        print_success "Apple Silicon (ARM64) détecté - Optimal"
    elif [[ "$arch" == "x86_64" ]]; then
        print_warning "Intel (x86_64) détecté - Compatible via Rosetta 2"
    else
        print_error "Architecture non supportée: $arch"
        exit 1
    fi
}

# --- Check Docker Desktop ---
check_docker() {
    print_step "Vérification de Docker Desktop..."
    
    # Check if docker command exists
    if ! command -v docker &> /dev/null; then
        print_error "Docker n'est pas installé."
        echo ""
        echo -e "${YELLOW}📥 Téléchargez Docker Desktop:${NC}"
        echo "   https://www.docker.com/products/docker-desktop/"
        echo ""
        echo "   Après installation:"
        echo "   1. Lancez Docker Desktop"
        echo "   2. Attendez que l'icône Docker (🐳) soit stable dans la barre de menu"
        echo "   3. Relancez ce script: ./install-aitao.sh"
        echo ""
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker Desktop n'est pas démarré."
        echo ""
        echo -e "${YELLOW}🐳 Démarrez Docker Desktop:${NC}"
        echo "   1. Ouvrez Docker Desktop depuis Applications"
        echo "   2. Attendez que l'icône soit stable (pas d'animation)"
        echo "   3. Relancez ce script: ./install-aitao.sh"
        echo ""
        
        # Try to open Docker Desktop
        if [[ -d "/Applications/Docker.app" ]]; then
            echo "   Tentative d'ouverture automatique..."
            open -a Docker
            echo "   Patientez quelques secondes puis relancez le script."
        fi
        exit 1
    fi
    
    # Check docker compose (v2)
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose V2 non disponible."
        echo "   Mettez à jour Docker Desktop vers la dernière version."
        exit 1
    fi
    
    docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
    print_success "Docker $docker_version - OK"
}

# --- Create configuration directories ---
create_directories() {
    print_step "Création des répertoires de configuration..."
    
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOGS_DIR"
    
    print_success "Répertoires créés dans $AITAO_HOME"
}

# --- Setup environment file ---
setup_env_file() {
    print_step "Configuration de l'environnement..."
    
    ENV_FILE="${SCRIPT_DIR}/.env"
    
    if [[ -f "$ENV_FILE" ]]; then
        print_warning "Fichier .env existant conservé"
    else
        if [[ -f "${SCRIPT_DIR}/.env.template" ]]; then
            cp "${SCRIPT_DIR}/.env.template" "$ENV_FILE"
            
            # Generate random Meilisearch master key
            MEILI_KEY=$(openssl rand -hex 16)
            sed -i '' "s/MEILISEARCH_MASTER_KEY=.*/MEILISEARCH_MASTER_KEY=${MEILI_KEY}/" "$ENV_FILE"
            
            print_success "Fichier .env créé avec clé Meilisearch générée"
        else
            print_warning "Template .env.template non trouvé, utilisation des valeurs par défaut"
        fi
    fi
}

# --- Pull Docker images ---
pull_images() {
    print_step "Téléchargement des images Docker (peut prendre quelques minutes)..."
    
    cd "$SCRIPT_DIR"
    
    # Pull images in parallel for faster download
    docker compose pull --quiet 2>/dev/null || docker compose pull
    
    print_success "Images téléchargées"
}

# --- Start services ---
start_services() {
    print_step "Démarrage des services..."
    
    cd "$SCRIPT_DIR"
    
    # Start all services
    docker compose up -d --remove-orphans
    
    print_success "Services démarrés"
}

# --- Wait for services to be healthy ---
wait_for_services() {
    print_step "Attente de la disponibilité des services..."
    
    local max_wait=120  # 2 minutes max
    local waited=0
    local interval=5
    
    while [[ $waited -lt $max_wait ]]; do
        # Check if all services are healthy
        local healthy=true
        
        # Check Ollama
        if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            healthy=false
        fi
        
        # Check Meilisearch
        if ! curl -s http://localhost:7700/health > /dev/null 2>&1; then
            healthy=false
        fi
        
        # Check AiTao API (may take longer to start)
        if ! curl -s http://localhost:8200/api/health > /dev/null 2>&1; then
            healthy=false
        fi
        
        if $healthy; then
            print_success "Tous les services sont prêts"
            return 0
        fi
        
        echo -n "."
        sleep $interval
        waited=$((waited + interval))
    done
    
    echo ""
    print_warning "Certains services mettent plus de temps à démarrer"
    print_warning "Vérifiez les logs avec: docker compose logs -f"
    return 1
}

# --- Print success message ---
print_success_message() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}            ${BOLD}✅ Installation terminée avec succès !${NC}           ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}🌐 Accès aux services:${NC}"
    echo ""
    echo -e "   ${BLUE}• Interface Web (Open WebUI):${NC}"
    echo "     http://localhost:3000"
    echo ""
    echo -e "   ${BLUE}• API AiTao:${NC}"
    echo "     http://localhost:8200"
    echo "     http://localhost:8200/docs  (documentation)"
    echo ""
    echo -e "   ${BLUE}• Meilisearch:${NC}"
    echo "     http://localhost:7700"
    echo ""
    echo -e "${BOLD}📖 Commandes utiles:${NC}"
    echo ""
    echo "   Voir les logs:           docker compose logs -f"
    echo "   Arrêter les services:    docker compose down"
    echo "   Redémarrer:              docker compose restart"
    echo "   Voir l'état:             docker compose ps"
    echo ""
    echo -e "${BOLD}📁 Données stockées dans:${NC} ${AITAO_HOME}"
    echo ""
    echo -e "${YELLOW}💡 Premier démarrage:${NC}"
    echo "   Ouvrez http://localhost:3000 dans votre navigateur"
    echo "   Le premier chargement peut prendre 1-2 minutes."
    echo ""
}

# --- Main ---
main() {
    print_banner
    
    check_macos_version
    check_architecture
    check_docker
    create_directories
    setup_env_file
    pull_images
    start_services
    wait_for_services
    
    print_success_message
}

# Run main function
main "$@"
