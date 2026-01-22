import sys
import logging
import os
from logging.handlers import RotatingFileHandler

# Import PathManager with fallback logic similar to other files
try:
    from src.core.path_manager import path_manager
except ImportError:
    try:
        from core.path_manager import path_manager
    except ImportError:
        # Emergency fallback relative path
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from src.core.path_manager import path_manager

# Configuration du format de log
log_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Fonction pour obtenir un logger configuré
def get_logger(name):
    logger = logging.getLogger(name)
    
    # Éviter d'ajouter plusieurs handlers si le logger existe déjà
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Handler fichier via PathManager
        try:
            logs_dir = path_manager.get_logs_dir()
            log_file = logs_dir / "web_search.log"
        except Exception:
            # Fallback très dégradé si path_manager échoue au boot
            log_file = "web_search.log"

        file_handler = RotatingFileHandler(str(log_file), maxBytes=1024*1024, backupCount=5)
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)
        
        # Handler console (optionnel, pour voir dans le terminal aussi)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)
        
        # Désactiver la propagation pour éviter les doublons dans les logs Uvicorn
        logger.propagate = False
        
    return logger
