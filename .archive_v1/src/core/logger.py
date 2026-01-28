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

def get_logger(name, log_filename=None):
    """
    Get a configured logger for a module.
    
    Args:
        name (str): Logger name (typically module path like 'web_search', 'sync_agent')
        log_filename (str, optional): Custom log filename. If None, derives from name.
                                     Example: 'web_search.log', 'api.log', 'sync.log'
    
    Returns:
        logging.Logger: Configured logger with file and console handlers
    
    Example:
        >>> logger = get_logger("web_search", "web_search.log")
        >>> logger.info("Search completed")
    """
    logger = logging.getLogger(name)
    
    # Éviter d'ajouter plusieurs handlers si le logger existe déjà
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Determine log filename
        if log_filename is None:
            # Extract last part of name: 'src.core.web_search' → 'web_search.log'
            module_name = name.split('.')[-1]
            log_filename = f"{module_name}.log"
        
        # Handler fichier via PathManager
        try:
            logs_dir = path_manager.get_logs_dir()
            log_file = logs_dir / log_filename
        except Exception as e:
            # Fallback très dégradé si path_manager échoue au boot
            print(f"⚠️ Logger: PathManager unavailable ({e}), using fallback")
            log_file = log_filename

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
