# Configuración del logger
import os
import logging
from logging.handlers import RotatingFileHandler

# Clase de configuración
class Config:
    
    """ Valores absolutos de los diferentes archivos creados e inlcuyendo la animacion  """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DIR_LOGS = os.path.join(BASE_DIR, "Registros")
    LOG_FILE = "Registro_Youtube.log"
    ANIMATION_DURATION = 300
    ICON_DIR = os.path.join(BASE_DIR, "icons")
    ICON_YOUTUBE = "icono_youtube.png"
    ICON_DOWNLOAD = "icono_descarga.png"
    ICON_CANCEL = "icono_cancelar.png"
    ICON_FOLDER = "icono_carpeta.png"
    MAX_LOG_SIZE = 1024 * 1024  # 1MB
    NUM_LOG_BACKUPS = 5
    
def configure_logger():
    """ configuracion del logger"""
    logger = logging.getLogger('YouTubeDownloader')
    logger.setLevel(logging.INFO)
    os.makedirs(Config.DIR_LOGS, exist_ok=True)
    handler = RotatingFileHandler(os.path.join(Config.DIR_LOGS, Config.LOG_FILE), 
                                maxBytes=Config.MAX_LOG_SIZE, 
                                backupCount=Config.NUM_LOG_BACKUPS, 
                                encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger

logger = configure_logger()
