#!/usr/bin/env bash

# =============================================================================
# ☯️ AI Tao — Interface de commande
# =============================================================================
#
# DÉMARRAGE RAPIDE
#   ./aitao.sh start             Démarrer tous les services
#   ./aitao.sh dashboard         État en un coup d'œil
#   ./aitao.sh stop              Arrêter tous les services
#
# SITUATIONS COURANTES
#   Fichiers en échec :
#     ./aitao.sh queue list failed    Voir quels fichiers ont échoué
#     ./aitao.sh queue retry          Remettre les échecs en file d'attente
#     ./aitao.sh start                Relancer le traitement
#
#   Vectorisation incomplète (LanceDB < Meilisearch) :
#     ./aitao.sh scan run             Re-scanner les dossiers
#     ./aitao.sh start                Compléter la vectorisation
#
#   Configuration et diagnostic :
#     ./aitao.sh config show          Voir la configuration active
#     ./aitao.sh config validate      Vérifier la configuration
#     ./aitao.sh status               État des services (résumé)
#     ./aitao.sh version              Version installée
#
# GROUPES DE COMMANDES (./aitao.sh <groupe> --help pour le détail)
#   start / stop / restart    Contrôle des services
#   dashboard                 Vue d'ensemble complète
#   queue                     File de traitement (list, retry, status...)
#   scan                      Scan des dossiers configurés
#   ms                        Meilisearch — recherche texte intégral
#   db                        LanceDB — vecteurs sémantiques
#   models                    Modèles Ollama/MLX
#   config                    Configuration
#   worker                    Worker indépendant
#   extract                   Extraction de texte
#   index                     Pipeline d'indexation
#   search                    Recherche hybride
#   api                       Serveur API
#
# DÉVELOPPEMENT
#   ./aitao.sh test            Tests unitaires
#   ./aitao.sh test -v         Tests unitaires (verbose)
#   ./aitao.sh validate        Pipeline complet (tests + e2e + fonctionnel)
#   ./aitao.sh contracts       Vérification des contrats d'architecture
#   ./aitao.sh benchmark       Benchmark MLX vs Ollama
#
# =============================================================================
#clear
set -euo pipefail

# --- Prevent OpenMP library conflicts (PyTorch + NumPy/scikit-learn) ---
export KMP_DUPLICATE_LIB_OK=TRUE

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
SRC_DIR="$SCRIPT_DIR/src"

# Colors for minimal output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# --- Check virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo ""
    echo "Setup with:"
    echo "  cd $SCRIPT_DIR"
    echo "  uv venv && uv pip install -e ."
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo -e "${RED}❌ Python not found in venv${NC}"
    exit 1
fi

# --- Validate (full pipeline) ---
if [ "${1:-}" = "validate" ]; then
    echo "🔍 Running full validation pipeline..."

    echo "✅ Step 1: Architecture contracts"
    "$PYTHON" "$SCRIPT_DIR/scripts/check_contracts.py" --stats
    
    echo ""
    echo "✅ Step 2: Unit tests"
    "$PYTHON" -m pytest "$SCRIPT_DIR/tests/unit" -v

    echo "✅ Step 3: E2E tests"
    "$PYTHON" -m pytest "$SCRIPT_DIR/tests/e2e" -v

    echo "✅ Step 4: Functional check (models status)"
    "$PYTHON" -m src.cli.main models status > /dev/null

    echo -e "${GREEN}✓ Validation complete${NC}"
    exit 0
fi

# --- Contracts check (architecture validation) ---
if [ "${1:-}" = "contracts" ]; then
    shift
    "$PYTHON" "$SCRIPT_DIR/scripts/check_contracts.py" "$@"
    exit $?
fi

# --- Benchmark (MLX vs Ollama) ---
if [ "${1:-}" = "benchmark" ]; then
    shift
    "$PYTHON" "$SCRIPT_DIR/scripts/benchmark_backends.py" "$@"
    exit $?
fi

# --- help / --help : afficher l'aide principale ---
if [ "${1:-}" = "help" ] || [ "${1:-}" = "--help" ]; then
    cd "$SRC_DIR"
    exec "$PYTHON" -m cli --help
fi

# --- <groupe> help : traduire en <groupe> --help ---
# Groupes avec sous-commandes : queue, scan, worker, ms, db, config,
#                               models, search, index, extract, lifecycle, api
_GROUPS="queue scan worker ms db config models search index extract lifecycle api license"
if [ -n "${1:-}" ] && [ -n "${2:-}" ] && [ "${2:-}" = "help" ]; then
    _GROUP="${1}"
    for _g in $_GROUPS; do
        if [ "$_GROUP" = "$_g" ]; then
            cd "$SRC_DIR"
            exec "$PYTHON" -m cli "$_GROUP" --help
        fi
    done
fi

# --- Delegate to Python CLI ---
# Pass original working directory for file path resolution
export AITAO_ORIG_PWD="$(pwd)"
cd "$SRC_DIR"
exec "$PYTHON" -m cli "$@"
