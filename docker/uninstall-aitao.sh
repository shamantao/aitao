#!/bin/bash

# =============================================================================
# ☯️ AI Tao - macOS Uninstallation Script
# =============================================================================
#
# This script completely removes AiTao from your system:
# - Stops and removes all Docker containers
# - Deletes Docker volumes (Ollama models, Meilisearch data, etc.)
# - Removes configuration files
# - Optionally removes Docker images
#
# Usage:
#   ./uninstall-aitao.sh
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

# --- Helper functions ---
print_banner() {
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║${NC}            ${BOLD}☯️  AI Tao - Désinstallation${NC}                    ${RED}║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
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

# --- Confirmation prompt ---
confirm() {
    local message="$1"
    local default="${2:-n}"
    
    if [[ "$default" == "y" ]]; then
        prompt="[O/n]"
    else
        prompt="[o/N]"
    fi
    
    echo -e -n "${YELLOW}$message${NC} $prompt "
    read -r response
    
    case "$response" in
        [oOyY]|[oOyY][uUeE][iIsS])
            return 0
            ;;
        [nN]|[nN][oO][nN])
            return 1
            ;;
        "")
            if [[ "$default" == "y" ]]; then
                return 0
            else
                return 1
            fi
            ;;
        *)
            return 1
            ;;
    esac
}

# --- Stop and remove containers ---
stop_containers() {
    print_step "Arrêt des containers Docker..."
    
    if [[ -f "${SCRIPT_DIR}/docker-compose.yml" ]]; then
        cd "$SCRIPT_DIR"
        
        # Check if any containers are running
        if docker compose ps -q 2>/dev/null | grep -q .; then
            docker compose down 2>/dev/null || true
            print_success "Containers arrêtés"
        else
            print_warning "Aucun container en cours d'exécution"
        fi
    else
        # Try to stop containers by name if docker-compose.yml not found
        for container in aitao-backend aitao-ollama aitao-meilisearch aitao-webui; do
            if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                docker stop "$container" 2>/dev/null || true
                docker rm "$container" 2>/dev/null || true
            fi
        done
        print_success "Containers arrêtés"
    fi
}

# --- Remove Docker volumes ---
remove_volumes() {
    print_step "Suppression des volumes Docker (données Ollama, Meilisearch, etc.)..."
    
    local volumes=(
        "aitao_ollama_data"
        "aitao_meilisearch_data"
        "aitao_openwebui_data"
        "aitao_backend_data"
        "aitao_backend_logs"
    )
    
    local removed=0
    for volume in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            docker volume rm "$volume" 2>/dev/null || true
            ((removed++))
        fi
    done
    
    if [[ $removed -gt 0 ]]; then
        print_success "$removed volume(s) supprimé(s)"
    else
        print_warning "Aucun volume AiTao trouvé"
    fi
}

# --- Remove configuration directory ---
remove_config() {
    print_step "Suppression de la configuration utilisateur..."
    
    if [[ -d "$AITAO_HOME" ]]; then
        rm -rf "$AITAO_HOME"
        print_success "Répertoire $AITAO_HOME supprimé"
    else
        print_warning "Répertoire $AITAO_HOME non trouvé"
    fi
}

# --- Remove Docker images ---
remove_images() {
    print_step "Suppression des images Docker..."
    
    local images=(
        "docker-aitao-backend"
        "aitao"
        "getmeili/meilisearch"
        "ollama/ollama"
        "ghcr.io/open-webui/open-webui"
    )
    
    local removed=0
    for image in "${images[@]}"; do
        # Find all tags for this image
        local image_ids
        image_ids=$(docker images --format '{{.ID}} {{.Repository}}' | grep "$image" | awk '{print $1}' | sort -u)
        
        for id in $image_ids; do
            docker rmi "$id" 2>/dev/null || true
            ((removed++))
        done
    done
    
    if [[ $removed -gt 0 ]]; then
        print_success "$removed image(s) supprimée(s)"
    else
        print_warning "Aucune image AiTao trouvée"
    fi
}

# --- Remove Docker network ---
remove_network() {
    if docker network ls --format '{{.Name}}' | grep -q "^aitao-network$"; then
        docker network rm aitao-network 2>/dev/null || true
        print_success "Réseau Docker aitao-network supprimé"
    fi
}

# --- Print summary ---
print_summary() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}           ${BOLD}✅ AiTao désinstallé avec succès !${NC}               ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Éléments supprimés:${NC}"
    echo "   • Containers Docker (aitao-backend, ollama, meilisearch, webui)"
    echo "   • Volumes Docker (modèles Ollama, données Meilisearch)"
    echo "   • Configuration utilisateur (~/.aitao)"
    if [[ "$REMOVE_IMAGES" == "true" ]]; then
        echo "   • Images Docker"
    fi
    echo ""
    echo -e "${YELLOW}💡 Note:${NC} Docker Desktop reste installé."
    echo "   Pour le supprimer, utilisez le désinstalleur officiel Docker."
    echo ""
}

# --- Main ---
main() {
    print_banner
    
    echo -e "${BOLD}Cette opération va supprimer:${NC}"
    echo "   • Tous les containers AiTao"
    echo "   • Les modèles Ollama téléchargés"
    echo "   • Les données Meilisearch indexées"
    echo "   • Vos conversations Open WebUI"
    echo "   • La configuration dans ~/.aitao"
    echo ""
    
    if ! confirm "Êtes-vous sûr de vouloir désinstaller AiTao ?"; then
        echo ""
        print_warning "Désinstallation annulée."
        exit 0
    fi
    
    echo ""
    
    # Stop containers
    stop_containers
    
    # Remove volumes (contains Ollama models, Meilisearch data, etc.)
    if confirm "Supprimer les volumes Docker (modèles Ollama, données Meilisearch) ?"; then
        remove_volumes
    else
        print_warning "Volumes conservés"
    fi
    
    # Remove config directory
    if confirm "Supprimer la configuration utilisateur (~/.aitao) ?"; then
        remove_config
    else
        print_warning "Configuration conservée"
    fi
    
    # Remove Docker images (optional, takes more space but faster reinstall)
    REMOVE_IMAGES="false"
    if confirm "Supprimer les images Docker (libère ~5GB, mais réinstallation plus longue) ?"; then
        REMOVE_IMAGES="true"
        remove_images
    else
        print_warning "Images Docker conservées (réinstallation plus rapide)"
    fi
    
    # Remove network
    remove_network
    
    print_summary
}

# Run main function
main "$@"
